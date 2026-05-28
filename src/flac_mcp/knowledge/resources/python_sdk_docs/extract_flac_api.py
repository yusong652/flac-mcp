"""Extract FLAC-unique Python SDK docs from a running FLAC runtime.

Bridge-introspection-led: ITASCA's embedded Python API carries high-quality
docstrings shaped as ``(params) -> return. Description`` which are
ground-truth for what is actually callable. This extractor is **purely
additive** — it writes FLAC-specific modules under ``modules/`` and merges
index.json without touching command docs.

No ``keywords.json`` is generated: mechanically decomposing API names into
tokens injects low-value short tokens (e.g. ``init`` from ``model_init``)
that degrade BM25 precision via the partial matcher. The FLAC modules ship
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

# mypy: ignore-errors

import json
import os
import re
import sys

# Resolve the python_sdk_docs dir relative to this file (location-agnostic).
DOCS_DIR = os.path.dirname(os.path.abspath(__file__))
MODULES_DIR = os.path.join(DOCS_DIR, "modules")
INDEX_PATH = os.path.join(DOCS_DIR, "index.json")


def _write_json(path, payload):
    """Write JSON with a trailing newline so files match POSIX/editor conventions."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")


# ITASCA 9.0 Python doc URL template (set to None to skip source_url emission).
SOURCE_URL_TEMPLATE = (
    "https://docs.itascacg.com/itasca900/common/docproject/source/manual/scripting/python/doc/itasca.{path}.html"
)

FLAC_MODULES = [
    {
        "path": "zone",
        "classes": ["Zone"],
        "description": "Zone object management — the FLAC continuum (finite-volume) grid",
    },
    {
        "path": "zonearray",
        "classes": [],
        "description": "Array interface for FLAC3D zones.",
    },
    {
        "path": "gridpoint",
        "classes": ["Gridpoint"],
        "description": "Gridpoint object management — nodes of the FLAC continuum grid",
    },
    {
        "path": "gridpointarray",
        "classes": [],
        "description": "Array interface for FLAC gridpoints.",
    },
    {
        "path": "attach",
        "classes": ["Attach"],
        "description": "Functions and classes for working with FLAC3D gridpoint attaches.",
    },
    {
        "path": "interface",
        "classes": ["Interface"],
        "description": "Functions and classes for working with FLAC interfaces.",
    },
    {
        "path": "interface.element",
        "classes": ["Element"],
        "description": "Functions and classes for working with FLAC interface elements.",
    },
    {
        "path": "interface.node",
        "classes": ["Node"],
        "description": "Functions and classes for working with FLAC interface nodes.",
    },
    {
        "path": "interfacearray",
        "classes": [],
        "description": "Array interface for FLAC interfaces.",
    },
    {
        "path": "interfaceelementarray",
        "classes": [],
        "description": "Array interface for FLAC interface elements.",
    },
    {
        "path": "interfacenodearray",
        "classes": [],
        "description": "Array interface for FLAC interface node.",
    },
    {
        "path": "vertexarray",
        "classes": [],
        "description": "Array interface for Itasca wall vertices.",
    },
]

_SIG_RE = re.compile(r"^\((?P<params>.*?)\)\s*->\s*(?P<ret>.*?)\.\s+(?P<desc>.*)$", re.DOTALL)
_SIG_RE_NORET = re.compile(r"^\((?P<params>.*?)\)\s*->\s*(?P<ret>[^.]+)\.?\s*$", re.DOTALL)


def _clean(text):
    return re.sub(r"\s+", " ", (text or "").strip())


def _parse_params(param_str):
    """Best-effort parse of ``a: int, b=None`` -> parameter dicts."""
    params = []
    for raw in (p.strip() for p in param_str.split(",")):
        if not raw or raw in ("self", "*", "/"):
            continue
        name, ptype, required = raw, "", True
        if "=" in name:
            name = name.split("=", 1)[0].strip()
            required = False
        if ":" in name:
            name, ptype = (s.strip() for s in name.split(":", 1))
        entry = {"name": name.lstrip("*")}
        if ptype:
            entry["type"] = ptype
        entry["required"] = required
        params.append(entry)
    return params


def _entry(prefix, name, doc):
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
    entry = {
        "name": name,
        "signature": signature,
        "description": desc or "(no docstring)",
    }
    parsed = _parse_params(param_str)
    if parsed:
        entry["parameters"] = parsed
    if ret:
        entry["returns"] = {"type": ret}
    return entry


def _group_methods(method_names):
    """Group ``pos/pos_x/set_pos`` -> {'pos': [...]} for method_groups."""
    groups = {}
    for n in method_names:
        base = n[4:] if n.startswith("set_") else n
        key = base.split("_")[0] or "misc"
        groups.setdefault(key, []).append(n)
    return groups


def _get_nested_attr(root, dotted_path):
    current = root
    for part in dotted_path.split("."):
        current = getattr(current, part, None)
        if current is None:
            return None
    return current


def _module_dir(module_path):
    return os.path.join(MODULES_DIR, *module_path.split("."))


def _module_file(module_path):
    return f"modules/{'/'.join(module_path.split('.'))}/module.json"


def _object_file(module_path, class_name):
    return f"modules/{'/'.join(module_path.split('.'))}/{class_name}.json"


def introspect_and_write():
    """Phase 1 — run INSIDE the FLAC bridge (requires ``itasca``)."""
    import itasca  # only available inside the FLAC bridge process

    written = []
    for spec in FLAC_MODULES:
        mod = spec["path"]
        classes = spec["classes"]
        mod_desc = spec["description"]
        module = _get_nested_attr(itasca, mod)
        if module is None:
            print(f"  [SKIP] itasca.{mod} absent in this session")
            continue

        func_names = sorted(
            a for a in dir(module) if not a.startswith("_") and a[:1].islower() and callable(getattr(module, a))
        )
        functions = [_entry(f"itasca.{mod}", fn, getattr(getattr(module, fn), "__doc__", "")) for fn in func_names]

        mod_dir = _module_dir(mod)
        os.makedirs(mod_dir, exist_ok=True)

        module_doc = {
            "module": f"itasca.{mod}",
            "description": mod_desc,
            "import_statement": "import itasca",
        }
        if SOURCE_URL_TEMPLATE:
            module_doc["source_url"] = SOURCE_URL_TEMPLATE.format(path=mod)
        module_doc["functions"] = functions
        _write_json(os.path.join(mod_dir, "module.json"), module_doc)

        class_counts = {}
        for cls_name in classes:
            cls = getattr(module, cls_name, None)
            method_names = []
            methods = []
            if cls is not None:
                method_names = sorted(a for a in dir(cls) if not a.startswith("_"))
                methods = [_entry(mod, mn, getattr(getattr(cls, mn), "__doc__", "")) for mn in method_names]

            object_doc = {
                "class": cls_name,
                "description": f"{cls_name} object instance in itasca.{mod}.",
            }
            if SOURCE_URL_TEMPLATE:
                object_doc["source_url"] = SOURCE_URL_TEMPLATE.format(path=f"{mod}.{cls_name}")
            object_doc["note"] = f"Do not instantiate directly; use itasca.{mod} module functions."
            object_doc["method_groups"] = _group_methods(method_names)
            object_doc["methods"] = methods
            _write_json(os.path.join(mod_dir, f"{cls_name}.json"), object_doc)
            class_counts[cls_name] = len(methods)

        written.append((mod, len(functions), class_counts))
        class_summary = ", ".join(f"{k} {v} methods" for k, v in sorted(class_counts.items()))
        print(f"  [{mod}] {len(functions)} funcs{(', ' + class_summary) if class_summary else ''}")

    print("introspect_and_write done:", written)
    return written


def patch_index() -> None:
    """Phase 2 — pure local. Merge generated modules into index.json."""
    with open(INDEX_PATH, encoding="utf-8") as f:
        index = json.load(f)

    modules = index.setdefault("modules", {})
    objects = index.setdefault("objects", {})
    quick_ref = index.setdefault("quick_ref", {})

    for spec in FLAC_MODULES:
        mod = spec["path"]
        classes = spec["classes"]
        mod_desc = spec["description"]
        mod_dir = _module_dir(mod)
        module_json = os.path.join(mod_dir, "module.json")
        if not os.path.exists(module_json):
            print(f"  [SKIP] {mod} not generated yet (run introspect in bridge first)")
            continue

        with open(module_json, encoding="utf-8") as f:
            mdoc = json.load(f)

        func_names = [fn["name"] for fn in mdoc["functions"]]
        modules[mod] = {
            "description": mod_desc,
            "file": _module_file(mod),
            "functions": func_names,
        }
        for fn in func_names:
            quick_ref[f"itasca.{mod}.{fn}"] = f"{_module_file(mod)}#{fn}"

        method_count = 0
        for cls_name in classes:
            object_json = os.path.join(mod_dir, f"{cls_name}.json")
            if not os.path.exists(object_json):
                continue
            with open(object_json, encoding="utf-8") as f:
                odoc = json.load(f)
            objects[cls_name] = {
                "description": f"{cls_name} object instance in itasca.{mod}",
                "file": _object_file(mod, cls_name),
                "note": odoc.get("note", ""),
                "method_groups": {g: ", ".join(ms) for g, ms in odoc.get("method_groups", {}).items()},
            }
            for me in odoc.get("methods", []):
                quick_ref[f"itasca.{mod}.{cls_name}.{me['name']}"] = f"{_object_file(mod, cls_name)}#{me['name']}"
            method_count += len(odoc.get("methods", []))
        print(f"  [index] {mod}: +{len(func_names)} funcs, +{method_count} methods")

    _write_json(INDEX_PATH, index)
    print("patch_index done ->", INDEX_PATH)


if __name__ == "__main__":
    if "--patch-index" in sys.argv:
        patch_index()
    else:
        introspect_and_write()
