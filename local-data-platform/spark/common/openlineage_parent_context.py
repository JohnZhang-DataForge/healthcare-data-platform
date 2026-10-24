#!/usr/bin/env python3
"""Inject authentic Airflow OpenLineage parent into a rendered SparkApplication.

Invoked by the existing Person / Visit / Reconcile runtime controllers BEFORE
kubectl dry-run/apply. No OpenLineage POST, fabricated UUID, or business write.
When explicit NEW_ONLY opt-in is absent, the legacy render is unchanged.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import sys
import uuid

NAMESPACE = "healthcare-platform-airflow"
SPARK_NAMESPACE = "healthcare-platform-spark-business"
MARQUEZ_ENDPOINT = "http://marquez.dw-marquez.svc.cluster.local"
ALLOWED_TASKS = frozenset({"spark_patient", "spark_encounter", "spark_reconcile"})
KEYS = (
    "OPENLINEAGE_PARENT_NAMESPACE",
    "OPENLINEAGE_PARENT_JOB",
    "OPENLINEAGE_PARENT_RUN_ID",
)
ANCHOR = re.compile(r"(?m)^    spark\.openlineage\.appName: ([a-z0-9-]+)$")
JOB_PREFIX = "new_only_omop_consumer."


def render(text: str, *, task_id: str, env: dict[str, str]) -> tuple[str, str]:
    """Return unchanged legacy YAML or authenticated-parent configuration.

    No arbitrary namespace/job/Run ID is accepted. UUID is supplied by the
    Airflow OpenLineage provider macro, NEVER computed from DAG run strings.
    """
    if task_id not in ALLOWED_TASKS:
        raise ValueError("BLOCKED:UNEXPECTED_AIRFLOW_TASK")
    required = env.get("OPENLINEAGE_PARENT_REQUIRED", "")
    fields = tuple(env.get(key, "") for key in KEYS)
    if not required and not any(fields):
        return text, "LEGACY_UNCHANGED"
    if required != "YES" or any(not value for value in fields):
        raise ValueError("BLOCKED:INCOMPLETE_PARENT_CONTEXT")
    namespace, job, run_id = fields
    if namespace != NAMESPACE or job != JOB_PREFIX + task_id:
        raise ValueError("BLOCKED:UNTRUSTED_PARENT_JOB")
    try:
        canonical = str(uuid.UUID(run_id))
    except (ValueError, AttributeError) as exc:
        raise ValueError("BLOCKED:INVALID_PARENT_RUN_UUID") from exc
    if canonical != run_id:
        raise ValueError("BLOCKED:NONCANONICAL_PARENT_RUN_UUID")
    if "spark.openlineage.namespace: " + SPARK_NAMESPACE not in text:
        raise ValueError("BLOCKED:SPARK_NAMESPACE_MISMATCH")
    if "spark.openlineage.transport.url: " + MARQUEZ_ENDPOINT not in text:
        raise ValueError("BLOCKED:MARQUEZ_ENDPOINT_MISMATCH")
    if any(re.search(r"(?m)^\s+spark\.openlineage\.(?:parent|rootParent)", text)
           for _ in (0,)):
        raise ValueError("BLOCKED:PARENT_ALREADY_CONFIGURED")
    anchors = list(ANCHOR.finditer(text))
    if len(anchors) != 1:
        raise ValueError("BLOCKED:SPARK_APP_NAME_ANCHOR")
    addition = (
        "\n    spark.openlineage.parentJobNamespace: " + namespace
        + "\n    spark.openlineage.parentJobName: " + job
        + "\n    spark.openlineage.parentRunId: " + run_id
    )
    match = anchors[0]
    return text[:match.end()] + addition + text[match.end():], "REAL_AIRFLOW_PARENT_INJECTED"


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print("ERROR=expected rendered YAML path and exact task ID", file=sys.stderr)
        return 2
    source = Path(args[0])
    if not source.is_file() or source.stat().st_size > 128 * 1024:
        print("ERROR=missing or oversized rendered SparkApplication", file=sys.stderr)
        return 2
    try:
        original = source.read_text(encoding="utf-8")
        updated, result = render(original, task_id=args[1], env=os.environ)
        if updated != original:
            source.write_text(updated, encoding="utf-8")
    except (ValueError, UnicodeError, OSError) as exc:
        print("ERROR=" + str(exc), file=sys.stderr)
        return 2
    print("OPENLINEAGE_SPARK_PARENT_CONTEXT=" + result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
