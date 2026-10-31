#!/usr/bin/env python3
"""Offline Shared/Fabric ownership, dependency, and Local Contract integrity gate.

Reads an exact Git commit, never executes candidate source or performs cloud I/O.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import posixpath
import re
import subprocess
from pathlib import PurePosixPath

SHARED_ROOT = "shared-data-engine/"
FABRIC_ROOT = "azure-fabric/workspaces/healthcare-omop/"
CONTRACT_HASHES = {
    "local-data-platform/spark/contracts/canonical/patient-v1.json":
        "e0be146222f13b2f24a84d883d70117fac9aab984c184558dab88726ac5a3dab",
    "local-data-platform/spark/contracts/canonical/encounter-v1.json":
        "473ae45225c9063a7560b0092ed7914d71a43623f593d4959c66294e942a5837",
}
OWNERS = {
    "shared": "documents/systems/data-platform/shared-engine/CODE.md",
    "notebooks": "documents/systems/azure-fabric/notebooks/CODE.md",
    "pipelines": "documents/systems/azure-fabric/pipelines/CODE.md",
    "environments": "documents/systems/azure-fabric/environments/CODE.md",
}
FORBIDDEN_IMPORTS = (
    "azure", "boto3", "botocore", "airflow", "delta", "psycopg", "psycopg2",
    "sqlalchemy", "requests", "httpx", "fabric", "notebookutils",
    "mssparkutils", "google.cloud", "kubernetes", "local_data_platform",
    "healthcare_fabric", "s3fs", "adlfs",
)
FORBIDDEN_CALLS = ("open", "exec", "eval", "os.getenv", "os.environ.get",
                   "requests.get", "requests.post", "SparkSession.builder")
LINK_RE = re.compile(r"\]\(([^)#]+)(?:#[^)]*)?\)")


def owner_for(path: str) -> str | None:
    if path.startswith(SHARED_ROOT):
        return "shared"
    if path.startswith(FABRIC_ROOT):
        relative = path[len(FABRIC_ROOT):]
        part = relative.split("/", 1)[0]
        if part in ("notebooks", "pipelines", "environments"):
            return part
        native_items = {".Notebook": "notebooks", ".DataPipeline": "pipelines",
                        ".Environment": "environments"}
        for suffix, owner in native_items.items():
            if part.endswith(suffix):
                return owner
    return None


def is_owned_source(path: str) -> bool:
    owner = owner_for(path)
    if owner is None or path.endswith((".md", ".mdx", ".rst", ".txt", "/.gitkeep")):
        return False
    if owner == "shared" and path in (SHARED_ROOT + "AGENTS.md",):
        return False
    return path.endswith((".py", ".json", ".toml", ".yaml", ".yml", ".platform", ".whl", ".lock"))


def declared_links(doc_path: str, body: str) -> list[str]:
    result = []
    for line in body.splitlines():
        if not re.match(r"^\|\s*\[[^\]]+\]\(", line):
            continue
        match = LINK_RE.search(line)
        if match and not match.group(1).startswith(("https:", "http:")):
            result.append(posixpath.normpath(posixpath.join(
                posixpath.dirname(doc_path), match.group(1))))
    return result


def check_ownership(files: set[str], docs: dict[str, str],
                    changed: set[str], added_deleted: set[str]) -> list[str]:
    errors = []
    registered: dict[str, list[str]] = {}
    for group, doc in OWNERS.items():
        if doc not in docs:
            errors.append("MISSING_CODE_MAP:" + doc)
            continue
        for path in declared_links(doc, docs[doc]):
            if is_owned_source(path):
                registered.setdefault(path, []).append(group)
    sources = {p for p in files if is_owned_source(p)}
    for path in sorted(sources - registered.keys()):
        errors.append("MISSING_OWNER:" + path)
    for path in sorted(registered.keys() - sources):
        errors.append("STALE_OWNER:" + path)
    for path, groups in sorted(registered.items()):
        if len(groups) != 1:
            errors.append("DUPLICATE_OWNER:" + path)
        if any(group != owner_for(path) for group in groups):
            errors.append("WRONG_OWNER:" + path)
    for group, doc in OWNERS.items():
        if any(is_owned_source(p) and owner_for(p) == group for p in added_deleted):
            if doc not in changed:
                errors.append("MISSING_SAME_PR_CODE_MAP_UPDATE:" + doc)
    return errors


def dotted(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return dotted(node.value) + "." + node.attr
    return ""


def check_imports(path: str, source: str) -> list[str]:
    """Only Shared production package is forbidden from platform/runtime imports."""
    if not path.startswith(SHARED_ROOT + "src/healthcare_data_engine/") or not path.endswith(".py"):
        return []
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as exc:
        return [f"INVALID_PYTHON:{path}:{exc.lineno}"]
    errors = []
    for node in ast.walk(tree):
        mods = []
        if isinstance(node, ast.Import):
            mods = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            mods = [node.module or ""]
        for mod in mods:
            if any(mod == forbidden or mod.startswith(forbidden + ".") for forbidden in FORBIDDEN_IMPORTS):
                errors.append(f"FORBIDDEN_SHARED_IMPORT:{path}:{mod}")
        if isinstance(node, ast.Call):
            name = dotted(node.func)
            if name in FORBIDDEN_CALLS or name.startswith(("SparkSession.builder.", "os.system", "subprocess.")):
                errors.append(f"FORBIDDEN_SHARED_SIDE_EFFECT:{path}:{name}")
        if isinstance(node, ast.Attribute) and dotted(node).startswith(("os.environ", "SparkSession.builder")):
            errors.append(f"FORBIDDEN_SHARED_RUNTIME:{path}:{dotted(node)}")
    return sorted(set(errors))


def check_layout(path: str, content: str) -> list[str]:
    errors = []
    if path.startswith(("azure-fabric/ingestion/", "azure-fabric/runtime/",
                        "azure-fabric/libraries/healthcare-fabric-io/",
                        "azure-fabric/workspaces/johnzhang-test/")):
        errors.append("RETIRED_OR_SUPERSEDED_PATH:" + path)
    if path.startswith(SHARED_ROOT + "src/") and not path.startswith(
            SHARED_ROOT + "src/healthcare_data_engine/"):
        errors.append("WRONG_SHARED_NAMESPACE:" + path)
    if path.startswith(FABRIC_ROOT):
        if "/.Environment/" in path or ".Environment/" in path:
            if path.endswith(".py") or (path.endswith(".whl") and
                    "/Libraries/CustomLibraries/" not in path):
                errors.append("ENVIRONMENT_CUSTOM_WHEEL_LAYOUT_REQUIRED:" + path)
        if path.endswith(".py") and ".Notebook/" not in path:
            errors.append("FABRIC_PYTHON_OUTSIDE_NATIVE_NOTEBOOK:" + path)
        if path.endswith(".py") and ".Notebook/" in path:
            try:
                tree = ast.parse(content, filename=path)
            except SyntaxError:
                errors.append("INVALID_NOTEBOOK_PYTHON:" + path)
            else:
                for item in ast.walk(tree):
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name.startswith(
                            ("map_patient_", "map_encounter_", "normalize_fhir_", "parse_fhir_")):
                        errors.append("DUPLICATE_BUSINESS_MAPPER:" + path + ":" + item.name)
    if path.endswith((".json", ".yaml", ".yml")) and (
            path.startswith(SHARED_ROOT) or path.startswith(FABRIC_ROOT)):
        try:
            data = json.loads(content) if path.endswith(".json") else None
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict) and {"fields", "primary_key", "canonical_version"} <= data.keys():
            errors.append("COPIED_LOCAL_CANONICAL_CONTRACT:" + path)
    if path.startswith(SHARED_ROOT) and "healthcare_fabric" in path:
        errors.append("SECOND_WHEEL_NAMESPACE:" + path)
    return errors


def git(*args: str, binary: bool = False):
    result = subprocess.run(["git", *args], check=True, capture_output=True,
                            **({} if binary else {"text": True}))
    return result.stdout if binary else result.stdout.splitlines()


def run(base: str, head: str) -> list[str]:
    files = set(git("ls-tree", "-r", "--name-only", head))
    changed = set(git("diff", "--no-ext-diff", "--name-only", base, head))
    added_deleted = set(git("diff", "--no-renames", "--no-ext-diff",
                            "--diff-filter=AD", "--name-only", base, head))
    docs = {doc: git("show", head + ":" + doc) for doc in OWNERS.values()}
    docs = {path: "\n".join(lines) for path, lines in docs.items()}
    errors = check_ownership(files, docs, changed, added_deleted)
    for contract_path, expected in CONTRACT_HASHES.items():
        if contract_path not in files:
            errors.append("MISSING_LOCAL_CONTRACT:" + contract_path)
            continue
        actual = hashlib.sha256(git("show", head + ":" + contract_path, binary=True)).hexdigest()
        if actual != expected:
            errors.append("LOCAL_CONTRACT_HASH_DRIFT:" + contract_path + ":" + actual)
    for path in sorted(files | changed):
        if not (path.startswith(SHARED_ROOT) or path.startswith(FABRIC_ROOT)
                or path.startswith(("azure-fabric/ingestion/", "azure-fabric/runtime/",
                                    "azure-fabric/libraries/healthcare-fabric-io/",
                                    "azure-fabric/workspaces/johnzhang-test/"))):
            continue
        if path not in files:
            continue
        if not (is_owned_source(path) or path.endswith(".py")):
            continue
        # Native Environment CustomLibraries wheel is a binary ZIP, not UTF-8 source.
        # Its checksum is pinned by the build/stage CI; layout is still enforced.
        if path.endswith(".whl"):
            errors.extend(check_layout(path, ""))
            continue
        body = git("show", head + ":" + path, binary=True).decode("utf-8")
        errors.extend(check_layout(path, body))
        errors.extend(check_imports(path, body))
    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    args = parser.parse_args()
    errors = run(args.base, args.head)
    for error in errors:
        print("SHARED_FABRIC_BOUNDARY_FAIL=" + error)
    if errors:
        return 1
    print("SHARED_FABRIC_BOUNDARY_PASS; owner_maps=4; contract_hashes=2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
