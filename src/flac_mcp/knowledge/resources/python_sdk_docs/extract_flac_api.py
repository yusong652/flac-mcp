"""Extract FLAC-unique Python SDK docs (itasca.zone / itasca.gridpoint).

Bridge-introspection-led: ITASCA's embedded Python API carries high-quality
docstrings shaped as ``(params) -> return. Description`` which are
ground-truth for what is actually callable. This extractor is **purely
additive** — it writes only the FLAC-unique modules (``modules/zone/``,
``modules/gridpoint/``) and merges index.json without touching existing PFC
API docs.

No ``keywords.json`` is generated: mechanically decomposing API names into
tokens injects low-value short tokens (e.g. ``init`` from ``model_init``)
that degrade BM25 precision via the partial matcher. The PFC modules ship
*hand-curated* natural-language keywords; FLAC relies on the (rich) API
name + docstring description fields, which give strong search signal on
their own. Curated FLAC keywords can be added later if needed.

Two phases (different processes):

  1. ``introspect_and_write()`` — MUST run inside the FLAC bridge (needs
     ``itasca``). Walk zone/gridpoint module callables + the Zone/Gridpoint
     object classes, parse docstrings, write module/object JSON.
  2. ``patch_index()`` — pure local (no bridge). Merge the generated
     modules/objects/quick_ref entries into index.json.

Usage:
  # inside FLAC bridge (e.g. via flac_execute_code):
  p = r"...\\python_sdk_docs\\extract_flac_api.py"
  g = {"__file__": p}; exec(compile(open(p).read(), p, "exec"), g)
  g["introspect_and_write"]()
  # then locally:
  uv run python .../python_sdk_docs/extract_flac_api.py --patch-index
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any

# Resolve the python_sdk_docs dir relative to this file (location-agnostic).
DOCS_DIR = os.path.dirname(os.path.abspath(__file__))
MODULES_DIR = os.path.join(DOCS_DIR, "modules")
INDEX_PATH = os.path.join(DOCS_DIR, "index.json")

# (module attr, Object class name, human module description)
FLAC_MODULES: list[tuple[str, str, str]] = [
    ("zone", "Zone", "Zone object management — the FLAC continuum (finite-volume) grid"),
    ("gridpoint", "Gridpoint", "Gridpoint object management — nodes of the FLAC continuum grid"),
]

_SIG_RE = re.compile(r"^\((?P<params>.*?)\)\s*->\s*(?P<ret>.*?)\.\s+(?P<desc>.*)$", re.DOTALL)
_SIG_RE_NORET = re.compile(r"^\((?P<params>.*?)\)\s*->\s*(?P<ret>[^.]+)\.?\s*$", re.DOTALL)


def _clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _parse_params(param_str: str) -> list[dict[str, Any]]:
    """Best-effort parse of ``a: int, b=None`` -> parameter dicts."""
    params: list[dict[str, Any]] = []
    for raw in (p.strip() for p in param_str.split(",")):
        if not raw or raw in ("self", "*", "/"):
            continue
        name, ptype, required = raw, "", True
        if "=" in name:
            name = name.split("=", 1)[0].strip()
            required = False
        if ":" in name:
            name, ptype = (s.strip() for s in name.split(":", 1))
        params.append({"name": name.lstrip("*"), "type": ptype, "required": required, "description": ""})
    return params


def _entry(prefix: str, name: str, doc: str | None) -> dict[str, Any]:
    """Build a function/method doc entry from a callable's docstring."""
    cleaned = _clean(doc)
    m = _SIG_RE.match(cleaned) or _SIG_RE_NORET.match(cleaned)
    if m:
        param_str = m.group("params")
        ret = _clean(m.group("ret"))
        desc = _clean(m.groupdict().get("desc") or "")
        signature = f"{prefix}.{name}({param_str}) -> {ret}"
    else:
        param_str, ret, desc = "", "", cleaned
        signature = f"{prefix}.{name}(...)"
    entry: dict[str, Any] = {
        "name": name,
        "signature": signature,
        "description": desc or "(no docstring)",
    }
    parsed = _parse_params(param_str)
    if parsed:
        entry["parameters"] = parsed
    if ret:
        entry["returns"] = {"type": ret, "description": ""}
    return entry


def _group_methods(method_names: list[str]) -> dict[str, list[str]]:
    """Group ``pos/pos_x/set_pos`` -> {'pos': [...]} for method_groups."""
    groups: dict[str, list[str]] = {}
    for n in method_names:
        base = n[4:] if n.startswith("set_") else n
        key = base.split("_")[0] or "misc"
        groups.setdefault(key, []).append(n)
    return groups


def introspect_and_write() -> list[tuple[str, str, int, int]]:
    """Phase 1 — run INSIDE the FLAC bridge (requires ``itasca``)."""
    import itasca  # only available inside the FLAC bridge process

    written: list[tuple[str, str, int, int]] = []
    for mod, cls_name, mod_desc in FLAC_MODULES:
        module = getattr(itasca, mod, None)
        if module is None:
            print(f"  [SKIP] itasca.{mod} absent in this session")
            continue

        func_names = sorted(
            a for a in dir(module) if not a.startswith("_") and a[:1].islower() and callable(getattr(module, a))
        )
        functions = [_entry(f"itasca.{mod}", fn, getattr(getattr(module, fn), "__doc__", "")) for fn in func_names]

        cls = getattr(module, cls_name, None)
        method_names: list[str] = []
        methods: list[dict[str, Any]] = []
        if cls is not None:
            method_names = sorted(a for a in dir(cls) if not a.startswith("_"))
            methods = [_entry(mod, mn, getattr(getattr(cls, mn), "__doc__", "")) for mn in method_names]

        mod_dir = os.path.join(MODULES_DIR, mod)
        os.makedirs(mod_dir, exist_ok=True)

        with open(os.path.join(mod_dir, "module.json"), "w", encoding="utf-8") as f:
            json.dump(
                {
                    "module": f"itasca.{mod}",
                    "description": mod_desc,
                    "import_statement": "import itasca",
                    "functions": functions,
                },
                f,
                indent=2,
                ensure_ascii=False,
            )

        with open(os.path.join(mod_dir, f"{cls_name}.json"), "w", encoding="utf-8") as f:
            json.dump(
                {
                    "class": cls_name,
                    "description": (
                        f"{cls_name} object instance in the FLAC continuum grid. "
                        f"Obtained via itasca.{mod}.find()/list()."
                    ),
                    "note": (
                        f"Do not instantiate directly; use itasca.{mod} module functions. "
                        f"{len(method_names)} methods — see method_groups."
                    ),
                    "method_groups": _group_methods(method_names),
                    "methods": methods,
                },
                f,
                indent=2,
                ensure_ascii=False,
            )

        written.append((mod, cls_name, len(functions), len(methods)))
        print(f"  [{mod}] {len(functions)} funcs, {cls_name} {len(methods)} methods")

    print("introspect_and_write done:", written)
    return written


def patch_index() -> None:
    """Phase 2 — pure local. Merge generated modules into index.json."""
    with open(INDEX_PATH, encoding="utf-8") as f:
        index = json.load(f)

    modules = index.setdefault("modules", {})
    objects = index.setdefault("objects", {})
    quick_ref = index.setdefault("quick_ref", {})

    for mod, cls_name, mod_desc in FLAC_MODULES:
        mod_dir = os.path.join(MODULES_DIR, mod)
        module_json = os.path.join(mod_dir, "module.json")
        object_json = os.path.join(mod_dir, f"{cls_name}.json")
        if not (os.path.exists(module_json) and os.path.exists(object_json)):
            print(f"  [SKIP] {mod} not generated yet (run introspect in bridge first)")
            continue

        with open(module_json, encoding="utf-8") as f:
            mdoc = json.load(f)
        with open(object_json, encoding="utf-8") as f:
            odoc = json.load(f)

        func_names = [fn["name"] for fn in mdoc["functions"]]
        modules[mod] = {
            "description": mod_desc,
            "file": f"modules/{mod}/module.json",
            "functions": func_names,
        }
        objects[cls_name] = {
            "description": f"{cls_name} object instance — FLAC continuum grid",
            "file": f"modules/{mod}/{cls_name}.json",
            "note": odoc.get("note", ""),
            "method_groups": {g: ", ".join(ms) for g, ms in odoc.get("method_groups", {}).items()},
        }
        for fn in func_names:
            quick_ref[f"itasca.{mod}.{fn}"] = f"modules/{mod}/module.json#{fn}"
        for me in odoc.get("methods", []):
            quick_ref[f"itasca.{mod}.{cls_name}.{me['name']}"] = f"modules/{mod}/{cls_name}.json#{me['name']}"
        print(f"  [index] {mod}: +{len(func_names)} funcs, +{len(odoc.get('methods', []))} methods")

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
    print("patch_index done ->", INDEX_PATH)


if __name__ == "__main__":
    if "--patch-index" in sys.argv:
        patch_index()
    else:
        introspect_and_write()
