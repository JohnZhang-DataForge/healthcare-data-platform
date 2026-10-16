#!/usr/bin/env python3
"""Require CODE.md source map sync for Airflow, apps, Spark, SQL, images, Kubernetes, scripts and config.

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



SPARK_MAP = "documents/components/spark/CODE.md"
SPARK_LINK_RE = re.compile(r"\]\(\.\./\.\./\.\./(spark/[^\s)#?]+)\)")


def is_spark_source(path: str) -> bool:
    return path.startswith("spark/") and not path.endswith((".md", ".mdx", ".rst", ".txt"))


def validate_spark_code_map(contents: str, actual: set[str]) -> tuple[list[str], list[str], list[str]]:
    matched = [p for p in SPARK_LINK_RE.findall(contents) if is_spark_source(p)]
    linked = set(matched)
    duplicate = sorted(p for p in linked if matched.count(p) > 1)
    return sorted(actual - linked), sorted(linked - actual), duplicate



CONTRACT_SQL_MAP_PATHS = (
    "documents/components/synthea/CODE.md",
    "documents/components/landing/CODE.md",
    "documents/components/omop/CODE.md",
)
# Inventory table rows declare ownership; cross-component prose links do not.
CONTRACT_SQL_ROW_RE = re.compile(
    r"^\|\s*\[[^\]]+\]\(\.\./\.\./\.\./((?:contracts|sql)/[^)\s#?]+)\)\s*\|",
    re.MULTILINE,
)


def is_contract_sql_source(path: str) -> bool:
    return path.startswith(("contracts/", "sql/")) and not path.endswith(
        (".md", ".mdx", ".rst", ".txt")
    )


def contract_sql_owned_links(contents: str) -> set[str]:
    return {p for p in CONTRACT_SQL_ROW_RE.findall(contents) if is_contract_sql_source(p)}


def validate_contract_sql_maps(
    documents: dict[str, str], actual: set[str]
) -> tuple[list[str], list[str], list[str]]:
    owned: dict[str, list[str]] = {}
    for doc, contents in documents.items():
        for path in contract_sql_owned_links(contents):
            owned.setdefault(path, []).append(doc)
    return (
        sorted(actual - owned.keys()),
        sorted(owned.keys() - actual),
        sorted(p for p, refs in owned.items() if len(refs) > 1),
    )


def required_contract_sql_updates(
    changed_paths: set[str], before: dict[str, str], after: dict[str, str]
) -> set[str]:
    return {
        doc for doc in CONTRACT_SQL_MAP_PATHS
        if changed_paths & (
            contract_sql_owned_links(before.get(doc, ""))
            | contract_sql_owned_links(after.get(doc, ""))
        )
    }



IMAGE_K8S_MAP_PATHS = (
    "documents/components/synthea/CODE.md",
    "documents/components/landing/CODE.md",
    "documents/components/omop/CODE.md",
    "documents/components/airflow/CODE.md",
)
# Only source inventory table rows declare an owner, not incidental prose links.
IMAGE_K8S_ROW_RE = re.compile(
    r"^\|\s*\[[^\]]+\]\(\.\./\.\./\.\./((?:images|kubernetes)/[^)\s#?]+)\)\s*\|",
    re.MULTILINE,
)


def is_image_k8s_source(path: str) -> bool:
    return path.startswith(("images/", "kubernetes/")) and not path.endswith(
        (".md", ".mdx", ".rst", ".txt")
    )


def image_k8s_owned_links(contents: str) -> set[str]:
    return {p for p in IMAGE_K8S_ROW_RE.findall(contents) if is_image_k8s_source(p)}


def validate_image_k8s_maps(
    documents: dict[str, str], actual: set[str]
) -> tuple[list[str], list[str], list[str]]:
    owners: dict[str, list[str]] = {}
    for doc, content in documents.items():
        for path in image_k8s_owned_links(content):
            owners.setdefault(path, []).append(doc)
    return (
        sorted(actual - owners.keys()),
        sorted(owners.keys() - actual),
        sorted(path for path, refs in owners.items() if len(refs) > 1),
    )


def required_image_k8s_updates(
    changed_paths: set[str], before: dict[str, str], after: dict[str, str]
) -> set[str]:
    return {
        doc for doc in IMAGE_K8S_MAP_PATHS
        if changed_paths & (
            image_k8s_owned_links(before.get(doc, ""))
            | image_k8s_owned_links(after.get(doc, ""))
        )
    }



SCRIPT_CONFIG_MAP_PATHS = (
    "documents/components/synthea/CODE.md",
    "documents/components/landing/CODE.md",
    "documents/components/spark/CODE.md",
    "documents/components/omop/CODE.md",
    "documents/components/airflow/CODE.md",
    "documents/development/CODE.md",
)
# Inventory table rows alone declare ownership. Developer CODE.md is one directory
# shallower than components: accept exactly ../../ or ../../../ source links.
SCRIPT_CONFIG_ROW_RE = re.compile(
    r"^\|\s*\[[^\]]+\]\((?:\.\./){2,3}((?:scripts|config)/[^)\s#?]+)\)\s*\|",
    re.MULTILINE,
)


def is_script_config_source(path: str) -> bool:
    return path.startswith(("scripts/", "config/")) and not path.endswith(
        (".md", ".mdx", ".rst", ".txt")
    )


def script_config_owned_links(contents: str) -> set[str]:
    return {p for p in SCRIPT_CONFIG_ROW_RE.findall(contents) if is_script_config_source(p)}


def validate_script_config_maps(
    documents: dict[str, str], actual: set[str]
) -> tuple[list[str], list[str], list[str]]:
    owners: dict[str, list[str]] = {}
    for doc, contents in documents.items():
        for path in script_config_owned_links(contents):
            owners.setdefault(path, []).append(doc)
    return (
        sorted(actual - owners.keys()),
        sorted(owners.keys() - actual),
        sorted(p for p, refs in owners.items() if len(refs) > 1),
    )


def required_script_config_updates(
    changed_paths: set[str], before: dict[str, str], after: dict[str, str]
) -> set[str]:
    return {
        doc for doc in SCRIPT_CONFIG_MAP_PATHS
        if changed_paths & (
            script_config_owned_links(before.get(doc, ""))
            | script_config_owned_links(after.get(doc, ""))
        )
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

    spark_sources = {
        p for p in git_lines("ls-tree", "-r", "--name-only", args.head, "--", "spark/")
        if is_spark_source(p)
    }
    spark_doc = Path(SPARK_MAP)
    if not spark_doc.is_file():
        print(f"CODE_MAP_GATE=FAIL; missing {SPARK_MAP}")
        return 1
    spark_missing, spark_stale, spark_duplicate = validate_spark_code_map(
        spark_doc.read_text(encoding="utf-8"), spark_sources
    )
    for p in spark_missing:
        print("CODE_MAP_SPARK_MISSING_LINK=" + p)
    for p in spark_stale:
        print("CODE_MAP_SPARK_STALE_LINK=" + p)
    for p in spark_duplicate:
        print("CODE_MAP_SPARK_DUPLICATE_LINK=" + p)
    if spark_missing or spark_stale or spark_duplicate:
        print("CODE_MAP_GATE=FAIL; Spark CODE.md must map each tracked source once")
        return 1

    changed_spark = {
        p for p in git_lines("diff", "--no-renames", "--name-only",
                             "--diff-filter=AD", "--no-ext-diff", args.base, args.head)
        if is_spark_source(p)
    }
    if changed_spark and SPARK_MAP not in changed:
        for p in sorted(changed_spark):
            print("CODE_MAP_SPARK_CHANGED_SOURCE=" + p)
        print(f"CODE_MAP_GATE=FAIL; update {SPARK_MAP} with Spark source changes")
        return 1

    cs_sources = {
        p for p in git_lines("ls-tree", "-r", "--name-only", args.head,
                             "--", "contracts/", "sql/")
        if is_contract_sql_source(p)
    }
    cs_after = {p: Path(p).read_text(encoding="utf-8") for p in CONTRACT_SQL_MAP_PATHS}
    cs_before = {p: git_file(args.base, p) for p in CONTRACT_SQL_MAP_PATHS}
    cs_missing, cs_stale, cs_duplicates = validate_contract_sql_maps(cs_after, cs_sources)
    for p in cs_missing:
        print("CODE_MAP_CONTRACT_SQL_MISSING_LINK=" + p)
    for p in cs_stale:
        print("CODE_MAP_CONTRACT_SQL_STALE_LINK=" + p)
    for p in cs_duplicates:
        print("CODE_MAP_CONTRACT_SQL_DUPLICATE_OWNER=" + p)
    if cs_missing or cs_stale or cs_duplicates:
        print("CODE_MAP_GATE=FAIL; every Contract/SQL source must have one CODE.md owner")
        return 1

    cs_changed = {
        p for p in git_lines("diff", "--no-renames", "--name-only",
                             "--diff-filter=AD", "--no-ext-diff", args.base, args.head)
        if is_contract_sql_source(p)
    }
    cs_required = required_contract_sql_updates(cs_changed, cs_before, cs_after)
    for path in sorted(cs_required - changed):
        print("CODE_MAP_CONTRACT_SQL_REQUIRED_UPDATE_MISSING=" + path)
    if cs_required - changed:
        print("CODE_MAP_GATE=FAIL; Contract/SQL change requires same PR CODE.md")
        return 1

    image_k8s_sources = {
        p for p in git_lines("ls-tree", "-r", "--name-only", args.head,
                             "--", "images/", "kubernetes/")
        if is_image_k8s_source(p)
    }
    image_k8s_after = {
        p: Path(p).read_text(encoding="utf-8") for p in IMAGE_K8S_MAP_PATHS
    }
    image_k8s_before = {
        p: git_file(args.base, p) for p in IMAGE_K8S_MAP_PATHS
    }
    ik_missing, ik_stale, ik_duplicate = validate_image_k8s_maps(
        image_k8s_after, image_k8s_sources
    )
    for p in ik_missing:
        print("CODE_MAP_IMAGE_K8S_MISSING_LINK=" + p)
    for p in ik_stale:
        print("CODE_MAP_IMAGE_K8S_STALE_LINK=" + p)
    for p in ik_duplicate:
        print("CODE_MAP_IMAGE_K8S_DUPLICATE_OWNER=" + p)
    if ik_missing or ik_stale or ik_duplicate:
        print("CODE_MAP_GATE=FAIL; image/k8s sources require exactly one CODE.md owner")
        return 1

    image_k8s_changed = {
        p for p in git_lines("diff", "--no-renames", "--name-only",
                             "--diff-filter=AD", "--no-ext-diff", args.base, args.head)
        if is_image_k8s_source(p)
    }
    image_k8s_required = required_image_k8s_updates(
        image_k8s_changed, image_k8s_before, image_k8s_after
    )
    for doc in sorted(image_k8s_required - changed):
        print("CODE_MAP_IMAGE_K8S_REQUIRED_UPDATE_MISSING=" + doc)
    if image_k8s_required - changed:
        print("CODE_MAP_GATE=FAIL; update owning CODE.md in same PR as image/k8s source")
        return 1

    script_config_sources = {
        p for p in git_lines("ls-tree", "-r", "--name-only", args.head,
                             "--", "scripts/", "config/")
        if is_script_config_source(p)
    }
    script_config_after = {
        p: Path(p).read_text(encoding="utf-8") for p in SCRIPT_CONFIG_MAP_PATHS
    }
    script_config_before = {
        p: git_file(args.base, p) for p in SCRIPT_CONFIG_MAP_PATHS
    }
    sc_missing, sc_stale, sc_duplicates = validate_script_config_maps(
        script_config_after, script_config_sources
    )
    for p in sc_missing:
        print("CODE_MAP_SCRIPT_CONFIG_MISSING_LINK=" + p)
    for p in sc_stale:
        print("CODE_MAP_SCRIPT_CONFIG_STALE_LINK=" + p)
    for p in sc_duplicates:
        print("CODE_MAP_SCRIPT_CONFIG_DUPLICATE_OWNER=" + p)
    if sc_missing or sc_stale or sc_duplicates:
        print("CODE_MAP_GATE=FAIL; each scripts/config source requires one CODE.md owner")
        return 1

    script_config_changed = {
        p for p in git_lines("diff", "--no-renames", "--name-only",
                             "--diff-filter=AD", "--no-ext-diff", args.base, args.head)
        if is_script_config_source(p)
    }
    script_config_required = required_script_config_updates(
        script_config_changed, script_config_before, script_config_after
    )
    for doc in sorted(script_config_required - changed):
        print("CODE_MAP_SCRIPT_CONFIG_REQUIRED_UPDATE_MISSING=" + doc)
    if script_config_required - changed:
        print("CODE_MAP_GATE=FAIL; scripts/config source add/delete/move requires CODE.md")
        return 1

    print("CODE_MAP_GATE=PASS; mapped_dag_files=" + str(len(current)) +
          "; mapped_app_files=" + str(len(app_sources)) +
          "; mapped_spark_files=" + str(len(spark_sources)) +
          "; mapped_contract_sql_files=" + str(len(cs_sources)) +
          "; mapped_image_k8s_files=" + str(len(image_k8s_sources)) +
          "; mapped_script_config_files=" + str(len(script_config_sources)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
