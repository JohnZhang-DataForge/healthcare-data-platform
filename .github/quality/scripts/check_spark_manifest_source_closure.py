#!/usr/bin/env python3
"""Static local SparkApplication template -> unique Python source provenance gate.

No yaml rendering, Kubernetes API calls, imports of application code, or writes.
This intentionally handles only the checked-in declarative template convention;
unknown/new kinds and ambiguous source resolution fail closed.
"""
import ast
import hashlib
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
MANIFESTS = "local-data-platform/spark/manifests"
APPS = "local-data-platform/spark/apps"
ENTRY_ROOT = "local:///opt/spark/app/"


def _single(text, regex, what):
    found = re.findall(regex, text, flags=re.MULTILINE)
    if len(found) != 1:
        raise ValueError(f"{what}: expected exactly one declaration, got {len(found)}")
    return found[0]


def _section(text, key, indent):
    lines = text.splitlines()
    header = " " * indent + key + ":"
    indexes = [i for i, line in enumerate(lines) if line == header]
    if len(indexes) != 1:
        raise ValueError(f"{key}: expected one section")
    start = indexes[0] + 1
    end = start
    for i in range(start, len(lines)):
        line = lines[i]
        if line.strip() and (len(line) - len(line.lstrip(" "))) <= indent:
            break
        end = i + 1
    return "\n".join(lines[start:end])


def _mount_ok(block):
    # Full-line structure: fail closed on substituted path, missing ro, or multiple mounts.
    return len(re.findall(
        r"(?m)^      - name: spark-app\n        mountPath: /opt/spark/app\n        readOnly: true\s*$",
        block)) == 1


def audit(root=ROOT):
    manifests = sorted((root / MANIFESTS).rglob("*.yaml.tpl"))
    app_paths = sorted((root / APPS).rglob("*.py"))
    if len(manifests) < 1 or len(app_paths) < 1:
        raise ValueError("Spark manifest or application source inventory empty")
    files_by_name = {}
    for src in app_paths:
        files_by_name.setdefault(src.name, []).append(src)
    records = []
    auxiliary = []
    for template in manifests:
        label = template.relative_to(root).as_posix()
        raw = template.read_text(encoding="utf-8")
        kind = _single(raw, r"^kind:\s*(\w+)\s*$", label + ":kind")
        if kind == "Pod":
            if "mainApplicationFile" in raw:
                raise ValueError(label + ":auxiliary Pod must not declare Spark main")
            auxiliary.append(label)
            continue
        if kind != "SparkApplication":
            raise ValueError(label + ":unsupported resource kind " + kind)
        spec = _section(raw, "spec", 0)
        if not re.search(r"(?m)^  type: Python$", spec) or not re.search(
                r"(?m)^  mode: cluster$", spec):
            raise ValueError(label + ":not a Python cluster-mode SparkApplication")
        entry = _single(spec, r"^  mainApplicationFile:\s*(\S+)\s*$",
                        label + ":mainApplicationFile")
        if not entry.startswith(ENTRY_ROOT):
            raise ValueError(label + ":Spark main must be local canonical app path")
        filename = entry[len(ENTRY_ROOT):]
        if not re.fullmatch(r"[a-z][a-z0-9_]*\.py", filename):
            raise ValueError(label + ":unsupported nested or substituted main path")
        candidates = files_by_name.get(filename, [])
        if len(candidates) != 1:
            raise ValueError(label + ":main must resolve to exactly one source: " + filename)
        src = candidates[0]
        ast.parse(src.read_text(encoding="utf-8"), filename=str(src))
        for role in ("driver", "executor"):
            if not _mount_ok(_section(spec, role, 2)):
                raise ValueError(label + ":" + role + " requires unique read-only spark-app mount")
        volume = _section(spec, "volumes", 2)
        if len(re.findall(
                r"(?m)^    - name: spark-app\n      configMap:\n        name: __CONFIGMAP_NAME__\s*$",
                volume)) != 1:
            raise ValueError(label + ":expected one parameterized source ConfigMap volume")
        records.append({
            "template": label,
            "source": src.relative_to(root).as_posix(),
            "template_sha256": hashlib.sha256(raw.encode()).hexdigest(),
            "source_sha256": hashlib.sha256(src.read_bytes()).hexdigest(),
        })
    if not records:
        raise ValueError("No SparkApplication templates inspected")
    return records, auxiliary


def main():
    if len(sys.argv) != 1:
        raise ValueError("No runtime inputs accepted")
    apps, pods = audit()
    print("#### LOCAL_DP_SPARK_SOURCE_CLOSURE_OUTPUT_BEGIN ####")
    print("SPARKAPPLICATION_TEMPLATE_COUNT=" + str(len(apps)))
    print("AUXILIARY_POD_TEMPLATE_COUNT=" + str(len(pods)))
    for row in apps:
        print("TEMPLATE=" + row["template"] + " SOURCE=" + row["source"] +
              " TEMPLATE_SHA256=" + row["template_sha256"] +
              " SOURCE_SHA256=" + row["source_sha256"])
    for name in pods:
        print("NON_SPARK_AUXILIARY_TEMPLATE=" + name)
    print("SPARK_TEMPLATE_STATIC_SOURCE_CLOSURE=PASS")
    print("RENDERED_SPARKAPPLICATION=NOT_VERIFIED")
    print("DRIVER_IMPORT=NOT_VERIFIED")
    print("KUBERNETES_ACCESS=NONE; BUSINESS_MUTATION=NONE")
    print("#### LOCAL_DP_SPARK_SOURCE_CLOSURE_OUTPUT_END ####")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, SyntaxError) as exc:
        print("SPARK_TEMPLATE_STATIC_SOURCE_CLOSURE=HOLD " +
              str(exc).splitlines()[0][:240], file=sys.stderr)
        sys.exit(2)
