"""Coverage expectations for bundled FLAC Python API documentation."""

from __future__ import annotations

from typing import Any

from flac_mcp.knowledge.python_api.loader import DocumentationLoader
from flac_mcp.knowledge.python_api.product_index import (
    SUPPORTED_PYTHON_API_PRODUCTS,
    SUPPORTED_PYTHON_API_VERSIONS,
    source_info,
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
        "9.1": EXPECTED_FLAC_9_MODULES,
        "9.2": EXPECTED_FLAC_9_MODULES,
        "9.3": EXPECTED_FLAC_9_MODULES,
        "9.4": EXPECTED_FLAC_9_MODULES,
        "9.5": EXPECTED_FLAC_9_MODULES,
        "9.6": EXPECTED_FLAC_9_MODULES,
        "9.7": EXPECTED_FLAC_9_MODULES,
    },
    "flac3d": {
        "6.0": set(),
        "7.0": set(),
        "9.0": EXPECTED_FLAC_9_MODULES,
        "9.1": EXPECTED_FLAC_9_MODULES,
        "9.2": EXPECTED_FLAC_9_MODULES,
        "9.3": EXPECTED_FLAC_9_MODULES,
        "9.4": EXPECTED_FLAC_9_MODULES,
        "9.5": EXPECTED_FLAC_9_MODULES,
        "9.6": EXPECTED_FLAC_9_MODULES,
        "9.7": EXPECTED_FLAC_9_MODULES,
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
            if not expected_modules and product_modules:
                expected_modules = product_modules
            present = sorted(expected_modules & product_modules)
            missing = sorted(expected_modules - product_modules)
            source = source_info(product, version)
            matrix[product][version] = {
                "expected_module_count": len(expected_modules),
                "present_module_count": len(present),
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
            "FLAC3D Python API snapshots are bundled for 6.0, 7.0, and 9.0.",
            "FLAC 9.1-9.7 Python API coverage reuses the bundled 9.0 snapshot as the documented 9.x baseline.",
            "FLAC2D product-scoped Python API is represented for 9.x from the official shared FLAC docs.",
            "FLAC2D 9.x hides explicit out-of-plane API leaves such as *_z, *_xz, *_yz, and *_zz.",
            "FLAC2D 6.0/7.0 are marked not applicable in the bundled source matrix.",
        ],
        "sources": [
            {
                "label": "FLAC3D 6.0 Python API index",
                "url": "https://docs.itascacg.com/pfc600/flac3d/docproject/source/options/python/itasca.html",
            },
            {
                "label": "FLAC3D 7.0 Python scripting index",
                "url": "https://docs.itascacg.com/flac3d700/common/docproject/source/manual/scripting/python/python.html",
            },
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
