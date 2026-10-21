"""TASK004 NEW_ONLY manual Airflow S3->Claim read->Spark Person/Visit.

Manual spark_processing=True only for a genuinely ABSENT Claim. All default
runs still hold new batches; COMPLETED always skips. Spark writes Processing
S3 only; immutable Writer Handoff remains NOT_AUTHORIZED, no CDM COMMIT.
No automatic Claim or schedule.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from airflow.providers.cncf.kubernetes.secret import Secret

DAG_DIR=str(Path(__file__).resolve().parent)
if DAG_DIR not in sys.path:
    sys.path.insert(0,DAG_DIR)
from new_only_omop_routing import (select_verified_new_only, route_claim_status,
                                   route_new_only_writer_commit)
from new_only_omop_writer_handoff import prepare_new_only_writer_handoff
from landing_spark_processing import make_processing_pod, NEW_ONLY_PROCESSING_IMAGE


def prepare_spark_handoff_json(selected_json, claim_json, patient_json, encounter_json):
    """Reject missing/malformed Spark XCom, publish immutable read-only plan."""
    sources=[]
    for value in (selected_json,claim_json,patient_json,encounter_json):
        if isinstance(value,str):
            value=json.loads(value)
        if not isinstance(value,dict):
            raise ValueError("BLOCKED:NEW_ONLY_MISSING_SPARK_XCOM")
        sources.append(value)
    return prepare_new_only_writer_handoff(*sources)


DISCOVERY_IMAGE=(
    "ghcr.io/johnzhang-dataforge/healthcare-landing-discovery"
    ":latest"
)
CDM_RUNTIME_IMAGE=(
    "ghcr.io/johnzhang-dataforge/healthcare-data-platform-task004-cdm-runtime"
    ":latest"
)

S3_SECRETS=[
    Secret("env","AWS_ACCESS_KEY_ID","dw-spark-s3-secret","AWS_ACCESS_KEY_ID"),
    Secret("env","AWS_SECRET_ACCESS_KEY","dw-spark-s3-secret","AWS_SECRET_ACCESS_KEY"),
]
PG_SECRETS=[
    Secret("env","PGUSER","landing-claim-db","username"),
    Secret("env","PGPASSWORD","landing-claim-db","password"),
]

# Runs in pinned CDM runtime without downloading/installing dependencies.
# This is ONLY a READ-ONLY PostgreSQL lookup under landing_claim_worker.
CLAIM_STATUS_SCRIPT = """
import json,os
from pathlib import Path
import psycopg
batch=os.environ['BATCH_ID'];sha=os.environ['MANIFEST_SHA256'];uri=os.environ['MANIFEST_URI']
with psycopg.connect(host=os.environ['PGHOST'],port=os.environ.get('PGPORT','5432'),
    dbname='omop',user=os.environ['PGUSER'],password=os.environ['PGPASSWORD'],
    connect_timeout=8,options='-c default_transaction_read_only=on -c statement_timeout=20000') as db:
    db.read_only=True
    with db.cursor() as cur:
        cur.execute("SELECT current_user,current_setting('transaction_read_only')")
        role,readonly=cur.fetchone()
        if role!='landing_claim_worker' or readonly!='on':
            raise ValueError('BLOCKED:CLAIM_LOOKUP_PRINCIPAL')
        cur.execute('SELECT manifest_sha256,manifest_uri,status,attempt_count FROM etl.landing_batch_ledger WHERE source_system=%s AND batch_id=%s',( 'synthea',batch))
        claim=cur.fetchone()
        cur.execute('SELECT count(*) FROM etl.task004_batch_ledger WHERE batch_id=%s AND source_system=%s',(batch,'synthea'))
        legacy_count=cur.fetchone()[0]
    db.rollback()
if claim is not None and (claim[0]!=sha or claim[1]!=uri):
    raise ValueError('BLOCKED:CLAIM_LOOKUP_MANIFEST_DRIFT')
result={'source_system':'synthea','batch_id':batch,'manifest_sha256':sha,'manifest_uri':uri,
        'role':role,'pg_transaction_readonly':True,'business_mutation':False,
        'claim_status':claim[2] if claim else 'ABSENT',
        'attempt_count':claim[3] if claim else 0,
        'writer_ledger_rows':legacy_count}
Path('/airflow/xcom/return.json').write_text(json.dumps(result,sort_keys=True))
print('TASK004_AIRFLOW_NEW_ONLY_CLAIM_READONLY=PASS',flush=True)
print('TASK004_AIRFLOW_NEW_ONLY_CLAIM_STATE='+result['claim_status'],flush=True)
print('OMOP_BUSINESS_MUTATION=NO',flush=True)
"""

SECURITY={"runAsNonRoot":True,"runAsUser":10001,"runAsGroup":10001,
          "allowPrivilegeEscalation":False,"capabilities":{"drop":["ALL"]}}
NODE={"kubernetes.io/hostname":"worker02"}

with DAG(
    dag_id="new_only_omop_consumer",
    description="Manual NEW_ONLY S3->Spark->atomically fenced OMOP Writer; strict 2-gate COMMIT",
    start_date=datetime(2026,10,14),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    is_paused_upon_creation=True,
    default_args={"retries":0},
    tags=["task004","new-only","omop","manual-gated"],
) as dag:
    scan_ready_manifests=KubernetesPodOperator(
        task_id="scan_ready_manifests",name="new-only-consumer-discovery",
        namespace="dw-spark",service_account_name="task004-control-runtime",
        image=DISCOVERY_IMAGE,image_pull_policy="Always",
        in_cluster=True,get_logs=True,do_xcom_push=True,
        env_vars={"S3_ENDPOINT":"http://dw-seaweedfs-s3.dw-seaweedfs.svc.cluster.local:8333",
                  "S3_REGION":"us-east-1","AWS_EC2_METADATA_DISABLED":"true"},
        secrets=S3_SECRETS,
        node_selector=NODE,security_context={"fsGroup":10001},
        container_security_context=SECURITY,
        on_finish_action="delete_succeeded_pod",on_kill_action="keep_pod",
        startup_timeout_seconds=180,execution_timeout=timedelta(minutes=5),
    )
    select_verified_new_only_batch=PythonOperator(
        task_id="select_verified_new_only_batch",
        python_callable=select_verified_new_only,
        op_args=[
            "{{ ti.xcom_pull(task_ids='scan_ready_manifests') | tojson }}",
            "{{ dag_run.conf | tojson }}",
            "{{ dag_run.run_type.value }}",
        ],
    )
    inspect_claim_readonly=KubernetesPodOperator(
        task_id="inspect_claim_readonly",name="new-only-consumer-pg-readonly",
        namespace="dw-spark",service_account_name="task004-control-runtime",
        image=CDM_RUNTIME_IMAGE,image_pull_policy="Always",
        in_cluster=True,get_logs=True,do_xcom_push=True,
        cmds=["python","-c"],arguments=[CLAIM_STATUS_SCRIPT],
        env_vars={
            "PGHOST":"dw-postgre.dw-postgre.svc.cluster.local",
            "PGPORT":"5432",
            "BATCH_ID":"{{ ti.xcom_pull(task_ids='select_verified_new_only_batch')['batch_id'] }}",
            "MANIFEST_URI":"{{ ti.xcom_pull(task_ids='select_verified_new_only_batch')['manifest_uri'] }}",
            "MANIFEST_SHA256":"{{ ti.xcom_pull(task_ids='select_verified_new_only_batch')['manifest_sha256'] }}",
        },
        secrets=PG_SECRETS,node_selector=NODE,security_context={"fsGroup":10001},
        container_security_context=SECURITY,
        on_finish_action="delete_succeeded_pod",on_kill_action="keep_pod",
        startup_timeout_seconds=180,execution_timeout=timedelta(minutes=4),
    )
    route_new_only_status=BranchPythonOperator(
        task_id="route_new_only_status",
        python_callable=route_claim_status,
        op_args=[
            "{{ ti.xcom_pull(task_ids='select_verified_new_only_batch') | tojson }}",
            "{{ ti.xcom_pull(task_ids='inspect_claim_readonly') | tojson }}",
        ],
    )
    already_completed_no_replay=EmptyOperator(task_id="already_completed_no_replay")
    unclaimed_batch_hold=EmptyOperator(task_id="unclaimed_batch_hold")
    scan_ready_manifests >> select_verified_new_only_batch >> inspect_claim_readonly >> route_new_only_status
    # Explicit one-off manual spark_processing=True on a fresh, unclaimed
    # REAL S3 manifest is the only way to reach these Kubernetes controllers.
    # The frozen v2 image is supplied directly (the historical factory default
    # references another DAG's authorize_processing_replay task).
    SPARK_INPUT={
        "BATCH_ID":"{{ ti.xcom_pull(task_ids='select_verified_new_only_batch')['batch_id'] }}",
        "MANIFEST_URI":"{{ ti.xcom_pull(task_ids='select_verified_new_only_batch')['manifest_uri'] }}",
        "MANIFEST_SHA256":"{{ ti.xcom_pull(task_ids='select_verified_new_only_batch')['manifest_sha256'] }}",
    }
    spark_patient=make_processing_pod(
        "spark_patient",process="person",env_vars=SPARK_INPUT,
        with_xcom=True,image_override=NEW_ONLY_PROCESSING_IMAGE,
    )
    spark_encounter=make_processing_pod(
        "spark_encounter",process="visit",env_vars=SPARK_INPUT,
        with_xcom=True,image_override=NEW_ONLY_PROCESSING_IMAGE,
    )
    spark_reconcile=make_processing_pod(
        "spark_reconcile",process="reconcile",
        env_vars={
            "BATCH_ID":SPARK_INPUT["BATCH_ID"],
            "PATIENT_PROCESSING_URI":
                "{{ ti.xcom_pull(task_ids='spark_patient')['processing_data_uri'] }}",
            "ENCOUNTER_PROCESSING_URI":
                "{{ ti.xcom_pull(task_ids='spark_encounter')['processing_data_uri'] }}",
            "EXPECTED_PATIENT_ROWS":
                "{{ ti.xcom_pull(task_ids='spark_patient')['canonical_rows'] }}",
            "EXPECTED_ENCOUNTER_ROWS":
                "{{ ti.xcom_pull(task_ids='spark_encounter')['canonical_rows'] }}",
        },
        with_xcom=False,image_override=NEW_ONLY_PROCESSING_IMAGE,
    )
    prepare_writer_handoff=PythonOperator(
        task_id="prepare_writer_handoff",
        python_callable=prepare_spark_handoff_json,
        op_args=[
            "{{ ti.xcom_pull(task_ids='select_verified_new_only_batch') | tojson }}",
            "{{ ti.xcom_pull(task_ids='inspect_claim_readonly') | tojson }}",
            "{{ ti.xcom_pull(task_ids='spark_patient') | tojson }}",
            "{{ ti.xcom_pull(task_ids='spark_encounter') | tojson }}",
        ],
    )
    writer_awaits_live_preflight=EmptyOperator(
        task_id="writer_awaits_live_preflight",
    )
    # A new batch is NOT authorized to COMMIT merely because Spark produced
    # an immutable, read-only handoff. Requires manual dag_run.conf with
    # spark_processing=True and writer_commit=True. The actual Pod separately
    # requires a Kubernetes commit-enable/admin-credential secret.
    route_writer_authorization=BranchPythonOperator(
        task_id="route_writer_authorization",
        python_callable=route_new_only_writer_commit,
        op_args=[
            "{{ ti.xcom_pull(task_ids='select_verified_new_only_batch') | tojson }}",
            "{{ ti.xcom_pull(task_ids='prepare_writer_handoff') | tojson }}",
            "{{ dag_run.run_type.value }}",
        ],
    )
    WRITER_IMAGE=(
        "ghcr.io/johnzhang-dataforge/healthcare-data-platform-local-dp-omop-writer"
        ":latest"
    )
    execute_new_only_writer=KubernetesPodOperator(
        task_id="execute_new_only_writer",name="task004-new-only-atomic-writer",
        namespace="dw-spark",service_account_name="task004-control-runtime",
        image=WRITER_IMAGE,image_pull_policy="Always",
        in_cluster=True,get_logs=True,do_xcom_push=False,
        env_vars={
            "TASK004_WRITER_MODE":"COMMIT",
            "TASK004_WRITER_AIRFLOW_COMMIT_SELECTION":
              "{{ 'YES' if ti.xcom_pull(task_ids='select_verified_new_only_batch').get('writer_commit') is sameas true else 'NO' }}",
            "TASK004_WRITER_HANDOFF_JSON":
              "{{ ti.xcom_pull(task_ids='prepare_writer_handoff') | tojson }}",
            "TASK004_WRITER_BATCH_ID":
              "{{ ti.xcom_pull(task_ids='select_verified_new_only_batch')['batch_id'] }}",
            "TASK004_WRITER_MANIFEST_SHA256":
              "{{ ti.xcom_pull(task_ids='select_verified_new_only_batch')['manifest_sha256'] }}",
            "PGHOST":"dw-postgre.dw-postgre.svc.cluster.local",
            "PGPORT":"5432",
            "TASK004_S3_ENDPOINT_URL":"http://dw-seaweedfs-s3.dw-seaweedfs.svc.cluster.local:8333",
            "AWS_DEFAULT_REGION":"us-east-1",
            "AWS_EC2_METADATA_DISABLED":"true",
        },
        # Secrets must be separately staged in dw-spark. Their absence means
        # the Pod cannot run: missing secret == fail closed, never business DML.
        secrets=S3_SECRETS+[
            Secret("env","PGUSER","task004-cdm-reader-db","username"),
            Secret("env","PGPASSWORD","task004-cdm-reader-db","password"),
            Secret("env","TASK004_WRITER_ADMIN_PASSWORD","task004-new-only-writer-commit","password"),
            Secret("env","TASK004_WRITER_DEPLOY_ENABLE","task004-new-only-writer-commit","enabled"),
        ],
        node_selector=NODE,security_context={"fsGroup":10001},
        container_security_context=SECURITY,
        automount_service_account_token=False,
        on_finish_action="delete_succeeded_pod",on_kill_action="keep_pod",
        startup_timeout_seconds=180,execution_timeout=timedelta(minutes=15),
        retries=0,
    )
    writer_committed_verified=EmptyOperator(task_id="writer_committed_verified")

    route_new_only_status >> [already_completed_no_replay,unclaimed_batch_hold,
                              spark_patient,spark_encounter]
    [spark_patient,spark_encounter] >> spark_reconcile
    spark_reconcile >> prepare_writer_handoff >> route_writer_authorization
    route_writer_authorization >> [writer_awaits_live_preflight,execute_new_only_writer]
    execute_new_only_writer >> writer_committed_verified
