#!/usr/bin/env python3
"""Read-only diff guard against new development-stage names in source contracts.

Legacy references and unchanged lines are not rewritten or rejected. Run from
a candidate checkout; never execute candidate code.
"""
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

SOURCE_ROOTS = (
    "local-data-platform/", "azure-fabric/", "shared-data-engine/",
    "platform-portal/", ".github/workflows/", ".github/quality/",
    "src/", "scripts/", "tests/",
)
DOCUMENT_ROOTS = ("documents/", "docs/", "openspec/")
SOURCE_EXTENSIONS = {".py", ".sh", ".sql", ".yml", ".yaml", ".json", ".toml", ".js", ".ts"}
PHASE = re.compile(
    r"(?i)(?<![A-Za-z0-9])(?:g[0-9]|p[0-9]|f[0-9]|b[0-9])(?=$|[^A-Za-z0-9])"
    r"|(?<![A-Za-z0-9])(?:G[0-9]|P[0-9]|F[0-9]|B[0-9])(?=[A-Z])"
)
TASK_STEP = re.compile(
    r"(?i)(?<![A-Za-z0-9])(?:task|step)[_-]?\d+[a-z]?(?![A-Za-z0-9])"
)
DECL = re.compile(r"^\s*(?:async\s+)?(?:def|class)\s+([A-Za-z_]\w*)\b")
BIND = re.compile(r"^\s*(?:export\s+)?([A-Za-z_]\w*)\s*(?::[^=]+)?\s*=\s*(.+)$")
FIELD = re.compile(r"^\s*([A-Za-z_]\w*)\s*:\s*[^=:]+(?:\s*=.*)?$")
YAML = re.compile(r"^\s*([A-Za-z_][\w-]*)\s*:\s*(.+)$")
PUBLIC_KEYS = frozenset({
    "SCHEMA", "SCHEMA_VERSION", "STATUS", "ERROR", "ERROR_CODE",
    "ISSUER", "AUDIENCE", "PROTOCOL", "DAG_ID", "JOB_ID",
    "MARKER", "CONFIRM", "WORKFLOW_NAME",
})
YAML_KEYS = frozenset({
    "name", "id", "dag_id", "status", "error_code", "schema",
    "schema_version", "issuer", "audience", "protocol", "job_name",
})


def has_phase(value: str) -> bool:
    return bool(PHASE.search(value) or TASK_STEP.search(value))


def owned_source(path: str) -> bool:
    return (path.startswith(SOURCE_ROOTS)
            and not path.startswith(DOCUMENT_ROOTS)
            and Path(path).suffix.lower() in SOURCE_EXTENSIONS)


def path_violation(path: str) -> bool:
    return owned_source(path) and has_phase(path)


def line_violations(path: str, line: str) -> list[str]:
    """Inspect only newly added source declarations, not old API references."""
    if not owned_source(path):
        return []
    value = line.strip()
    if not value or value.startswith(("#", "//", "*", '"""', "'''")):
        return []
    problems = []
    declaration = DECL.match(line)
    if declaration and has_phase(declaration.group(1)):
        problems.append("development-number-declaration")
    assignment = BIND.match(line)
    if assignment:
        identifier, rhs = assignment.groups()
        if has_phase(identifier):
            problems.append("development-number-binding")
        if identifier.upper() in PUBLIC_KEYS and has_phase(rhs):
            problems.append("development-number-public-contract")
    field = FIELD.match(line) if path.endswith(".py") else None
    if field and has_phase(field.group(1)):
        problems.append("development-number-field")
    yaml = YAML.match(line) if path.endswith((".yml", ".yaml")) else None
    if yaml:
        identifier, rhs = yaml.groups()
        if has_phase(identifier) or (
            identifier.lower() in YAML_KEYS and has_phase(rhs)
        ):
            problems.append("development-number-yaml-identifier")
    # New exception codes and public response statuses must not reintroduce
    # a development phase even inside an otherwise semantic function.
    if re.search(r"\braise\b", value) and re.search(
        r"['\"](?:HOLD_|FAIL_|ERROR_|G[0-9]_|P[0-9]_|F[0-9]_|B[0-9]_)[^'\"]*['\"]", value
    ) and has_phase(value):
        problems.append("development-number-error-code")
    return sorted(set(problems))


def evaluate(added_paths: list[str], new_lines: dict[str, list[str]]) -> list[str]:
    errors = []
    for path in sorted(set(added_paths)):
        if path_violation(path):
            errors.append(f"{path}:development-number-source-path")
    for path in sorted(new_lines):
        for line in new_lines[path]:
            for reason in line_violations(path, line):
                errors.append(f"{path}:{reason}: {line.strip()[:150]}")
    return sorted(set(errors))


def git_bytes(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], timeout=45)


def read_diff(base: str, head: str) -> tuple[list[str], dict[str, list[str]]]:
    raw_paths = git_bytes(
        "diff", "--no-renames", "--diff-filter=A", "--name-only",
        "-z", base, head
    )
    added = [p.decode("utf-8") for p in raw_paths.split(b"\0") if p]
    # Parse only actual '+' diff text (not context or metadata), from a
    # zero-context diff. Paths with special Git quoting fail closed below.
    patch = git_bytes("diff", "--no-renames", "--no-ext-diff",
                      "--unified=0", base, head).decode("utf-8")
    current = None
    lines: dict[str, list[str]] = {}
    for row in patch.splitlines():
        if row.startswith("diff --git "):
            current = None
        elif row.startswith("+++ b/"):
            current = row[6:]
            if current.startswith('"') or current.startswith("b/"):
                raise ValueError("unsupported diff path encoding")
            lines.setdefault(current, [])
        elif row.startswith("+++ /dev/null"):
            current = None
        elif current is not None and row.startswith("+") and not row.startswith("+++"):
            lines[current].append(row[1:])
    return added, lines


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    args = parser.parse_args()
    try:
        added, new_lines = read_diff(args.base, args.head)
        errors = evaluate(added, new_lines)
    except (subprocess.CalledProcessError, UnicodeError, ValueError,
            subprocess.TimeoutExpired) as exc:
        print(f"SEMANTIC_NAMING=FAIL; scanner-error={exc}")
        return 1
    for error in errors:
        print("SEMANTIC_NAMING_VIOLATION=" + error)
    print(f"SEMANTIC_NAMING={'FAIL' if errors else 'PASS'};"
          f" added_paths={len(added)}; changed_files={len(new_lines)}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
