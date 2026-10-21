from datetime import datetime
import json
from airflow.operators.python import PythonOperator
from task004_cdm_preflight_contract import validate_handoff
from task004_cdm_materialization_plan import plan as prepare_cdm_plan


def _validate_handoff_json(generate, person, visit):
    return validate_handoff(json.loads(generate), json.loads(person), json.loads(visit))


def _prepare_cdm_plan_json(handoff):
    return prepare_cdm_plan(json.loads(handoff))

from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from airflow.providers.cncf.kubernetes.secret import Secret


RUNTIME_IMAGE = (
    "ghcr.io/johnzhang-dataforge/"
    "healthcare-data-platform-task004-runtime"
    ":latest"
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

GENERATE_PUBLISH_ENV = {
    "BATCH_ID": (
        "task004-airflow-"
        "{{ run_id "
        "| replace(':', '-') "
        "| replace('+', '-') "
        "| replace('/', '-') "
        "| replace(' ', '-') }}"
    ),
    "POPULATION_SIZE": "{{ params.population_size }}",
    "SEED": "{{ params.seed }}",
    "CLINICIAN_SEED": "{{ params.clinician_seed }}",
    "REFERENCE_DATE": "{{ dag_run.run_after.strftime('%Y%m%d') }}",
    "STATE": "{{ params.state }}",
    "CITY": "{{ params.city }}",
    "LANDING_INGEST_DATE": "{{ dag_run.run_after.strftime('%Y-%m-%d') }}",
}

PROCESSING_ENV = {
    "BATCH_ID": (
        "{{ ti.xcom_pull(task_ids='generate_publish')"
        "['batch_id'] }}"
    ),
    "MANIFEST_URI": (
        "{{ ti.xcom_pull(task_ids='generate_publish')"
        "['manifest_uri'] }}"
    ),
    "MANIFEST_SHA256": (
        "{{ ti.xcom_pull(task_ids='generate_publish')"
        "['manifest_sha256'] }}"
    ),
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

GENERATE_PUBLISH_COMMAND = r"""
set -Eeuo pipefail

LOG=/tmp/task004-generate-publish.log

task004-runtime generate-publish 2>&1 | tee "$LOG"

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
import re
import sys
from pathlib import Path

state = json.loads(
    Path(sys.argv[1]).read_text(
        encoding="utf-8"
    )
)

assert state["status"] == "INTAKE_VERIFIED"
assert state["source_version"] == "v3.3.0"
assert state["verified_file_count"] == 18
assert state["report_source"] == "POD_LOG"

assert re.fullmatch(
    r"[0-9a-f]{64}",
    state["manifest_sha256"],
)

assert state["manifest_uri"] == (
    state["landing_uri"]
    + "manifest.json"
)

result = {
    "batch_id":
        state["batch_id"],
    "source_version":
        state["source_version"],
    "ingest_date":
        state["ingest_date"],
    "landing_uri":
        state["landing_uri"],
    "manifest_uri":
        state["manifest_uri"],
    "manifest_sha256":
        state["manifest_sha256"],
    "verified_file_count":
        state["verified_file_count"],
    "status":
        state["status"],
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
        image_pull_policy="Always",
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
        "TASK004 Synthea generation and Landing publication "
        "followed by Person, Visit, and batch reconciliation"
    ),
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    is_paused_upon_creation=False,
    params={
        "population_size": "20",
        "seed": "20261012",
        "clinician_seed": "20261012",
        "state": "Georgia",
        "city": "",
    },
    tags=[
        "task004",
        "synthea",
        "landing",
        "spark",
        "processing",
    ],
) as dag:

    generate_publish = control_pod(
        task_id="generate_publish",
        cmds=[
            "/bin/bash",
            "-lc",
        ],
        arguments=[
            GENERATE_PUBLISH_COMMAND,
        ],
        env_vars=GENERATE_PUBLISH_ENV,
        do_xcom_push=True,
    )

    person = control_pod(
        task_id="person",
        cmds=[
            "/bin/bash",
            "-lc",
        ],
        arguments=[
            PERSON_COMMAND,
        ],
        env_vars=PROCESSING_ENV,
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
        env_vars=PROCESSING_ENV,
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
            "BATCH_ID": (
                "{{ ti.xcom_pull(task_ids='generate_publish')"
                "['batch_id'] }}"
            ),
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

    cdm_load_preflight = PythonOperator(
        task_id="cdm_load_preflight",
        python_callable=_validate_handoff_json,
        op_args=[
            "{{ ti.xcom_pull(task_ids='generate_publish') | tojson }}",
            "{{ ti.xcom_pull(task_ids='person') | tojson }}",
            "{{ ti.xcom_pull(task_ids='visit') | tojson }}",
        ],
    )

    generate_publish >> [person, visit]
    [person, visit] >> reconcile
    cdm_materialization_plan = PythonOperator(
        task_id="cdm_materialization_plan",
        python_callable=_prepare_cdm_plan_json,
        op_args=["{{ ti.xcom_pull(task_ids='cdm_load_preflight') | tojson }}"],
    )

    reconcile >> cdm_load_preflight >> cdm_materialization_plan
