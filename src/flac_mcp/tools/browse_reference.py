"""FLAC Reference Browse Tool - Navigate syntax elements and model properties."""

from typing import Any, cast

from fastmcp import FastMCP
from pydantic import Field

from flac_mcp.contracts import build_docs_data, build_error, build_ok
from flac_mcp.knowledge.compatibility import (
    FLACProduct,
    compatibility_summary,
    is_compatible_with_product,
    is_product_version_applicable,
    normalize_product,
    product_version_error_payload,
)
from flac_mcp.knowledge.references import ReferenceLoader
from flac_mcp.utils import (
    CommandDocVersion,
    normalize_command_doc_version,
    normalize_input,
)


def register(mcp: FastMCP) -> None:
    """Register flac_browse_reference tool with the MCP server."""

    @mcp.tool()
    def flac_browse_reference(
        topic: str | None = Field(
            None,
            description=(
                "Reference topic to browse (space-separated path). Examples:\n"
                "- None or '': List all reference categories\n"
                "- 'constitutive-models': List all FLAC zone material models\n"
                "- 'constitutive-models mohr-coulomb': Mohr-Coulomb zone "
                "property keywords (for 'zone property')\n"
                "- 'range-elements': Range elements overview (24 elements)\n"
                "- 'range-elements position': Position range syntax\n"
                "- 'plot-items zone color-by': Zone plot coloring keywords"
            ),
        ),
        version: CommandDocVersion = Field(
            CommandDocVersion.V7_0,
            description=(
                "FLAC documentation version (6.0/7.0/9.0). Defaults to 7.0. "
                "constitutive-models and range-elements are version-agnostic."
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
        """Browse FLAC reference documentation (syntax elements, model properties).

        References are language elements used within commands, not standalone commands.

        Navigation levels:
        - No topic: All reference categories
        - Category (e.g., "constitutive-models"): List items in category
        - Full path (e.g., "constitutive-models mohr-coulomb"): Full documentation

        When to use:
        - Need FLAC zone constitutive model property names
          (mohr-coulomb: young/poisson/cohesion/friction/...; cysoil; etc.)
          before a 'zone property' / 'zone cmodel assign' command
        - Need range filtering syntax (position, cylinder, group, id)
        - Need plot item coloring/cut keywords for zone, gridpoint, or structure plots
        - Using range filters in any FLAC command

        Related tools:
        - flac_browse_commands: Command syntax (e.g., "zone cmodel assign")
        - flac_query_command: Search commands by keywords
        """
        topic_str = normalize_input(topic, lowercase=True)
        version_value = normalize_command_doc_version(version)
        product_value = normalize_product(product)
        if not is_product_version_applicable(product_value, version_value):
            return _wrap_payload(product_version_error_payload("reference", "browse", product_value, version_value))

        if not topic_str:
            return build_ok(_browse_references_root(version_value, product_value))

        parts = topic_str.split()
        category = parts[0]

        if len(parts) == 1:
            payload = _browse_category(category, version_value, product_value)
        elif len(parts) == 2:
            payload = _browse_item(category, parts[1], version_value, product_value)
        else:
            # 3+ parts: category + item + sub-item (remaining parts joined)
            payload = _browse_sub_item(category, parts[1], " ".join(parts[2:]), version_value, product_value)
        return _wrap_payload(payload)


def _browse_references_root(version: str, product: str) -> dict[str, Any]:
    refs_index = ReferenceLoader.load_index()
    categories = refs_index.get("categories", {})
    category_items: list[dict[str, Any]] = []

    for category_name, category_data in categories.items():
        items = [
            item
            for item in ReferenceLoader.get_item_list(category_name, version)
            if is_compatible_with_product(item, product)
        ]
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
        summary={"count": len(category_items), "version": version, "product": product},
    )


def _browse_category(category: str, version: str, product: str) -> dict[str, Any]:
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
            "input": {"category": category, "version": version, "product": product},
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
            "input": {"category": category, "version": version, "product": product},
        }
    raw_items = ReferenceLoader.get_item_list(category, version)
    items = []
    for item in raw_items:
        if not is_compatible_with_product(item, product):
            continue
        entry: dict[str, Any] = {
            "name": item.get("name", ""),
            "description": item.get("description", ""),
            "compatibility": compatibility_summary(item, product),
        }
        if "full_name" in item:
            entry["full_name"] = item["full_name"]
        if "category" in item:
            entry["category"] = item["category"]
        if "common_use" in item:
            entry["common_use"] = item["common_use"]
        if "availability" in item:
            entry["availability"] = item["availability"]
        items.append(entry)

    return build_docs_data(
        source="reference",
        action="browse",
        entries=items,
        summary={
            "count": len(items),
            "category": category,
            "version": version,
            "product": product,
        },
    )


def _browse_item(category: str, item: str, version: str, product: str) -> dict[str, Any]:
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
            "input": {"category": category, "item": item, "version": version, "product": product},
            "available_categories": sorted(categories.keys()),
        }

    item_doc = ReferenceLoader.load_item_doc(category, item)

    if not item_doc:
        items = ReferenceLoader.get_item_list(category, version)
        available = [i.get("name", "") for i in items]
        return {
            "source": "reference",
            "action": "browse",
            "error": {
                "code": "item_not_found",
                "message": f"Item '{item}' not found in '{category}'.",
            },
            "input": {"category": category, "item": item, "version": version, "product": product},
            "available_items": available,
        }

    availability = item_doc.get("availability")
    if isinstance(availability, dict) and not availability.get(version, False):
        supported = [v for v, ok in availability.items() if ok]
        return {
            "source": "reference",
            "action": "browse",
            "error": {
                "code": "item_unavailable_for_version",
                "message": (
                    f"'{item}' is not available in FLAC {version} (available in: {', '.join(supported) or 'none'})."
                ),
            },
            "input": {"category": category, "item": item, "version": version, "product": product},
            "available_versions": supported,
        }

    if not is_compatible_with_product(item_doc, product):
        return {
            "source": "reference",
            "action": "browse",
            "error": {
                "code": "item_unavailable_for_product",
                "message": f"'{item}' is not compatible with product filter '{product}'.",
            },
            "input": {"category": category, "item": item, "version": version, "product": product},
            "compatibility": compatibility_summary(item_doc, product),
        }

    # Directory-based item: return overview with sub-item list instead of full doc
    if ReferenceLoader.is_directory_item(category, item):
        sub_items = item_doc.get("sub_items", [])
        overview: dict[str, Any] = {
            "category": category,
            "item": item,
            "description": item_doc.get("description", ""),
            "base_syntax": item_doc.get("base_syntax", ""),
            "compatibility": compatibility_summary(item_doc, product),
        }
        if "basic_keywords" in item_doc:
            overview["basic_keywords"] = item_doc["basic_keywords"]
        if "common_usage_patterns" in item_doc:
            overview["common_usage_patterns"] = item_doc["common_usage_patterns"]
        overview["sub_items"] = [{"name": s["name"], "description": s.get("description", "")} for s in sub_items]
        return build_docs_data(
            source="reference",
            action="browse",
            entries=[overview],
            summary={
                "count": 1,
                "sub_item_count": len(sub_items),
                "version": version,
                "product": product,
                "hint": f"Use flac_browse_reference('{category} {item} <sub_item>') for details",
            },
        )

    entry: dict[str, Any] = {
        "category": category,
        "item": item,
        "compatibility": compatibility_summary(item_doc, product),
        "doc": item_doc,
    }
    summary: dict[str, Any] = {"count": 1, "version": version, "product": product}
    if isinstance(item_doc.get("availability"), dict):
        summary["available_in"] = [v for v, ok in item_doc["availability"].items() if ok]
    return build_docs_data(
        source="reference",
        action="browse",
        entries=[entry],
        summary=summary,
    )


def _browse_sub_item(category: str, item: str, sub_item: str, version: str, product: str) -> dict[str, Any]:
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
            "input": {
                "category": category,
                "item": item,
                "sub_item": sub_item,
                "version": version,
                "product": product,
            },
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
            "input": {
                "category": category,
                "item": item,
                "sub_item": sub_item,
                "version": version,
                "product": product,
            },
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
            "input": {
                "category": category,
                "item": item,
                "sub_item": sub_item,
                "version": version,
                "product": product,
            },
            "available_sub_items": available,
        }

    if not is_compatible_with_product(sub_doc, product):
        return {
            "source": "reference",
            "action": "browse",
            "error": {
                "code": "sub_item_unavailable_for_product",
                "message": f"'{category} {item} {sub_item}' is not compatible with product filter '{product}'.",
            },
            "input": {
                "category": category,
                "item": item,
                "sub_item": sub_item,
                "version": version,
                "product": product,
            },
            "compatibility": compatibility_summary(sub_doc, product),
        }

    return build_docs_data(
        source="reference",
        action="browse",
        entries=[
            {
                "category": category,
                "item": item,
                "sub_item": sub_item,
                "compatibility": compatibility_summary(sub_doc, product),
                "doc": sub_doc,
            }
        ],
        summary={"count": 1, "version": version, "product": product},
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
