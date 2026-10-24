"""Render NEW_ONLY Spark KPO parent fields using real Provider macro functions.

Runs only in the pinned Airflow 3.2.2 CI container, without a scheduler,
metadatabase, K8s, Spark job, secrets, or any network access.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import uuid

from airflow.providers.openlineage.plugins import macros as real_provider_macros
from airflow.models.dagbag import DagBag
from jinja2 import Environment, StrictUndefined
import pendulum


ROOT = Path("/opt/local-data-platform")
DAGS = ROOT / "airflow/dags"
EXPECTED_DAG = "new_only_omop_consumer"
ROLES = ("spark_patient", "spark_encounter", "spark_reconcile")


def require(ok, reason):
    if not ok:
        raise AssertionError("BLOCKED:" + reason)


def verify():
    # Call the REAL Provider's implementation, not fake UUID generators.
    # The isolated parse-only container does not initialize task-runner plugin
    # discovery; verify deployment registration separately inside actual
    # Airflow Pods before authorizing a live Spark job.
    for name in ("lineage_job_namespace", "lineage_job_name", "lineage_run_id"):
        require(callable(getattr(real_provider_macros, name, None)),
                "OPENLINEAGE_PROVIDER_MACRO_NOT_INSTALLED_" + name)
    provider_namespace = SimpleNamespace(OpenLineageProviderPlugin=real_provider_macros)

    bag = DagBag(dag_folder=str(DAGS), include_examples=False, safe_mode=False)
    require(not bag.import_errors, "DAG_IMPORT_ERRORS")
    require(EXPECTED_DAG in bag.dags, "NEW_ONLY_DAG_MISSING")
    dag = bag.dags[EXPECTED_DAG]
    jinja = Environment(undefined=StrictUndefined, autoescape=False)
    seen_runs = set()
    for task_id in ROLES:
        task = dag.get_task(task_id)
        # Verify these really are KPO fields declared templateable by Airflow.
        require("env_vars" in task.template_fields,
                "KPO_ENV_VARS_NOT_TEMPLATABLE")
        # KPO normalizes dict input into Kubernetes V1EnvVar objects;
        # both dict and V1EnvVar list are legitimate operator internals.
        raw_env = task.env_vars
        if isinstance(raw_env, dict):
            env = raw_env
        elif isinstance(raw_env, list):
            env = {item.name: item.value for item in raw_env
                   if isinstance(getattr(item, "name", None), str)}
            require(len(env) == len(raw_env), "KPO_ENV_DUPLICATE_OR_INVALID")
        else:
            raise AssertionError("BLOCKED:KPO_PARENT_ENV_SHAPE")
        required = {
            "OPENLINEAGE_PARENT_REQUIRED",
            "OPENLINEAGE_PARENT_NAMESPACE",
            "OPENLINEAGE_PARENT_JOB",
            "OPENLINEAGE_PARENT_RUN_ID",
        }
        require(required.issubset(env), "KPO_PARENT_FIELDS_MISSING")
        require(env["OPENLINEAGE_PARENT_REQUIRED"] == "YES",
                "KPO_PARENT_NOT_REQUIRED")
        ti = SimpleNamespace(
            dag_id=EXPECTED_DAG, task_id=task_id, try_number=1,
            map_index=-1,
            logical_date=pendulum.datetime(2026, 10, 24, 21, 0, tz="UTC"),
        )
        rendered = {
            key: jinja.from_string(env[key]).render(
                macros=provider_namespace, task_instance=ti, ti=ti
            )
            for key in required
        }
        require(rendered["OPENLINEAGE_PARENT_NAMESPACE"]
                == "healthcare-platform-airflow",
                "PARENT_NAMESPACE_MISMATCH")
        require(rendered["OPENLINEAGE_PARENT_JOB"]
                == EXPECTED_DAG + "." + task_id,
                "PARENT_JOB_MISMATCH")
        run_id = rendered["OPENLINEAGE_PARENT_RUN_ID"]
        require(str(uuid.UUID(run_id)) == run_id,
                "INVALID_REAL_PROVIDER_UUID")
        # Provider should derive unique IDs for different task instances.
        require(run_id not in seen_runs, "DUPLICATE_TASK_RUN_ID")
        seen_runs.add(run_id)
        print("AIRFLOW_OPENLINEAGE_REAL_MACRO_RENDER=" + task_id + ":PASS")
    require(len(seen_runs) == len(ROLES), "INCOMPLETE_OPENLINEAGE_TASKS")
    print("AIRFLOW_OPENLINEAGE_PROVIDER_FUNCTIONS_OFFLINE=PASS")
    print("AIRFLOW_LIVE_PLUGIN_REGISTRATION=NOT_CHECKED")
    print("AIRFLOW_DATABASE_QUERY=NONE")
    print("DAGRUN_CREATED=NO")
    print("KUBERNETES_SPARK_OR_WRITER_EXECUTION=NO")


if __name__ == "__main__":
    verify()
