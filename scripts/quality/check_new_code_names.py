#!/usr/bin/env python3
"""Reject NEW maintained source paths named with taskNNN/stepNNN IDs.

Existing legacy files are grandfathered. Do not rename them automatically.
No network, cluster, or cloud operations.
"""
from __future__ import annotations

import argparse
import re
import subprocess

PATTERN = re.compile(r"(?i)(?<![A-Za-z0-9])(?:task|step)[-_]?\d+[A-Za-z]?(?![A-Za-z0-9])")
ROOTS = (
    "apps/", "spark/", "airflow/", "sql/", "scripts/", "tests/", "images/",
    "kubernetes/", "contracts/", "azure/", "platform-portal/", "config/",
    ".github/workflows/",
)


def invalid_path(path: str) -> bool:
    if path.startswith(("docs/", "documents/")) or path.endswith((".md", ".mdx", ".rst", ".txt")):
        return False
    return path.startswith(ROOTS) and bool(PATTERN.search(path))


def added_paths(base: str, head: str) -> list[str]:
    cmd = ["git", "diff", "--no-renames", "--name-only", "--diff-filter=A", "--no-ext-diff", base, head]
    result = subprocess.run(cmd, text=True, capture_output=True, check=True)
    return [p for p in result.stdout.splitlines() if p]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    args = parser.parse_args()
    paths = added_paths(args.base, args.head)
    violations = [p for p in paths if invalid_path(p)]
    print(f"NAMING_ADDED_PATHS={len(paths)}")
    for path in violations:
        print(f"NAMING_FORBIDDEN_NEW_SOURCE={path}")
    if violations:
        print("NAMING_GATE=FAIL; use component/capability names")
        return 1
    print("NAMING_GATE=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
