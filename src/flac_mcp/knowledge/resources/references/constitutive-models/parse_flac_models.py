"""Extract FLAC zone constitutive-model property references.

References counterpart to ``command_docs/parse_flac900.py``. Purely additive:
emits ``resources/references/constitutive-models/<model>.json`` plus an
``index.json`` from the ITASCA model docs at
``<install>/exe64/doc/common/models/*/doc/model*.html``.

The model pages use the *identical* Sphinx ``id="kwd:..."`` definition-list
scheme as the command docs, so the shared ``FlacCommandHTMLParser`` is reused
unchanged. The constitutive-model keyword used by ``zone cmodel assign`` is the
id prefix (``kwd:mohr-coulomb.cohesion`` -> ``mohr-coulomb``), so — as in
``parse_flac900`` — no hand-maintained directory->keyword map is needed.

This is a **pure-parse** pass: property ``keyword`` + ``symbol`` +
``description`` + a coarse ``type``. Curated fields
(``typical_applications`` / usage patterns / typical values) are intentionally
left empty for a later curation phase.

Usage::

    uv run python src/flac_mcp/knowledge/resources/references/constitutive-models/parse_flac_models.py
    uv run python .../parse_flac_models.py --dry-run
"""

from __future__ import annotations

import html as _html
import json
import re
import sys
from pathlib import Path
from typing import Any

# NOTE: extraction is deliberately regex-based rather than reusing the
# command-doc HTMLParser. The constitutive-model pages nest the property
# definition list inside an outer group ``<dt>(group)<dd><dl><dt
# id="kwd:...">``; the shared stateful parser lets that outer group ``<dd>``
# swallow the *first* nested property's description (one lost description per
# model). A bounded per-``kwd:``-id slice is immune to the nesting and keeps
# this extractor independent of the shared FLAC parser (which must not change).

# ---------------------------------------------------------------------------
# Path configuration
# ---------------------------------------------------------------------------

DOC_ROOT = Path("C:/Program Files/Itasca/ItascaSoftware900/exe64/doc")
MODELS_DIR = DOC_ROOT / "common" / "models"
OUT_DIR = Path(__file__).parent
DOC_BASE_URL = "https://docs.itascacg.com/itasca900/common/models"

# ---------------------------------------------------------------------------
# HTML field extraction
# ---------------------------------------------------------------------------

_KWD_ID_RE = re.compile(r'id="kwd:([^"]+)"')
_TAG_RE = re.compile(r"<[^>]+>")
_MATH_RE = re.compile(r"\\\((.+?)\\\)")
_WS_RE = re.compile(r"\s+")

# Doc ``kwd:`` prefix -> actual ``zone cmodel assign`` keyword, for the rare
# pages where the two diverge. The elastic model's property ids are
# ``kwd:isotropic.*`` (legacy/internal naming), but FLAC 9.0's authoritative
# registry (``zone cmodel list``) names the command keyword ``elastic``
# ("Isotropic Elastic"); ``zone cmodel assign isotropic`` is rejected.
# Verified against C:/Program Files/Itasca/ItascaSoftware900 on 2026-05-20.
MODEL_KEYWORD_OVERRIDES = {
    "isotropic": "elastic",
}

# (model keyword, doc kwd: leaf) -> actual `zone property` keyword, for the
# rare pages where Itasca's own HTML kwd id is wrong/inconsistent. Verified
# against the live FLAC2D 9.0 binary on 2026-05-20:
#   - finn / strain-softening: doc id `table_dilation` (underscore) is an
#     Itasca typo; siblings are `table-cohesion/-friction/-tension` and the
#     binary only accepts the hyphenated `table-dilation`. (A blanket
#     `_`->`-` rule is unsafe: imass legitimately uses underscore names.)
#   - cap-yield: doc ids `pressure-effective-cy` / `stress-deviatoric-cy`
#     carry a cysoil-page anchor suffix; the binary's read-only state
#     keywords are the unsuffixed `pressure-effective` / `stress-deviatoric`.
PROPERTY_KEYWORD_OVERRIDES = {
    ("finn", "table_dilation"): "table-dilation",
    ("strain-softening", "table_dilation"): "table-dilation",
    ("cap-yield", "pressure-effective-cy"): "pressure-effective",
    ("cap-yield", "stress-deviatoric-cy"): "stress-deviatoric",
}


def model_keyword_from_html(html: str) -> str | None:
    """Return the ``zone cmodel assign`` name, i.e. the common ``kwd:`` prefix.

    ``kwd:mohr-coulomb.cohesion`` / ``kwd:mohr-coulomb.bulk`` -> ``mohr-coulomb``
    (the token before the final dot, which never contains an internal dot for
    constitutive-model property ids). Falls back to the most common prefix if
    the page mixes prefixes.
    """
    ids = _KWD_ID_RE.findall(html)
    if not ids:
        return None
    prefixes: dict[str, int] = {}
    for raw in ids:
        prefix = raw.rsplit(".", 1)[0] if "." in raw else raw
        prefixes[prefix] = prefixes.get(prefix, 0) + 1
    return max(prefixes, key=lambda k: prefixes[k])


def full_name_from_html(html: str) -> str:
    """Model title from ``<h1>`` (fallback ``<title>``)."""
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    if m:
        return _WS_RE.sub(" ", _html.unescape(_TAG_RE.sub("", m.group(1)))).strip()
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    if m:
        return _html.unescape(m.group(1)).split("—")[0].split("—")[0].strip()
    return ""


def model_description_from_html(html: str) -> str:
    """Lead prose between ``</h1>`` and the first ``<dl>``, equation-trimmed."""
    m = re.search(r"</h1>(.*?)<dl", html, re.S)
    if not m:
        return ""
    text = _WS_RE.sub(" ", _html.unescape(_TAG_RE.sub(" ", m.group(1)))).strip()
    # Cut at the first formulation/equation section header to keep the
    # human-readable overview and drop the math derivation.
    idx = text.find("Formulation")
    if idx > 40:
        text = text[:idx].strip()
    return text[:600].strip()


def _first_dd_paragraph(segment: str) -> str:
    """First ``<dd>`` ``<p>`` text within a single property's HTML slice.

    The slice starts at a ``kwd:`` id and ends at the next one, so the first
    ``<dd>`` after the property's ``</dt>`` is that property's own
    description regardless of how the list is nested.
    """
    dt_close = segment.find("</dt>")
    if dt_close != -1:
        segment = segment[dt_close + len("</dt>") :]
    dd = re.search(r"<dd\b[^>]*>", segment)
    if not dd:
        return ""
    p = re.search(r"<p\b[^>]*>(.*?)</p>", segment[dd.end() :], re.S)
    if not p:
        return ""
    return _WS_RE.sub(" ", _html.unescape(_TAG_RE.sub("", p.group(1)))).strip()


def extract_properties(html: str, model: str) -> list[dict[str, str]]:
    """Per-``kwd:``-id property catalog, bounded slice per property."""
    matches = list(_KWD_ID_RE.finditer(html))
    props: list[dict[str, str]] = []
    seen: set[str] = set()
    for i, m in enumerate(matches):
        raw = m.group(1)
        if "." not in raw:
            continue
        prefix, leaf = raw.rsplit(".", 1)
        if prefix != model:
            continue
        name = leaf.strip()
        name = PROPERTY_KEYWORD_OVERRIDES.get((model, name), name)
        if not name or name in seen:
            continue
        seen.add(name)
        end = matches[i + 1].start() if i + 1 < len(matches) else len(html)
        raw_desc = _first_dd_paragraph(html[m.end() : end])
        prop = {
            "keyword": name,
            "symbol": _symbol_from_desc(raw_desc),
            "description": _clean_desc(raw_desc),
            "type": _coarse_type(name),
            "default": "",
        }
        dim = _dimension(name)
        if dim:
            prop["dim"] = dim
        props.append(prop)
    return props


def _coarse_type(keyword: str) -> str:
    """Heuristic property type (pure-parse: float unless an obvious flag)."""
    low = keyword.lower()
    if low.startswith("flag") or low.endswith("-flag") or low == "brittle":
        return "BOOL"
    return "FLT"


# Non-obvious FLAC3D-only keywords. Out-of-plane components are self-evident
# from the name (``*-xz`` / ``*-yz`` / ``normal-z``) and need no tag. The
# weak-plane orientation pair is the opposite: nothing in ``dip`` /
# ``dip-direction`` signals 3D, yet FLAC2D rejects them (it uses the single
# in-plane ``angle`` keyword). Verified rejected on the live FLAC2D 9.0
# binary 2026-05-20 for the ubiquitous / anisotropic model family.
_DIM_3D_KEYWORDS = {"dip", "dip-direction"}


def _dimension(keyword: str) -> str | None:
    """Return ``"3D"`` for non-obvious FLAC3D-only keywords, else ``None``.

    A missing ``dim`` means dimension-agnostic *or* self-evidently 3D from
    the name (``xz`` / ``yz`` / ``-z`` tokens) — only the orientation pair
    ``dip`` / ``dip-direction`` is flagged, since its 3D-only nature is not
    apparent from the keyword text (FLAC2D uses ``angle`` instead).
    """
    return "3D" if keyword.lower() in _DIM_3D_KEYWORDS else None


def _symbol_from_desc(description: str) -> str:
    """First ``\\(...\\)`` math token in the description, if any."""
    m = _MATH_RE.search(description)
    return m.group(1).strip() if m else ""


def _clean_desc(description: str) -> str:
    """Drop math delimiters but keep the symbol text; collapse whitespace."""
    text = _MATH_RE.sub(lambda mm: mm.group(1), description)
    return _WS_RE.sub(" ", text).strip()


def build_model_doc(html: str, source_rel: str, dir_name: str) -> dict[str, Any] | None:
    """Parse one constitutive-model HTML page into the reference schema."""
    doc_prefix = model_keyword_from_html(html)
    full_name = full_name_from_html(html)

    # The null model carries no kwd ids (it has no properties) but
    # `zone cmodel assign null` is heavily used for excavation / staged
    # construction — fall back to the directory name so it stays
    # discoverable as a property-less stub.
    if doc_prefix is None:
        doc_prefix = dir_name

    # Properties are keyed by the doc's kwd: prefix; the emitted model
    # keyword may differ (see MODEL_KEYWORD_OVERRIDES) but the command-level
    # `zone property` keywords themselves are unaffected by the rename.
    properties = extract_properties(html, doc_prefix)
    model = MODEL_KEYWORD_OVERRIDES.get(doc_prefix, doc_prefix)

    search_keywords: list[str] = []
    # Keep the legacy doc prefix discoverable (e.g. searching "isotropic"
    # must still surface the renamed "elastic" model).
    name_tokens = model.split("-") + (full_name.lower().split() if full_name else [])
    if doc_prefix != model:
        name_tokens = [doc_prefix, *name_tokens]
    for tok in name_tokens:
        t = tok.strip().lower()
        if t and t != "model" and t not in search_keywords:
            search_keywords.append(t)
    search_keywords.append("constitutive")
    for p in properties:
        if p["keyword"] not in search_keywords:
            search_keywords.append(p["keyword"])

    return {
        "model": model,
        "full_name": full_name or f"{model} model",
        "search_keywords": search_keywords,
        "description": model_description_from_html(html),
        "property_groups": [
            {
                "name": "Properties",
                "description": (
                    f"Material properties for the '{model}' zone constitutive "
                    f"model. Assign the model with 'zone cmodel assign {model} "
                    "[range ...]', then set these with 'zone property "
                    f"<keyword> <value> [range cmodel-name {model}]'."
                ),
                "properties": properties,
            }
        ],
        # Curated content (left empty for a later curation phase).
        "typical_applications": [],
        "notes": [],
        "source": f"{DOC_BASE_URL}/{source_rel}",
        "usage": {
            "assign": f"zone cmodel assign {model} [range ...]",
            "property": (f"zone property <keyword> <value> [range cmodel-name {model}]"),
        },
        # No `availability` map -> version-agnostic (always browsable),
        # matching range-elements / plot-items. FLAC 9.0 is the unified
        # binary; the reference tool's stale 7.0 default would otherwise
        # hide a 9.0-only availability map.
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def iter_model_html() -> list[tuple[str, Path]]:
    """Yield (source_rel, html_path) for every common/models/*/doc/*.html."""
    out: list[tuple[str, Path]] = []
    for model_dir in sorted(MODELS_DIR.iterdir()):
        doc_dir = model_dir / "doc"
        if not doc_dir.is_dir():
            continue
        for html in sorted(doc_dir.glob("*.html")):
            rel = f"{model_dir.name}/doc/{html.name}"
            out.append((rel, html))
    return out


def main() -> int:
    dry_run = "--dry-run" in sys.argv

    if not MODELS_DIR.is_dir():
        print(f"Error: models doc dir not found: {MODELS_DIR}")
        return 1

    print(f"=== FLAC constitutive-model reference extractor ({'DRY RUN' if dry_run else 'WRITE'}) ===")
    print(f"  source: {MODELS_DIR}")
    print(f"  output: {OUT_DIR}\n")

    index_models: list[dict[str, Any]] = []
    written = 0
    skipped = 0

    for source_rel, html_path in iter_model_html():
        try:
            html = html_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            print(f"  [READ ERR] {source_rel}: {exc}")
            skipped += 1
            continue

        dir_name = source_rel.split("/", 1)[0]
        doc = build_model_doc(html, source_rel, dir_name)
        if doc is None:
            print(f"  [SKIP] {source_rel}: no kwd: property ids")
            skipped += 1
            continue

        model = doc["model"]
        prop_count = len(doc["property_groups"][0]["properties"])
        index_models.append(
            {
                "name": model,
                "file": f"{model}.json",
                "full_name": doc["full_name"],
                "description": doc["description"][:120],
                "property_count": prop_count,
            }
        )

        if not dry_run:
            OUT_DIR.mkdir(parents=True, exist_ok=True)
            (OUT_DIR / f"{model}.json").write_text(
                json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        print(f"  [{model:24s}] {prop_count:2d} properties  <- {source_rel}")
        written += 1

    index_models.sort(key=lambda m: m["name"])
    index = {
        "type": "constitutive_model_properties",
        "description": (
            "Reference documentation for FLAC zone constitutive (material) "
            "model properties. Each zone constitutive model has specific "
            "properties controlling its mechanical/creep behavior. Use when "
            "setting properties via 'zone cmodel assign' + 'zone property', "
            "or the Python SDK."
        ),
        "usage_contexts": [
            "zone cmodel assign <name> [range ...]",
            "zone property <prop> <value> [range cmodel-name <name>]",
            "zone property-distribution <prop> ... [range ...]",
            "Python: zone.set_prop('<prop>', value)",
        ],
        "property_metadata_fields": {
            "keyword": "Property name used in 'zone property' commands",
            "symbol": "Mathematical symbol used in the model documentation",
            "description": "Description including physical meaning and units",
            "type": "Coarse data type (FLT=float, BOOL=boolean) — heuristic",
            "default": "Default value if documented",
            "dim": (
                "Present (value '3D') only for the dip/dip-direction "
                "weak-plane orientation keywords, which FLAC2D rejects "
                "(it uses 'angle'). Self-evidently out-of-plane keywords "
                "(xz/yz/-z) are left untagged. Absent = dimension-agnostic "
                "or obvious from the name."
            ),
        },
        "models": index_models,
    }
    if not dry_run:
        (OUT_DIR / "index.json").write_text(
            json.dumps(index, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    print(
        f"\n  TOTAL: {written} constitutive-model docs, {skipped} skipped "
        f"{'(dry run, nothing written)' if dry_run else 'written'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
