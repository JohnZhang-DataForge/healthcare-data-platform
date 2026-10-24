#!/usr/bin/env python3
"""Reject new Task/Step paths; except pre-approved, blob-identical legacy moves.

Trust the allowlist from the PR BASE, not from the PR HEAD. Approve a mapping
in a separate reviewed PR before attempting relocation. No runtime writes.
"""
from __future__ import annotations
import argparse
import json
import re
import subprocess

PATTERN = re.compile(r"(?i)(?<![A-Za-z0-9])(?:task|step)[-_]?\d+[A-Za-z]?(?![A-Za-z0-9])")
ROOTS = (
    "apps/", "spark/", "airflow/", "sql/", "scripts/", "tests/", "images/",
    "kubernetes/", "contracts/", "azure/", "azure-fabric/", "platform-portal/",
    "config/", "data-platform/", "local-data-platform/", ".github/workflows/", ".github/quality/",
)
LEGACY_ROOTS = (
    "apps/", "spark/", "airflow/", "sql/", "scripts/", "tests/", "images/",
    "kubernetes/", "contracts/", "config/",
)
ALLOWLIST = ".github/legacy-relocations.json"
SHA = re.compile(r"^[0-9a-f]{40}$")


def invalid_path(path: str) -> bool:
    if path.startswith(("docs/", "documents/")) or path.endswith((".md", ".mdx", ".rst", ".txt")):
        return False
    return path.startswith(ROOTS) and bool(PATTERN.search(path))


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=check)


def added_paths(base: str, head: str) -> list[str]:
    return git("diff", "--no-renames", "--name-only", "--diff-filter=A",
               "--no-ext-diff", base, head).stdout.splitlines()


def tree_blob(ref: str, path: str) -> str | None:
    result = git("rev-parse", "--verify", f"{ref}:{path}", check=False)
    value = result.stdout.strip()
    return value if result.returncode == 0 and SHA.fullmatch(value) else None


def authorized_moves(base: str) -> dict[str, str]:
    raw = git("show", f"{base}:{ALLOWLIST}", check=False)
    if raw.returncode:
        raise ValueError(f"Missing approved relocation policy in PR base: {ALLOWLIST}")
    policy = json.loads(raw.stdout)
    if not isinstance(policy, dict) or set(policy) != {"schema_version", "entries"}:
        raise ValueError("Unexpected relocation policy keys")
    if policy["schema_version"] != 1 or not isinstance(policy["entries"], list):
        raise ValueError("Unsupported relocation policy version")
    moves: dict[str, str] = {}
    for entry in policy["entries"]:
        if not isinstance(entry, dict) or set(entry) != {
            "old_path", "new_path", "source_commit", "blob_sha"
        }:
            raise ValueError("Invalid relocation entry fields")
        old, new = entry["old_path"], entry["new_path"]
        commit, blob = entry["source_commit"], entry["blob_sha"]
        if not all(isinstance(x, str) for x in (old, new, commit, blob)):
            raise ValueError("Relocation entry values must be strings")
        if (not old.startswith(LEGACY_ROOTS) or new != "data-platform/" + old
                or not invalid_path(new) or not SHA.fullmatch(commit)
                or not SHA.fullmatch(blob) or new in moves):
            raise ValueError(f"Unapproved or duplicate relocation path: {new}")
        if git("merge-base", "--is-ancestor", commit, base, check=False).returncode:
            raise ValueError(f"Source commit not ancestor of PR base: {old}")
        if tree_blob(commit, old) != blob or tree_blob(base, old) != blob:
            raise ValueError(f"Source blob mismatch before relocation: {old}")
        moves[new] = old
    return moves


def scan(base: str, head: str) -> tuple[list[str], list[str], list[str]]:
    added = added_paths(base, head)
    forbidden = [p for p in added if invalid_path(p)]
    if not forbidden:
        return added, [], []
    moves = authorized_moves(base)
    changed = set(git("diff", "--no-renames", "--name-only", "--no-ext-diff",
                      base, head).stdout.splitlines())
    relocated, violations = [], []
    for target in forbidden:
        source = moves.get(target)
        if (source and source in changed and tree_blob(head, source) is None
                and tree_blob(base, target) is None
                and tree_blob(base, source) == tree_blob(head, target)):
            relocated.append(target)
        else:
            violations.append(target)
    return added, relocated, violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    args = parser.parse_args()
    try:
        added, relocated, violations = scan(args.base, args.head)
    except (ValueError, subprocess.CalledProcessError) as exc:
        print(f"NAMING_GATE=FAIL; unsafe relocation policy: {exc}")
        return 1
    print(f"NAMING_ADDED_PATHS={len(added)}")
    for path in relocated:
        print(f"NAMING_VERIFIED_IDENTICAL_LEGACY_MOVE={path}")
    for path in violations:
        print(f"NAMING_FORBIDDEN_NEW_SOURCE={path}")
    if violations:
        print("NAMING_GATE=FAIL; use component/capability names")
        return 1
    print("NAMING_GATE=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
