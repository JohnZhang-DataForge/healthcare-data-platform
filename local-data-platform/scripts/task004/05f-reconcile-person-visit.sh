#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  echo "ERROR=execute with bash; do not source"
  return 2
fi

ROOT="${PROJECT_ROOT:-/data/spark/healthcare-data-platform}"

APP="${ROOT}/spark/apps/task004/reconcile_person_visit.py"
TPL="${ROOT}/spark/manifests/task004/person-visit-reconciliation.yaml.tpl"

NS="dw-spark"
REPORT_ROOT="${ROOT}/runtime/reports/task004/batch-reconciliation"

MODE="run"

if [[ "${1:-}" == "--render-only" ]]; then
  MODE="render"
elif [[ $# -ne 0 ]]; then
  echo "ERROR=unsupported argument"
  exit 2
fi

APP_NAME=""
CM_NAME=""
DRIVER_POD=""
RUN_DIR=""
LOG=""
STATE_FILE=""
SUCCESS=0

fail() {
  echo "ERROR=$*" >&2
  exit 1
}

report_failure_resources() {
  command -v kubectl >/dev/null 2>&1 || return 0

  if [[ -n "$APP_NAME" ]]     && kubectl get sparkapplication "$APP_NAME" -n "$NS" >/dev/null 2>&1
  then
    echo "FAILED_SPARKAPPLICATION_RETAINED=YES" >&2
  fi

  if [[ -n "$CM_NAME" ]]     && kubectl get configmap "$CM_NAME" -n "$NS" >/dev/null 2>&1
  then
    echo "FAILED_CONFIGMAP_RETAINED=YES" >&2
  fi

  if [[ -n "$DRIVER_POD" ]]     && kubectl get pod "$DRIVER_POD" -n "$NS" >/dev/null 2>&1
  then
    echo "FAILED_DRIVER_POD_RETAINED=YES" >&2
  fi
}

on_exit() {
  local rc="$?"

  if [[ "$rc" -ne 0 && "$SUCCESS" -eq 0 ]]; then
    report_failure_resources
    echo "RECONCILIATION_EXIT_CODE=$rc" >&2
  fi
}

trap on_exit EXIT

: "${PATIENT_PROCESSING_URI:?PATIENT_PROCESSING_URI is required}"
: "${ENCOUNTER_PROCESSING_URI:?ENCOUNTER_PROCESSING_URI is required}"
: "${BATCH_ID:?BATCH_ID is required}"
: "${EXPECTED_PATIENT_ROWS:?EXPECTED_PATIENT_ROWS is required}"
: "${EXPECTED_ENCOUNTER_ROWS:?EXPECTED_ENCOUNTER_ROWS is required}"

[[ "$EXPECTED_PATIENT_ROWS" =~ ^[1-9][0-9]*$ ]]   || fail "EXPECTED_PATIENT_ROWS must be a positive integer"

[[ "$EXPECTED_ENCOUNTER_ROWS" =~ ^[1-9][0-9]*$ ]]   || fail "EXPECTED_ENCOUNTER_ROWS must be a positive integer"

for file in "$APP" "$TPL"
do
  [[ -s "$file" ]]     || fail "missing reconciliation source: $file"
done

URI_PREFLIGHT="$(
  python3 -     "$PATIENT_PROCESSING_URI"     "$ENCOUNTER_PROCESSING_URI"     "$BATCH_ID" <<'PY'
import sys
from urllib.parse import urlparse

patient_uri, encounter_uri, expected_batch = sys.argv[1:]


def require(ok, message):
    if not ok:
        raise SystemExit("ERROR=" + message)


def parse_processing_uri(uri, expected_entity):
    parsed = urlparse(uri)

    require(
        parsed.scheme == "s3a",
        f"{expected_entity} URI scheme must be s3a",
    )
    require(
        parsed.netloc == "health-processing",
        f"{expected_entity} URI bucket must be health-processing",
    )

    parts = [
        item
        for item in parsed.path.strip("/").split("/")
        if item
    ]

    require(
        len(parts) >= 9,
        f"{expected_entity} URI path is incomplete",
    )
    require(
        parts[-3:] == ["work", "normalized", "data"],
        f"{expected_entity} URI must end in work/normalized/data/",
    )

    values = {}

    for item in parts[:-3]:
        if "=" not in item:
            continue

        key, value = item.split("=", 1)
        values[key] = value

    for key in (
        "source",
        "source_version",
        "ingest_date",
        "batch_id",
        "entity",
        "run_id",
    ):
        require(
            values.get(key, "").strip() != "",
            f"{expected_entity} URI missing {key}",
        )

    require(
        values["batch_id"] == expected_batch,
        f"{expected_entity} URI batch_id mismatch",
    )
    require(
        values["entity"] == expected_entity,
        f"{expected_entity} URI entity mismatch",
    )

    return values


patient = parse_processing_uri(
    patient_uri,
    "patient",
)

encounter = parse_processing_uri(
    encounter_uri,
    "encounter",
)

for key in (
    "source",
    "source_version",
    "ingest_date",
    "batch_id",
):
    require(
        patient[key] == encounter[key],
        f"Processing URI {key} mismatch",
    )

print("INPUT_URI_PREFLIGHT=PASS")
print("SOURCE_SYSTEM=" + patient["source"])
print("SOURCE_VERSION=" + patient["source_version"])
print("SOURCE_INGEST_DATE=" + patient["ingest_date"])
PY
)"

printf '%s\n' "$URI_PREFLIGHT"

URI_SOURCE_SYSTEM="$(
  printf '%s\n' "$URI_PREFLIGHT"   | awk -F= '$1 == "SOURCE_SYSTEM" {print substr($0, index($0, "=") + 1)}'
)"

URI_SOURCE_VERSION="$(
  printf '%s\n' "$URI_PREFLIGHT"   | awk -F= '$1 == "SOURCE_VERSION" {print substr($0, index($0, "=") + 1)}'
)"

URI_SOURCE_INGEST_DATE="$(
  printf '%s\n' "$URI_PREFLIGHT"   | awk -F= '$1 == "SOURCE_INGEST_DATE" {print substr($0, index($0, "=") + 1)}'
)"

[[ -n "$URI_SOURCE_SYSTEM" ]]   || fail "URI source_system preflight output missing"

[[ -n "$URI_SOURCE_VERSION" ]]   || fail "URI source_version preflight output missing"

[[ -n "$URI_SOURCE_INGEST_DATE" ]]   || fail "URI source_ingest_date preflight output missing"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

APP_NAME="task004-reconcile-${STAMP,,}-$$"
CM_NAME="${APP_NAME}-app"
DRIVER_POD="${APP_NAME}-driver"

RUN_DIR="${REPORT_ROOT}/${APP_NAME}"
YAML="${RUN_DIR}/sparkapplication.yaml"
LOG="${RUN_DIR}/driver.log"
STATE_FILE="${RUN_DIR}/run-state.json"

mkdir -p "$RUN_DIR"

python3 -   "$TPL"   "$YAML"   "$APP_NAME"   "$CM_NAME"   "$PATIENT_PROCESSING_URI"   "$ENCOUNTER_PROCESSING_URI"   "$BATCH_ID"   "$EXPECTED_PATIENT_ROWS"   "$EXPECTED_ENCOUNTER_ROWS" <<'PY'
import sys
from pathlib import Path

(
    source,
    output,
    app_name,
    configmap_name,
    patient_uri,
    encounter_uri,
    batch_id,
    patient_rows,
    encounter_rows,
) = sys.argv[1:]

text = Path(source).read_text(
    encoding="utf-8"
)

values = {
    "__APP_NAME__": app_name,
    "__CONFIGMAP_NAME__": configmap_name,
    "__PATIENT_URI__": patient_uri,
    "__ENCOUNTER_URI__": encounter_uri,
    "__BATCH_ID__": batch_id,
    "__EXPECTED_PATIENT_ROWS__": patient_rows,
    "__EXPECTED_ENCOUNTER_ROWS__": encounter_rows,
}

for key, value in values.items():
    text = text.replace(key, value)

remaining = [
    key
    for key in values
    if key in text
]

if remaining:
    raise SystemExit(
        "ERROR=unresolved placeholders: "
        + repr(remaining)
    )

Path(output).write_text(
    text,
    encoding="utf-8",
)
PY

kubectl apply   --dry-run=client   -f "$YAML"   >/dev/null

if [[ "$MODE" == "render" ]]; then
  echo "TASK004_RECONCILIATION_INTERFACE_RENDER=PASS"
  echo "BATCH_ID=$BATCH_ID"
  echo "EXPECTED_PATIENT_ROWS=$EXPECTED_PATIENT_ROWS"
  echo "EXPECTED_ENCOUNTER_ROWS=$EXPECTED_ENCOUNTER_ROWS"
  echo "PATIENT_PROCESSING_URI=$PATIENT_PROCESSING_URI"
  echo "ENCOUNTER_PROCESSING_URI=$ENCOUNTER_PROCESSING_URI"
  echo "SPARKAPPLICATION_APPLY=NO"
  echo "PROCESSING_MUTATION=NO"
  echo "POSTGRESQL_MUTATION=NO"
  echo "RESULT=PASS"

  rm -rf "$RUN_DIR"
  SUCCESS=1
  exit 0
fi

kubectl get secret   dw-spark-s3-secret   -n "$NS"   >/dev/null

kubectl get serviceaccount   spark-job   -n "$NS"   >/dev/null

kubectl create configmap   "$CM_NAME"   -n "$NS"   --from-file=reconcile_person_visit.py="$APP"   --dry-run=client   -o yaml | kubectl apply     -f -     >/dev/null

kubectl apply   -f "$YAML"   >/dev/null

FINAL_STATE=""

for _ in $(seq 1 180)
do
  FINAL_STATE="$(
    kubectl get sparkapplication       "$APP_NAME"       -n "$NS"       -o jsonpath='{.status.applicationState.state}'       2>/dev/null     || true
  )"

  case "$FINAL_STATE" in
    COMPLETED|FAILED|FAILING|UNKNOWN)
      break
      ;;
  esac

  sleep 5
done

kubectl logs   "$DRIVER_POD"   -n "$NS"   > "$LOG"   2>&1   || true

if [[ "$FINAL_STATE" != "COMPLETED" ]]; then
  tail -250 "$LOG" || true
  fail "Batch reconciliation SparkApplication failed"
fi

REQUIRED_MARKERS=(
  "PATIENT_ROWS=$EXPECTED_PATIENT_ROWS"
  "PATIENT_UNIQUE_IDS=$EXPECTED_PATIENT_ROWS"
  "ENCOUNTER_ROWS=$EXPECTED_ENCOUNTER_ROWS"
  "ENCOUNTER_UNIQUE_IDS=$EXPECTED_ENCOUNTER_ROWS"
  "ORPHAN_ENCOUNTERS=0"
  "SOURCE_BATCH_ID=$BATCH_ID"
  "PROCESSING_MUTATION=NO"
  "POSTGRESQL_MUTATION=NO"
  "BATCH_RECONCILIATION=PASS"
  "RESULT=PASS"
)

for marker in "${REQUIRED_MARKERS[@]}"
do
  grep -Fx     "$marker"     "$LOG"     >/dev/null     || fail "missing reconciliation marker: $marker"
done

REFERENCED_PATIENTS="$(
  grep '^REFERENCED_PATIENTS=' "$LOG"   | tail -1   | cut -d= -f2-
)"

LOG_SOURCE_SYSTEM="$(
  grep '^SOURCE_SYSTEM=' "$LOG"   | tail -1   | cut -d= -f2-
)"

LOG_SOURCE_VERSION="$(
  grep '^SOURCE_VERSION=' "$LOG"   | tail -1   | cut -d= -f2-
)"

LOG_SOURCE_INGEST_DATE="$(
  grep '^SOURCE_INGEST_DATE=' "$LOG"   | tail -1   | cut -d= -f2-
)"

[[ "$REFERENCED_PATIENTS" =~ ^[1-9][0-9]*$ ]]   || fail "invalid REFERENCED_PATIENTS marker"

(( REFERENCED_PATIENTS <= EXPECTED_PATIENT_ROWS ))   || fail "REFERENCED_PATIENTS exceeds Patient rows"

[[ "$LOG_SOURCE_SYSTEM" == "$URI_SOURCE_SYSTEM" ]]   || fail "driver source_system differs from URI lineage"

[[ "$LOG_SOURCE_VERSION" == "$URI_SOURCE_VERSION" ]]   || fail "driver source_version differs from URI lineage"

[[ "$LOG_SOURCE_INGEST_DATE" == "$URI_SOURCE_INGEST_DATE" ]]   || fail "driver source_ingest_date differs from URI lineage"

python3 -   "$STATE_FILE"   "$APP_NAME"   "$BATCH_ID"   "$PATIENT_PROCESSING_URI"   "$ENCOUNTER_PROCESSING_URI"   "$EXPECTED_PATIENT_ROWS"   "$EXPECTED_ENCOUNTER_ROWS"   "$REFERENCED_PATIENTS"   "$LOG_SOURCE_SYSTEM"   "$LOG_SOURCE_VERSION"   "$LOG_SOURCE_INGEST_DATE" <<'PY'
import json
import sys
from pathlib import Path

(
    output,
    spark_application,
    batch_id,
    patient_uri,
    encounter_uri,
    patient_rows,
    encounter_rows,
    referenced_patients,
    source_system,
    source_version,
    source_ingest_date,
) = sys.argv[1:]

state = {
    "task": "TASK-004",
    "stage": "batch-reconciliation",
    "status": "PASS",
    "batch_id": batch_id,
    "spark_application": spark_application,
    "patient_processing_uri": patient_uri,
    "encounter_processing_uri": encounter_uri,
    "patient_rows": int(patient_rows),
    "patient_unique_ids": int(patient_rows),
    "encounter_rows": int(encounter_rows),
    "encounter_unique_ids": int(encounter_rows),
    "referenced_patients": int(referenced_patients),
    "orphan_encounters": 0,
    "source_system": source_system,
    "source_version": source_version,
    "source_ingest_date": source_ingest_date,
    "processing_mutation": False,
    "postgresql_mutation": False,
}

Path(output).write_text(
    json.dumps(
        state,
        indent=2,
        sort_keys=True,
    )
    + "\n",
    encoding="utf-8",
)
PY

cat "$LOG"

kubectl delete sparkapplication   "$APP_NAME"   -n "$NS"   --ignore-not-found=true   --wait=true   >/dev/null

kubectl delete configmap   "$CM_NAME"   -n "$NS"   --ignore-not-found=true   >/dev/null

for _ in $(seq 1 30)
do
  APP_EXISTS=0
  CM_EXISTS=0
  POD_EXISTS=0

  kubectl get sparkapplication "$APP_NAME" -n "$NS" >/dev/null 2>&1     && APP_EXISTS=1

  kubectl get configmap "$CM_NAME" -n "$NS" >/dev/null 2>&1     && CM_EXISTS=1

  kubectl get pod "$DRIVER_POD" -n "$NS" >/dev/null 2>&1     && POD_EXISTS=1

  if [[ "$APP_EXISTS" -eq 0     && "$CM_EXISTS" -eq 0     && "$POD_EXISTS" -eq 0 ]]
  then
    break
  fi

  sleep 1
done

if kubectl get sparkapplication "$APP_NAME" -n "$NS" >/dev/null 2>&1; then
  fail "successful SparkApplication residual remains"
fi

if kubectl get configmap "$CM_NAME" -n "$NS" >/dev/null 2>&1; then
  fail "successful ConfigMap residual remains"
fi

if kubectl get pod "$DRIVER_POD" -n "$NS" >/dev/null 2>&1; then
  fail "successful driver Pod residual remains"
fi

echo "TASK004_BATCH_RECONCILIATION=PASS"
echo "PATIENT_ROWS=$EXPECTED_PATIENT_ROWS"
echo "PATIENT_UNIQUE_IDS=$EXPECTED_PATIENT_ROWS"
echo "ENCOUNTER_ROWS=$EXPECTED_ENCOUNTER_ROWS"
echo "ENCOUNTER_UNIQUE_IDS=$EXPECTED_ENCOUNTER_ROWS"
echo "REFERENCED_PATIENTS=$REFERENCED_PATIENTS"
echo "ORPHAN_ENCOUNTERS=0"
echo "SOURCE_SYSTEM=$LOG_SOURCE_SYSTEM"
echo "SOURCE_VERSION=$LOG_SOURCE_VERSION"
echo "SOURCE_BATCH_ID=$BATCH_ID"
echo "SOURCE_INGEST_DATE=$LOG_SOURCE_INGEST_DATE"
echo "PROCESSING_MUTATION=NO"
echo "POSTGRESQL_MUTATION=NO"
echo "SUCCESSFUL_SPARKAPPLICATION_RESIDUAL=NO"
echo "SUCCESSFUL_CONFIGMAP_RESIDUAL=NO"
echo "SUCCESSFUL_DRIVER_POD_RESIDUAL=NO"
echo "STATE_FILE=$STATE_FILE"
echo "RESULT=PASS"

SUCCESS=1
trap - EXIT
exit 0
