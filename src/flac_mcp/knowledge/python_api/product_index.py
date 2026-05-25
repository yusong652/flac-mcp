"""Product/version scoping for bundled FLAC Python API documentation."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from flac_mcp.knowledge.compatibility import FLACProduct, normalize_product

SUPPORTED_PYTHON_API_PRODUCTS = ("flac2d", "flac3d")
SUPPORTED_PYTHON_API_VERSIONS = ("6.0", "7.0", "9.0")

PYTHON_API_SOURCES: dict[str, dict[str, dict[str, Any]]] = {
    "flac2d": {
        "6.0": {
            "applicable": False,
            "bundled": False,
            "reason": "FLAC2D is represented in the bundled official FLAC docs starting with 9.0.",
        },
        "7.0": {
            "applicable": False,
            "bundled": False,
            "reason": "FLAC2D is represented in the bundled official FLAC docs starting with 9.0.",
        },
        "9.0": {
            "applicable": True,
            "bundled": True,
            "source": "Derived from the official ITASCA 9.0 FLAC shared docs and FLAC3D-Python API pages.",
            "url": "https://docs.itascacg.com/itasca900/common/docproject/source/manual/scripting/python/python_flac3d.html",
        },
    },
    "flac3d": {
        "6.0": {
            "applicable": True,
            "bundled": False,
            "source": "Official FLAC3D 6.0 Python API exists, but this package bundles the 9.0 API snapshot.",
            "url": "https://docs.itascacg.com/pfc600/flac3d/docproject/source/options/python/itasca.html",
        },
        "7.0": {
            "applicable": True,
            "bundled": False,
            "source": "Official FLAC3D 7.0 Python API exists, but this package bundles the 9.0 API snapshot.",
            "url": "https://docs.itascacg.com/flac3d700/common/docproject/source/manual/scripting/python/python.html",
        },
        "9.0": {
            "applicable": True,
            "bundled": True,
            "source": "Official ITASCA 9.0 FLAC3D-Python API pages.",
            "url": "https://docs.itascacg.com/itasca900/common/docproject/source/manual/scripting/python/python_flac3d.html",
        },
    },
}

_THREE_D_ONLY_NAME_PATTERNS = (
    re.compile(
        r"(?<![A-Za-z0-9])("
        r"gravity_z|set_gravity_z|domain_min_z|domain_max_z|"
        r"set_domain_min_z|set_domain_max_z|pos_z|pos_z_set|vel_z|vel_z_set|"
        r"normal_z|disp_shear_z|disp_shear_z_set|stress_shear_z|stress_shear_z_set|"
        r"stress_prin_z"
        r")(?![A-Za-z0-9])",
        re.IGNORECASE,
    ),
)

_THREE_D_ONLY_TEXT_PATTERNS = (
    re.compile(r"\b3D\s+only\b", re.IGNORECASE),
    re.compile(r"\bFLAC3D[-\s]only\b", re.IGNORECASE),
    re.compile(r"\bnot\s+available\s+in\s+FLAC2D\b", re.IGNORECASE),
)


def normalize_api_version(value: str | None) -> str:
    """Normalize a Python API documentation version."""
    if value is None:
        return "9.0"
    normalized = str(value).strip()
    if normalized in {"6", "6.0"}:
        return "6.0"
    if normalized in {"7", "7.0"}:
        return "7.0"
    if normalized in {"9", "9.0"}:
        return "9.0"
    return normalized


def source_info(product: str, version: str) -> dict[str, Any]:
    """Return source metadata for a product/version API index."""
    product_value = normalize_product(product)
    version_value = normalize_api_version(version)
    if product_value == FLACProduct.ANY.value:
        return {
            "applicable": True,
            "bundled": True,
            "source": "Combined bundled Python API index.",
        }
    return dict(PYTHON_API_SOURCES.get(product_value, {}).get(version_value, {"applicable": False, "bundled": False}))


def is_source_available(product: str, version: str) -> bool:
    """Whether bundled API docs are available for the product/version."""
    info = source_info(product, version)
    return bool(info.get("applicable")) and bool(info.get("bundled"))


def api_products(api_path: str, doc: Any, version: str) -> list[str]:
    """Return products supported by an API entry in the bundled index."""
    version_value = normalize_api_version(version)
    if version_value in {"6.0", "7.0"}:
        return [FLACProduct.FLAC3D.value]

    text = api_path + " " + json.dumps(doc, ensure_ascii=False)
    three_d_only = any(pattern.search(text) for pattern in _THREE_D_ONLY_NAME_PATTERNS)
    three_d_only = three_d_only or any(pattern.search(text) for pattern in _THREE_D_ONLY_TEXT_PATTERNS)
    if three_d_only:
        return [FLACProduct.FLAC3D.value]
    return [FLACProduct.FLAC2D.value, FLACProduct.FLAC3D.value]


def is_api_available(api_path: str, doc: Any, product: str, version: str) -> bool:
    """Whether an API entry belongs in a product/version API index."""
    product_value = normalize_product(product)
    version_value = normalize_api_version(version)
    if product_value == FLACProduct.ANY.value:
        return True
    if not is_source_available(product_value, version_value):
        return False
    return product_value in api_products(api_path, doc, version_value)


def annotate_api_doc(api_path: str, doc: dict[str, Any], product: str, version: str) -> dict[str, Any]:
    """Attach first-class availability metadata to a loaded API doc."""
    annotated = deepcopy(doc)
    version_value = normalize_api_version(version)
    annotated["availability"] = {
        "products": api_products(api_path, annotated, version_value),
        "version": version_value,
        "source": source_info(product, version_value),
    }
    return annotated
