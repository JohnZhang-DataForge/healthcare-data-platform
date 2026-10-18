"""Real opt-in Airflow OpenLineage validation without TASK004 business work."""
from datetime import datetime, timezone

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from airflow.providers.openlineage.utils.selective_enable import enable_lineage


def _observe() -> str:
    print("PORTAL_A3_NO_BUSINESS_DATA_OBSERVE=PASS")
    return "portal-observed"


def _confirm() -> str:
    print("PORTAL_A3_NO_BUSINESS_DATA_CONFIRM=PASS")
    return "portal-confirmed"


with enable_lineage(
    DAG(
        dag_id="platform_portal_openlineage_probe",
        description="Real OpenLineage opt-in Airflow run; no S3/PG/Spark/Writer operations",
        start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        schedule=None,
        catchup=False,
        max_active_runs=1,
        tags=["platform-portal", "openlineage", "opt-in"],
    )
) as dag:
    a = PythonOperator(task_id="observe_runtime", python_callable=_observe)
    b = PythonOperator(task_id="confirm_runtime", python_callable=_confirm)
    a >> b
