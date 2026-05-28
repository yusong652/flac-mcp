"""Strip empty placeholder fields from command JSON docs.

Mirrors the cleanup pattern applied in PR #9 to fracture/ and geometry/
across the rest of the command_docs tree, for schema consistency.

Removes, when empty:
  - top-level "notes": []
  - python_sdk_alternative.workaround: ""
  - per-version "examples": []
  - per-version "keywords": [] (only when the version slot is unavailable,
    i.e. has no command/syntax — never on populated slots)
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src" / "flac_mcp" / "knowledge" / "resources" / "command_docs" / "commands"


def clean_doc(doc: dict) -> bool:
    changed = False

    if doc.get("notes") == []:
        del doc["notes"]
        changed = True

    psa = doc.get("python_sdk_alternative")
    if isinstance(psa, dict) and psa.get("workaround") == "":
        del psa["workaround"]
        changed = True

    versions = doc.get("versions")
    if isinstance(versions, dict):
        for vkey, vdoc in versions.items():
            if not isinstance(vdoc, dict):
                continue
            if vdoc.get("examples") == []:
                del vdoc["examples"]
                changed = True
            populated = "command" in vdoc or "syntax" in vdoc
            if not populated and vdoc.get("keywords") == []:
                del vdoc["keywords"]
                changed = True
    return changed


def main() -> int:
    if not ROOT.is_dir():
        print(f"error: {ROOT} not found", file=sys.stderr)
        return 2
    touched = 0
    scanned = 0
    for path in sorted(ROOT.rglob("*.json")):
        scanned += 1
        text = path.read_text(encoding="utf-8")
        doc = json.loads(text)
        if not isinstance(doc, dict):
            continue
        if clean_doc(doc):
            new_text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
            path.write_text(new_text, encoding="utf-8", newline="\n")
            touched += 1
    print(f"scanned={scanned} touched={touched}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
