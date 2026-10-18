#!/usr/bin/env python3
"""Fail-closed OpenSpec Change association for Healthcare pull requests.

This validator consumes a GitHub pull_request event and Git paths. It does not
execute PR-controlled instructions or touch runtime infrastructure.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Callable

SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
SLUG_RE = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
TASK_ID_RE = re.compile(r"\d+(?:\.\d+)+\Z")
TASK_LINE_RE = re.compile(r"^- \[([ x])\] (\d+(?:\.\d+)+)\b", re.MULTILINE)
TAGS = ("OpenSpec-Change", "OpenSpec-Task", "OpenSpec-Exemption")
ARCHIVE_DATE_RE = re.compile(r"20\d{2}-\d{2}-\d{2}-")
REPO = Path(__file__).resolve().parents[3]


def git(*args: str, cwd: Path = REPO) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True,
        check=True,
    ).stdout


def changed_paths(base: str, head: str, root: Path = REPO) -> list[str]:
    if not SHA_RE.fullmatch(base) or not SHA_RE.fullmatch(head):
        raise ValueError("base and head must be full 40-digit lowercase Git SHAs")
    return [p for p in git(
        "diff", "--no-renames", "--name-only", "--diff-filter=ACDMRT",
        "--no-ext-diff", base, head, "--", cwd=root,
    ).splitlines() if p]


def tag_values(body: str, tag: str) -> list[str]:
    # Even a malformed value counts as a declaration, so it cannot silently
    # fall through into another mode.
    return re.findall(rf"(?m)^{re.escape(tag)}:[^\S\n]*([^\n]*)$", body)


def safe_docs_only(path: str) -> bool:
    if path == "README.md":
        return True
    if not path.startswith("documents/") or not path.endswith((".md", ".mdx")):
        return False
    if path == "documents/README.md" or path.endswith("/CODE.md"):
        return False
    return not path.startswith(("documents/architecture/", "documents/engineering/"))


def tracked_tasks(text: str) -> dict[str, bool]:
    result: dict[str, bool] = {}
    for checked, task in TASK_LINE_RE.findall(text):
        if task in result:
            raise ValueError("Duplicate OpenSpec task number: " + task)
        result[task] = checked == "x"
    return result


def is_change_path(path: str, change_id: str) -> bool:
    return path.startswith("openspec/changes/" + change_id + "/")


def is_archive_path(path: str, archived: str) -> bool:
    return path.startswith("openspec/changes/archive/" + archived + "/")


def evaluate(
    paths: list[str], body: str, root: Path,
    base_has_active: Callable[[str], bool] | None = None,
) -> tuple[bool, str]:
    """Return (accepted, reason); root is the PR HEAD tree.

    The only exemption is an explicit docs-only marker plus path allowlist.
    All other changed files require an active Change and matching task update.
    """
    if not paths:
        return False, "No changed files could be identified"
    if len(set(paths)) != len(paths):
        return False, "Duplicate paths in PR diff"
    if not isinstance(body, str):
        return False, "Missing PR description"

    declarations = {tag: tag_values(body, tag) for tag in TAGS}
    for name, values in declarations.items():
        if len(values) > 1:
            return False, f"Duplicate {name} declaration"

    exemptions = declarations["OpenSpec-Exemption"]
    ids = declarations["OpenSpec-Change"]
    task_ids = declarations["OpenSpec-Task"]
    if exemptions:
        if exemptions[0].strip() != "docs-only":
            return False, "Only the explicit docs-only exemption is supported"
        if ids or task_ids:
            return False, "Exemption and Change association are mutually exclusive"
        unsafe = sorted(p for p in paths if not safe_docs_only(p))
        if unsafe:
            return False, "docs-only exemption covers forbidden paths: " + ", ".join(unsafe)
        return True, "docs-only exemption; all paths restricted to safe Markdown"

    if len(ids) != 1 or len(task_ids) != 1:
        return False, "Require OpenSpec-Change and OpenSpec-Task on separate PR body lines"
    change_id, task_id = ids[0].strip(), task_ids[0].strip()
    if not SLUG_RE.fullmatch(change_id):
        return False, "Invalid OpenSpec Change ID"
    if not TASK_ID_RE.fullmatch(task_id):
        return False, "Invalid OpenSpec task number"

    active = root / "openspec" / "changes" / change_id
    archived_parent = root / "openspec" / "changes" / "archive"
    # Only match the exact date-prefixed name, not a guessed fuzzy prefix.
    archives = [
        p for p in archived_parent.glob("*") if p.is_dir()
        and p.name.endswith("-" + change_id)
        and ARCHIVE_DATE_RE.match(p.name)
        and p.name[len(p.name) - len(change_id) - 1:] == "-" + change_id
        and re.fullmatch(rf"20\d{{2}}-\d{{2}}-\d{{2}}-{re.escape(change_id)}", p.name)
    ] if archived_parent.is_dir() else []
    if active.is_dir() and archives:
        return False, "Ambiguous Change: both active and archived at PR HEAD"
    if active.is_dir():
        folder = active
        archive_name = None
        task_diff_path = f"openspec/changes/{change_id}/tasks.md"
    elif len(archives) == 1:
        folder = archives[0]
        archive_name = folder.name
        task_diff_path = f"openspec/changes/archive/{archive_name}/tasks.md"
        if base_has_active is None or not base_has_active(change_id):
            return False, "Archive requires original active Change at PR BASE"
        if not any(p.startswith(f"openspec/changes/{change_id}/") for p in paths):
            return False, "Archive must move the original active Change"
        forbidden = sorted(
            p for p in paths if not (
                p.startswith("openspec/")
                or p.startswith("documents/")
                or p == "AGENTS.md"
            )
        )
        if forbidden:
            return False, "Archive PR must not include runtime or tooling changes: " + ", ".join(forbidden)
    else:
        return False, "Associated active Change absent, or archive is ambiguous/unrecognized"

    required = (".openspec.yaml", "proposal.md", "design.md", "tasks.md")
    missing = [x for x in required if not (folder / x).is_file()]
    if missing:
        return False, "Missing required Change files: " + ", ".join(missing)
    if task_diff_path not in paths:
        return False, "PR must modify its own OpenSpec Change tasks.md"

    tasks = tracked_tasks((folder / "tasks.md").read_text(encoding="utf-8"))
    if not tasks:
        return False, "No real tasks found in associated Change"
    if task_id not in tasks:
        return False, "OpenSpec-Task ID is absent from associated tasks.md"
    if archive_name is not None:
        if not all(tasks.values()):
            return False, "Archive rejected: some tasks are incomplete"
        return True, f"archived Change {change_id} with completed task {task_id}"
    return True, f"active Change {change_id}, linked task {task_id}, tasks.md synchronized"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--event", type=Path, required=True)
    args = parser.parse_args()
    try:
        body = json.loads(args.event.read_text(encoding="utf-8"))["pull_request"]["body"]
        if body is None:
            body = ""
        paths = changed_paths(args.base, args.head)
        def base_has_active(change_id: str) -> bool:
            for filename in (".openspec.yaml", "tasks.md"):
                r = subprocess.run(
                    ["git", "cat-file", "-e",
                     f"{args.base}:openspec/changes/{change_id}/{filename}"],
                    cwd=REPO, capture_output=True, check=False,
                )
                if r.returncode != 0:
                    return False
            return True
        passed, reason = evaluate(paths, body, REPO, base_has_active)
    except (KeyError, ValueError, OSError, UnicodeError, subprocess.CalledProcessError) as ex:
        passed, reason = False, f"Validation error: {ex}"
    print("OPENSPEC_CHANGE_GATE=" + ("PASS" if passed else "FAIL"))
    print("OPENSPEC_CHANGE_GATE_REASON=" + reason)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
