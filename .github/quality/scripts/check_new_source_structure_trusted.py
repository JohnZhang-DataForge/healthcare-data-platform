#!/usr/bin/env python3
"""Read-only trusted gate for new component paths and legacy Task dependencies.

Run exclusively from the default-branch checkout under pull_request_target.
The PR checkout is Git data only; never execute, import, build or shell its code.
"""
from __future__ import annotations

import argparse
import ast
from pathlib import Path
import re
import subprocess
import sys

POLICY_SCRIPT = ".github/quality/scripts/check_new_source_structure_trusted.py"
POLICY_TEST = ".github/quality/tests/test_new_source_structure_trusted.py"
TRUSTED_WORKFLOW = ".github/workflows/component-source-structure-trusted.yml"
PROTECTED = frozenset({POLICY_SCRIPT, POLICY_TEST, TRUSTED_WORKFLOW})
SOURCE_ROOTS = (
    "local-data-platform/", "azure-fabric/", "shared-data-engine/",
    "platform-portal/", ".github/workflows/", ".github/quality/",
)
BUSINESS_ROOTS = (
    "local-data-platform/", "azure-fabric/",
    "shared-data-engine/", "platform-portal/",
)
# A semantic "task" or "step" followed by a development counter is
# prohibited in newly introduced production-source and CI paths.
TASK_PATH = re.compile(r"(?i)(?<![a-z0-9])(?:task|step)[_-]?\d+[a-z]?(?![a-z0-9])")
LEGACY_PATH = re.compile(
    r"(?i)(?:local-data-platform/)?"
    r"(?:apps|scripts|sql|spark/(?:apps|manifests)|kubernetes/manifests)/"
    r"(?:task|step)[_-]?\d+[a-z]?/"
)
LEGACY_MODULE = re.compile(r"(?i)(?:^|\.)(?:task|step)[_-]?\d+[a-z]?(?:$|[_.])")
SOURCE_TEXT_SUFFIXES = frozenset({".py", ".sh", ".yml", ".yaml", ".json", ".toml", ".tpl"})
SOURCE_TEXT_NAMES = frozenset({"Dockerfile", "Containerfile"})


def git_output(repo: Path, *args: str) -> bytes:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], stderr=subprocess.PIPE, timeout=30
    )


def git_paths(repo: Path, ref: str) -> set[str]:
    return {p.decode("utf-8") for p in
            git_output(repo, "ls-tree", "-r", "--name-only", "-z", ref).split(b"\0") if p}


def git_changes(repo: Path, base: str, head: str) -> dict[str, str]:
    raw = git_output(repo, "diff", "--no-renames", "--name-status",
                     "--no-ext-diff", "--diff-filter=ADMR", "-z", base, head)
    fields = [p.decode("utf-8") for p in raw.split(b"\0") if p]
    if len(fields) % 2:
        raise ValueError("malformed Git status/path record")
    result = {}
    for i in range(0, len(fields), 2):
        kind, path = fields[i], fields[i + 1]
        if kind not in ("A", "D", "M") or path in result:
            raise ValueError("unrecognized/duplicate Git status")
        result[path] = kind
    return result


def is_owned_source(path: str) -> bool:
    return path.startswith(SOURCE_ROOTS)


def introduced_bad_name(path: str) -> bool:
    return is_owned_source(path) and bool(TASK_PATH.search(path))


def candidate_text(path: str) -> bool:
    if not path.startswith(BUSINESS_ROOTS):
        return False
    name = Path(path).name
    return Path(path).suffix.lower() in SOURCE_TEXT_SUFFIXES or name in SOURCE_TEXT_NAMES


def direct_legacy_dependencies(path: str, content: str) -> list[str]:
    """No new production module may directly couple to an old Task source.

    Existing modules/tests/Workflows keep their operational compatibility
    until the separately approved Clean Slate process completes. New central
    quality tests may intentionally reference existing legacy source.
    """
    if not candidate_text(path):
        return []
    errors = []
    if LEGACY_PATH.search(content):
        errors.append(f"{path}:new-direct-legacy-task-filepath")
    if path.endswith(".py"):
        try:
            tree = ast.parse(content, filename=path)
        except SyntaxError as exc:
            errors.append(f"{path}:invalid-new-python-syntax:{exc.lineno}")
        else:
            names = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    names.append(node.module or "")
            if any(LEGACY_MODULE.search(name) for name in names):
                errors.append(f"{path}:new-direct-legacy-task-import")
    return errors


def evaluate(
    changes: dict[str, str],
    *,
    base_paths: set[str] | None = None,
    head_paths: set[str] | None = None,
    head_text: dict[str, str] | None = None,
) -> list[str]:
    errors = []
    # Initial bootstrap may introduce the policy and trusted workflow.
    # Once present in the PR base, routine PRs may not edit or remove them.
    established = base_paths is not None and TRUSTED_WORKFLOW in base_paths
    for path, kind in sorted(changes.items()):
        if established and path in PROTECTED:
            errors.append(f"{path}:trusted-directory-policy-mutation")
        if kind != "A":
            continue
        if introduced_bad_name(path):
            errors.append(f"{path}:new-task-or-step-source-path")
        if candidate_text(path) and head_text is not None:
            if path not in head_text:
                errors.append(f"{path}:new-source-text-not-provided")
            else:
                errors.extend(direct_legacy_dependencies(path, head_text[path]))
    if established and head_paths is not None and TRUSTED_WORKFLOW not in head_paths:
        errors.append(f"{TRUSTED_WORKFLOW}:trusted-workflow-deleted")
    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--repo-root", required=True, type=Path)
    args = parser.parse_args()
    try:
        base_paths = git_paths(args.repo_root, args.base)
        head_paths = git_paths(args.repo_root, args.head)
        changed = git_changes(args.repo_root, args.base, args.head)
        source = {}
        for path, kind in changed.items():
            if kind != "A" or not candidate_text(path):
                continue
            raw = git_output(args.repo_root, "show", f"{args.head}:{path}")
            if len(raw) > 1024 * 1024:
                raise ValueError(f"new source too large to inspect safely: {path}")
            source[path] = raw.decode("utf-8")
        errors = evaluate(changed, base_paths=base_paths,
                          head_paths=head_paths, head_text=source)
    except (UnicodeError, ValueError, OSError, subprocess.CalledProcessError,
            subprocess.TimeoutExpired) as exc:
        print("SOURCE_STRUCTURE_TRUSTED=FAIL CHECKER_ERROR=" + str(exc))
        return 1
    for error in errors:
        print("SOURCE_STRUCTURE_VIOLATION=" + error)
    print("SOURCE_STRUCTURE_TRUSTED=" + ("FAIL" if errors else "PASS")
          + f"; inspected_files={len(head_paths)}; changes={len(changed)}; cloud_actions=0")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
