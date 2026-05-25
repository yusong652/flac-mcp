"""Fetch official FLAC Python API docs into versioned JSON resources.

The generated snapshots are written under
``src/flac_mcp/knowledge/resources/python_sdk_docs_versions/<product>/<version>``
so they do not overwrite the legacy bundled 9.0 snapshot.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RESOURCES_DIR = ROOT / "src" / "flac_mcp" / "knowledge" / "resources"
VERSIONED_DOCS_ROOT = RESOURCES_DIR / "python_sdk_docs_versions"


@dataclass(frozen=True)
class VersionSpec:
    product: str
    version: str
    base_urls: tuple[str, ...]
    source_url: str


VERSION_SPECS: dict[tuple[str, str], VersionSpec] = {
    ("flac3d", "6.0"): VersionSpec(
        product="flac3d",
        version="6.0",
        base_urls=(
            "https://docs.itascacg.com/pfc600/flac3d/docproject/source/options/python",
            "https://docs.itascacg.com/pfc600/common/docproject/source/manual/scripting/python/doc",
        ),
        source_url="https://docs.itascacg.com/pfc600/flac3d/docproject/source/options/python/itasca.html",
    ),
    ("flac3d", "7.0"): VersionSpec(
        product="flac3d",
        version="7.0",
        base_urls=("https://docs.itascacg.com/flac3d700/common/docproject/source/manual/scripting/python/doc",),
        source_url="https://docs.itascacg.com/flac3d700/common/docproject/source/manual/scripting/python/python.html",
    ),
    ("flac3d", "9.0"): VersionSpec(
        product="flac3d",
        version="9.0",
        base_urls=("https://docs.itascacg.com/itasca900/common/docproject/source/manual/scripting/python/doc",),
        source_url="https://docs.itascacg.com/itasca900/common/docproject/source/manual/scripting/python/python_flac3d.html",
    ),
}

MODULE_SPECS: list[dict[str, Any]] = [
    {"key": "itasca", "page": "itasca.html", "description": "Core simulation control and command execution", "classes": []},
    {"key": "attach", "page": "itasca.attach.html", "description": "Attach condition object management.", "classes": ["Attach"]},
    {"key": "gridpoint", "page": "itasca.gridpoint.html", "description": "Gridpoint object management.", "classes": ["Gridpoint"]},
    {"key": "gridpointarray", "page": "itasca.gridpointarray.html", "description": "Array interface for gridpoints.", "classes": []},
    {"key": "interface", "page": "itasca.interface.html", "description": "Interface object management.", "classes": ["Interface"]},
    {"key": "interfacearray", "page": "itasca.interfacearray.html", "description": "Array interface for interfaces.", "classes": []},
    {
        "key": "interfaceelementarray",
        "page": "itasca.interfaceelementarray.html",
        "description": "Array interface for interface elements.",
        "classes": [],
    },
    {
        "key": "interfacenodearray",
        "page": "itasca.interfacenodearray.html",
        "description": "Array interface for interface nodes.",
        "classes": [],
    },
    {"key": "vertexarray", "page": "itasca.vertexarray.html", "description": "Array interface for model vertices.", "classes": []},
    {"key": "zone", "page": "itasca.zone.html", "description": "Zone object management.", "classes": ["Zone"]},
    {"key": "zonearray", "page": "itasca.zonearray.html", "description": "Array interface for zones.", "classes": []},
]

EXTRA_CLASSES: list[dict[str, str]] = [
    {"key": "interface.element", "name": "Element", "page": "itasca.interface.element.Element.html"},
    {"key": "interface.node", "name": "Node", "page": "itasca.interface.node.Node.html"},
]


def clean(raw: str) -> str:
    raw = re.sub(r"<script.*?</script>", " ", raw, flags=re.S)
    raw = re.sub(r"<style.*?</style>", " ", raw, flags=re.S)
    raw = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(raw)).strip()


def docs_dir(spec: VersionSpec) -> Path:
    return VERSIONED_DOCS_ROOT / spec.product / spec.version


def module_dir(root: Path, module_key: str) -> Path:
    return root / "modules" / Path(*module_key.split("."))


def module_file(module_key: str) -> str:
    return f"modules/{'/'.join(module_key.split('.'))}/module.json"


def object_file(module_key: str, class_name: str) -> str:
    return f"modules/{'/'.join(module_key.split('.'))}/{class_name}.json"


def fetch_page(spec: VersionSpec, page: str) -> tuple[str, str] | None:
    for base_url in spec.base_urls:
        url = f"{base_url}/{page}"
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 flac-mcp-docs-generator"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read().decode("utf-8"), url
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                continue
            raise
    return None


def description_from_page(page_html: str, fallback: str) -> str:
    match = re.search(r"<h1>.*?</h1>\s*<p>(.*?)</p>", page_html, flags=re.S)
    return clean(match.group(1)) if match else fallback


def parse_entries(page_html: str, id_prefix: str, *, exact_depth: int | None = None) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    pattern = re.compile(r"<dt\b(?P<attrs>[^>]*)>(?P<sig>.*?)</dt>", flags=re.S)
    matches = list(pattern.finditer(page_html))
    for index, match in enumerate(matches):
        id_match = re.search(r'\bid="(?P<id>[^"]+)"', match.group("attrs"))
        if not id_match:
            continue
        api_id = id_match.group("id")
        if api_id.startswith(id_prefix + "."):
            parts = api_id.split(".")
        elif exact_depth is None and "." not in api_id:
            parts = [*id_prefix.split("."), api_id]
        else:
            continue
        if exact_depth is not None and len(parts) != exact_depth:
            continue
        name = parts[-1]
        if name[:1].isupper():
            continue
        signature = clean(match.group("sig")).replace("¶", "").strip()
        next_start = matches[index + 1].start() if index + 1 < len(matches) else len(page_html)
        description = clean(page_html[match.end() : next_start])
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
        groups.setdefault(base.split("_", 1)[0], []).append(name)
    return {key: ", ".join(values) for key, values in sorted(groups.items())}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_class(root: Path, spec: VersionSpec, index: dict[str, Any], module_key: str, class_name: str, page: str) -> bool:
    fetched = fetch_page(spec, page)
    if fetched is None:
        return False
    class_html, source_url = fetched
    methods = parse_entries(class_html, f"itasca.{module_key}.{class_name}")
    if not methods:
        return False

    description = description_from_page(class_html, f"{class_name} object instance in itasca.{module_key}.")
    write_json(
        module_dir(root, module_key) / f"{class_name}.json",
        {
            "class": class_name,
            "description": description,
            "source_url": source_url,
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
    return True


def fetch_version(product: str, version: str) -> dict[str, Any]:
    spec = VERSION_SPECS[(product, version)]
    root = docs_dir(spec)
    index: dict[str, Any] = {
        "version": "1.0",
        "product": product,
        "api_version": version,
        "description": f"Official FLAC Python API snapshot for {product} {version}.",
        "source_url": spec.source_url,
        "modules": {},
        "objects": {},
        "quick_ref": {},
    }

    for module_spec in MODULE_SPECS:
        key = module_spec["key"]
        fetched = fetch_page(spec, module_spec["page"])
        if fetched is None:
            print(f"  [skip] {version} {key}: page not found")
            continue
        page_html, source_url = fetched
        exact_depth = 2 if key == "itasca" else 3 + key.count(".")
        functions = parse_entries(page_html, "itasca" if key == "itasca" else f"itasca.{key}", exact_depth=exact_depth)
        if not functions and key != "vec":
            print(f"  [skip] {version} {key}: no functions parsed")
            continue

        description = description_from_page(page_html, str(module_spec["description"]))
        write_json(
            module_dir(root, key) / "module.json",
            {
                "module": "itasca" if key == "itasca" else f"itasca.{key}",
                "description": description,
                "import_statement": "import itasca",
                "source_url": source_url,
                "functions": functions,
            },
        )
        index["modules"][key] = {
            "description": description,
            "file": module_file(key),
            "functions": [fn["name"] for fn in functions],
        }
        prefix = "itasca" if key == "itasca" else f"itasca.{key}"
        for fn in functions:
            index["quick_ref"][f"{prefix}.{fn['name']}"] = f"{module_file(key)}#{fn['name']}"

        for class_name in module_spec["classes"]:
            write_class(root, spec, index, key, class_name, f"itasca.{key}.{class_name}.html")
        print(f"  [{version}] {key}: {len(functions)} funcs")

    for class_spec in EXTRA_CLASSES:
        if write_class(root, spec, index, class_spec["key"], class_spec["name"], class_spec["page"]):
            print(f"  [{version}] {class_spec['key']}.{class_spec['name']}")

    vec_page = fetch_page(spec, "vec.html")
    if vec_page is not None:
        vec_html, vec_url = vec_page
        vec_desc = description_from_page(vec_html, "Fast length two and three vectors.")
        write_json(
            module_dir(root, "vec") / "module.json",
            {
                "module": "vec",
                "description": vec_desc,
                "import_statement": "from vec import vec, vec2, vec3, tens3, stens3",
                "source_url": vec_url,
                "functions": [],
                "notes": [clean(vec_html[vec_html.find("<h1>") : vec_html.find("<div class=\"clearer\">")])],
            },
        )
        index["modules"]["vec"] = {"description": vec_desc, "file": module_file("vec"), "functions": []}

    write_json(root / "index.json", index)
    return index


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--product", default="flac3d", choices=["flac3d"])
    parser.add_argument("--version", required=True, choices=["6.0", "7.0", "9.0"])
    args = parser.parse_args()

    index = fetch_version(args.product, args.version)
    print(
        json.dumps(
            {
                "product": args.product,
                "version": args.version,
                "modules": len(index["modules"]),
                "objects": len(index["objects"]),
                "api_entries": len(index["quick_ref"]),
                "path": str(docs_dir(VERSION_SPECS[(args.product, args.version)])),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
