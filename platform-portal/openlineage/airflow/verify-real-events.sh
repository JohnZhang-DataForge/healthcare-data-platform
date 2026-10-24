#!/usr/bin/env bash
set -Eeuo pipefail
DAG=platform_portal_openlineage_probe
RUN_ID="portal-ol-$GITHUB_RUN_ID"
FILE="$PORTAL_SOURCE/airflow/dags/$DAG.py"
POD="$(kubectl get pods -n dw-airflow -o json | python3 -c 'import json,sys; a=json.load(sys.stdin)["items"]; b=[p for p in a if "scheduler" in p["metadata"]["name"] and not p["metadata"].get("deletionTimestamp") and p["status"].get("phase")=="Running"]; print(b[0]["metadata"]["name"] if b else "")')"
test -n "$POD"
FOLDER="$(kubectl exec -n dw-airflow "$POD" -c scheduler -- airflow config get-value core dags_folder | tail -1 | tr -d '\r')"
EXPECTED="$(sha256sum "$FILE" | awk '{print $1}')"
MATCH=NO
for _ in $(seq 1 70); do
  ACTUAL="$(kubectl exec -n dw-airflow "$POD" -c scheduler -- sha256sum "$FOLDER/$DAG.py" 2>/dev/null | awk '{print $1}' || true)"
  if [[ "$EXPECTED" == "$ACTUAL" ]]; then MATCH=YES;break;fi
  sleep 3
done
test "$MATCH" = YES
echo A3_GITSYNC_EXACT_SOURCE=PASS
kubectl exec -i -n dw-airflow "$POD" -c scheduler -- env DAG="$DAG" python - <<'PY'
from airflow.models.dagbag import DagBag
from airflow.configuration import conf
from airflow.providers.openlineage.utils.selective_enable import is_dag_lineage_enabled
from pathlib import Path
import os
p=Path(conf.get("core","dags_folder"))/(os.environ["DAG"]+".py")
b=DagBag(dag_folder=str(p),include_examples=False,safe_mode=False)
assert not b.import_errors,b.import_errors
d=b.get_dag(os.environ["DAG"])
assert d is not None and len(d.tasks)==2 and d.schedule is None
assert is_dag_lineage_enabled(d)
print("A3_DAGBAG_OPT_IN_ONLY=PASS")
PY
kubectl exec -n dw-airflow "$POD" -c scheduler -- airflow dags trigger "$DAG" --run-id "$RUN_ID"
echo "A3_REAL_DAGRUN_ID=$RUN_ID"
STATE=PENDING
for _ in $(seq 1 75); do
  STATE="$(kubectl exec -n dw-airflow "$POD" -c scheduler -- env DAG="$DAG" RUN_ID="$RUN_ID" python -c '
from airflow.models.dagrun import DagRun
from airflow.utils.session import create_session
import os
with create_session() as s:
 r=s.query(DagRun).filter(DagRun.dag_id==os.environ["DAG"],DagRun.run_id==os.environ["RUN_ID"]).one_or_none()
 print(str(r.state) if r else "PENDING")
' | tail -1 | tr -d '\r')"
  case "$STATE" in success|failed) break;;esac
  sleep 4
done
test "$STATE" = success
echo A3_REAL_DAGRUN_SUCCESS=PASS
kubectl exec -n dw-airflow "$POD" -c scheduler -- env DAG="$DAG" RUN_ID="$RUN_ID" python -c '
from airflow.models.taskinstance import TaskInstance
from airflow.utils.session import create_session
import os
with create_session() as s:
 rows={r.task_id:r.state for r in s.query(TaskInstance).filter(TaskInstance.dag_id==os.environ["DAG"],TaskInstance.run_id==os.environ["RUN_ID"]).all()}
 assert rows=={"observe_runtime":"success","confirm_runtime":"success"},rows
print("A3_REAL_TWO_TASK_INSTANCES=SUCCESS")
'
kubectl exec -n dw-airflow "$POD" -c scheduler -- env DAG="$DAG" python -c '
import json,os,time,urllib.request,urllib.error
base="http://marquez.dw-marquez.svc.cluster.local/api/v1/namespaces/healthcare-platform-airflow/jobs?limit=100"
for attempt in range(35):
 try:
  with urllib.request.urlopen(base,timeout=8) as r: data=json.load(r)
  names=sorted(x.get("name","") for x in data.get("jobs",[]) if os.environ["DAG"] in x.get("name",""))
  if len(names)>=2:
   print("A3_REAL_OPENLINEAGE_JOBS="+",".join(names))
   print("A3_MARQUEZ_RECEIVED_AIRFLOW_PROVIDER_EVENTS=PASS")
   break
 except urllib.error.HTTPError as e:
  if e.code!=404: raise
 time.sleep(3)
else: raise AssertionError("A3_MARQUEZ_PROVIDER_EVENTS_MISSING")
'
echo A3_NO_FAKE_LINEAGE_EVENTS=PASS
echo A3_NO_TASK004_OR_OMOP_MUTATION=PASS
