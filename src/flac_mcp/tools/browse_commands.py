"""FLAC Command Browse Tool - Navigate and retrieve command documentation."""

from typing import Any

from fastmcp import FastMCP
from pydantic import Field

from flac_mcp.contracts import build_docs_data, build_ok, wrap_payload
from flac_mcp.knowledge.commands import CommandLoader
from flac_mcp.knowledge.compatibility import (
    FLACProduct,
    compatibility_summary,
    is_compatible_with_product,
    is_product_version_applicable,
    normalize_product,
    product_version_error_payload,
)
from flac_mcp.utils import CommandDocVersion, normalize_command_doc_version, normalize_input


def register(mcp: FastMCP) -> None:
    """Register flac_browse_commands tool with the MCP server."""

    @mcp.tool()
    def flac_browse_commands(
        command: str | None = Field(
            None,
            description=(
                "FLAC command to browse (space-separated, matching FLAC syntax). Examples:\n"
                "- None or '': List all command categories\n"
                "- 'zone': List all zone commands\n"
                "- 'zone cmodel assign': Get zone cmodel assignment documentation\n"
                "- 'structure': List all structural-element commands\n"
                "- 'model solve': Get model solve command documentation"
            ),
        ),
        version: CommandDocVersion = Field(
            CommandDocVersion.V9_0,
            description=(
                "FLAC documentation version to browse. Defaults to 9.0 "
                "(bundled 9.x baseline; covers FLAC continuum + "
                "structural-element commands). Use 9.1-9.7 for newer 9.x command "
                "differences; 9.4+ resolves against the nearest bundled 9.3-era "
                "baseline. Use 7.0/6.0 for legacy FLAC3D documentation."
            ),
        ),
        product: FLACProduct = Field(
            FLACProduct.ANY,
            description=(
                "FLAC product/dimension filter. Use 'flac2d' to hide docs marked 3D-only, "
                "'flac3d' to hide docs marked 2D-only, or 'any' for no product filter."
            ),
        ),
    ) -> dict[str, Any]:
        """Browse FLAC command documentation by path (like glob + cat).

        Navigation levels:
        - No command: All command categories overview
        - Category only (e.g., "zone"): List commands in category
        - Full command (e.g., "zone cmodel assign"): Full documentation

        When to use:
        - You know the command category or exact command
        - You want to explore available commands

        Related tools:
        - flac_query_command: Search commands by keywords (when path unknown)
        - flac_browse_reference: Browse reference docs (e.g., "constitutive-models mohr-coulomb")
        """
        cmd = normalize_input(command, lowercase=True)
        version_value = normalize_command_doc_version(version)
        product_value = normalize_product(product)
        if not is_product_version_applicable(product_value, version_value):
            return wrap_payload(product_version_error_payload("commands", "browse", product_value, version_value))

        if not cmd:
            return build_ok(_browse_root(version_value, product_value))

        parts = cmd.split()

        if len(parts) == 1:
            payload = _browse_category(parts[0], version_value, product_value)
        else:
            category = parts[0]
            command_name = " ".join(parts[1:])
            payload = _browse_command(category, command_name, version_value, product_value)
        return wrap_payload(payload)


def _iter_available_category_commands(
    category: str,
    version: str,
    product: str = FLACProduct.ANY.value,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Return commands that are available in the requested version."""
    index = CommandLoader.load_index()
    category_data = index.get("categories", {}).get(category, {})
    available: list[tuple[dict[str, Any], dict[str, Any]]] = []

    for cmd_meta in category_data.get("commands", []):
        try:
            cmd_doc = CommandLoader.load_command_doc(category, cmd_meta.get("name", ""), version)
        except KeyError:
            # Doc has no entry for this version — not available here, skip.
            continue
        if cmd_doc and cmd_doc.get("available") is not False and is_compatible_with_product(cmd_doc, product):
            available.append((cmd_meta, cmd_doc))

    return available


def _browse_root(version: str, product: str) -> dict[str, Any]:
    """Level 0: Return overview of all command categories."""
    index = CommandLoader.load_index()
    categories = index.get("categories", {})
    category_items: list[dict[str, Any]] = []
    total_commands = 0

    for category_name, category_data in categories.items():
        available_commands = _iter_available_category_commands(category_name, version, product)
        command_count = len(available_commands)
        total_commands += command_count
        category_items.append(
            {
                "name": category_name,
                "description": category_data.get("description", ""),
                "command_count": command_count,
            }
        )

    return build_docs_data(
        source="commands",
        action="browse",
        entries=category_items,
        summary={
            "count": len(category_items),
            "total_commands": total_commands,
            "version": version,
            "product": product,
        },
    )


def _browse_category(category: str, version: str, product: str) -> dict[str, Any]:
    """Level 1: Return list of commands in a category."""
    index = CommandLoader.load_index()
    categories = index.get("categories", {})

    if category not in categories:
        return {
            "source": "commands",
            "action": "browse",
            "error": {
                "code": "category_not_found",
                "message": f"Category '{category}' not found.",
            },
            "input": {"category": category, "version": version, "product": product},
            "available_categories": sorted(categories.keys()),
        }

    cat_data = categories[category]
    command_items: list[dict[str, Any]] = []
    for cmd, cmd_doc in _iter_available_category_commands(category, version, product):
        command_items.append(
            {
                "name": cmd.get("name", ""),
                "short_description": cmd.get("short_description", ""),
                "syntax": cmd_doc.get("syntax"),
                "python_available": bool(cmd.get("python_available", False)),
                "dimension": compatibility_summary(cmd_doc, product)["dimension"],
            }
        )

    return build_docs_data(
        source="commands",
        action="browse",
        entries=command_items,
        summary={
            "count": len(command_items),
            "category": category,
            "description": cat_data.get("description", ""),
            "version": version,
            "product": product,
        },
    )


def _browse_command(category: str, command_name: str, version: str, product: str) -> dict[str, Any]:
    """Level 2: Return full documentation for a specific command."""
    # JSON filenames use dash as sub-command separator (e.g. edge-create,
    # cmat-add, scalar-create) while FLAC syntax separates them with spaces.
    # Accept either form on input.
    try:
        cmd_doc = CommandLoader.load_command_doc(category, command_name, version)
        if not cmd_doc and " " in command_name:
            cmd_doc = CommandLoader.load_command_doc(category, command_name.replace(" ", "-"), version)
    except KeyError:
        # Command exists but has no entry for this version. Same structured
        # error as the available=false path, reporting the versions it does
        # support.
        available_versions: list[str] = []
        for probe in ("9.7", "9.6", "9.5", "9.4", "9.3", "9.2", "9.1", "9.0", "7.0", "6.0"):
            for name in (command_name, command_name.replace(" ", "-")):
                try:
                    probe_doc = CommandLoader.load_command_doc(category, name, probe)
                except KeyError:
                    continue
                if probe_doc:
                    available_versions = probe_doc.get("versions", [])
                    break
            if available_versions:
                break
        return {
            "source": "commands",
            "action": "browse",
            "error": {
                "code": "command_unavailable_for_version",
                "message": f"Command '{command_name}' is not available in FLAC {version}.",
            },
            "input": {"category": category, "command": command_name, "version": version, "product": product},
            "available_versions": available_versions,
        }

    if not cmd_doc:
        index = CommandLoader.load_index()
        categories = index.get("categories", {})

        if category not in categories:
            return {
                "source": "commands",
                "action": "browse",
                "error": {
                    "code": "category_not_found",
                    "message": f"Category '{category}' not found.",
                },
                "input": {"category": category, "command": command_name, "version": version, "product": product},
                "available_categories": sorted(categories.keys()),
            }

        available_cmds = [
            cmd_meta.get("name") for cmd_meta, _cmd_doc in _iter_available_category_commands(category, version, product)
        ]
        return {
            "source": "commands",
            "action": "browse",
            "error": {
                "code": "command_not_found",
                "message": f"Command '{command_name}' not found in '{category}'.",
            },
            "input": {"category": category, "command": command_name, "version": version, "product": product},
            "available_commands": available_cmds,
        }

    if cmd_doc.get("available") is False:
        return {
            "source": "commands",
            "action": "browse",
            "error": {
                "code": "command_unavailable_for_version",
                "message": f"Command '{command_name}' is not available in FLAC {version}.",
            },
            "input": {"category": category, "command": command_name, "version": version, "product": product},
            "available_versions": cmd_doc.get("versions", []),
        }

    if not is_compatible_with_product(cmd_doc, product):
        return {
            "source": "commands",
            "action": "browse",
            "error": {
                "code": "command_unavailable_for_product",
                "message": f"Command '{command_name}' is not compatible with product filter '{product}'.",
            },
            "input": {"category": category, "command": command_name, "version": version, "product": product},
            "compatibility": compatibility_summary(cmd_doc, product),
        }

    return build_docs_data(
        source="commands",
        action="browse",
        entries=[
            {
                "category": category,
                "command": command_name,
                "version": version,
                "compatibility": compatibility_summary(cmd_doc, product),
                "doc": cmd_doc,
            }
        ],
        summary={"count": 1, "version": version, "product": product},
    )
