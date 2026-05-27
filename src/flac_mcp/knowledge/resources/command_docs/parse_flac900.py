"""Extract FLAC-unique 9.0 command documentation into the command_docs tree.

This is the FLAC counterpart to ``parse_pfc900.py``. It is **purely
additive**: it only emits the categories that are unique to the FLAC family
(continuum + structural elements + geometry builders) and does NOT touch the
existing PFC-derived JSON or the shared ``common/`` kernel categories
(model/fish/history/geometry/...), which are identical across the unified
ITASCA 9.0 suite and already present.

Source of truth is ``<install>/exe64/doc/out_commands.txt`` — the suite-wide
authoritative command index (``dotted.command  relative/html/path  syntax``).
Product membership is derived from the html path prefix, so the FLAC command
surface needs no hand-maintained category map.

Reuses the shared HTML parser from ``parse_pfc600`` unchanged: the FLAC docs
use the identical Sphinx ``id="command:" / id="kwd:"`` scheme as PFC.

Usage:
    uv run python src/flac_mcp/knowledge/resources/command_docs/parse_flac900.py
    uv run python .../parse_flac900.py --dry-run   # report only, no writes
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from parse_pfc600 import CommandHTMLParser as SharedCommandHTMLParser
    from parse_pfc600 import normalize_syntax as shared_normalize_syntax
except ModuleNotFoundError:
    from .parse_pfc600 import CommandHTMLParser as SharedCommandHTMLParser
    from .parse_pfc600 import normalize_syntax as shared_normalize_syntax

# ---------------------------------------------------------------------------
# Path configuration
# ---------------------------------------------------------------------------

DOC_ROOT = Path("C:/Program Files/Itasca/ItascaSoftware900/exe64/doc")
OUT_COMMANDS = DOC_ROOT / "out_commands.txt"
# Resolve relative to this script so the extractor is repo-location agnostic
# (the old parse_pfc900.py hardcoded a stale C:/Dev/Han/pfc-mcp path).
COMMANDS_DIR = Path(__file__).parent / "commands"

# FLAC-unique categories. A page is included when its dotted command root
# matches ``col1_root`` AND its html path starts with ``html_prefix`` AND
# (when set) ``exclude`` does not appear in the html path.
#
#   category     -> output directory under commands/
#   col1_root    -> first dotted token of the canonical command path
#   html_prefix  -> canonical command-doc directory (disambiguates from
#                    constitutive-model / coupling pages that share a root)
#   exclude      -> substring to skip (structure ships 2D-syntax variants
#                    under .../commands/2d/; the base page is dimension-shared)
FLAC_CATEGORIES: list[tuple[str, str, str, str | None]] = [
    ("zone", "zone", "flac3d/zone/doc/manual/zone_manual/zone_commands/", None),
    ("structure", "structure", "common/sel/doc/manual/sel_manual/", "/commands/2d/"),
    (
        "body",
        "building-blocks",
        "flac3d/body/doc/manual/buildingblocks_manual/building-blocks_commands/",
        None,
    ),
    # extruder: hierarchical keyword ids (sketch.block.create.at.group) are
    # handled by FlacCommandHTMLParser's command-relative naming.
    ("extruder", "sketch", "flac3d/extruder/doc/manual/sketch_manual/", None),
]

DOC_BASE_URL = "https://docs.itascacg.com/flac3d900/common/docproject/source/manual"


# ---------------------------------------------------------------------------
# out_commands.txt parsing
# ---------------------------------------------------------------------------


def iter_page_lines() -> list[tuple[str, str]]:
    """Yield (dotted_command, relative_html_path) for command *page* lines.

    Keyword anchors (``...#kwd:...``) and non-html targets are skipped — the
    HTML parser extracts keywords from the page itself.
    """
    pages: list[tuple[str, str]] = []
    text = OUT_COMMANDS.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        parts = line.split(None, 2)
        if len(parts) < 2:
            continue
        cmd, rel = parts[0], parts[1]
        if "#" in rel or not rel.endswith(".html"):
            continue
        pages.append((cmd, rel.replace("\\", "/")))
    return pages


def subcommand_key(dotted_cmd: str, col1_root: str) -> str:
    """``structure.beam.create`` + root ``structure`` -> ``beam-create``."""
    rest = dotted_cmd[len(col1_root) :].lstrip(".")
    return rest.replace(".", "-")


def build_search_keywords(subcommand: str, command_name: str) -> list[str]:
    """Lightweight token set for BM25 keyword-field matching."""
    tokens: list[str] = []
    for tok in subcommand.split("-"):
        if tok and tok not in tokens:
            tokens.append(tok)
    for tok in command_name.split():
        low = tok.lower()
        if low and low not in tokens:
            tokens.append(low)
    return tokens


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


class FlacCommandHTMLParser(SharedCommandHTMLParser):  # type: ignore[misc, valid-type]
    """Shared parser + command-relative keyword names.

    The base parser derives a keyword name from ``id.split(".")[-1]``. That
    is fine for flat ids (``kwd:zone.create.brick`` -> ``brick``) but
    collapses *hierarchical* ids — extruder ships
    ``kwd:sketch.block.create.at`` and ``kwd:sketch.block.create.at.group``,
    both of which the base parser names ``at`` / ``group`` (the latter
    colliding across every parent). This subclass instead strips the
    command's own id path, yielding the keyword path *relative to the
    command* (``at``, ``at-group``, ``automatic``, ``automatic-group``).

    Backward-compatible: for flat ids the relative path is exactly the last
    token, so zone/structure/body output is byte-identical to the base
    parser. The shared ``parse_pfc600`` parser is left untouched so pfc-mcp,
    which consumes it, is unaffected.
    """

    def __init__(self) -> None:
        super().__init__()
        self._command_id_path = ""

    def _kwd_name_from_id(self, id_: str) -> str:
        rawkey = id_
        for prefix in ("kwd:", "keyword:"):
            if rawkey.startswith(prefix):
                rawkey = rawkey[len(prefix) :]
                break
        cmd = self._command_id_path
        if cmd and rawkey.startswith(cmd + "."):
            rel = rawkey[len(cmd) + 1 :]
        else:
            # Fallback also drops the kwd:/keyword: prefix, which fixes
            # stray names like ``kwd:distinct`` from prefix-only ids.
            rel = rawkey.split(".")[-1]
        return rel.replace(".", "-")

    def handle_starttag(self, tag: str, attrs: list) -> None:  # type: ignore[override]
        id_ = dict(attrs).get("id", "")
        if tag == "dt" and id_.startswith("command:"):
            self._command_id_path = id_[len("command:") :]
        super().handle_starttag(tag, attrs)
        if tag == "dt" and (id_.startswith("kwd:") or id_.startswith("keyword:")):
            # Override the base parser's last-token name with the
            # command-relative path (set just above by super()).
            self._current_kwd_id = self._kwd_name_from_id(id_)


def parse_html_file(html_path: Path) -> dict | None:
    try:
        content = html_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"    [READ ERROR] {html_path}: {exc}")
        return None

    parser = FlacCommandHTMLParser()
    parser.feed(content)
    return {
        "command": parser.command_name,
        "syntax": parser.command_syntax,
        "keywords": parser.keywords,
        "description": parser.description,
    }


def _dedupe_keywords(keywords: list[dict]) -> list[dict]:
    """Drop later keywords whose name already appeared.

    The shared parser derives a keyword name from ``id.split(".")[-1]``.
    For categories with *hierarchical* keyword ids (notably extruder's
    ``...create.at`` / ``...create.at.group``) this flattens distinct
    sub-keywords onto the same trailing token; keep the first, drop the
    collisions rather than emit ``['group', 'group', ...]`` noise. This
    matches the existing flat-keyword behaviour of the PFC docs.
    """
    seen: set[str] = set()
    out: list[dict] = []
    for kw in keywords:
        name = kw.get("name", "")
        if name in seen:
            continue
        seen.add(name)
        out.append(kw)
    return out


def build_doc(category: str, subcommand: str, dotted_cmd: str, parsed: dict) -> dict:
    # out_commands.txt's dotted path is the authoritative command identity;
    # the h1 is unreliable (extruder's h1 holds only the trailing verb).
    command_name = dotted_cmd.replace(".", " ")
    keywords = _dedupe_keywords(parsed["keywords"])
    return {
        "category": category,
        "search_keywords": build_search_keywords(subcommand, command_name),
        "description": parsed["description"],
        # Per-command Python availability is determined in the later
        # Python-API phase; default conservatively so the adapter is happy.
        "python_sdk_alternative": {"available": False},
        "versions": {
            "9.0": {
                "command": command_name,
                "syntax": shared_normalize_syntax(parsed["syntax"]),
                "keywords": keywords,
                # FLAC command HTML has no structured <example> blocks
                # (same limitation parse_pfc900 worked around for PFC).
                "examples": [],
            }
        },
    }


def process_category(
    category: str,
    col1_root: str,
    html_prefix: str,
    exclude: str | None,
    pages: list[tuple[str, str]],
    dry_run: bool,
) -> tuple[int, int]:
    cat_dir = COMMANDS_DIR / category
    written = 0
    skipped = 0
    seen: set[str] = set()

    for dotted_cmd, rel in pages:
        if dotted_cmd.split(".", 1)[0] != col1_root:
            continue
        if not rel.startswith(html_prefix):
            continue
        if exclude and exclude in rel:
            continue

        sub = subcommand_key(dotted_cmd, col1_root)
        if not sub:
            # Bare root page (e.g. category landing); no command payload.
            continue
        if sub in seen:
            print(f"    [DUP] {category}/{sub} ({dotted_cmd}) — keeping first")
            continue
        seen.add(sub)

        parsed = parse_html_file(DOC_ROOT / rel)
        if parsed is None or not parsed["command"]:
            print(f"    [SKIP] {dotted_cmd}: parse produced no command")
            skipped += 1
            continue

        doc = build_doc(category, sub, dotted_cmd, parsed)
        if not dry_run:
            cat_dir.mkdir(parents=True, exist_ok=True)
            out = cat_dir / f"{sub}.json"
            out.write_text(
                json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        written += 1

    return written, skipped


def main() -> int:
    dry_run = "--dry-run" in sys.argv

    if not OUT_COMMANDS.exists():
        print(f"Error: command index not found: {OUT_COMMANDS}")
        return 1

    print(f"=== FLAC 9.0 command extractor ({'DRY RUN' if dry_run else 'WRITE'}) ===")
    print(f"  index : {OUT_COMMANDS}")
    print(f"  output: {COMMANDS_DIR}\n")

    pages = iter_page_lines()
    total_written = 0
    for category, root, prefix, exclude in FLAC_CATEGORIES:
        written, skipped = process_category(category, root, prefix, exclude, pages, dry_run)
        total_written += written
        print(f"  [{category:10s}] {written:4d} written, {skipped} skipped")

    print(f"\n  TOTAL: {total_written} FLAC command docs {'(dry run, nothing written)' if dry_run else 'written'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
