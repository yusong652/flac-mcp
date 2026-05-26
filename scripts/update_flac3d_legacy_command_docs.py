#!/usr/bin/env python3
"""Generate FLAC3D 6.0/7.0 command availability blocks.

The bundled 9.0 command JSON files contain the detailed syntax used by the MCP
tools. This script verifies whether each bundled command is listed in the
official legacy FLAC3D command indexes, then writes a 6.0/7.0 version block:

- listed in the official legacy index: clone the 9.0 syntax block and attach
  legacy_documentation provenance metadata;
- absent from the official legacy index: mark the command unavailable for that
  version.

The script is intentionally conservative. It defaults to dry-run mode; pass
``--write`` to update files.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
import time
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
COMMAND_DOCS_ROOT = REPO_ROOT / "src" / "flac_mcp" / "knowledge" / "resources" / "command_docs"
DEFAULT_TMP = REPO_ROOT / ".tmp"

SOURCE_URLS = {
    "6.0": [
        "https://docs.itascacg.com/pfc600/flac3d/docproject/source/elements/command_summary.html",
        "https://docs.itascacg.com/pfc600/flac3d/sel/doc/manual/sel_manual/sel_commands/sel_commands.html",
    ],
    "7.0": [
        "https://docs.itascacg.com/flac3d700/contents.html",
    ],
}

SOURCE_LABELS = {
    "6.0": "official FLAC3D 6.0 command indexes",
    "7.0": "official FLAC3D 7.0 contents command index",
}

DEFAULT_HTML = {
    "6.0": [
        DEFAULT_TMP / "flac3d600_command_summary.html",
        DEFAULT_TMP / "flac3d600_sel_commands.html",
    ],
    "7.0": [
        DEFAULT_TMP / "flac3d700_contents.html",
    ],
}

COMMAND_HREF_RE = re.compile(r"cmd_([A-Za-z0-9_.-]+)\.html(?:#[A-Za-z0-9_.-]+)?")
ANCHOR_RE = re.compile(r"<a\b(?P<attrs>[^>]*)>(?P<body>.*?)</a>", re.IGNORECASE | re.DOTALL)
HREF_RE = re.compile(r'href="(?P<href>[^"]+)"', re.IGNORECASE)
FISHCMD_RE = re.compile(r'<span[^>]*class="[^"]*\bfishcmd\b[^"]*"[^>]*>(.*?)</span>', re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")
COMMAND_DT_RE = re.compile(r'<dt\b[^>]*id="command:[^"]+"[^>]*>(?P<body>.*?)</dt>', re.IGNORECASE | re.DOTALL)
KEYWORD_DT_RE = re.compile(
    r'<dt\b[^>]*id="kwd:(?P<id>[^"]+)"[^>]*>(?P<body>.*?)</dt>',
    re.IGNORECASE | re.DOTALL,
)
PARAGRAPH_RE = re.compile(r"<p\b[^>]*>(?P<body>.*?)</p>", re.IGNORECASE | re.DOTALL)

LEGACY_COMMAND_ALIASES = {
    "sketch edge zone-length": "extrude edge length",
    "sketch edge zone-length-default": "extrude edge length-default",
}

PREFIX_MATCH_ALLOWED = {
    "building-blocks block snapon",
    "building-blocks face snapon",
    "building-blocks edge snapon",
    "building-blocks point snapon",
    "building-blocks point move-to",
}


@dataclass(frozen=True)
class LegacySource:
    version: str
    html_paths: list[Path]
    commands: set[str]
    detail_urls: dict[str, str]


@dataclass(frozen=True)
class ParsedCommandPage:
    command: str
    syntax: str
    description: str
    keywords: list[dict[str, str]]
    url: str


def _normalize_label(value: str) -> str:
    return " ".join(unescape(value).replace("\xa0", " ").split()).lower()


def _clean_text(value: str) -> str:
    cleaned = " ".join(unescape(value).replace("\xa0", " ").split())
    cleaned = re.sub(r"\s+([,.;:])", r"\1", cleaned)
    cleaned = re.sub(r"\s+\)", ")", cleaned)
    cleaned = re.sub(r"\(\s+", "(", cleaned)
    return cleaned.strip()


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_entityref(self, name: str) -> None:
        self.parts.append(unescape(f"&{name};"))

    def handle_charref(self, name: str) -> None:
        self.parts.append(unescape(f"&#{name};"))

    def text(self) -> str:
        return _clean_text("".join(self.parts))


def html_text(fragment: str) -> str:
    parser = TextExtractor()
    parser.feed(fragment)
    return parser.text()


def _command_from_href(value: str) -> str | None:
    match = COMMAND_HREF_RE.search(value)
    if not match:
        return None
    return _normalize_label(match.group(1).replace(".", " "))


def _command_from_fishcmd_html(value: str) -> str:
    text = TAG_RE.sub("", value)
    return _normalize_label(text)


def _index_base_url(version: str, path: Path) -> str:
    if version == "7.0":
        return "https://docs.itascacg.com/flac3d700/contents.html"
    if path.name == "flac3d600_sel_commands.html":
        return "https://docs.itascacg.com/pfc600/flac3d/sel/doc/manual/sel_manual/sel_commands/sel_commands.html"
    return "https://docs.itascacg.com/pfc600/flac3d/docproject/source/elements/command_summary.html"


def parse_command_index(version: str, paths: list[Path]) -> tuple[set[str], dict[str, str]]:
    """Extract command labels and detail URLs from official command indexes."""
    commands: set[str] = set()
    detail_urls: dict[str, str] = {}
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing command index HTML file(s): " + ", ".join(missing))

    for path in paths:
        html = path.read_text(encoding="utf-8", errors="ignore")
        base_url = _index_base_url(version, path)
        for match in ANCHOR_RE.finditer(html):
            attrs = match.group("attrs")
            body = match.group("body")
            href_match = HREF_RE.search(attrs)
            if not href_match or "cmd_" not in href_match.group("href"):
                continue

            url = urljoin(base_url, href_match.group("href"))
            labels = set()
            href_label = _command_from_href(href_match.group("href"))
            if href_label:
                labels.add(href_label)
            text_label = _command_from_fishcmd_html(body)
            if text_label:
                labels.add(text_label)
            for label in labels:
                commands.add(label)
                detail_urls.setdefault(label, url)

    return {command for command in commands if command}, detail_urls


def command_files(command_docs_root: Path) -> list[Path]:
    return sorted((command_docs_root / "commands").rglob("*.json"))


def legacy_command_label(command_doc: dict[str, Any]) -> str | None:
    versions = command_doc.get("versions")
    if not isinstance(versions, dict):
        return None

    base_doc = versions.get("9.0")
    if not isinstance(base_doc, dict):
        return None

    command = base_doc.get("command")
    if not isinstance(command, str) or not command.strip():
        return None

    label = _normalize_label(command)
    if label in LEGACY_COMMAND_ALIASES:
        return LEGACY_COMMAND_ALIASES[label]
    if label.startswith("sketch "):
        return "extrude " + label.removeprefix("sketch ")
    return label


def is_listed_in_legacy_index(label: str, commands: set[str]) -> bool:
    if label in commands:
        return True
    # Some official contents entries include an additional keyword segment in
    # the href, for example "building-blocks block snapon id", while the
    # command page title is "building-blocks block snapon".
    return label in PREFIX_MATCH_ALLOWED and any(command.startswith(label + " ") for command in commands)


def detail_url_for_label(label: str, urls: dict[str, str]) -> str | None:
    if label in urls:
        return urls[label]
    if label in PREFIX_MATCH_ALLOWED:
        for candidate, url in urls.items():
            if candidate.startswith(label + " "):
                return url
    return None


def cache_path_for_url(cache_root: Path, version: str, url: str) -> Path:
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
    filename = Path(url.split("#", 1)[0]).name
    return cache_root / version.replace(".", "_") / f"{digest}_{filename}"


def fetch_url(url: str, timeout: float) -> str:
    request = Request(url, headers={"User-Agent": "flac-mcp-docs-maintenance/1.0"})
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="ignore")


def ensure_detail_page(
    url: str, cache_root: Path, version: str, *, fetch: bool, timeout: float, delay: float
) -> Path | None:
    path = cache_path_for_url(cache_root, version, url)
    if path.exists():
        return path
    if not fetch:
        return None

    path.parent.mkdir(parents=True, exist_ok=True)
    html = fetch_url(url, timeout)
    path.write_text(html, encoding="utf-8")
    if delay > 0:
        time.sleep(delay)
    return path


def _keyword_name(raw_id: str, command_label: str) -> str:
    prefix = command_label.replace(" ", ".") + "."
    raw = raw_id.lower()
    if raw.startswith(prefix):
        raw = raw[len(prefix) :]
    return raw.replace(".", "-")


def _description_after(html: str, start: int, end: int | None = None) -> str:
    fragment = html[start:end]
    for match in PARAGRAPH_RE.finditer(fragment):
        body = match.group("body")
        text = html_text(body)
        lowered = text.lower()
        if not text:
            continue
        if lowered in {"primary keywords:", "keyword block"} or lowered.endswith(" modifiers"):
            continue
        if "#kwd:" in body:
            continue
        return text
    return ""


def parse_command_page(html: str, command_label: str, url: str) -> ParsedCommandPage | None:
    command_match = COMMAND_DT_RE.search(html)
    if not command_match:
        return None

    syntax = html_text(command_match.group("body"))
    if not syntax:
        return None

    first_keyword = KEYWORD_DT_RE.search(html, command_match.end())
    description = _description_after(html, command_match.end(), first_keyword.start() if first_keyword else None)
    keywords: list[dict[str, str]] = []
    keyword_matches = list(KEYWORD_DT_RE.finditer(html))
    for index, match in enumerate(keyword_matches):
        name = _keyword_name(match.group("id"), command_label)
        keyword_syntax = html_text(match.group("body"))
        next_start = keyword_matches[index + 1].start() if index + 1 < len(keyword_matches) else None
        keyword_description = _description_after(html, match.end(), next_start)
        if not name or not keyword_syntax:
            continue
        entry = {"name": name, "syntax": keyword_syntax}
        if keyword_description:
            entry["description"] = keyword_description
        keywords.append(entry)

    return ParsedCommandPage(
        command=command_label,
        syntax=syntax,
        description=description,
        keywords=keywords,
        url=url,
    )


def _replace_legacy_command(value: Any, base_label: str, legacy_label: str) -> Any:
    if not isinstance(value, str):
        return value
    if value.lower().startswith(base_label):
        return legacy_label + value[len(base_label) :]
    return value


def build_available_version_doc(
    base_doc: dict[str, Any],
    version: str,
    legacy_label: str,
    parsed_page: ParsedCommandPage | None = None,
) -> dict[str, Any]:
    if parsed_page is not None:
        version_doc: dict[str, Any] = {
            "command": parsed_page.command,
            "syntax": parsed_page.syntax,
        }
        if parsed_page.description:
            version_doc["description"] = parsed_page.description
        if parsed_page.keywords:
            version_doc["keywords"] = parsed_page.keywords
        syntax_basis = f"official FLAC3D {version} detailed command page"
        source_urls = [parsed_page.url]
    else:
        version_doc = copy.deepcopy(base_doc)
        base_label = _normalize_label(str(base_doc.get("command", "")))
        version_doc["command"] = _replace_legacy_command(version_doc.get("command"), base_label, legacy_label)
        version_doc["syntax"] = _replace_legacy_command(version_doc.get("syntax"), base_label, legacy_label)
        syntax_basis = "bundled 9.0 command documentation with the legacy command prefix normalized"
        source_urls = SOURCE_URLS[version]

    version_doc["legacy_documentation"] = {
        "availability_verified": True,
        "source": SOURCE_LABELS[version],
        "source_urls": source_urls,
        "syntax_basis": syntax_basis,
        "target_version": version,
    }
    return version_doc


def build_unavailable_version_doc(version: str) -> dict[str, Any]:
    return {
        "available": False,
        "reason": f"Not listed in the {SOURCE_LABELS[version]}.",
        "source_urls": SOURCE_URLS[version],
        "target_version": version,
    }


def _is_script_managed_version_doc(version_doc: Any) -> bool:
    if not isinstance(version_doc, dict):
        return False
    if isinstance(version_doc.get("legacy_documentation"), dict):
        return True
    return (
        version_doc.get("available") is False
        and isinstance(version_doc.get("source_urls"), list)
        and isinstance(version_doc.get("target_version"), str)
    )


def updated_doc(
    command_doc: dict[str, Any],
    sources: dict[str, LegacySource],
    *,
    refresh_existing: bool = False,
    cache_root: Path,
    fetch_pages: bool = False,
    parse_pages: bool = False,
    fetch_timeout: float = 20.0,
    fetch_delay: float = 0.0,
) -> dict[str, Any] | None:
    label = legacy_command_label(command_doc)
    versions = command_doc.get("versions")
    if label is None or not isinstance(versions, dict) or not isinstance(versions.get("9.0"), dict):
        return None

    new_doc = copy.deepcopy(command_doc)
    new_versions = new_doc["versions"]
    base_doc = versions["9.0"]

    for version, source in sources.items():
        existing = versions.get(version)
        if existing is not None and not refresh_existing and not _is_script_managed_version_doc(existing):
            continue

        if is_listed_in_legacy_index(label, source.commands):
            parsed_page = None
            detail_url = detail_url_for_label(label, source.detail_urls)
            if parse_pages and detail_url:
                detail_path = ensure_detail_page(
                    detail_url,
                    cache_root,
                    version,
                    fetch=fetch_pages,
                    timeout=fetch_timeout,
                    delay=fetch_delay,
                )
                if detail_path:
                    parsed_page = parse_command_page(
                        detail_path.read_text(encoding="utf-8", errors="ignore"), label, detail_url
                    )
            new_versions[version] = build_available_version_doc(base_doc, version, label, parsed_page)
        else:
            new_versions[version] = build_unavailable_version_doc(version)

    return new_doc


def json_dump(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def run(args: argparse.Namespace) -> int:
    versions = ["6.0", "7.0"] if args.version == "all" else [args.version]
    sources: dict[str, LegacySource] = {}
    for version in versions:
        html_paths = [Path(path) for path in getattr(args, f"html_{version.replace('.', '_')}")]
        commands, detail_urls = parse_command_index(version, html_paths)
        sources[version] = LegacySource(
            version=version,
            html_paths=html_paths,
            commands=commands,
            detail_urls=detail_urls,
        )

    changed: list[Path] = []
    skipped = 0
    for path in command_files(Path(args.command_docs_root)):
        original = path.read_text(encoding="utf-8")
        command_doc = json.loads(original)
        replacement = updated_doc(
            command_doc,
            sources,
            refresh_existing=args.refresh_existing,
            cache_root=Path(args.page_cache_root),
            fetch_pages=args.fetch_pages,
            parse_pages=args.parse_pages,
            fetch_timeout=args.fetch_timeout,
            fetch_delay=args.fetch_delay,
        )
        if replacement is None:
            skipped += 1
            continue

        rendered = json_dump(replacement)
        if rendered == original:
            continue

        changed.append(path)
        if args.write:
            path.write_text(rendered, encoding="utf-8")

    action = "updated" if args.write else "would update"
    print(
        f"{action} {len(changed)} command doc file(s); "
        f"skipped {skipped}; scanned {sum(len(source.commands) for source in sources.values())} legacy command labels"
    )
    for path in changed[: args.list_limit]:
        print(f"  {path.relative_to(REPO_ROOT)}")
    if len(changed) > args.list_limit:
        print(f"  ... {len(changed) - args.list_limit} more")

    if args.check and changed:
        return 1
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--command-docs-root",
        default=str(COMMAND_DOCS_ROOT),
        help="Path to src/flac_mcp/knowledge/resources/command_docs",
    )
    parser.add_argument("--version", choices=["6.0", "7.0", "all"], default="all")
    parser.add_argument("--html-6-0", nargs="+", default=[str(path) for path in DEFAULT_HTML["6.0"]])
    parser.add_argument("--html-7-0", nargs="+", default=[str(path) for path in DEFAULT_HTML["7.0"]])
    parser.add_argument(
        "--page-cache-root",
        default=str(DEFAULT_TMP / "flac3d_legacy_command_pages"),
        help="Directory used to cache official command detail pages.",
    )
    parser.add_argument("--fetch-pages", action="store_true", help="Download missing official detail pages into cache.")
    parser.add_argument(
        "--parse-pages", action="store_true", help="Use cached/fetched detail pages for syntax/keywords."
    )
    parser.add_argument("--fetch-timeout", type=float, default=20.0)
    parser.add_argument("--fetch-delay", type=float, default=0.0)
    parser.add_argument("--write", action="store_true", help="Write changed JSON files. Default is dry-run.")
    parser.add_argument("--check", action="store_true", help="Exit 1 if any file would change.")
    parser.add_argument(
        "--refresh-existing",
        action="store_true",
        help="Overwrite existing 6.0/7.0 blocks even when they were not previously script-managed.",
    )
    parser.add_argument("--list-limit", type=int, default=20, help="Maximum changed files to print.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    return run(parse_args(sys.argv[1:] if argv is None else argv))


if __name__ == "__main__":
    raise SystemExit(main())
