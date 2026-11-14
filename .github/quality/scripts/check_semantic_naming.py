#!/usr/bin/env python3
"""Read-only diff guard against new development-stage names in source contracts.

Legacy references and unchanged lines are not rewritten or rejected. Run from
a candidate checkout; never execute candidate code.
"""
from __future__ import annotations

import argparse
import ast
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
)
TASK_STEP = re.compile(
    r"(?i)(?<![A-Za-z0-9])(?:task|step)[_-]?\d+[a-z]?(?![A-Za-z0-9])"
)
DECL = re.compile(r"^\s*(?:async\s+)?(?:def|class)\s+([A-Za-z_]\w*)\b")
CAMEL_PHASE = re.compile(r"[GgPpFfBb][0-9](?=[A-Z])")
JS_DECL = re.compile(
    r"^\s*(?:(?:export|default|async|declare)\s+)*"
    r"(?:const|let|var|function|class|interface|type|enum)\s+([A-Za-z_$][\w$]*)\b"
)
SHELL_DECL = re.compile(r"^\s*(?:function\s+)?([A-Za-z_]\w*)\s*\(\)\s*\{")
JSON_MEMBER = re.compile(r"""^\s*["']([^"']+)["']\s*:\s*(.*)$""")
PUBLIC_MEMBER = re.compile(
    r"""["'](?:schema|schema_version|status|error_code|issuer|audience|protocol|job_name|dag_id)["']\s*:\s*["']([^"']+)["']""",
    re.IGNORECASE,
)
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


PUBLIC_SUFFIXES = (
    "_SCHEMA", "_SCHEMA_VERSION", "_STATUS", "_ERROR_CODE",
    "_ISSUER", "_AUDIENCE", "_PROTOCOL", "_MARKER", "_CONFIRM",
    "_DAG_ID", "_JOB_ID", "_WORKFLOW_NAME",
)


def public_binding(identifier: str) -> bool:
    name = identifier.upper()
    return name in PUBLIC_KEYS or name.endswith(PUBLIC_SUFFIXES)


def has_phase(value: str) -> bool:
    return bool(PHASE.search(value) or CAMEL_PHASE.search(value) or TASK_STEP.search(value))


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
    js_decl = JS_DECL.match(line) if path.endswith((".js", ".ts")) else None
    if js_decl and has_phase(js_decl.group(1)):
        problems.append("development-number-js-declaration")
    sh_decl = SHELL_DECL.match(line) if path.endswith(".sh") else None
    if sh_decl and has_phase(sh_decl.group(1)):
        problems.append("development-number-shell-function")
    if path.endswith(".sql") and re.match(
        r"^\s*CREATE\s+(?:OR\s+REPLACE\s+)?(?:TABLE|VIEW|INDEX|FUNCTION|PROCEDURE|SCHEMA)\b",
        line, re.IGNORECASE
    ) and has_phase(line):
        problems.append("development-number-sql-object")
    assignment = BIND.match(line)
    if assignment:
        identifier, rhs = assignment.groups()
        if has_phase(identifier):
            problems.append("development-number-binding")
        if public_binding(identifier) and has_phase(rhs):
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
    if path.endswith(".json"):
        json_member = JSON_MEMBER.match(line)
        if json_member:
            key, rhs = json_member.groups()
            if has_phase(key) or (
                key.lower() in YAML_KEYS and has_phase(rhs)
            ):
                problems.append("development-number-json-identifier")
    if "/tests/" not in path and not Path(path).name.startswith("test_"):
        public_member = PUBLIC_MEMBER.search(line)
        if public_member and has_phase(public_member.group(1)):
            problems.append("development-number-public-object-value")
    # New exception codes and public response statuses must not reintroduce
    # a development phase even inside an otherwise semantic function.
    if re.match(r"^\s*raise\b", line) and re.search(
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



# Structural validation complements, but does not replace, the diff text guard.
# Only Python source is parsed; it is NEVER imported or executed.
VAGUE_FUNCTION = re.compile(
    r"^(?:do_stuff|handle_it|temp_func|process_data\d+|final_v\d+)$"
    r"|(?:^|_)(?:foo|bar|baz|stuff|dummy|placeholder)(?:_|$)",
    re.IGNORECASE,
)
PUBLIC_JSON_KEYS = frozenset({
    "schema", "schema_version", "status", "error", "error_code",
    "issuer", "audience", "protocol", "dag_id", "job_id",
})


def _static_text(node: ast.AST | None) -> str | None:
    if node is None:
        return None
    try:
        value = ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
        return None
    return value if isinstance(value, str) else None


def _python_inventory(source: str) -> tuple[
    dict[tuple[str, str], str],
    dict[str, str | None],
    set[tuple[str, str]],
]:
    """Extract scoped symbols and literal public contracts without executing code.

    Existing stage-number names are retained through a baseline inventory.
    Public contract *value* changes are checked even for pre-existing bindings.
    """
    tree = ast.parse(source)
    symbols: dict[tuple[str, str], str] = {}
    public: dict[str, str | None] = {}
    dictionaries: set[tuple[str, str]] = set()

    class Scan(ast.NodeVisitor):
        def __init__(self) -> None:
            self.scope: list[str] = []

        def _record(self, kind: str, name: str, value: ast.AST | None = None) -> None:
            key = ".".join((*self.scope, name))
            symbols[(kind, key)] = name
            if public_binding(name):
                public[key] = _static_text(value)

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self._record("function", node.name)
            self.scope.append(node.name)
            self.generic_visit(node)
            self.scope.pop()

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self._record("function", node.name)
            self.scope.append(node.name)
            self.generic_visit(node)
            self.scope.pop()

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            self._record("class", node.name)
            self.scope.append(node.name)
            self.generic_visit(node)
            self.scope.pop()

        def visit_Assign(self, node: ast.Assign) -> None:
            for target in node.targets:
                for item in ast.walk(target):
                    if isinstance(item, ast.Name):
                        self._record("binding", item.id, node.value)
            self.generic_visit(node)

        def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
            if isinstance(node.target, ast.Name):
                self._record("binding", node.target.id, node.value)
            self.generic_visit(node)

        def visit_Dict(self, node: ast.Dict) -> None:
            for key, value in zip(node.keys, node.values):
                label, literal = _static_text(key), _static_text(value)
                if label is not None and label.lower() in PUBLIC_JSON_KEYS and literal is not None:
                    dictionaries.add((label.lower(), literal))
            self.generic_visit(node)

    Scan().visit(tree)
    return symbols, public, dictionaries


def python_ast_violations(path: str, old_source: str, new_source: str) -> list[str]:
    """Compare Python ASTs; ignore existing names but reject newly introduced ones."""
    if not owned_source(path) or not path.endswith(".py"):
        return []
    try:
        old_symbols, old_public, old_dicts = _python_inventory(old_source)
        new_symbols, new_public, new_dicts = _python_inventory(new_source)
    except SyntaxError as exc:
        return [f"python-ast-parse-error:{exc.msg}"]

    errors = []
    for (kind, qualified), name in sorted(new_symbols.items()):
        if (kind, qualified) in old_symbols:
            continue
        if has_phase(name):
            errors.append(f"python-ast-development-phase-{kind}:{qualified}")
        if kind in ("function", "class") and VAGUE_FUNCTION.search(name):
            errors.append(f"python-ast-vague-{kind}:{qualified}")
    # A changed published Schema/status must not escape detection by moving
    # the string onto another line; unchanged legacy values remain permitted.
    if "/tests/" not in path and not Path(path).name.startswith("test_"):
        for qualified, literal in sorted(new_public.items()):
            if literal is not None and has_phase(literal) and old_public.get(qualified) != literal:
                errors.append(f"python-ast-public-contract:{qualified}")
        for key, literal in sorted(new_dicts - old_dicts):
            if has_phase(literal):
                errors.append(f"python-ast-public-dict:{key}")
    return errors


def _read_git_source(ref: str, path: str, *, missing_ok: bool = False) -> str:
    result = subprocess.run(
        ["git", "show", f"{ref}:{path}"], capture_output=True, timeout=45,
        check=False,
    )
    if result.returncode:
        if missing_ok:
            return ""
        raise ValueError(f"cannot read source at {ref}:{path}")
    return result.stdout.decode("utf-8")


def inspect_python_ast_diff(
    base: str, head: str, changed_paths: list[str], added_paths: list[str],
) -> list[str]:
    """Git object reads only; no imports or execution of untrusted code."""
    errors: list[str] = []
    added = set(added_paths)
    for path in sorted(set(changed_paths)):
        if not path.endswith(".py") or not owned_source(path):
            continue
        previous = "" if path in added else _read_git_source(base, path)
        current = _read_git_source(head, path)
        errors.extend(f"{path}:{item}" for item in
                      python_ast_violations(path, previous, current))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    args = parser.parse_args()
    try:
        added, new_lines = read_diff(args.base, args.head)
        errors = evaluate(added, new_lines)
        errors.extend(inspect_python_ast_diff(
            args.base, args.head, list(new_lines), added))
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
