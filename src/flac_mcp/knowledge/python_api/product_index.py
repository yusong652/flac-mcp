"""Product/version scoping for bundled FLAC Python API documentation."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from flac_mcp.knowledge.compatibility import FLACProduct, normalize_product
from flac_mcp.knowledge.config import FLAC_PYTHON_API_DOCS_VERSION_ROOT

SUPPORTED_PYTHON_API_PRODUCTS = ("flac2d", "flac3d")
SUPPORTED_PYTHON_API_VERSIONS = ("6.0", "7.0", "9.0", "9.1", "9.2", "9.3", "9.4", "9.5", "9.6", "9.7")

ITASCA_9X_PYTHON_API_URL = (
    "https://docs.itascacg.com/itasca900/common/docproject/source/manual/scripting/python/python_flac3d.html"
)
ITASCA_9X_PYTHON_API_SOURCE = (
    "Uses the bundled ITASCA 9.0 FLAC Python API snapshot as the documented 9.x baseline; "
    "runtime validation is recommended for version-specific embedded Python behavior."
)

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
            "url": ITASCA_9X_PYTHON_API_URL,
        },
        "9.1": {
            "applicable": True,
            "bundled": True,
            "source": ITASCA_9X_PYTHON_API_SOURCE,
            "source_version": "9.0",
            "url": ITASCA_9X_PYTHON_API_URL,
        },
        "9.2": {
            "applicable": True,
            "bundled": True,
            "source": ITASCA_9X_PYTHON_API_SOURCE,
            "source_version": "9.0",
            "url": ITASCA_9X_PYTHON_API_URL,
        },
        "9.3": {
            "applicable": True,
            "bundled": True,
            "source": ITASCA_9X_PYTHON_API_SOURCE,
            "source_version": "9.0",
            "url": ITASCA_9X_PYTHON_API_URL,
        },
        "9.4": {
            "applicable": True,
            "bundled": True,
            "source": ITASCA_9X_PYTHON_API_SOURCE,
            "source_version": "9.0",
            "reference_version": "9.3",
            "url": ITASCA_9X_PYTHON_API_URL,
        },
        "9.5": {
            "applicable": True,
            "bundled": True,
            "source": ITASCA_9X_PYTHON_API_SOURCE,
            "source_version": "9.0",
            "reference_version": "9.3",
            "url": ITASCA_9X_PYTHON_API_URL,
        },
        "9.6": {
            "applicable": True,
            "bundled": True,
            "source": ITASCA_9X_PYTHON_API_SOURCE,
            "source_version": "9.0",
            "reference_version": "9.3",
            "url": ITASCA_9X_PYTHON_API_URL,
        },
        "9.7": {
            "applicable": True,
            "bundled": True,
            "source": ITASCA_9X_PYTHON_API_SOURCE,
            "source_version": "9.0",
            "reference_version": "9.3",
            "url": ITASCA_9X_PYTHON_API_URL,
        },
    },
    "flac3d": {
        "6.0": {
            "applicable": True,
            "bundled": False,
            "source": "Official FLAC3D 6.0 Python API pages.",
            "url": "https://docs.itascacg.com/pfc600/flac3d/docproject/source/options/python/itasca.html",
        },
        "7.0": {
            "applicable": True,
            "bundled": False,
            "source": "Official FLAC3D 7.0 Python API pages.",
            "url": "https://docs.itascacg.com/flac3d700/common/docproject/source/manual/scripting/python/python.html",
        },
        "9.0": {
            "applicable": True,
            "bundled": True,
            "source": "Official ITASCA 9.0 FLAC3D-Python API pages.",
            "url": ITASCA_9X_PYTHON_API_URL,
        },
        "9.1": {
            "applicable": True,
            "bundled": True,
            "source": ITASCA_9X_PYTHON_API_SOURCE,
            "source_version": "9.0",
            "url": ITASCA_9X_PYTHON_API_URL,
        },
        "9.2": {
            "applicable": True,
            "bundled": True,
            "source": ITASCA_9X_PYTHON_API_SOURCE,
            "source_version": "9.0",
            "url": ITASCA_9X_PYTHON_API_URL,
        },
        "9.3": {
            "applicable": True,
            "bundled": True,
            "source": ITASCA_9X_PYTHON_API_SOURCE,
            "source_version": "9.0",
            "url": ITASCA_9X_PYTHON_API_URL,
        },
        "9.4": {
            "applicable": True,
            "bundled": True,
            "source": ITASCA_9X_PYTHON_API_SOURCE,
            "source_version": "9.0",
            "reference_version": "9.3",
            "url": ITASCA_9X_PYTHON_API_URL,
        },
        "9.5": {
            "applicable": True,
            "bundled": True,
            "source": ITASCA_9X_PYTHON_API_SOURCE,
            "source_version": "9.0",
            "reference_version": "9.3",
            "url": ITASCA_9X_PYTHON_API_URL,
        },
        "9.6": {
            "applicable": True,
            "bundled": True,
            "source": ITASCA_9X_PYTHON_API_SOURCE,
            "source_version": "9.0",
            "reference_version": "9.3",
            "url": ITASCA_9X_PYTHON_API_URL,
        },
        "9.7": {
            "applicable": True,
            "bundled": True,
            "source": ITASCA_9X_PYTHON_API_SOURCE,
            "source_version": "9.0",
            "reference_version": "9.3",
            "url": ITASCA_9X_PYTHON_API_URL,
        },
    },
}

# Product scoping is applied before browse/search builds its API index.  The
# official FLAC Python pages do not ship a per-product manifest, so keep the
# MCP-side rules explicit and API-shaped instead of relying on broad text
# searches over descriptions.
FLAC3D_ONLY_API_LEAF_NAMES = {
    "domain_max_z",
    "domain_min_z",
    "gravity_z",
    "normal_z",
    "set_domain_max_z",
    "set_domain_min_z",
    "set_gravity_z",
    "stress_prin_z",
}

FLAC3D_ONLY_API_LEAF_SUFFIXES = (
    "_z",
    "_z_set",
    "_xz",
    "_xz_set",
    "_yz",
    "_yz_set",
    "_zz",
    "_zz_set",
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
    if normalized in {"9.1", "9.2", "9.3", "9.4", "9.5", "9.6", "9.7"}:
        return normalized
    return normalized


def versioned_docs_dir(product: str, version: str) -> Path:
    """Return the optional versioned Python API docs directory."""
    return FLAC_PYTHON_API_DOCS_VERSION_ROOT / normalize_product(product) / normalize_api_version(version)


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
    info = dict(PYTHON_API_SOURCES.get(product_value, {}).get(version_value, {"applicable": False, "bundled": False}))
    if info.get("applicable") and versioned_docs_dir(product_value, version_value).exists():
        info["bundled"] = True
        info["bundled_resource"] = f"python_sdk_docs_versions/{product_value}/{version_value}"
    return info


def is_source_available(product: str, version: str) -> bool:
    """Whether bundled API docs are available for the product/version."""
    info = source_info(product, version)
    return bool(info.get("applicable")) and bool(info.get("bundled"))


def api_products(api_path: str, doc: Any, version: str) -> list[str]:
    """Return products supported by an API entry in the bundled index."""
    version_value = normalize_api_version(version)
    if version_value in {"6.0", "7.0"}:
        return [FLACProduct.FLAC3D.value]

    three_d_only = _is_explicit_flac3d_only_api(api_path)
    text = api_path + " " + json.dumps(doc, ensure_ascii=False)
    three_d_only = three_d_only or any(pattern.search(text) for pattern in _THREE_D_ONLY_TEXT_PATTERNS)
    if three_d_only:
        return [FLACProduct.FLAC3D.value]
    return [FLACProduct.FLAC2D.value, FLACProduct.FLAC3D.value]


def _is_explicit_flac3d_only_api(api_path: str) -> bool:
    """Return True when an API path uses an explicit out-of-plane component."""
    leaf = api_path.rsplit(".", 1)[-1].lower()
    if leaf in FLAC3D_ONLY_API_LEAF_NAMES:
        return True
    return any(leaf.endswith(suffix) for suffix in FLAC3D_ONLY_API_LEAF_SUFFIXES)


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
