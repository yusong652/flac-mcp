"""Coverage report for bundled FLAC command documentation."""

from __future__ import annotations

from typing import Any

from flac_mcp.knowledge.commands.loader import CommandLoader
from flac_mcp.knowledge.compatibility import (
    FLACProduct,
    infer_dimension,
    is_compatible_with_product,
    product_version_info,
)
from flac_mcp.utils import CommandDocVersion

SUPPORTED_COMMAND_PRODUCTS = (FLACProduct.FLAC2D.value, FLACProduct.FLAC3D.value)
SUPPORTED_COMMAND_VERSIONS = tuple(version.value for version in CommandDocVersion)

SAMPLE_LIMIT = 8


def build_command_coverage() -> dict[str, Any]:
    """Return a structured coverage report for bundled command docs."""
    index = CommandLoader.load_index()
    commands = CommandLoader.get_all_commands()
    categories = index.get("categories", {})

    matrix: dict[str, dict[str, Any]] = {}
    for product in SUPPORTED_COMMAND_PRODUCTS:
        matrix[product] = {}
        for version in SUPPORTED_COMMAND_VERSIONS:
            matrix[product][version] = _build_product_version_row(commands, product, version)

    return {
        "products": list(SUPPORTED_COMMAND_PRODUCTS),
        "versions": list(SUPPORTED_COMMAND_VERSIONS),
        "bundled": {
            "category_count": len(categories),
            "command_count": len(commands),
            "categories": sorted(categories.keys()),
            "index_version": index.get("version"),
        },
        "matrix": matrix,
        "known_limits": [
            "Command coverage is measured against the bundled command index.",
            "FLAC2D 6.0/7.0 are marked not applicable in the bundled source matrix.",
            "FLAC3D 6.0/7.0 rows show missing_version for commands whose bundled docs only include newer versions.",
            "Product compatibility is inferred from 2D/3D markers in bundled docs; runtime validation is still required before executing model code.",
        ],
    }


def _build_product_version_row(commands: list[dict[str, Any]], product: str, version: str) -> dict[str, Any]:
    source = product_version_info(product, version)
    if not source.get("applicable", False):
        return _not_applicable_row(len(commands), source)

    indexed_count = len(commands)
    loaded_count = 0
    available_for_version_count = 0
    available_for_product_count = 0
    unavailable_for_version_count = 0
    missing_file_count = 0
    missing_version_count = 0
    filtered_by_product_count = 0
    python_available_count = 0

    category_counts: dict[str, int] = {}
    dimension_counts = {"any": 0, "2D": 0, "3D": 0, "mixed": 0}
    missing_files: list[str] = []
    missing_versions: list[str] = []
    unavailable_for_version: list[str] = []
    filtered_by_product: list[dict[str, str]] = []

    for meta in commands:
        category = str(meta.get("category", ""))
        name = str(meta.get("name", ""))
        command_label = _command_label(category, name)

        try:
            doc = CommandLoader.load_command_doc(category, name, version)
        except KeyError:
            missing_version_count += 1
            _append_sample(missing_versions, command_label)
            continue

        if doc is None:
            missing_file_count += 1
            _append_sample(missing_files, command_label)
            continue

        loaded_count += 1
        if doc.get("available") is False:
            unavailable_for_version_count += 1
            _append_sample(unavailable_for_version, command_label)
            continue

        available_for_version_count += 1
        dimension = infer_dimension(doc)
        dimension_counts[dimension] = dimension_counts.get(dimension, 0) + 1

        if not is_compatible_with_product(doc, product):
            filtered_by_product_count += 1
            _append_sample(
                filtered_by_product,
                {
                    "command": command_label,
                    "dimension": dimension,
                },
            )
            continue

        available_for_product_count += 1
        category_counts[category] = category_counts.get(category, 0) + 1
        if bool(meta.get("python_available", False)):
            python_available_count += 1

    resolved_count = indexed_count - missing_file_count - missing_version_count
    return {
        "indexed_command_count": indexed_count,
        "loaded_command_count": loaded_count,
        "resolved_command_count": resolved_count,
        "available_for_version_count": available_for_version_count,
        "available_for_product_count": available_for_product_count,
        "python_available_count": python_available_count,
        "category_count": len(category_counts),
        "category_counts": dict(sorted(category_counts.items())),
        "dimension_counts": dimension_counts,
        "missing_file_count": missing_file_count,
        "missing_version_count": missing_version_count,
        "unavailable_for_version_count": unavailable_for_version_count,
        "filtered_by_product_count": filtered_by_product_count,
        "resolved_ratio": _ratio(resolved_count, indexed_count),
        "product_available_ratio": _ratio(available_for_product_count, indexed_count),
        "complete": missing_file_count == 0 and missing_version_count == 0,
        "applicable": True,
        "source": source,
        "samples": {
            "missing_files": missing_files,
            "missing_versions": missing_versions,
            "unavailable_for_version": unavailable_for_version,
            "filtered_by_product": filtered_by_product,
        },
    }


def _not_applicable_row(indexed_count: int, source: dict[str, Any]) -> dict[str, Any]:
    return {
        "indexed_command_count": indexed_count,
        "loaded_command_count": 0,
        "resolved_command_count": 0,
        "available_for_version_count": 0,
        "available_for_product_count": 0,
        "python_available_count": 0,
        "category_count": 0,
        "category_counts": {},
        "dimension_counts": {"any": 0, "2D": 0, "3D": 0, "mixed": 0},
        "missing_file_count": 0,
        "missing_version_count": 0,
        "unavailable_for_version_count": 0,
        "filtered_by_product_count": 0,
        "resolved_ratio": 0.0,
        "product_available_ratio": 0.0,
        "complete": False,
        "applicable": False,
        "source": source,
        "samples": {
            "missing_files": [],
            "missing_versions": [],
            "unavailable_for_version": [],
            "filtered_by_product": [],
        },
    }


def _command_label(category: str, name: str) -> str:
    return f"{category} {name.replace('-', ' ')}".strip()


def _append_sample(items: list[Any], value: Any) -> None:
    if len(items) < SAMPLE_LIMIT:
        items.append(value)


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)
