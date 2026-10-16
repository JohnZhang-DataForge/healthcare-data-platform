#!/usr/bin/env python3
"""Validate local Markdown link destinations in tracked repository documents.

Offline, path-only check: does not access the network, evaluate anchors or
change project files. Skips external URLs and links inside fenced code blocks.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from urllib.parse import unquote

REPO = Path(__file__).resolve().parents[2]
LINK_RE = re.compile(r"!?\[[^\]]*\]\(\s*(<[^>]+>|[^\s)]+)")
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


def missing_links(text: str, document: Path, root: Path) -> tuple[int, list[str]]:
    checked = 0
    errors: list[str] = []
    in_fence = False
    for line_no, line in enumerate(text.splitlines(), start=1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for match in LINK_RE.finditer(line):
            original = match.group(1).strip("<>")
            if not original or original.startswith(("#", "//")) or SCHEME_RE.match(original):
                continue
            path = unquote(original.split("#", 1)[0].split("?", 1)[0])
            if not path:
                continue
            checked += 1
            candidate = (document.parent / path).resolve()
            try:
                candidate.relative_to(root.resolve())
            except ValueError:
                errors.append(f"{document.relative_to(root)}:{line_no}: OUTSIDE_REPO {original}")
                continue
            if not candidate.exists():
                errors.append(f"{document.relative_to(root)}:{line_no}: MISSING {original}")
    return checked, errors


def main() -> int:
    tracked = subprocess.check_output(
        ["git", "ls-files", "-z", "--", "*.md", "*.mdx"], cwd=REPO
    ).decode("utf-8").split("\0")
    total = 0
    all_errors: list[str] = []
    files = 0
    for relative in (p for p in tracked if p):
        doc = REPO / relative
        if not doc.is_file():
            continue
        files += 1
        checked, errors = missing_links(doc.read_text(encoding="utf-8"), doc, REPO)
        total += checked
        all_errors.extend(errors)
    for error in all_errors:
        print("DOCUMENTATION_LINK_ERROR=" + error)
    if all_errors:
        print(f"DOCUMENTATION_LINKS_GATE=FAIL; files={files}; checked={total}; missing={len(all_errors)}")
        return 1
    print(f"DOCUMENTATION_LINKS_GATE=PASS; files={files}; checked={total}; missing=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
