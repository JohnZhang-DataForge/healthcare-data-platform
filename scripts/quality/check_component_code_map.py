#!/usr/bin/env python3
"""Require Airflow and apps source-map synchronization, ownership and valid links.

Uses only Git tree/diff and local CODE.md text; no network or runtime access.
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



APP_MAP_PATHS = (
    "documents/components/synthea/CODE.md",
    "documents/components/landing/CODE.md",
    "documents/components/omop/CODE.md",
    "documents/components/airflow/CODE.md",
)
APP_LINK_RE = re.compile(r"\]\(\.\./\.\./\.\./(apps/[^\s)#?]+)\)")


def is_app_source(path: str) -> bool:
    return path.startswith("apps/") and not path.endswith((".md", ".mdx", ".rst", ".txt"))


def app_links(text: str) -> set[str]:
    return {p for p in APP_LINK_RE.findall(text) if is_app_source(p)}


def validate_app_code_maps(mapping: dict[str, str], current: set[str]) -> tuple[list[str], list[str], list[str]]:
    owned: dict[str, list[str]] = {}
    for doc, content in mapping.items():
        for path in app_links(content):
            owned.setdefault(path, []).append(doc)
    return (
        sorted(current - owned.keys()),
        sorted(owned.keys() - current),
        sorted(path for path, owners in owned.items() if len(owners) > 1),
    )


def git_file(ref: str, path: str) -> str:
    result = subprocess.run(["git", "show", f"{ref}:{path}"], text=True, capture_output=True)
    return result.stdout if result.returncode == 0 else ""


def required_app_updates(changed_sources: set[str], before: dict[str, str], after: dict[str, str]) -> set[str]:
    return {
        doc for doc in APP_MAP_PATHS
        if changed_sources.intersection(app_links(before.get(doc, "")) | app_links(after.get(doc, "")))
    }


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

    app_sources = {
        path for path in git_lines("ls-tree", "-r", "--name-only", args.head, "--", "apps/")
        if is_app_source(path)
    }
    after = {doc: Path(doc).read_text(encoding="utf-8") for doc in APP_MAP_PATHS}
    before = {doc: git_file(args.base, doc) for doc in APP_MAP_PATHS}
    missing, stale, duplicates = validate_app_code_maps(after, app_sources)
    for path in missing:
        print("CODE_MAP_APPS_MISSING_LINK=" + path)
    for path in stale:
        print("CODE_MAP_APPS_STALE_LINK=" + path)
    for path in duplicates:
        print("CODE_MAP_APPS_DUPLICATE_OWNER=" + path)
    if missing or stale or duplicates:
        print("CODE_MAP_GATE=FAIL; every apps source needs exactly one owning CODE.md")
        return 1

    changed_app_sources = {
        path for path in git_lines("diff", "--no-renames", "--name-only",
                                   "--diff-filter=AD", "--no-ext-diff", args.base, args.head)
        if is_app_source(path)
    }
    required = required_app_updates(changed_app_sources, before, after)
    for doc in sorted(required - changed):
        print("CODE_MAP_APPS_REQUIRED_UPDATE_MISSING=" + doc)
    if required - changed:
        print("CODE_MAP_GATE=FAIL; edit owning CODE.md in same PR as apps source add/delete/move")
        return 1

    print("CODE_MAP_GATE=PASS; mapped_dag_files=" + str(len(current)) +
          "; mapped_app_files=" + str(len(app_sources)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
