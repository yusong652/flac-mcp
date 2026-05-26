#!/usr/bin/env python3
"""Regenerate the FLAC command documentation index command lists.

This keeps the category metadata already present in ``index.json`` and updates
only each category's ``commands`` array by scanning ``commands/**/*.json``.
It is a maintenance helper; dry-run is the default.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
COMMAND_DOCS_ROOT = REPO_ROOT / "src" / "flac_mcp" / "knowledge" / "resources" / "command_docs"
DEFAULT_VERSION = "9.0"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def first_sentence(value: str, max_length: int = 140) -> str:
    text = " ".join(value.split())
    if not text:
        return ""
    sentence = text.split(". ", 1)[0].strip()
    if len(sentence) <= max_length:
        return sentence
    return sentence[: max_length - 3].rstrip() + "..."


def resolve_version_doc(doc: dict[str, Any], version: str = DEFAULT_VERSION) -> dict[str, Any]:
    versions = doc.get("versions")
    if isinstance(versions, dict) and isinstance(versions.get(version), dict):
        return versions[version]
    return doc


def command_entry(
    path: Path,
    command_docs_root: Path,
    existing_entry: dict[str, Any] | None = None,
    *,
    refresh_metadata: bool = False,
) -> tuple[str, dict[str, Any]]:
    doc = load_json(path)
    category = str(doc.get("category") or path.parent.name)
    name = path.stem
    version_doc = resolve_version_doc(doc)
    description = str(version_doc.get("description") or doc.get("description") or "")
    python_alternative = doc.get("python_sdk_alternative") or version_doc.get("python_sdk_alternative") or {}
    generated = {
        "short_description": first_sentence(description),
        "syntax": version_doc.get("syntax"),
        "python_available": bool(python_alternative.get("available", False)),
    }
    entry = dict(existing_entry or {})
    entry["name"] = name
    entry["file"] = path.relative_to(command_docs_root).as_posix()
    for key, value in generated.items():
        if refresh_metadata or key not in entry or entry[key] in ("", None):
            entry[key] = value
    return category, entry


def existing_entries_by_file(index: dict[str, Any]) -> dict[str, dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    categories = index.get("categories", {})
    if not isinstance(categories, dict):
        return entries

    for category in categories.values():
        if not isinstance(category, dict):
            continue
        commands = category.get("commands", [])
        if not isinstance(commands, list):
            continue
        for entry in commands:
            if isinstance(entry, dict) and isinstance(entry.get("file"), str):
                entries[entry["file"]] = entry
    return entries


def build_index(command_docs_root: Path, *, refresh_metadata: bool = False) -> dict[str, Any]:
    index_path = command_docs_root / "index.json"
    index = load_json(index_path)
    categories = index.setdefault("categories", {})
    existing_entries = existing_entries_by_file(index)

    grouped: dict[str, list[dict[str, Any]]] = {}
    for path in sorted((command_docs_root / "commands").rglob("*.json")):
        file_ref = path.relative_to(command_docs_root).as_posix()
        category, entry = command_entry(
            path,
            command_docs_root,
            existing_entries.get(file_ref),
            refresh_metadata=refresh_metadata,
        )
        grouped.setdefault(category, []).append(entry)

    for category_name in sorted(grouped):
        category = categories.setdefault(
            category_name,
            {
                "full_name": category_name,
                "description": "",
            },
        )
        category["commands"] = sorted(grouped[category_name], key=lambda item: str(item["name"]))

    for category_name in list(categories):
        if category_name not in grouped:
            categories[category_name]["commands"] = []

    return index


def run(args: argparse.Namespace) -> int:
    command_docs_root = Path(args.command_docs_root)
    index_path = command_docs_root / "index.json"
    original = index_path.read_text(encoding="utf-8")
    generated = dump_json(build_index(command_docs_root, refresh_metadata=args.refresh_metadata))

    if generated == original:
        print("command index is up to date")
        return 0

    if args.write:
        index_path.write_text(generated, encoding="utf-8")
        print(f"updated {index_path.relative_to(REPO_ROOT)}")
        return 0

    print(f"command index would change: {index_path.relative_to(REPO_ROOT)}")
    return 1 if args.check else 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--command-docs-root", default=str(COMMAND_DOCS_ROOT))
    parser.add_argument("--write", action="store_true", help="Write index.json. Default is dry-run.")
    parser.add_argument("--check", action="store_true", help="Exit 1 if index.json is not up to date.")
    parser.add_argument(
        "--refresh-metadata",
        action="store_true",
        help="Refresh index descriptions, syntax, and python flags from command JSON docs.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    return run(parse_args(sys.argv[1:] if argv is None else argv))


if __name__ == "__main__":
    raise SystemExit(main())
