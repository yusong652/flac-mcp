"""Coverage expectations for bundled FLAC Python API documentation."""

from __future__ import annotations

from typing import Any

from flac_mcp.knowledge.python_api.loader import DocumentationLoader
from flac_mcp.knowledge.python_api.product_index import (
    PYTHON_API_SOURCES,
    SUPPORTED_PYTHON_API_PRODUCTS,
    SUPPORTED_PYTHON_API_VERSIONS,
)

SUPPORTED_PRODUCTS = SUPPORTED_PYTHON_API_PRODUCTS
SUPPORTED_VERSIONS = SUPPORTED_PYTHON_API_VERSIONS

# Official ITASCA 9.0 FLAC Python index lists these FLAC API modules. The
# pages are shared across FLAC2D/FLAC3D where the API itself is dimension-aware.
EXPECTED_FLAC_9_MODULES = {
    "itasca",
    "vec",
    "attach",
    "gridpoint",
    "gridpointarray",
    "interface",
    "interfacearray",
    "interfaceelementarray",
    "interfacenodearray",
    "vertexarray",
    "zone",
    "zonearray",
}

EXPECTED_BY_PRODUCT_VERSION: dict[str, dict[str, set[str]]] = {
    "flac2d": {
        "6.0": set(),
        "7.0": set(),
        "9.0": EXPECTED_FLAC_9_MODULES,
    },
    "flac3d": {
        "6.0": set(),
        "7.0": set(),
        "9.0": EXPECTED_FLAC_9_MODULES,
    },
}


def build_python_api_coverage() -> dict[str, Any]:
    """Return a structured coverage report for bundled Python API docs."""
    base_index = DocumentationLoader.load_index()
    modules = set(base_index.get("modules", {}).keys())
    objects = set(base_index.get("objects", {}).keys())
    quick_ref = base_index.get("quick_ref", {})

    matrix: dict[str, dict[str, Any]] = {}
    for product, versions in EXPECTED_BY_PRODUCT_VERSION.items():
        matrix[product] = {}
        for version, expected_modules in versions.items():
            product_index = DocumentationLoader.load_index(product, version)
            product_modules = set(product_index.get("modules", {}).keys())
            present = sorted(expected_modules & product_modules)
            missing = sorted(expected_modules - product_modules)
            source = PYTHON_API_SOURCES.get(product, {}).get(version, {})
            matrix[product][version] = {
                "expected_modules": sorted(expected_modules),
                "present_modules": present,
                "missing_modules": missing,
                "api_entry_count": len(product_index.get("quick_ref", {})),
                "source": source,
                "complete": bool(source.get("bundled")) and not missing,
            }

    return {
        "products": list(SUPPORTED_PRODUCTS),
        "versions": list(SUPPORTED_VERSIONS),
        "bundled": {
            "modules": sorted(modules),
            "objects": sorted(objects),
            "module_count": len(modules),
            "object_count": len(objects),
            "api_entry_count": len(quick_ref),
        },
        "matrix": matrix,
        "known_limits": [
            "The bundled product-scoped Python API index is currently complete for FLAC 9.0.",
            "FLAC3D 6.0/7.0 official Python API pages exist, but this package does not yet bundle separate snapshots.",
            "FLAC2D 6.0/7.0 are marked not applicable in the bundled source matrix.",
        ],
        "sources": [
            {
                "label": "ITASCA 9.0 FLAC3D Python API index",
                "url": "https://docs.itascacg.com/itasca900/common/docproject/source/manual/scripting/python/python_flac3d.html",
            },
            {
                "label": "ITASCA 9.0 common vec API",
                "url": "https://docs.itascacg.com/itasca900/common/docproject/source/manual/scripting/python/doc/vec.html",
            },
        ],
    }
