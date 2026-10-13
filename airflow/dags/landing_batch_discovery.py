"""Scheduled, producer-independent SeaweedFS Landing discovery.

The first Pod discovers immutable S3 Manifest candidates; the second Pod
queries a least-privilege PostgreSQL consumer ledger. Claiming is DISABLED by
default until an explicit per-batch allowlist and ETL consumer have been deployed.
No Generator, Spark or OMOP business writes are triggered here.
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from airflow.providers.cncf.kubernetes.secret import Secret
from airflow.operators.python import PythonOperator, ShortCircuitOperator
from landing_spark_processing import (
    select_verified_processing_replay,
    processing_gate,
    validate_processing_output,
    make_processing_pod,
)


CLAIM_IMAGE = (
    "ghcr.io/johnzhang-dataforge/healthcare-landing-claim"
    "@sha256:cdc9666b0834d0af88cc60ce4b5da4f5b5161b09c12886e95f80342a1fcd5eea"
)

DISCOVERY_IMAGE = (
    "ghcr.io/johnzhang-dataforge/healthcare-landing-discovery"
    "@sha256:06a5caaf1d62e62fa7f6227de2422690f1c8e4bf7a893c6c239456affce0bfbd"
)

S3_ACCESS_KEY = Secret(
    deploy_type="env",
    deploy_target="AWS_ACCESS_KEY_ID",
    secret="dw-spark-s3-secret",
    key="AWS_ACCESS_KEY_ID",
)

S3_SECRET_KEY = Secret(
    deploy_type="env",
    deploy_target="AWS_SECRET_ACCESS_KEY",
    secret="dw-spark-s3-secret",
    key="AWS_SECRET_ACCESS_KEY",
)

with DAG(
    dag_id="landing_batch_discovery",
    description="Periodic Landing discovery with optional safeguarded historical Spark processing replay",
    start_date=datetime(2026, 10, 13),
    schedule="*/15 * * * *",
    catchup=False,
    max_active_runs=1,
    is_paused_upon_creation=True,
    default_args={"retries": 1, "retry_delay": timedelta(minutes=2)},
    tags=["landing", "s3", "discovery", "claim-guard"],
) as dag:
    scan_ready_manifests = KubernetesPodOperator(
        task_id="scan_ready_manifests",
        name="landing-batch-discovery",
        namespace="dw-spark",
        service_account_name="task004-control-runtime",
        image=DISCOVERY_IMAGE,
        image_pull_policy="IfNotPresent",
        in_cluster=True,
        get_logs=True,
        log_events_on_failure=True,
        do_xcom_push=True,
        env_vars={
            "S3_ENDPOINT": "http://dw-seaweedfs-s3.dw-seaweedfs.svc.cluster.local:8333",
            "S3_REGION": "us-east-1",
            "AWS_EC2_METADATA_DISABLED": "true",
        },
        secrets=[S3_ACCESS_KEY, S3_SECRET_KEY],
        node_selector={"kubernetes.io/hostname": "worker02"},
        security_context={"fsGroup": 10001},
        container_security_context={
            "runAsNonRoot": True,
            "runAsUser": 10001,
            "runAsGroup": 10001,
            "allowPrivilegeEscalation": False,
            "capabilities": {"drop": ["ALL"]},
        },
        on_finish_action="delete_succeeded_pod",
        on_kill_action="keep_pod",
        startup_timeout_seconds=180,
        execution_timeout=timedelta(minutes=6),
    )

    evaluate_batch_claims = KubernetesPodOperator(
        task_id="evaluate_batch_claims",
        name="landing-batch-claim-guard",
        namespace="dw-spark",
        service_account_name="task004-control-runtime",
        image=CLAIM_IMAGE,
        image_pull_policy="IfNotPresent",
        in_cluster=True,
        get_logs=True,
        log_events_on_failure=True,
        do_xcom_push=True,
        arguments=[
            "--inventory-json",
            "{{ (ti.xcom_pull(task_ids='scan_ready_manifests') or {}) | tojson }}",
        ],
        env_vars={
            "PGHOST": "dw-postgre.dw-postgre.svc.cluster.local",
            "PGPORT": "5432",
            "CLAIM_ENABLE": "NO",
            "CLAIM_ALLOWLIST": "",
            "S3_ENDPOINT": "http://dw-seaweedfs-s3.dw-seaweedfs.svc.cluster.local:8333",
            "AWS_EC2_METADATA_DISABLED": "true",
        },
        secrets=[
            Secret("env", "PGUSER", "landing-claim-db", "username"),
            Secret("env", "PGPASSWORD", "landing-claim-db", "password"),
            S3_ACCESS_KEY, S3_SECRET_KEY,
        ],
        node_selector={"kubernetes.io/hostname": "worker02"},
        security_context={"fsGroup": 10001},
        container_security_context={
            "runAsNonRoot": True,
            "runAsUser": 10001,
            "runAsGroup": 10001,
            "allowPrivilegeEscalation": False,
            "capabilities": {"drop": ["ALL"]},
        },
        on_finish_action="delete_succeeded_pod",
        on_kill_action="keep_pod",
        startup_timeout_seconds=180,
        execution_timeout=timedelta(minutes=6),
    )

    authorize_processing_replay = PythonOperator(
        task_id="authorize_processing_replay",
        python_callable=select_verified_processing_replay,
        op_args=[
            "{{ ti.xcom_pull(task_ids='scan_ready_manifests') | tojson }}",
            "{{ ti.xcom_pull(task_ids='evaluate_batch_claims') | tojson }}",
            "{{ dag_run.conf | tojson }}",
            "{{ dag_run.run_type.value }}",
        ],
    )

    processing_only_gate = ShortCircuitOperator(
        task_id="processing_only_gate",
        python_callable=processing_gate,
        op_args=[
            "{{ ti.xcom_pull(task_ids='authorize_processing_replay') | tojson }}",
        ],
    )

    SELECTED = {
        "BATCH_ID": "{{ ti.xcom_pull(task_ids='authorize_processing_replay')['batch_id'] }}",
        "MANIFEST_URI": "{{ ti.xcom_pull(task_ids='authorize_processing_replay')['manifest_uri'] }}",
        "MANIFEST_SHA256": "{{ ti.xcom_pull(task_ids='authorize_processing_replay')['manifest_sha256'] }}",
    }

    spark_patient = make_processing_pod(
        "spark_patient", process="person", env_vars=SELECTED, with_xcom=True
    )
    spark_encounter = make_processing_pod(
        "spark_encounter", process="visit", env_vars=SELECTED, with_xcom=True
    )

    spark_reconcile = make_processing_pod(
        "spark_reconcile",
        process="reconcile",
        env_vars={
            "BATCH_ID": SELECTED["BATCH_ID"],
            "PATIENT_PROCESSING_URI":
                "{{ ti.xcom_pull(task_ids='spark_patient')['processing_data_uri'] }}",
            "ENCOUNTER_PROCESSING_URI":
                "{{ ti.xcom_pull(task_ids='spark_encounter')['processing_data_uri'] }}",
            "EXPECTED_PATIENT_ROWS":
                "{{ ti.xcom_pull(task_ids='spark_patient')['canonical_rows'] }}",
            "EXPECTED_ENCOUNTER_ROWS":
                "{{ ti.xcom_pull(task_ids='spark_encounter')['canonical_rows'] }}",
        },
        with_xcom=False,
    )

    verify_spark_processing = PythonOperator(
        task_id="verify_spark_processing",
        python_callable=validate_processing_output,
        op_args=[
            "{{ ti.xcom_pull(task_ids='authorize_processing_replay') | tojson }}",
            "{{ ti.xcom_pull(task_ids='spark_patient') | tojson }}",
            "{{ ti.xcom_pull(task_ids='spark_encounter') | tojson }}",
        ],
    )

    scan_ready_manifests >> evaluate_batch_claims >> authorize_processing_replay
    authorize_processing_replay >> processing_only_gate
    processing_only_gate >> [spark_patient, spark_encounter]
    [spark_patient, spark_encounter] >> spark_reconcile >> verify_spark_processing
