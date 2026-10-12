#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1
ROOT="${PROJECT_ROOT:-/data/spark/healthcare-data-platform}"
APP="$ROOT/spark/apps/task004/reconcile_person_visit.py"
TPL="$ROOT/spark/manifests/task004/person-visit-reconciliation.yaml.tpl"
NS=dw-spark
: "${PATIENT_PROCESSING_URI:?PATIENT_PROCESSING_URI is required}"
: "${ENCOUNTER_PROCESSING_URI:?ENCOUNTER_PROCESSING_URI is required}"
: "${BATCH_ID:?BATCH_ID is required}"
: "${EXPECTED_PATIENT_ROWS:?EXPECTED_PATIENT_ROWS is required}"
: "${EXPECTED_ENCOUNTER_ROWS:?EXPECTED_ENCOUNTER_ROWS is required}"
[[ "$EXPECTED_PATIENT_ROWS" =~ ^[1-9][0-9]*$ ]]
[[ "$EXPECTED_ENCOUNTER_ROWS" =~ ^[1-9][0-9]*$ ]]
[[ -s "$APP" && -s "$TPL" ]]
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
APP_NAME="task004-reconcile-${STAMP,,}-$$"
CM_NAME="${APP_NAME}-app"
RUN_DIR="$ROOT/runtime/reports/task004/batch-reconciliation/$APP_NAME"
mkdir -p "$RUN_DIR"
YAML="$RUN_DIR/sparkapplication.yaml"
LOG="$RUN_DIR/driver.log"
python3 - "$TPL" "$YAML" "$APP_NAME" "$CM_NAME" "$PATIENT_PROCESSING_URI" "$ENCOUNTER_PROCESSING_URI" "$BATCH_ID" "$EXPECTED_PATIENT_ROWS" "$EXPECTED_ENCOUNTER_ROWS" <<'PY'
import sys
from pathlib import Path
src,out,app,cm,puri,euri,batch,prows,erows=sys.argv[1:]
text=Path(src).read_text()
vals={"__APP_NAME__":app,"__CONFIGMAP_NAME__":cm,"__PATIENT_URI__":puri,"__ENCOUNTER_URI__":euri,"__BATCH_ID__":batch,"__EXPECTED_PATIENT_ROWS__":prows,"__EXPECTED_ENCOUNTER_ROWS__":erows}
for k,v in vals.items(): text=text.replace(k,v)
left=[k for k in vals if k in text]
if left: raise SystemExit("ERROR unresolved placeholders: "+repr(left))
Path(out).write_text(text)
PY
kubectl apply --dry-run=client -f "$YAML" >/dev/null
kubectl create configmap "$CM_NAME" -n "$NS" --from-file=reconcile_person_visit.py="$APP" --dry-run=client -o yaml | kubectl apply -f - >/dev/null
kubectl apply -f "$YAML" >/dev/null
STATE=""
for _ in $(seq 1 180); do
  STATE="$(kubectl get sparkapplication "$APP_NAME" -n "$NS" -o jsonpath='{.status.applicationState.state}' 2>/dev/null || true)"
  case "$STATE" in COMPLETED|FAILED|FAILING|UNKNOWN) break;; esac
  sleep 5
done
DRIVER_POD="${APP_NAME}-driver"
kubectl logs "$DRIVER_POD" -n "$NS" > "$LOG" 2>&1 || true
if [[ "$STATE" != "COMPLETED" ]]; then
  tail -250 "$LOG" || true
  echo "FAILED_SPARKAPPLICATION_RETAINED=YES"
  echo "FAILED_CONFIGMAP_RETAINED=YES"
  echo "ERROR=Batch reconciliation SparkApplication failed"
  exit 1
fi
for marker in   "PATIENT_ROWS=$EXPECTED_PATIENT_ROWS"   "ENCOUNTER_ROWS=$EXPECTED_ENCOUNTER_ROWS"   "ORPHAN_ENCOUNTERS=0"   "PROCESSING_MUTATION=NO"   "POSTGRESQL_MUTATION=NO"   "BATCH_RECONCILIATION=PASS"   "RESULT=PASS"
do
  grep -Fx "$marker" "$LOG" >/dev/null || { echo "ERROR=missing reconciliation marker: $marker"; exit 1; }
done
cat "$LOG"
kubectl delete sparkapplication "$APP_NAME" -n "$NS" --ignore-not-found=true --wait=true >/dev/null
kubectl delete configmap "$CM_NAME" -n "$NS" --ignore-not-found=true >/dev/null
echo "TASK004_BATCH_RECONCILIATION=PASS"
echo "PATIENT_ROWS=$EXPECTED_PATIENT_ROWS"
echo "ENCOUNTER_ROWS=$EXPECTED_ENCOUNTER_ROWS"
echo "PROCESSING_MUTATION=NO"
echo "POSTGRESQL_MUTATION=NO"
echo "SUCCESSFUL_SPARKAPPLICATION_RESIDUAL=NO"
echo "SUCCESSFUL_CONFIGMAP_RESIDUAL=NO"
echo "RESULT=PASS"
