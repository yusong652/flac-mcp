#!/usr/bin/env python3
"""Validate bundled FLAC command documentation resources."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
COMMAND_DOCS_ROOT = REPO_ROOT / "src" / "flac_mcp" / "knowledge" / "resources" / "command_docs"
SUPPORTED_VERSIONS = ("6.0", "7.0", "9.0", "9.1", "9.2", "9.3", "9.4", "9.5", "9.6", "9.7")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def validate_index(command_docs_root: Path) -> list[str]:
    errors: list[str] = []
    index = load_json(command_docs_root / "index.json")
    categories = index.get("categories")
    if not isinstance(categories, dict):
        return ["command_docs/index.json: categories must be an object"]

    seen_files: set[str] = set()
    seen_keys: set[tuple[str, str]] = set()
    for category_name, category_data in categories.items():
        commands = category_data.get("commands") if isinstance(category_data, dict) else None
        if not isinstance(commands, list):
            errors.append(f"category {category_name}: commands must be a list")
            continue
        for entry in commands:
            if not isinstance(entry, dict):
                errors.append(f"category {category_name}: command entry must be an object")
                continue
            name = entry.get("name")
            file_ref = entry.get("file")
            if not isinstance(name, str) or not name:
                errors.append(f"category {category_name}: command entry missing name")
            if not isinstance(file_ref, str) or not file_ref:
                errors.append(f"category {category_name} {name}: command entry missing file")
                continue
            key = (str(category_name), str(name))
            if key in seen_keys:
                errors.append(f"duplicate command index entry: {category_name} {name}")
            seen_keys.add(key)
            if file_ref in seen_files:
                errors.append(f"duplicate command file reference: {file_ref}")
            seen_files.add(file_ref)
            path = command_docs_root / file_ref
            if not path.exists():
                errors.append(f"missing command file referenced by index: {file_ref}")
                continue
            doc = load_json(path)
            if doc.get("category") != category_name:
                errors.append(f"{rel(path)}: category {doc.get('category')!r} does not match index {category_name!r}")
            if path.stem != name:
                errors.append(f"{rel(path)}: file stem does not match index name {name!r}")

    indexed_paths = {command_docs_root / file_ref for file_ref in seen_files}
    for path in (command_docs_root / "commands").rglob("*.json"):
        if path not in indexed_paths:
            errors.append(f"{rel(path)}: command file is not referenced by index")
    return errors


def validate_version_doc(path: Path, version: str, version_doc: Any) -> list[str]:
    errors: list[str] = []
    label = f"{rel(path)} versions[{version}]"
    if not isinstance(version_doc, dict):
        return [f"{label}: must be an object"]

    if "alias_of" in version_doc:
        if not isinstance(version_doc.get("alias_of"), str) or not version_doc.get("alias_of"):
            errors.append(f"{label}: alias_of must be a non-empty string")
        return errors

    if version_doc.get("available") is False:
        if not isinstance(version_doc.get("reason"), str) or not version_doc.get("reason"):
            errors.append(f"{label}: unavailable doc must include reason")
        return errors

    command = version_doc.get("command")
    syntax = version_doc.get("syntax")
    if not isinstance(command, str) or not command:
        errors.append(f"{label}: available doc must include command")
    if not isinstance(syntax, str) or not syntax:
        errors.append(f"{label}: available doc must include syntax")

    legacy = version_doc.get("legacy_documentation")
    if version in {"6.0", "7.0"} and legacy is not None:
        if not isinstance(legacy, dict):
            errors.append(f"{label}: legacy_documentation must be an object")
        else:
            if legacy.get("availability_verified") is not True:
                errors.append(f"{label}: legacy_documentation.availability_verified must be true")
            if legacy.get("target_version") != version:
                errors.append(f"{label}: legacy_documentation.target_version must be {version}")
            source_urls = legacy.get("source_urls")
            if not isinstance(source_urls, list) or not source_urls:
                errors.append(f"{label}: legacy_documentation.source_urls must be a non-empty list")
            syntax_basis = legacy.get("syntax_basis")
            if not isinstance(syntax_basis, str) or not syntax_basis:
                errors.append(f"{label}: legacy_documentation.syntax_basis must be set")

    keywords = version_doc.get("keywords")
    if keywords is not None:
        if not isinstance(keywords, list):
            errors.append(f"{label}: keywords must be a list")
        else:
            for index, keyword in enumerate(keywords):
                if not isinstance(keyword, dict):
                    errors.append(f"{label}: keywords[{index}] must be an object")
                    continue
                if not isinstance(keyword.get("name"), str) or not keyword.get("name"):
                    errors.append(f"{label}: keywords[{index}] missing name")
                if not isinstance(keyword.get("syntax"), str) or not keyword.get("syntax"):
                    errors.append(f"{label}: keywords[{index}] missing syntax")
    return errors


def validate_command_files(command_docs_root: Path) -> list[str]:
    errors: list[str] = []
    for path in sorted((command_docs_root / "commands").rglob("*.json")):
        doc = load_json(path)
        versions = doc.get("versions")
        if not isinstance(versions, dict):
            errors.append(f"{rel(path)}: versions must be an object")
            continue
        unknown_versions = sorted(set(versions) - set(SUPPORTED_VERSIONS))
        if unknown_versions:
            errors.append(f"{rel(path)}: unknown versions {unknown_versions}")
        if "9.0" not in versions:
            errors.append(f"{rel(path)}: missing 9.0 version")
        for version, version_doc in versions.items():
            errors.extend(validate_version_doc(path, version, version_doc))
    return errors


def run(args: argparse.Namespace) -> int:
    command_docs_root = Path(args.command_docs_root)
    errors = validate_index(command_docs_root)
    errors.extend(validate_command_files(command_docs_root))

    if errors:
        print(f"found {len(errors)} command documentation issue(s):")
        for error in errors[: args.limit]:
            print(f"  {error}")
        if len(errors) > args.limit:
            print(f"  ... {len(errors) - args.limit} more")
        return 1

    print("command documentation validation passed")
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--command-docs-root", default=str(COMMAND_DOCS_ROOT))
    parser.add_argument("--limit", type=int, default=50, help="Maximum errors to print.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    return run(parse_args(sys.argv[1:] if argv is None else argv))


if __name__ == "__main__":
    raise SystemExit(main())
