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


_THREE_D_PATTERNS = (
    re.compile(r"\b3D\s+ONLY\b", re.IGNORECASE),
    re.compile(r"\b3D\s+only\b", re.IGNORECASE),
    re.compile(r"\bFLAC3D[-\s]only\b", re.IGNORECASE),
    re.compile(r"\bnot\s+available\s+in\s+FLAC2D\b", re.IGNORECASE),
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


def infer_dimension(doc: Any) -> str:
    """Infer dimension compatibility from a documentation object.

    Returns:
        ``"2D"`` for FLAC2D-only docs, ``"3D"`` for FLAC3D-only docs,
        ``"mixed"`` when conflicting markers appear, and ``"any"`` when no
        restrictive marker is visible.
    """
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


def compatibility_summary(doc: Any, product: str) -> dict[str, Any]:
    """Small metadata block describing inferred compatibility."""
    dimension = infer_dimension(doc)
    return {
        "product_filter": normalize_product(product),
        "dimension": dimension,
        "compatible": is_compatible_with_product(doc, product),
        "basis": "inferred from 2D/3D markers in bundled documentation",
    }
