"""Fetch missing ITASCA 9.0 FLAC Python API docs into bundled JSON resources.

This script intentionally uses only the Python standard library so it can run
in the project dev environment without extra dependencies. It parses Sphinx
HTML pages from docs.itascacg.com into the same JSON shape used by
flac_browse_python_api.
"""

from __future__ import annotations

import html
import json
import re
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "src" / "flac_mcp" / "knowledge" / "resources" / "python_sdk_docs"
MODULES_DIR = DOCS_DIR / "modules"
BASE = "https://docs.itascacg.com/itasca900/common/docproject/source/manual/scripting/python/doc"

MODULE_SPECS: list[dict[str, Any]] = [
    {
        "key": "attach",
        "page": "itasca.attach.html",
        "description": "Functions and classes for working with FLAC3D gridpoint attaches.",
        "classes": [{"name": "Attach", "page": "itasca.attach.Attach.html"}],
    },
    {
        "key": "gridpointarray",
        "page": "itasca.gridpointarray.html",
        "description": "Array interface for FLAC gridpoints.",
        "classes": [],
    },
    {
        "key": "interface",
        "page": "itasca.interface.html",
        "description": "Functions and classes for working with FLAC interfaces.",
        "classes": [{"name": "Interface", "page": "itasca.interface.Interface.html"}],
    },
    {
        "key": "interfacearray",
        "page": "itasca.interfacearray.html",
        "description": "Array interface for FLAC interfaces.",
        "classes": [],
    },
    {
        "key": "interfaceelementarray",
        "page": "itasca.interfaceelementarray.html",
        "description": "Array interface for FLAC interface elements.",
        "classes": [],
    },
    {
        "key": "interfacenodearray",
        "page": "itasca.interfacenodearray.html",
        "description": "Array interface for FLAC interface nodes.",
        "classes": [],
    },
    {
        "key": "vertexarray",
        "page": "itasca.vertexarray.html",
        "description": "Array interface for FLAC model vertices.",
        "classes": [],
    },
    {
        "key": "zonearray",
        "page": "itasca.zonearray.html",
        "description": "Array interface for FLAC zones.",
        "classes": [],
    },
]

EXTRA_CLASSES: list[dict[str, str]] = [
    {"key": "interface.element", "name": "Element", "page": "itasca.interface.element.Element.html"},
    {"key": "interface.node", "name": "Node", "page": "itasca.interface.node.Node.html"},
]


def fetch(page: str) -> str:
    request = urllib.request.Request(
        f"{BASE}/{page}",
        headers={"User-Agent": "Mozilla/5.0 flac-mcp-docs-generator"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def clean(raw: str) -> str:
    raw = re.sub(r"<script.*?</script>", " ", raw, flags=re.S)
    raw = re.sub(r"<style.*?</style>", " ", raw, flags=re.S)
    raw = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(raw)).strip()


def description_from_page(page_html: str) -> str:
    match = re.search(r"<h1>.*?</h1>\s*<p>(.*?)</p>", page_html, flags=re.S)
    return clean(match.group(1)) if match else ""


def parse_entries(page_html: str, id_prefix: str, *, exact_depth: int | None = None) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    pattern = re.compile(
        r'<dt class="sig sig-object py" id="(?P<id>[^"]+)">(?P<sig>.*?)</dt>\s*<dd>(?P<body>.*?)</dd>',
        flags=re.S,
    )
    for match in pattern.finditer(page_html):
        api_id = match.group("id")
        if not api_id.startswith(id_prefix + "."):
            continue
        parts = api_id.split(".")
        if exact_depth is not None and len(parts) != exact_depth:
            continue
        name = parts[-1]
        if name[:1].isupper():
            continue
        signature = clean(match.group("sig"))
        signature = signature.replace("¶", "").strip()
        description = clean(match.group("body"))
        entry: dict[str, Any] = {
            "name": name,
            "signature": signature,
            "description": description or "(no description)",
        }
        return_match = re.search(r"→\s*([^\.]+\.?)", signature)
        if return_match:
            entry["returns"] = {"type": return_match.group(1).strip()}
        entries.append(entry)
    return entries


def method_groups(methods: list[dict[str, Any]]) -> dict[str, str]:
    groups: dict[str, list[str]] = {}
    for method in methods:
        name = method["name"]
        base = name[4:] if name.startswith("set_") else name
        key = base.split("_", 1)[0]
        groups.setdefault(key, []).append(name)
    return {key: ", ".join(values) for key, values in sorted(groups.items())}


def module_dir(module_key: str) -> Path:
    return MODULES_DIR.joinpath(*module_key.split("."))


def module_file(module_key: str) -> str:
    return f"modules/{'/'.join(module_key.split('.'))}/module.json"


def object_file(module_key: str, class_name: str) -> str:
    return f"modules/{'/'.join(module_key.split('.'))}/{class_name}.json"


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    index = json.loads((DOCS_DIR / "index.json").read_text(encoding="utf-8"))
    modules = index.setdefault("modules", {})
    index.setdefault("objects", {})
    quick_ref = index.setdefault("quick_ref", {})

    for spec in MODULE_SPECS:
        key = spec["key"]
        page_html = fetch(spec["page"])
        description = description_from_page(page_html) or spec["description"]
        functions = parse_entries(page_html, f"itasca.{key}", exact_depth=3 + key.count("."))
        write_json(
            module_dir(key) / "module.json",
            {
                "module": f"itasca.{key}",
                "description": description,
                "import_statement": "import itasca",
                "source_url": f"{BASE}/{spec['page']}",
                "functions": functions,
            },
        )
        modules[key] = {
            "description": description,
            "file": module_file(key),
            "functions": [fn["name"] for fn in functions],
        }
        for fn in functions:
            quick_ref[f"itasca.{key}.{fn['name']}"] = f"{module_file(key)}#{fn['name']}"

        for class_spec in spec["classes"]:
            write_class(index, key, class_spec["name"], class_spec["page"])

    for class_spec in EXTRA_CLASSES:
        write_class(index, class_spec["key"], class_spec["name"], class_spec["page"])

    # vec is a common module with prose documentation rather than Sphinx py
    # signatures. Include it in the coverage matrix and root API overview.
    vec_html = fetch("vec.html")
    vec_desc = description_from_page(vec_html) or "Fast length two and three vectors."
    write_json(
        module_dir("vec") / "module.json",
        {
            "module": "vec",
            "description": vec_desc,
            "import_statement": "from vec import vec, vec2, vec3, tens3, stens3",
            "source_url": f"{BASE}/vec.html",
            "functions": [],
            "notes": [clean(vec_html[vec_html.find("<h1>") : vec_html.find('<div class="clearer">')])],
        },
    )
    modules["vec"] = {"description": vec_desc, "file": module_file("vec"), "functions": []}

    write_json(DOCS_DIR / "index.json", index)
    print("Updated Python API docs:", sorted(spec["key"] for spec in MODULE_SPECS) + ["vec"])


def write_class(index: dict[str, Any], module_key: str, class_name: str, page: str) -> None:
    class_html = fetch(page)
    methods = parse_entries(class_html, f"itasca.{module_key}.{class_name}")
    description = description_from_page(class_html) or f"{class_name} object instance in itasca.{module_key}."
    write_json(
        module_dir(module_key) / f"{class_name}.json",
        {
            "class": class_name,
            "description": description,
            "source_url": f"{BASE}/{page}",
            "note": f"Do not instantiate directly; use itasca.{module_key} module functions.",
            "method_groups": method_groups(methods),
            "methods": methods,
        },
    )
    objects = index.setdefault("objects", {})
    quick_ref = index.setdefault("quick_ref", {})
    objects[class_name] = {
        "description": description,
        "file": object_file(module_key, class_name),
        "note": f"Do not instantiate directly; use itasca.{module_key} module functions.",
        "method_groups": method_groups(methods),
    }
    for method in methods:
        quick_ref[f"itasca.{module_key}.{class_name}.{method['name']}"] = (
            f"{object_file(module_key, class_name)}#{method['name']}"
        )


if __name__ == "__main__":
    main()
