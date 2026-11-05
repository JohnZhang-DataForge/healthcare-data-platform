#!/usr/bin/env python3
"""Read-only trusted Git-tree repository layout guard.

Run this file from the *default branch* checkout under pull_request_target.
Never execute or import code from the untrusted PR candidate checkout.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

BASELINE_FILE = Path(__file__).resolve().parents[1] / "repository-layout-legacy-baseline.txt"
BASELINE_COMMIT = "ee435d8720cfed698e239f767f313addf36a924e"
NATIVE_ROOT = "azure-fabric/workspaces/healthcare-omop/"
NATIVE_OWNERS = {
    "nb_fhir_ingest.Notebook": "documents/systems/azure-fabric/notebooks/CODE.md",
    "pl_fhir_ingest.DataPipeline": "documents/systems/azure-fabric/pipelines/CODE.md",
    "env_healthcare.Environment": "documents/systems/azure-fabric/environments/CODE.md",
    "lh_omop_analytics.Lakehouse": "documents/systems/azure-fabric/CODE.md",
}
SOURCE_ROOTS = ("azure-fabric", "local-data-platform", "platform-portal", "shared-data-engine")
ALLOWED_TOP_LEVEL = frozenset((".github", "azure-fabric", "documents", "local-data-platform", "openspec", "platform-portal", "shared-data-engine", "AGENTS.md", "README.md"))
GUARD_FILES = frozenset((
    ".github/quality/scripts/check_repository_layout.py",
    ".github/quality/scripts/check_component_code_map.py",
    ".github/quality/repository-layout-legacy-baseline.txt",
    ".github/workflows/openspec-trusted-change-gate.yml",
))
DOC_NAME = re.compile(r"(?i)(?:readme|code|architecture|publisher|design|runbook|guide|overview|id-allocation-state-machine)\.(?:md|mdx|rst)$")
TEST_NAME = re.compile(r"(?i)(?:test_[^/]+|[^/]+_test)\.(?:py|js|ts|tsx|jsx)$")


def is_valid_path(path: str) -> bool:
    return bool(path) and not path.startswith("/") and "\\" not in path and all(
        part not in ("", ".", "..") for part in path.split("/")
    )


def legacy_violation(path: str) -> bool:
    """Classify only old source-area docs and tests; no wildcard exemptions."""
    if not is_valid_path(path):
        return False
    parts = path.split("/")
    if parts[0] not in SOURCE_ROOTS or len(parts) == 1 or parts[-1] == "AGENTS.md":
        return False
    if DOC_NAME.fullmatch(parts[-1]) or parts[-1].lower().endswith((".md", ".mdx", ".rst")):
        return True
    if any(part.lower() in ("test", "tests") or part.lower().endswith("_tests") for part in parts[1:-1]) or TEST_NAME.fullmatch(parts[-1]):
        return True
    return False


def load_legacy_baseline(path: Path = BASELINE_FILE) -> frozenset[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    paths = [line.strip() for line in lines if line.strip() and not line.startswith("#")]
    if paths != sorted(set(paths)):
        raise ValueError("legacy baseline must be sorted and unique")
    if not all(legacy_violation(p) for p in paths):
        raise ValueError("legacy baseline contains a non-legacy or unsafe path")
    return frozenset(paths)


def violation(path: str, rule: str, owner: str) -> str:
    return f"PATH={path} RULE={rule} EXPECTED_OWNER={owner}"


def check_layout(base_paths: set[str], head_paths: set[str], changed: set[str], baseline: frozenset[str]) -> list[str]:
    """Pure tree/diff validator; never reads PR-controlled file contents."""
    errors: set[str] = set()
    for path in sorted(head_paths | changed):
        if not is_valid_path(path):
            errors.add(violation(path, "unsafe-git-path", "normalized repository relative path"))
            continue
        if path in GUARD_FILES and path in changed and path in base_paths:
            errors.add(violation(path, "trusted-policy-mutation", "separate approved governance/bootstrap procedure"))
        parts = path.split("/")
        if parts[0] not in ALLOWED_TOP_LEVEL:
            errors.add(violation(path, "unapproved-top-level-module", "approved root module and OpenSpec architecture approval"))
        if path not in head_paths:
            continue
        if path.startswith(".github/quality/") and not (
            path.startswith((".github/quality/tests/", ".github/quality/scripts/", ".github/quality/fixtures/"))
            or path == ".github/quality/repository-layout-legacy-baseline.txt"
        ):
            errors.add(violation(path, "quality-owner", ".github/quality/tests|scripts|fixtures/"))
        if path.startswith(NATIVE_ROOT):
            rest = path[len(NATIVE_ROOT):]
            item = rest.split("/", 1)[0]
            if "/" not in rest or item not in NATIVE_OWNERS or item.endswith(".Warehouse"):
                errors.add(violation(path, "fabric-native-unapproved-item", "existing root-level Fabric Git Item; Warehouse SQL/Writer: azure-fabric/warehouse/"))
            elif path not in base_paths and NATIVE_OWNERS[item] not in changed:
                errors.add(violation(path, "fabric-code-map-sync", NATIVE_OWNERS[item]))
        if legacy_violation(path):
            if path not in baseline or path not in base_paths:
                expected = ".github/quality/tests/" if any(part.lower() in ("test", "tests") or part.lower().endswith("_tests") for part in parts[1:-1]) or TEST_NAME.fullmatch(parts[-1]) else "documents/"
                rule = "new-test-outside-quality" if expected.startswith(".github") else "new-source-document"
                errors.add(violation(path, rule, expected))
        if path.startswith(".github/quality/scripts/") and TEST_NAME.fullmatch(parts[-1]):
            errors.add(violation(path, "misplaced-quality-test", ".github/quality/tests/"))
    return sorted(errors)


def git_paths(repo: Path, ref: str) -> set[str]:
    cmd = ["git", "-C", str(repo), "ls-tree", "-r", "--name-only", "-z", ref]
    completed = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return {p.decode("utf-8") for p in completed.stdout.split(b"\0") if p}


def changed_paths(repo: Path, base: str, head: str) -> set[str]:
    cmd = ["git", "-C", str(repo), "diff", "--no-renames", "--name-only", "-z", base, head]
    completed = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return {p.decode("utf-8") for p in completed.stdout.split(b"\0") if p}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    args = parser.parse_args()
    try:
        baseline = load_legacy_baseline()
        old = git_paths(args.repo_root, args.base)
        new = git_paths(args.repo_root, args.head)
        changed = changed_paths(args.repo_root, args.base, args.head)
        errors = check_layout(old, new, changed, baseline)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f"REPOSITORY_LAYOUT_GATE=FAIL RULE=checker-failure DETAILS={exc}")
        return 1
    for err in errors:
        print("REPOSITORY_LAYOUT_VIOLATION " + err)
    print(f"REPOSITORY_LAYOUT_GATE={'FAIL' if errors else 'PASS'}; base={args.base}; head={args.head}; legacy_exact_paths={len(baseline)}; checked_head_files={len(new)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
