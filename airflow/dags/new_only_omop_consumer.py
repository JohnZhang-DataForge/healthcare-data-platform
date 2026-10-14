"""TASK004 NEW_ONLY manual Airflow consumer router: S3 -> PG -> safe terminal.

First-stage real DAG, not yet a batch executor. Unclaimed/new batches are
explicitly held; COMPLETED batches are skipped without rerunning Spark/Writer.
Airflow is not permitted to claim until the full consumer has its own
integration acceptance. Independent Generator/Portal sessions are unaffected.
"""
from __future__ import annotations
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
from new_only_omop_routing import select_verified_new_only, route_claim_status

DISCOVERY_IMAGE=(
    "ghcr.io/johnzhang-dataforge/healthcare-landing-discovery"
    "@sha256:059d94e4d1348c194956203fea6b19be23ec39595127eea397419e66fa4e5924"
)
CDM_RUNTIME_IMAGE=(
    "ghcr.io/johnzhang-dataforge/healthcare-data-platform-task004-cdm-runtime"
    "@sha256:94979587aeee2f2ea13e2c27ffc5a8850b97381f3f126c72201fe2b2b3086f5e"
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
    description="Manual NEW_ONLY real S3+Claim route; COMPLETED skip / new batch hold",
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
        image=DISCOVERY_IMAGE,image_pull_policy="IfNotPresent",
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
        image=CDM_RUNTIME_IMAGE,image_pull_policy="IfNotPresent",
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
    route_new_only_status >> [already_completed_no_replay,unclaimed_batch_hold]
