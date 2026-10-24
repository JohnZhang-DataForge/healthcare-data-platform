"""Render NEW_ONLY Spark KPO parent fields with the REAL Airflow provider plugin.

Runs only in the pinned Airflow 3.2.2 CI container, without a scheduler,
metadatabase, K8s, Spark job, secrets, or any network access.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import uuid

from airflow.sdk.execution_time import macros
from airflow.models.dagbag import DagBag
from airflow.sdk.plugins_manager import integrate_macros_plugins
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
    # This imports the actual Provider plugin registered in the Airflow image.
    # It must expose its own macros module via the same name as the DAG Jinja.
    integrate_macros_plugins()
    module = getattr(macros, "OpenLineageProviderPlugin", None)
    require(module is not None, "AIRFLOW_PROVIDER_MACROS_NOT_REGISTERED")
    for name in ("lineage_job_namespace", "lineage_job_name", "lineage_run_id"):
        require(callable(getattr(module, name, None)),
                "OPENLINEAGE_MACRO_MISSING_" + name)

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
        env = task.env_vars
        require(isinstance(env, dict), "KPO_PARENT_ENV_SHAPE")
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
                macros=macros, task_instance=ti, ti=ti
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
    print("AIRFLOW_OPENLINEAGE_PARENT_MACROS_OFFLINE=PASS")
    print("AIRFLOW_DATABASE_QUERY=NONE")
    print("DAGRUN_CREATED=NO")
    print("KUBERNETES_SPARK_OR_WRITER_EXECUTION=NO")


if __name__ == "__main__":
    verify()
