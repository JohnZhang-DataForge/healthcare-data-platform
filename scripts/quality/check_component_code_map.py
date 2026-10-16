#!/usr/bin/env python3
"""Require Airflow source-map updates for added/removed source; audit all mapped DAG files.

This first component rollout is deliberately narrow. No network or runtime access.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess

AIRFLOW_PREFIX = "airflow/"
CODE_MAP = "documents/components/airflow/CODE.md"
DAG_PREFIX = "airflow/dags/"
SOURCE_SUFFIXES = {".py", ".sh", ".yaml", ".yml", ".json", ".toml"}


def git_lines(*args: str) -> list[str]:
    return subprocess.run(["git", *args], check=True, text=True,
                          capture_output=True).stdout.splitlines()


def is_guarded_source(path: str) -> bool:
    return path.startswith(AIRFLOW_PREFIX) and Path(path).suffix.lower() in SOURCE_SUFFIXES


def added_removed_sources(base: str, head: str) -> list[str]:
    """--no-renames makes a rename trigger the same A/D gate as moves."""
    paths = git_lines("diff", "--no-renames", "--name-only", "--diff-filter=AD",
                      "--no-ext-diff", base, head)
    return sorted(p for p in paths if is_guarded_source(p))


def validate_dag_file_map(contents: str, current_dags: set[str]) -> tuple[list[str], list[str]]:
    """All tracked Airflow DAG Python files must be linked directly and none be stale."""
    linked = set(re.findall(
        r"\]\(\.\./\.\./\.\./(airflow/dags/[^\s)#?]+\.py)\)", contents
    ))
    return sorted(current_dags - linked), sorted(linked - current_dags)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    args = parser.parse_args()

    changed = set(git_lines("diff", "--name-only", "--no-ext-diff", args.base, args.head))
    relevant = added_removed_sources(args.base, args.head)
    print("CODE_MAP_AIRFLOW_SOURCE_ADDED_REMOVED=" + str(len(relevant)))
    for path in relevant:
        print("CODE_MAP_AIRFLOW_CHANGED_SOURCE=" + path)

    if relevant and CODE_MAP not in changed:
        print(f"CODE_MAP_GATE=FAIL; update {CODE_MAP} in the same PR")
        return 1

    map_path = Path(CODE_MAP)
    if not map_path.is_file():
        print(f"CODE_MAP_GATE=FAIL; missing {CODE_MAP}")
        return 1

    current = {
        path for path in git_lines("ls-tree", "-r", "--name-only", args.head, "--", DAG_PREFIX)
        if path.startswith(DAG_PREFIX) and path.endswith(".py")
    }
    missing, obsolete = validate_dag_file_map(map_path.read_text(encoding="utf-8"), current)
    for path in missing:
        print("CODE_MAP_MISSING_LINK=" + path)
    for path in obsolete:
        print("CODE_MAP_STALE_LINK=" + path)
    if missing or obsolete:
        print("CODE_MAP_GATE=FAIL; CODE.md source list does not match git tree")
        return 1

    print("CODE_MAP_GATE=PASS; mapped_dag_files=" + str(len(current)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
