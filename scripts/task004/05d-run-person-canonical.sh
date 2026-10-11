#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT="${PROJECT_ROOT:-/data/spark/healthcare-data-platform}"

BRIDGE="${ROOT}/scripts/task004/05c-resolve-runtime-lineage.sh"

APP="${ROOT}/spark/apps/person/synthea_patient_adapter.py"
COMMON="${ROOT}/spark/common/batch_manifest.py"
CONTRACT="${ROOT}/spark/contracts/canonical/patient-v1.json"
TEMPLATE="${ROOT}/spark/manifests/task002/person-canonical-adapter.yaml.tpl"

NS="dw-spark"

REPORT_ROOT="${ROOT}/runtime/reports/task004/person-canonical"

MODE="run"

if [[ "${1:-}" == "--render-only" ]]; then
  MODE="render"
elif [[ $# -ne 0 ]]; then
  echo "ERROR=unsupported argument"
  exit 2
fi

fail() {
  echo "ERROR=$*"
  exit 1
}

: "${BATCH_ID:?BATCH_ID is required}"
: "${MANIFEST_URI:?MANIFEST_URI is required}"
: "${MANIFEST_SHA256:?MANIFEST_SHA256 is required}"

[[ "$MANIFEST_SHA256" =~ ^[0-9a-f]{64}$ ]] \
  || fail "MANIFEST_SHA256 is invalid"

for file in \
  "$BRIDGE" \
  "$APP" \
  "$COMMON" \
  "$CONTRACT" \
  "$TEMPLATE"
do
  [[ -s "$file" ]] \
    || fail "missing runtime source: ${file}"
done

RESOLVED="$(
  "$BRIDGE" patients
)"

readarray -t META < <(
  printf '%s\n' "$RESOLVED" \
  | python3 -c '
import json
import sys

d = json.load(sys.stdin)

for key in (
    "manifest_status",
    "manifest_sha256",
    "source",
    "source_version",
    "batch_id",
    "ingest_date",
    "path",
    "source_uri",
    "row_count",
    "size_bytes",
    "sha256",
):
    print(d[key])
'
)

MANIFEST_STATUS="${META[0]}"
RESOLVED_MANIFEST_SHA="${META[1]}"
SOURCE="${META[2]}"
SOURCE_VERSION="${META[3]}"
RESOLVED_BATCH_ID="${META[4]}"
INGEST_DATE="${META[5]}"
SOURCE_FILE="${META[6]}"
SOURCE_URI="${META[7]}"
EXPECTED_ROWS="${META[8]}"
SOURCE_FILE_SIZE_BYTES="${META[9]}"
SOURCE_FILE_SHA256="${META[10]}"

[[ "$MANIFEST_STATUS" == "INTAKE_VERIFIED" ]] \
  || fail "manifest not INTAKE_VERIFIED"

[[ "$RESOLVED_MANIFEST_SHA" == "$MANIFEST_SHA256" ]] \
  || fail "manifest SHA mismatch"

[[ "$RESOLVED_BATCH_ID" == "$BATCH_ID" ]] \
  || fail "batch mismatch"

[[ "$EXPECTED_ROWS" =~ ^[1-9][0-9]*$ ]] \
  || fail "invalid patient row count"

[[ "$SOURCE_FILE_SIZE_BYTES" =~ ^[1-9][0-9]*$ ]] \
  || fail "invalid patient size"

[[ "$SOURCE_FILE_SHA256" =~ ^[0-9a-f]{64}$ ]] \
  || fail "invalid patient SHA"

UTC_STAMP="$(
  date -u +%Y%m%dT%H%M%SZ
)"

RUN_ID="task004-person-${UTC_STAMP}-$$"

APP_NAME="$(
  printf '%s' \
    "task004-person-${UTC_STAMP,,}-$$" \
  | tr -cd 'a-z0-9-'
)"

CONFIGMAP_NAME="$(
  printf '%s' \
    "task004-person-app-${UTC_STAMP,,}-$$" \
  | tr -cd 'a-z0-9-'
)"

PROCESSING_DATA_URI="s3a://health-processing/source=${SOURCE}/source_version=${SOURCE_VERSION}/ingest_date=${INGEST_DATE}/batch_id=${BATCH_ID}/entity=patient/run_id=${RUN_ID}/work/normalized/data/"

MANIFEST_S3A="$(
  printf '%s' "$MANIFEST_URI" \
  | sed 's#^s3://#s3a://#'
)"

RUN_DIR="${REPORT_ROOT}/${RUN_ID}"
RENDERED="${RUN_DIR}/sparkapplication.yaml"
DRIVER_LOG="${RUN_DIR}/driver.log"
STATE_FILE="${RUN_DIR}/run-state.json"

mkdir -p "$RUN_DIR"

python3 - \
  "$TEMPLATE" \
  "$RENDERED" \
  "$APP_NAME" \
  "$CONFIGMAP_NAME" \
  "$MANIFEST_S3A" \
  "$BATCH_ID" \
  "$RUN_ID" \
  "$PROCESSING_DATA_URI" <<'PY'
import sys
from pathlib import Path

(
    template,
    output,
    app_name,
    configmap_name,
    manifest_uri,
    batch_id,
    run_id,
    processing_uri,
) = sys.argv[1:]

text = Path(
    template
).read_text(
    encoding="utf-8"
)

values = {
    "__APP_NAME__":
        app_name,

    "__CONFIGMAP_NAME__":
        configmap_name,

    "__MANIFEST_URI__":
        manifest_uri,

    "__BATCH_ID__":
        batch_id,

    "__RUN_ID__":
        run_id,

    "__PROCESSING_DATA_URI__":
        processing_uri,
}

for key, value in values.items():
    text = text.replace(
        key,
        value,
    )

text = text.replace(
    "healthcare-task: task002",
    "healthcare-task: task004",
)

for key in values:
    if key in text:
        raise SystemExit(
            "ERROR: unresolved placeholder "
            + key
        )

Path(
    output
).write_text(
    text,
    encoding="utf-8",
)
PY

kubectl apply \
  --dry-run=client \
  -f "$RENDERED" \
  >/dev/null

if [[ "$MODE" == "render" ]]; then
  echo "TASK004_PERSON_INTERFACE_RENDER=PASS"
  echo "BATCH_ID=${BATCH_ID}"
  echo "MANIFEST_SHA256=${MANIFEST_SHA256}"
  echo "SOURCE_DATASET=patients"
  echo "SOURCE_FILE=${SOURCE_FILE}"
  echo "SOURCE_URI=${SOURCE_URI}"
  echo "EXPECTED_ROWS=${EXPECTED_ROWS}"
  echo "SOURCE_FILE_SIZE_BYTES=${SOURCE_FILE_SIZE_BYTES}"
  echo "SOURCE_FILE_SHA256=${SOURCE_FILE_SHA256}"
  echo "PROCESSING_DATA_URI=${PROCESSING_DATA_URI}"
  echo "SPARKAPPLICATION_APPLY=NO"
  echo "PROCESSING_WRITE=NO"
  echo "POSTGRESQL_MUTATION=NO"
  echo "RESULT=PASS"

  rm -rf "$RUN_DIR"
  exit 0
fi

kubectl get secret \
  dw-spark-s3-secret \
  -n "$NS" \
  >/dev/null

kubectl get serviceaccount \
  spark-job \
  -n "$NS" \
  >/dev/null

kubectl create configmap \
  "$CONFIGMAP_NAME" \
  -n "$NS" \
  --from-file=synthea_patient_adapter.py="$APP" \
  --from-file=batch_manifest.py="$COMMON" \
  --from-file=patient-v1.json="$CONTRACT" \
  --dry-run=client \
  -o yaml \
| kubectl apply \
    -f - \
    >/dev/null

kubectl apply \
  -f "$RENDERED" \
  >/dev/null

FINAL_STATE=""

for _ in $(seq 1 180)
do
  FINAL_STATE="$(
    kubectl get sparkapplication \
      "$APP_NAME" \
      -n "$NS" \
      -o jsonpath='{.status.applicationState.state}' \
      2>/dev/null \
    || true
  )"

  case "$FINAL_STATE" in
    COMPLETED)
      break
      ;;
    FAILED|FAILING|UNKNOWN)
      break
      ;;
  esac

  sleep 5
done

DRIVER_POD="${APP_NAME}-driver"

kubectl logs \
  "$DRIVER_POD" \
  -n "$NS" \
  > "$DRIVER_LOG" \
  2>&1 \
  || true

if [[ "$FINAL_STATE" != "COMPLETED" ]]; then
  tail -250 "$DRIVER_LOG" || true
  echo "FAILED_SPARKAPPLICATION_RETAINED=YES"
  echo "FAILED_CONFIGMAP_RETAINED=YES"
  fail "Person SparkApplication failed"
fi

for marker in \
  "INTAKE_MANIFEST_STATUS=INTAKE_VERIFIED" \
  "EXPECTED_ROWS=${EXPECTED_ROWS}" \
  "CANONICAL_ROWS=${EXPECTED_ROWS}" \
  "PROCESSING_READBACK_ROWS=${EXPECTED_ROWS}" \
  "CANONICAL_CONTRACT=PASS" \
  "PROCESSING_WRITE=PASS" \
  "PROCESSING_READBACK=PASS" \
  "PERSON_CANONICAL_ADAPTER=PASS"
do
  grep -Fx \
    "$marker" \
    "$DRIVER_LOG" \
    >/dev/null \
    || fail "missing Person driver marker: ${marker}"
done

python3 - \
  "$STATE_FILE" \
  "$BATCH_ID" \
  "$MANIFEST_URI" \
  "$MANIFEST_SHA256" \
  "$RUN_ID" \
  "$APP_NAME" \
  "$SOURCE" \
  "$SOURCE_VERSION" \
  "$INGEST_DATE" \
  "$SOURCE_FILE" \
  "$SOURCE_FILE_SHA256" \
  "$SOURCE_FILE_SIZE_BYTES" \
  "$EXPECTED_ROWS" \
  "$PROCESSING_DATA_URI" <<'PY'
import json
import sys
from pathlib import Path

(
    output,
    batch_id,
    manifest_uri,
    manifest_sha,
    run_id,
    app_name,
    source,
    source_version,
    ingest_date,
    source_file,
    source_file_sha,
    source_size,
    rows,
    processing_uri,
) = sys.argv[1:]

doc = {
    "task":
        "TASK-004",

    "stage":
        "person-canonical",

    "status":
        "PASS",

    "entity":
        "patient",

    "batch_id":
        batch_id,

    "manifest_uri":
        manifest_uri,

    "manifest_sha256":
        manifest_sha,

    "run_id":
        run_id,

    "spark_application":
        app_name,

    "source":
        source,

    "source_version":
        source_version,

    "ingest_date":
        ingest_date,

    "source_file":
        source_file,

    "source_file_sha256":
        source_file_sha,

    "source_file_size_bytes":
        int(source_size),

    "canonical_rows":
        int(rows),

    "processing_data_uri":
        processing_uri,

    "processing_readback":
        "PASS",

    "postgresql_mutation":
        False,
}

Path(output).write_text(
    json.dumps(
        doc,
        indent=2,
        sort_keys=True,
    )
    + "\n",
    encoding="utf-8",
)
PY

kubectl delete sparkapplication \
  "$APP_NAME" \
  -n "$NS" \
  --ignore-not-found=true \
  --wait=true \
  >/dev/null

kubectl delete configmap \
  "$CONFIGMAP_NAME" \
  -n "$NS" \
  --ignore-not-found=true \
  >/dev/null

echo "TASK004_PERSON_CANONICAL_RUNTIME=PASS"
echo "BATCH_ID=${BATCH_ID}"
echo "EXPECTED_ROWS=${EXPECTED_ROWS}"
echo "CANONICAL_ROWS=${EXPECTED_ROWS}"
echo "PROCESSING_READBACK=PASS"
echo "POSTGRESQL_MUTATION=NO"
echo "SUCCESSFUL_SPARKAPPLICATION_RESIDUAL=NO"
echo "SUCCESSFUL_CONFIGMAP_RESIDUAL=NO"
echo "STATE_FILE=${STATE_FILE}"
echo "RESULT=PASS"
