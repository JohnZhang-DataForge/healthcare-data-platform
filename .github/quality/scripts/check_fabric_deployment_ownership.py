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

def evaluate(changes: dict[str, str], content: str) -> list[str]:
    registry = load_registry(content)
    errors = []
    touched = []
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
    if touched and CODE_MAP not in changes:
        errors.append(f"missing-code-map-update:{CODE_MAP}")
    return errors

def git_changes(base: str, head: str) -> dict[str, str]:
    data = subprocess.check_output(["git", "diff", "--no-renames", "--name-status",
                                    "--diff-filter=ADMR", base, head], text=True)
    result = {}
    for line in data.splitlines():
        status, path = line.split("\t", 1)
        result[path] = status[0]
    return result

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--base", required=True)
    p.add_argument("--head", required=True)
    args = p.parse_args()
    try:
        registry = Path(OWNER_FILE).read_text(encoding="utf-8")
        errors = evaluate(git_changes(args.base, args.head), registry)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print("FABRIC_DEPLOYMENT_OWNERSHIP=FAIL; invalid-policy-or-git: " + str(exc))
        return 1
    for err in errors:
        print("FABRIC_DEPLOYMENT_OWNER_VIOLATION=" + err)
    print("FABRIC_DEPLOYMENT_OWNERSHIP=" + ("FAIL" if errors else "PASS")
          + "; cloud_actions=0")
    return 1 if errors else 0

if __name__ == "__main__":
    sys.exit(main())
