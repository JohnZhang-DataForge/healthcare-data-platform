from datetime import datetime

from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from airflow.providers.cncf.kubernetes.secret import Secret


RUNTIME_IMAGE = (
    "ghcr.io/johnzhang-dataforge/"
    "healthcare-data-platform-task004-runtime"
    "@sha256:"
    "bf7f4611a9dcbd8bd79b420f80c5f97f4ec92e0dbd5ba8132cea4be59fdf57bf"
)

CONTROL_NAMESPACE = "dw-spark"
CONTROL_SERVICE_ACCOUNT = "task004-control-runtime"

AWS_ACCESS_KEY = Secret(
    deploy_type="env",
    deploy_target="AWS_ACCESS_KEY_ID",
    secret="dw-spark-s3-secret",
    key="AWS_ACCESS_KEY_ID",
)

AWS_SECRET_KEY = Secret(
    deploy_type="env",
    deploy_target="AWS_SECRET_ACCESS_KEY",
    secret="dw-spark-s3-secret",
    key="AWS_SECRET_ACCESS_KEY",
)

COMMON_ENV = {
    "BATCH_ID": "{{ params.batch_id }}",
    "MANIFEST_URI": "{{ params.manifest_uri }}",
    "MANIFEST_SHA256": "{{ params.manifest_sha256 }}",
}

BASE_CONTAINER_SECURITY_CONTEXT = {
    "runAsNonRoot": True,
    "runAsUser": 10001,
    "runAsGroup": 10001,
    "allowPrivilegeEscalation": False,
    "capabilities": {
        "drop": ["ALL"],
    },
}

POD_SECURITY_CONTEXT = {
    "fsGroup": 10001,
}

PERSON_COMMAND = r"""
set -Eeuo pipefail

LOG=/tmp/task004-person.log

task004-runtime person 2>&1 | tee "$LOG"

STATE_FILE="$(
  awk -F= '
    $1 == "STATE_FILE" {
      print substr($0, index($0, "=") + 1)
    }
  ' "$LOG" | tail -1
)"

test -n "$STATE_FILE"
test -s "$STATE_FILE"

mkdir -p /airflow/xcom

python3 - "$STATE_FILE" <<'PY'
import json
import sys
from pathlib import Path

state = json.loads(
    Path(sys.argv[1]).read_text(
        encoding="utf-8"
    )
)

assert state["status"] == "PASS"
assert state["entity"] == "patient"
assert state["processing_readback"] == "PASS"

result = {
    "processing_data_uri":
        state["processing_data_uri"],
    "canonical_rows":
        state["canonical_rows"],
    "run_id":
        state["run_id"],
}

Path(
    "/airflow/xcom/return.json"
).write_text(
    json.dumps(
        result,
        sort_keys=True,
    ),
    encoding="utf-8",
)
PY
"""

VISIT_COMMAND = r"""
set -Eeuo pipefail

LOG=/tmp/task004-visit.log

task004-runtime visit 2>&1 | tee "$LOG"

STATE_FILE="$(
  awk -F= '
    $1 == "STATE_FILE" {
      print substr($0, index($0, "=") + 1)
    }
  ' "$LOG" | tail -1
)"

test -n "$STATE_FILE"
test -s "$STATE_FILE"

mkdir -p /airflow/xcom

python3 - "$STATE_FILE" <<'PY'
import json
import sys
from pathlib import Path

state = json.loads(
    Path(sys.argv[1]).read_text(
        encoding="utf-8"
    )
)

assert state["status"] == "PASS"
assert state["entity"] == "encounter"
assert state["processing_readback"] == "PASS"

result = {
    "processing_data_uri":
        state["processing_data_uri"],
    "canonical_rows":
        state["canonical_rows"],
    "run_id":
        state["run_id"],
}

Path(
    "/airflow/xcom/return.json"
).write_text(
    json.dumps(
        result,
        sort_keys=True,
    ),
    encoding="utf-8",
)
PY
"""


def control_pod(task_id, **kwargs):
    return KubernetesPodOperator(
        task_id=task_id,
        name=task_id,
        namespace=CONTROL_NAMESPACE,
        service_account_name=CONTROL_SERVICE_ACCOUNT,
        image=RUNTIME_IMAGE,
        image_pull_policy="IfNotPresent",
        in_cluster=True,
        get_logs=True,
        log_events_on_failure=True,
        node_selector={
            "workload": "platform",
        },
        security_context=POD_SECURITY_CONTEXT,
        container_security_context=(
            BASE_CONTAINER_SECURITY_CONTEXT
        ),
        on_finish_action="delete_succeeded_pod",
        on_kill_action="keep_pod",
        startup_timeout_seconds=180,
        **kwargs,
    )


with DAG(
    dag_id="task004_processing_pipeline",
    description=(
        "TASK004 canonical Person and Visit processing "
        "followed by batch reconciliation"
    ),
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    params={
        "batch_id":
            "task004-p20-first-landing-20261011",
        "manifest_uri": (
            "s3://health-landing/"
            "source=synthea/"
            "source_version=v3.3.0/"
            "ingest_date=2026-10-11/"
            "batch_id="
            "task004-p20-first-landing-20261011/"
            "manifest.json"
        ),
        "manifest_sha256": (
            "d7a1ce5fb3cc1e25737b2ed5c35b7d463bbc8e7523b6531dcd1ce819360ff445"
        ),
    },
    tags=[
        "task004",
        "synthea",
        "spark",
        "processing",
    ],
) as dag:

    person = control_pod(
        task_id="person",
        cmds=[
            "/bin/bash",
            "-lc",
        ],
        arguments=[
            PERSON_COMMAND,
        ],
        env_vars=COMMON_ENV,
        secrets=[
            AWS_ACCESS_KEY,
            AWS_SECRET_KEY,
        ],
        do_xcom_push=True,
    )

    visit = control_pod(
        task_id="visit",
        cmds=[
            "/bin/bash",
            "-lc",
        ],
        arguments=[
            VISIT_COMMAND,
        ],
        env_vars=COMMON_ENV,
        secrets=[
            AWS_ACCESS_KEY,
            AWS_SECRET_KEY,
        ],
        do_xcom_push=True,
    )

    reconcile = control_pod(
        task_id="reconcile",
        arguments=[
            "reconcile",
        ],
        env_vars={
            "BATCH_ID":
                "{{ params.batch_id }}",
            "PATIENT_PROCESSING_URI": (
                "{{ ti.xcom_pull(task_ids='person')"
                "['processing_data_uri'] }}"
            ),
            "ENCOUNTER_PROCESSING_URI": (
                "{{ ti.xcom_pull(task_ids='visit')"
                "['processing_data_uri'] }}"
            ),
            "EXPECTED_PATIENT_ROWS": (
                "{{ ti.xcom_pull(task_ids='person')"
                "['canonical_rows'] }}"
            ),
            "EXPECTED_ENCOUNTER_ROWS": (
                "{{ ti.xcom_pull(task_ids='visit')"
                "['canonical_rows'] }}"
            ),
        },
    )

    [person, visit] >> reconcile
