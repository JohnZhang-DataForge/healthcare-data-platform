from datetime import datetime

from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator


with DAG(
    dag_id="airflow_smoke_test",
    description="Phase 2 Airflow deployment smoke test",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["platform", "smoke-test"],
) as dag:

    check_airflow = BashOperator(
        task_id="check_airflow",
        bash_command="""
        echo "======================================"
        echo "Airflow DAG execution test"
        echo "Hostname: $(hostname)"
        echo "Time: $(date)"
        echo "Airflow execution OK"
        echo "======================================"
        """,
    )
