#!/usr/bin/env bash
# Guarded A3 configuration of the shared Airflow Scheduler.
# Only the opt-in portal DAG will emit; TASK004 remains unmodified.
set -Eeuo pipefail
NAMESPACE=dw-airflow
DEPLOY=dw-airflow-scheduler
CONTAINER=scheduler
test "$(kubectl get deploy "$DEPLOY" -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}')" = 1
test "$(kubectl get deploy "$DEPLOY" -n "$NAMESPACE" -o jsonpath='{.spec.replicas}')" = 1
test "$(kubectl get svc marquez -n dw-marquez -o jsonpath='{.spec.type}')" = ClusterIP
POD="$(kubectl get pods -n "$NAMESPACE" -o json | python3 -c 'import json,sys; a=json.load(sys.stdin)["items"]; b=[p for p in a if p["metadata"]["name"].startswith("dw-airflow-scheduler-") and p.get("status",{}).get("phase")=="Running"]; print(b[0]["metadata"]["name"] if b else "")')"
test -n "$POD"

# No restarts when any scheduler-managed Airflow task could be active.
kubectl exec -n "$NAMESPACE" "$POD" -c "$CONTAINER" -- python -c '
from airflow.models.taskinstance import TaskInstance
from airflow.utils.session import create_session
with create_session() as s:
    count=s.query(TaskInstance).filter(TaskInstance.state.in_(["running","queued","scheduled","restarting","up_for_retry","up_for_reschedule"])).count()
    print("A3_ACTIVE_TASK_INSTANCES="+str(count))
    assert count==0,"A3_SHARED_SCHEDULER_BUSY"
'
echo A3_SHARED_AIRFLOW_IDLE_GATE=PASS

kubectl exec -n "$NAMESPACE" "$POD" -c "$CONTAINER" -- python -c '
import urllib.request
with urllib.request.urlopen("http://marquez.dw-marquez.svc.cluster.local/api/v1/namespaces",timeout=8) as r:
    assert r.status==200
print("A3_PRIVATE_MARQUEZ_REACHABLE=PASS")
'
TRANSPORT='{"type":"http","url":"http://marquez.dw-marquez.svc.cluster.local","endpoint":"api/v1/lineage"}'
kubectl set env -n "$NAMESPACE" deployment/"$DEPLOY" --containers="$CONTAINER" \
  "AIRFLOW__OPENLINEAGE__TRANSPORT=$TRANSPORT" \
  "AIRFLOW__OPENLINEAGE__NAMESPACE=healthcare-platform-airflow" \
  "AIRFLOW__OPENLINEAGE__SELECTIVE_ENABLE=True" \
  "AIRFLOW__OPENLINEAGE__DISABLE_SOURCE_CODE=True" \
  "AIRFLOW__OPENLINEAGE__EXECUTION_TIMEOUT=5"
kubectl rollout status -n "$NAMESPACE" deployment/"$DEPLOY" --timeout=240s
POD="$(kubectl get pods -n "$NAMESPACE" -o json | python3 -c 'import json,sys; a=json.load(sys.stdin)["items"]; b=[p for p in a if p["metadata"]["name"].startswith("dw-airflow-scheduler-") and not p.get("metadata",{}).get("deletionTimestamp") and p.get("status",{}).get("phase")=="Running" and any(c.get("name")=="scheduler" and c.get("ready") for c in p.get("status",{}).get("containerStatuses",[]))]; print(b[0]["metadata"]["name"] if b else "")')"
test -n "$POD"
kubectl exec -n "$NAMESPACE" "$POD" -c scheduler -- python -c '
import json
from airflow.configuration import conf
assert json.loads(conf.get("openlineage","transport"))=={"type":"http","url":"http://marquez.dw-marquez.svc.cluster.local","endpoint":"api/v1/lineage"}
assert conf.getboolean("openlineage","selective_enable")
assert conf.getboolean("openlineage","disable_source_code")
assert conf.get("openlineage","namespace")=="healthcare-platform-airflow"
print("A3_REAL_SCHEDULER_SELECTIVE_OPENLINEAGE_CONFIG=PASS")
'
echo A3_TASK004_DAG_MODIFICATION=NO
echo A3_OMOP_POSTGRES_MUTATION=NO
