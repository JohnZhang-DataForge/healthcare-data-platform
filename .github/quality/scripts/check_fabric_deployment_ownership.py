#!/usr/bin/env python3
"""Fail-closed offline check for newly added Fabric deployment component paths.

This PR-check is informational until an approved trusted Required Check
consumes the *default-branch* policy. It never performs deployment or imports
candidate source code.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import sys

OWNER_FILE = "azure-fabric/deployment/owners.json"
CODE_MAP = "documents/systems/azure-fabric/deployment/CODE.md"
TRUSTED_WORKFLOW = ".github/workflows/fabric-deployment-ownership-trusted.yml"
PROTECTED_POLICY = frozenset((
    OWNER_FILE,
    ".github/quality/scripts/check_fabric_deployment_ownership.py",
    ".github/quality/tests/azure-fabric/deployment/test_fabric_deployment_ownership.py",
    TRUSTED_WORKFLOW,
))

EXPECTED = frozenset({"notebook", "pipeline", "environment", "lakehouse",
                     "warehouse", "openlineage", "common"})

def load_registry(content: str) -> dict:
    obj = json.loads(content)
    if obj.get("schema_version") != "fabric-deployment-ownership-v1":
        raise ValueError("unknown owner registry version")
    components = obj.get("components")
    if not isinstance(components, dict) or frozenset(components) != EXPECTED:
        raise ValueError("incomplete or unapproved deployment components")
    for name, item in components.items():
        if not isinstance(item, dict) or item.get("path") != f"azure-fabric/deployment/{name}/":
            raise ValueError(f"component owner path drift: {name}")
        if not isinstance(item.get("purpose"), str) or not item["purpose"].strip():
            raise ValueError(f"component purpose missing: {name}")
    if obj.get("owner_document") != CODE_MAP:
        raise ValueError("owner CODE.md drift")
    if obj.get("quality_tests") != ".github/quality/tests/azure-fabric/deployment/":
        raise ValueError("test owner drift")
    return obj

def evaluate(changes: dict[str, str], content: str, *,
             base_paths: set[str] | None = None,
             head_paths: set[str] | None = None,
             code_map_text: str | None = None) -> list[str]:
    registry = load_registry(content)
    errors = []
    touched = []
    # Bootstrap permits the first trusted workflow introduction only.
    established = base_paths is not None and TRUSTED_WORKFLOW in base_paths
    if established:
        for protected in PROTECTED_POLICY.intersection(changes):
            errors.append(f"{protected}:trusted-owner-policy-mutation")
    if head_paths is not None:
        for path in sorted(head_paths):
            if not path.startswith("azure-fabric/deployment/") or path == OWNER_FILE:
                continue
            parts = path.split("/")
            if len(parts) < 4 or parts[2] not in registry["components"]:
                errors.append(f"{path}:unregistered-deployment-component")
        for owner in (OWNER_FILE, CODE_MAP):
            if owner not in head_paths:
                errors.append(f"{owner}:required-policy-file-missing")
        if established and TRUSTED_WORKFLOW not in head_paths:
            errors.append(f"{TRUSTED_WORKFLOW}:trusted-workflow-deleted")
    for path, kind in sorted(changes.items()):
        if not path.startswith("azure-fabric/deployment/") or kind == "D":
            continue
        if path == OWNER_FILE:
            continue
        components = registry["components"]
        parts = path.split("/")
        if len(parts) < 4 or parts[2] not in components:
            errors.append(f"{path}:unregistered-deployment-component")
            continue
        if path.lower().endswith((".md", ".mdx", ".rst")):
            errors.append(f"{path}:source-document-belongs-in-documents")
        if path.split("/")[-1].startswith("test_") or "/tests/" in path:
            errors.append(f"{path}:test-belongs-in-quality")
        if "workspaces" in parts or "src" in parts[3:]:
            errors.append(f"{path}:wrong-deployment-owner")
        touched.append(path)
    new_sources = [path for path in touched if changes[path] == "A"]
    if new_sources and (CODE_MAP not in changes or changes[CODE_MAP] == "D"):
        errors.append(f"missing-code-map-update:{CODE_MAP}")
    if code_map_text is not None:
        for path in new_sources:
            if path not in code_map_text:
                errors.append(f"{path}:missing-exact-code-map-source-link")
    return errors

def git_changes(base: str, head: str, repo: Path = Path(".")) -> dict[str, str]:
    data = subprocess.check_output(["git", "-C", str(repo), "diff", "--no-renames", "--name-status",
                                    "--diff-filter=ADMR", base, head], text=True)
    result = {}
    for line in data.splitlines():
        status, path = line.split("\t", 1)
        result[path] = status[0]
    return result

def git_paths(repo: Path, ref: str) -> set[str]:
    raw = subprocess.check_output(
        ["git", "-C", str(repo), "ls-tree", "-r", "--name-only", "-z", ref])
    return {p.decode("utf-8") for p in raw.split(b"\\0") if p}


def git_content(repo: Path, ref: str, path: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), "show", f"{ref}:{path}"], timeout=15
    ).decode("utf-8")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--base", required=True)
    p.add_argument("--head", required=True)
    p.add_argument("--repo-root", type=Path, default=Path("."))
    p.add_argument("--policy-root", type=Path, default=Path("."))
    args = p.parse_args()
    try:
        registry = (args.policy_root / OWNER_FILE).read_text(encoding="utf-8")
        base_paths = git_paths(args.repo_root, args.base)
        head_paths = git_paths(args.repo_root, args.head)
        changes = git_changes(args.base, args.head, repo=args.repo_root)
        code_map = git_content(args.repo_root, args.head, CODE_MAP) if CODE_MAP in head_paths else ""
        errors = evaluate(changes, registry, base_paths=base_paths,
                          head_paths=head_paths, code_map_text=code_map)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print("FABRIC_DEPLOYMENT_OWNER_TRUSTED=FAIL; invalid-policy-or-git: " + str(exc))
        return 1
    for err in errors:
        print("FABRIC_DEPLOYMENT_OWNER_VIOLATION=" + err)
    print("FABRIC_DEPLOYMENT_OWNERSHIP=" + ("FAIL" if errors else "PASS")
          + "; cloud_actions=0")
    return 1 if errors else 0

if __name__ == "__main__":
    sys.exit(main())
