"""PFC Reference Browse Tool - Navigate syntax elements and model properties."""

from typing import Any, cast

from fastmcp import FastMCP
from pydantic import Field

from pfc_mcp.contracts import build_docs_data, build_error, build_ok
from pfc_mcp.knowledge.references import ReferenceLoader
from pfc_mcp.utils import normalize_input


def register(mcp: FastMCP) -> None:
    """Register pfc_browse_reference tool with the MCP server."""

    @mcp.tool()
    def pfc_browse_reference(
        topic: str | None = Field(
            None,
            description=(
                "Reference topic to browse (space-separated path). Examples:\n"
                "- None or '': List all reference categories\n"
                "- 'contact-models': List all contact models\n"
                "- 'contact-models linear': Linear model properties\n"
                "- 'range-elements': Range elements overview (24 elements)\n"
                "- 'range-elements position': Position range syntax\n"
                "- 'plot-items': Plot item types (ball, wall, contact keywords)\n"
                "- 'plot-items ball': Ball overview + available sub-topics\n"
                "- 'plot-items ball color-by': Ball color-by keyword details"
            ),
        ),
    ) -> dict[str, Any]:
        """Browse PFC reference documentation (syntax elements, model properties).

        References are language elements used within commands, not standalone commands.

        Navigation levels:
        - No topic: All reference categories
        - Category (e.g., "contact-models"): List items in category
        - Full path (e.g., "contact-models linear"): Full documentation

        When to use:
        - Need contact model property names (kn, ks, fric, pb_*)
        - Need range filtering syntax (position, cylinder, group, id)
        - Need plot item configuration (color-by, cut plane, transparency, legend)
        - Setting up "contact cmat add model ... property ..." commands
        - Using range filters in any PFC command
        - Configuring "plot item create" commands

        Related tools:
        - pfc_browse_commands: Command syntax (e.g., "ball create")
        - pfc_query_command: Search commands by keywords
        """
        topic_str = normalize_input(topic, lowercase=True)

        if not topic_str:
            return build_ok(_browse_references_root())

        parts = topic_str.split()
        category = parts[0]

        if len(parts) == 1:
            payload = _browse_category(category)
        elif len(parts) == 2:
            payload = _browse_item(category, parts[1])
        else:
            # 3+ parts: category + item + sub-item (remaining parts joined)
            payload = _browse_sub_item(category, parts[1], " ".join(parts[2:]))
        return _wrap_payload(payload)


def _browse_references_root() -> dict[str, Any]:
    refs_index = ReferenceLoader.load_index()
    categories = refs_index.get("categories", {})
    category_items: list[dict[str, Any]] = []

    for category_name, category_data in categories.items():
        items = ReferenceLoader.get_item_list(category_name)
        category_items.append(
            {
                "name": category_name,
                "description": category_data.get("description", ""),
                "item_count": len(items),
            }
        )

    return build_docs_data(
        source="reference",
        action="browse",
        entries=category_items,
        summary={"count": len(category_items)},
    )


def _browse_category(category: str) -> dict[str, Any]:
    refs_index = ReferenceLoader.load_index()
    categories = refs_index.get("categories", {})

    if category not in categories:
        return {
            "source": "reference",
            "action": "browse",
            "error": {
                "code": "category_not_found",
                "message": f"Category '{category}' not found.",
            },
            "input": {"category": category},
            "available_categories": sorted(categories.keys()),
        }

    cat_index = cast(dict[str, Any], ReferenceLoader.load_category_index(category))
    if not cat_index:
        return {
            "source": "reference",
            "action": "browse",
            "error": {
                "code": "category_index_not_found",
                "message": f"Category index not found for '{category}'.",
            },
            "input": {"category": category},
        }
    raw_items = ReferenceLoader.get_item_list(category)
    items = []
    for item in raw_items:
        entry: dict[str, Any] = {
            "name": item.get("name", ""),
            "description": item.get("description", ""),
        }
        if "full_name" in item:
            entry["full_name"] = item["full_name"]
        if "category" in item:
            entry["category"] = item["category"]
        if "common_use" in item:
            entry["common_use"] = item["common_use"]
        items.append(entry)

    return build_docs_data(
        source="reference",
        action="browse",
        entries=items,
        summary={
            "count": len(items),
            "category": category,
        },
    )


def _browse_item(category: str, item: str) -> dict[str, Any]:
    refs_index = ReferenceLoader.load_index()
    categories = refs_index.get("categories", {})
    if category not in categories:
        return {
            "source": "reference",
            "action": "browse",
            "error": {
                "code": "category_not_found",
                "message": f"Category '{category}' not found.",
            },
            "input": {"category": category, "item": item},
            "available_categories": sorted(categories.keys()),
        }

    item_doc = ReferenceLoader.load_item_doc(category, item)

    if not item_doc:
        items = ReferenceLoader.get_item_list(category)
        available = [i.get("name", "") for i in items]
        return {
            "source": "reference",
            "action": "browse",
            "error": {
                "code": "item_not_found",
                "message": f"Item '{item}' not found in '{category}'.",
            },
            "input": {"category": category, "item": item},
            "available_items": available,
        }

    # Directory-based item: return overview with sub-item list instead of full doc
    if ReferenceLoader.is_directory_item(category, item):
        sub_items = item_doc.get("sub_items", [])
        overview: dict[str, Any] = {
            "category": category,
            "item": item,
            "description": item_doc.get("description", ""),
            "base_syntax": item_doc.get("base_syntax", ""),
        }
        if "basic_keywords" in item_doc:
            overview["basic_keywords"] = item_doc["basic_keywords"]
        if "common_usage_patterns" in item_doc:
            overview["common_usage_patterns"] = item_doc["common_usage_patterns"]
        overview["sub_items"] = [
            {"name": s["name"], "description": s.get("description", "")}
            for s in sub_items
        ]
        return build_docs_data(
            source="reference",
            action="browse",
            entries=[overview],
            summary={
                "count": 1,
                "sub_item_count": len(sub_items),
                "hint": f"Use pfc_browse_reference('{category} {item} <sub_item>') for details",
            },
        )

    return build_docs_data(
        source="reference",
        action="browse",
        entries=[
            {
                "category": category,
                "item": item,
                "doc": item_doc,
            }
        ],
        summary={"count": 1},
    )


def _browse_sub_item(category: str, item: str, sub_item: str) -> dict[str, Any]:
    refs_index = ReferenceLoader.load_index()
    categories = refs_index.get("categories", {})
    if category not in categories:
        return {
            "source": "reference",
            "action": "browse",
            "error": {
                "code": "category_not_found",
                "message": f"Category '{category}' not found.",
            },
            "input": {"category": category, "item": item, "sub_item": sub_item},
            "available_categories": sorted(categories.keys()),
        }

    if not ReferenceLoader.is_directory_item(category, item):
        return {
            "source": "reference",
            "action": "browse",
            "error": {
                "code": "no_sub_items",
                "message": f"Item '{item}' in '{category}' does not have sub-items.",
            },
            "input": {"category": category, "item": item, "sub_item": sub_item},
        }

    sub_doc = ReferenceLoader.load_sub_item_doc(category, item, sub_item)
    if not sub_doc:
        item_doc = ReferenceLoader.load_item_doc(category, item)
        available = [s["name"] for s in (item_doc or {}).get("sub_items", [])]
        return {
            "source": "reference",
            "action": "browse",
            "error": {
                "code": "sub_item_not_found",
                "message": f"Sub-item '{sub_item}' not found in '{category} {item}'.",
            },
            "input": {"category": category, "item": item, "sub_item": sub_item},
            "available_sub_items": available,
        }

    return build_docs_data(
        source="reference",
        action="browse",
        entries=[
            {
                "category": category,
                "item": item,
                "sub_item": sub_item,
                "doc": sub_doc,
            }
        ],
        summary={"count": 1},
    )


def _wrap_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if "error" in payload:
        err = payload.get("error") or {}
        details = {k: v for k, v in payload.items() if k != "error"}
        return build_error(
            code=str(err.get("code") or "browse_error"),
            message=str(err.get("message") or "Browse failed"),
            details=details or None,
        )
    return build_ok(payload)
