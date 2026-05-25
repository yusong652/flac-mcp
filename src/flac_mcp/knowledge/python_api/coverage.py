"""Coverage expectations for bundled FLAC Python API documentation."""

from __future__ import annotations

from typing import Any

from flac_mcp.knowledge.python_api.loader import DocumentationLoader

SUPPORTED_PRODUCTS = ("flac2d", "flac3d")
SUPPORTED_VERSIONS = ("6.0", "7.0", "9.0")

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
    product: {
        "6.0": {"itasca", "zone", "gridpoint"},
        "7.0": {"itasca", "zone", "gridpoint"},
        "9.0": EXPECTED_FLAC_9_MODULES,
    }
    for product in SUPPORTED_PRODUCTS
}


def build_python_api_coverage() -> dict[str, Any]:
    """Return a structured coverage report for bundled Python API docs."""
    index = DocumentationLoader.load_index()
    modules = set(index.get("modules", {}).keys())
    objects = set(index.get("objects", {}).keys())
    quick_ref = index.get("quick_ref", {})

    matrix: dict[str, dict[str, Any]] = {}
    for product, versions in EXPECTED_BY_PRODUCT_VERSION.items():
        matrix[product] = {}
        for version, expected_modules in versions.items():
            present = sorted(expected_modules & modules)
            missing = sorted(expected_modules - modules)
            matrix[product][version] = {
                "expected_modules": sorted(expected_modules),
                "present_modules": present,
                "missing_modules": missing,
                "complete": not missing,
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
            "Command docs are versioned for 6.0/7.0/9.0; Python API docs are currently a bundled snapshot.",
            "FLAC2D/FLAC3D dimension differences are partly represented in signatures/descriptions, not as a first-class filter.",
            "Use extract_flac_api.py inside each target FLAC runtime to regenerate ground-truth API docs.",
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
