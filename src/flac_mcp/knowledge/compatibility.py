"""Product/dimension compatibility helpers for FLAC documentation."""

from __future__ import annotations

import json
import re
from enum import Enum
from typing import Any


class FLACProduct(str, Enum):
    """Supported FLAC product filters for documentation tools."""

    ANY = "any"
    FLAC2D = "flac2d"
    FLAC3D = "flac3d"


PRODUCT_VERSION_SOURCES: dict[str, dict[str, dict[str, Any]]] = {
    FLACProduct.FLAC2D.value: {
        "6.0": {
            "applicable": False,
            "reason": "FLAC2D is represented in the bundled documentation matrix starting with 9.0.",
        },
        "7.0": {
            "applicable": False,
            "reason": "FLAC2D is represented in the bundled documentation matrix starting with 9.0.",
        },
        "9.0": {"applicable": True},
    },
    FLACProduct.FLAC3D.value: {
        "6.0": {"applicable": True},
        "7.0": {"applicable": True},
        "9.0": {"applicable": True},
    },
}


_THREE_D_PATTERNS = (
    re.compile(r"\b3D\s+ONLY\b", re.IGNORECASE),
    re.compile(r"\b3D\s+only\b", re.IGNORECASE),
    re.compile(r"\b3D\s+zone[-\s]filled\b", re.IGNORECASE),
    re.compile(r"\b3D\s+zones?\b", re.IGNORECASE),
    re.compile(r"\bFLAC3D[-\s]only\b", re.IGNORECASE),
    re.compile(r"\bnot\s+available\s+in\s+FLAC2D\b", re.IGNORECASE),
    re.compile(
        r"(?<![A-Za-z0-9])("
        r"position-z|velocity-z|displacement-z|stress-xz|stress-yz|stress-zz|"
        r"normal-z|gravity_z|set_gravity_z|domain_min_z|domain_max_z|"
        r"set_domain_min_z|set_domain_max_z|pos_z|pos_z_set|vel_z|vel_z_set|"
        r"normal_z|stress_shear_z|disp_shear_z|stress_prin_z"
        r")(?![A-Za-z0-9])",
        re.IGNORECASE,
    ),
)
_TWO_D_PATTERNS = (
    re.compile(r"\b2D\s+ONLY\b", re.IGNORECASE),
    re.compile(r"\b2D\s+only\b", re.IGNORECASE),
    re.compile(r"\bFLAC2D[-\s]only\b", re.IGNORECASE),
    re.compile(r"\bfor\s+FLAC2D\b", re.IGNORECASE),
    re.compile(r"\b2D\s+zones?\b", re.IGNORECASE),
    re.compile(r"\bnot\s+available\s+in\s+FLAC3D\b", re.IGNORECASE),
)


def normalize_product(value: FLACProduct | str | None) -> str:
    """Return a normalized product filter value."""
    if value is None:
        return FLACProduct.ANY.value
    if isinstance(value, FLACProduct):
        return value.value
    normalized = str(value).strip().lower()
    if normalized in {"", "all", "both", "auto"}:
        return FLACProduct.ANY.value
    return normalized


def product_version_info(product: FLACProduct | str | None, version: str) -> dict[str, Any]:
    """Return product/version applicability metadata."""
    product_value = normalize_product(product)
    if product_value == FLACProduct.ANY.value:
        return {"applicable": True}
    return dict(
        PRODUCT_VERSION_SOURCES.get(product_value, {}).get(
            str(version),
            {"applicable": False, "reason": f"Unsupported FLAC product/version combination: {product_value} {version}."},
        )
    )


def is_product_version_applicable(product: FLACProduct | str | None, version: str) -> bool:
    """Whether the product/version combination is valid in this documentation matrix."""
    return bool(product_version_info(product, version).get("applicable"))


def product_version_error_payload(source: str, action: str, product: str, version: str) -> dict[str, Any]:
    """Build a structured docs-tool error for invalid product/version pairs."""
    info = product_version_info(product, version)
    return {
        "source": source,
        "action": action,
        "error": {
            "code": "product_version_not_applicable",
            "message": f"{product} {version} is not applicable in the bundled FLAC documentation matrix.",
        },
        "input": {"product": product, "version": version},
        "availability": info,
    }


def infer_dimension(doc: Any) -> str:
    """Infer dimension compatibility from a documentation object.

    Returns:
        ``"2D"`` for FLAC2D-only docs, ``"3D"`` for FLAC3D-only docs,
        ``"mixed"`` when conflicting markers appear, and ``"any"`` when no
        restrictive marker is visible.
    """
    if isinstance(doc, dict):
        explicit = doc.get("dimension") or doc.get("compatibility_dimension")
        if isinstance(explicit, str) and explicit.lower() in {"any", "2d", "3d", "mixed"}:
            explicit_value = explicit.lower()
            if explicit_value == "2d":
                return "2D"
            if explicit_value == "3d":
                return "3D"
            return explicit_value
        products = doc.get("products") or doc.get("compatible_products")
        if isinstance(products, list):
            normalized_products = {normalize_product(product) for product in products}
            has_2d = FLACProduct.FLAC2D.value in normalized_products
            has_3d = FLACProduct.FLAC3D.value in normalized_products
            if has_2d and has_3d:
                return "mixed"
            if has_2d:
                return "2D"
            if has_3d:
                return "3D"

    text = json.dumps(doc, ensure_ascii=False)
    has_3d = any(pattern.search(text) for pattern in _THREE_D_PATTERNS)
    has_2d = any(pattern.search(text) for pattern in _TWO_D_PATTERNS)
    if has_3d and has_2d:
        return "mixed"
    if has_3d:
        return "3D"
    if has_2d:
        return "2D"
    return "any"


def is_compatible_with_product(doc: Any, product: str) -> bool:
    """Whether a doc should be shown for a requested FLAC product."""
    normalized = normalize_product(product)
    if normalized == FLACProduct.ANY.value:
        return True

    dimension = infer_dimension(doc)
    if normalized == FLACProduct.FLAC2D.value:
        return dimension in {"any", "2D", "mixed"}
    if normalized == FLACProduct.FLAC3D.value:
        return dimension in {"any", "3D", "mixed"}
    return True


def _has_explicit_dimension_metadata(doc: Any) -> bool:
    if not isinstance(doc, dict):
        return False
    if isinstance(doc.get("dimension") or doc.get("compatibility_dimension"), str):
        return True
    return isinstance(doc.get("products") or doc.get("compatible_products"), list)


def compatibility_summary(doc: Any, product: str) -> dict[str, Any]:
    """Small metadata block describing inferred compatibility."""
    dimension = infer_dimension(doc)
    return {
        "product_filter": normalize_product(product),
        "dimension": dimension,
        "compatible": is_compatible_with_product(doc, product),
        "basis": (
            "explicit dimension metadata"
            if _has_explicit_dimension_metadata(doc)
            else "inferred from 2D/3D markers in bundled documentation"
        ),
    }
