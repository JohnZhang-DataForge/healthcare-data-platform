#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="/data/spark/healthcare-data-platform"

RESOLVER="${ROOT}/apps/resolve_verified_intake_file.py"

APP="${ROOT}/spark/apps/visit/synthea_encounter_adapter.py"
CONTRACT="${ROOT}/spark/contracts/canonical/encounter-v1.json"
TEMPLATE="${ROOT}/spark/manifests/task003/encounter-canonical-adapter.yaml.tpl"

NS="dw-spark"


echo "============================================================"
echo "TASK-003 / STEP 03"
echo "Synthea Encounter -> Canonical Encounter v1"
echo "============================================================"
echo


# ============================================================
# 1. Runtime prerequisites
# ============================================================

echo "[1/7] Runtime prerequisites..."


for file in \
  "${RESOLVER}" \
  "${APP}" \
  "${CONTRACT}" \
  "${TEMPLATE}"
do
    [[ -s "${file}" ]] || {
        echo "ERROR: missing file:"
        echo "  ${file}"
        exit 1
    }
done


kubectl get secret \
  dw-spark-s3-secret \
  -n "${NS}" \
  >/dev/null


kubectl get serviceaccount \
  spark-job \
  -n "${NS}" \
  >/dev/null


echo "PASS"
echo


# ============================================================
# 2. Resolve authoritative TASK-001 encounters entry
# ============================================================

echo "[2/7] Resolve verified TASK-001 encounters.csv..."


readarray -t META < <(
    "${RESOLVER}" \
      encounters \
      --format json \
    | python3 -c '
import json
import sys

d = json.load(sys.stdin)

values = [
    d["manifest_status"],
    d["manifest_uri"],
    d["manifest_sha256"],
    d["source"],
    d["source_version"],
    d["batch_id"],
    d["ingest_date"],
    d["path"],
    d["source_uri"],
    d["row_count"],
    d["size_bytes"],
    d["sha256"],
]

for value in values:
    print(value)
'
)


MANIFEST_STATUS="${META[0]}"
MANIFEST_URI="${META[1]}"
MANIFEST_SHA256="${META[2]}"
SOURCE="${META[3]}"
SOURCE_VERSION="${META[4]}"
BATCH_ID="${META[5]}"
INGEST_DATE="${META[6]}"
SOURCE_FILE="${META[7]}"
SOURCE_URI="${META[8]}"
EXPECTED_ROWS="${META[9]}"
SOURCE_FILE_SIZE_BYTES="${META[10]}"
SOURCE_FILE_SHA256="${META[11]}"


if [[ "${MANIFEST_STATUS}" != "INTAKE_VERIFIED" ]]
then
    echo "ERROR: TASK-001 manifest is not verified."
    exit 1
fi


if [[ ! "${EXPECTED_ROWS}" =~ ^[1-9][0-9]*$ ]]
then
    echo "ERROR: invalid source row count."
    exit 1
fi


if [[ ! "${SOURCE_FILE_SIZE_BYTES}" =~ ^[1-9][0-9]*$ ]]
then
    echo "ERROR: invalid source file size."
    exit 1
fi


if [[ ! "${SOURCE_FILE_SHA256}" =~ ^[0-9a-f]{64}$ ]]
then
    echo "ERROR: invalid source SHA256."
    exit 1
fi


INPUT_URI="$(
    printf '%s' "${SOURCE_URI}" \
    | sed 's#^s3://#s3a://#'
)"


echo "MANIFEST_STATUS=${MANIFEST_STATUS}"
echo "MANIFEST_SHA256=${MANIFEST_SHA256}"
echo "SOURCE=${SOURCE}"
echo "SOURCE_VERSION=${SOURCE_VERSION}"
echo "BATCH_ID=${BATCH_ID}"
echo "INGEST_DATE=${INGEST_DATE}"
echo "SOURCE_FILE=${SOURCE_FILE}"
echo "EXPECTED_ROWS=${EXPECTED_ROWS}"
echo "SOURCE_FILE_SIZE_BYTES=${SOURCE_FILE_SIZE_BYTES}"
echo "SOURCE_FILE_SHA256=${SOURCE_FILE_SHA256}"
echo "PASS"
echo


# ============================================================
# 3. Create immutable processing run
# ============================================================

echo "[3/7] Create processing run..."


UTC_STAMP="$(
    date -u +%Y%m%dT%H%M%SZ
)"

RUN_ID="encounter-${UTC_STAMP}-$$"

APP_NAME="$(
    printf '%s' \
      "task003-encounter-${UTC_STAMP,,}-$$"
)"

CONFIGMAP_NAME="$(
    printf '%s' \
      "task003-encounter-app-${UTC_STAMP,,}-$$"
)"


PROCESSING_DATA_URI="s3a://health-processing/source=${SOURCE}/source_version=${SOURCE_VERSION}/ingest_date=${INGEST_DATE}/batch_id=${BATCH_ID}/entity=encounter/run_id=${RUN_ID}/work/normalized/data/"


RUN_DIR="${ROOT}/runtime/reports/task003/step03/${RUN_ID}"

RENDERED="${RUN_DIR}/sparkapplication.yaml"
DRIVER_LOG="${RUN_DIR}/driver.log"
STATE_FILE="${RUN_DIR}/run-state.json"


mkdir -p "${RUN_DIR}"


echo "RUN_ID=${RUN_ID}"
echo "APP_NAME=${APP_NAME}"
echo "INPUT_URI=${INPUT_URI}"
echo "PROCESSING_DATA_URI=${PROCESSING_DATA_URI}"

echo "PASS"
echo


# ============================================================
# 4. ConfigMap
# ============================================================

echo "[4/7] Encounter adapter ConfigMap..."


kubectl create configmap \
    "${CONFIGMAP_NAME}" \
    -n "${NS}" \
    --from-file=synthea_encounter_adapter.py="${APP}" \
    --from-file=encounter-v1.json="${CONTRACT}" \
    --dry-run=client \
    -o yaml \
| kubectl apply -f - \
    >/dev/null


echo "CONFIGMAP=${CONFIGMAP_NAME}"
echo "PASS"
echo


# ============================================================
# 5. Render SparkApplication
# ============================================================

echo "[5/7] Render SparkApplication..."


sed \
    -e "s/__APP_NAME__/${APP_NAME}/g" \
    -e "s/__CONFIGMAP_NAME__/${CONFIGMAP_NAME}/g" \
    -e "s#__INPUT_URI__#${INPUT_URI}#g" \
    -e "s#__OUTPUT_DATA_URI__#${PROCESSING_DATA_URI}#g" \
    -e "s/__EXPECTED_ROWS__/${EXPECTED_ROWS}/g" \
    -e "s/__SOURCE_SYSTEM__/${SOURCE}/g" \
    -e "s/__SOURCE_VERSION__/${SOURCE_VERSION}/g" \
    -e "s/__SOURCE_BATCH_ID__/${BATCH_ID}/g" \
    -e "s/__SOURCE_INGEST_DATE__/${INGEST_DATE}/g" \
    -e "s#__SOURCE_FILE__#${SOURCE_FILE}#g" \
    -e "s/__SOURCE_FILE_SHA256__/${SOURCE_FILE_SHA256}/g" \
    -e "s/__SOURCE_FILE_SIZE_BYTES__/${SOURCE_FILE_SIZE_BYTES}/g" \
    -e "s/__PROCESSING_RUN_ID__/${RUN_ID}/g" \
    "${TEMPLATE}" \
    > "${RENDERED}"


if grep -q \
  '__[A-Z_]*__' \
  "${RENDERED}"
then
    echo "ERROR: unresolved template placeholder."

    grep \
      '__[A-Z_]*__' \
      "${RENDERED}"

    exit 1
fi


kubectl apply \
    --dry-run=client \
    -f "${RENDERED}" \
    >/dev/null


echo "PASS"
echo


# ============================================================
# 6. Submit + wait
# ============================================================

echo "[6/7] Submit Encounter SparkApplication..."


kubectl apply \
    -f "${RENDERED}"


FINAL_STATE=""


for _ in $(seq 1 180)
do
    FINAL_STATE="$(
        kubectl get sparkapplication \
            "${APP_NAME}" \
            -n "${NS}" \
            -o jsonpath='{.status.applicationState.state}' \
            2>/dev/null \
        || true
    )"


    case "${FINAL_STATE}" in

        COMPLETED)
            break
            ;;

        FAILED|FAILING|UNKNOWN)
            break
            ;;

    esac


    sleep 5
done


echo "FINAL_STATE=${FINAL_STATE}"


kubectl logs \
    -n "${NS}" \
    "${APP_NAME}-driver" \
    > "${DRIVER_LOG}" \
    2>&1 \
    || true


if [[ "${FINAL_STATE}" != "COMPLETED" ]]
then
    echo
    tail -250 "${DRIVER_LOG}" || true

    echo
    echo "ERROR:"
    echo "Encounter SparkApplication failed."

    exit 1
fi


echo "PASS"
echo


# ============================================================
# 7. Validate driver output + persist state
# ============================================================

echo "[7/7] Validate Encounter adapter..."


REQUIRED_MARKERS=(
    "SOURCE_ROWS=${EXPECTED_ROWS}"
    "SOURCE_UNIQUE_ENCOUNTERS=${EXPECTED_ROWS}"
    "CANONICAL_ROWS=${EXPECTED_ROWS}"
    "CANONICAL_UNIQUE_ENCOUNTERS=${EXPECTED_ROWS}"
    "CANONICAL_INVALID_REQUIRED=0"
    "CANONICAL_INVALID_CLASSES=0"
    "CANONICAL_INVALID_TIME_ORDER=0"
    "CANONICAL_ENCOUNTER_CONTRACT=PASS"
    "CANONICAL_ENCOUNTER_DQ=PASS"
    "PROCESSING_WRITE=PASS"
    "PROCESSING_READBACK_ROWS=${EXPECTED_ROWS}"
    "PROCESSING_READBACK_UNIQUE_ENCOUNTERS=${EXPECTED_ROWS}"
    "PROCESSING_READBACK=PASS"
    "RAW_PUBLISH=NO"
    "POSTGRESQL_WRITE=NO"
    "TASK003_ENCOUNTER_ADAPTER=PASS"
)


for marker in "${REQUIRED_MARKERS[@]}"
do
    if ! grep -Fxq \
        "${marker}" \
        "${DRIVER_LOG}"
    then
        echo "ERROR:"
        echo "Missing driver marker:"
        echo "  ${marker}"

        echo
        tail -250 "${DRIVER_LOG}" || true

        exit 1
    fi
done


python3 - \
    "${STATE_FILE}" \
    "${RUN_ID}" \
    "${APP_NAME}" \
    "${CONFIGMAP_NAME}" \
    "${MANIFEST_URI}" \
    "${MANIFEST_SHA256}" \
    "${SOURCE}" \
    "${SOURCE_VERSION}" \
    "${BATCH_ID}" \
    "${INGEST_DATE}" \
    "${SOURCE_FILE}" \
    "${SOURCE_FILE_SHA256}" \
    "${SOURCE_FILE_SIZE_BYTES}" \
    "${EXPECTED_ROWS}" \
    "${PROCESSING_DATA_URI}" <<'PY'

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


(
    output,
    run_id,
    app_name,
    configmap_name,
    manifest_uri,
    manifest_sha256,
    source,
    source_version,
    batch_id,
    ingest_date,
    source_file,
    source_file_sha256,
    source_file_size_bytes,
    rows,
    processing_data_uri,
) = sys.argv[1:]


state = {
    "task": "TASK-003",
    "step": "STEP-03",
    "status": "PASS",

    "entity": "encounter",
    "canonical_version": "v1",

    "run_id": run_id,

    "spark_application":
        app_name,

    "configmap":
        configmap_name,

    "intake_manifest_uri":
        manifest_uri,

    "intake_manifest_sha256":
        manifest_sha256,

    "source":
        source,

    "source_version":
        source_version,

    "batch_id":
        batch_id,

    "ingest_date":
        ingest_date,

    "source_file":
        source_file,

    "source_file_sha256":
        source_file_sha256,

    "source_file_size_bytes":
        int(source_file_size_bytes),

    "canonical_rows":
        int(rows),

    "canonical_unique_encounters":
        int(rows),

    "processing_data_uri":
        processing_data_uri,

    "processing_readback":
        "PASS",

    "raw_published":
        False,

    "postgresql_write":
        False,

    "phase3c_touched":
        False,

    "completed_at":
        (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        ),
}


Path(output).write_text(
    json.dumps(
        state,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
PY


python3 -m json.tool \
    "${STATE_FILE}" \
    >/dev/null


echo "PASS"
echo

echo "============================================================"
echo "TASK-003 STEP 03 RESULT"
echo "============================================================"
echo
echo "STEP03=PASS"
echo "SPARK_APPLICATION=COMPLETED"
echo "ENTITY=encounter"
echo "CANONICAL_VERSION=v1"
echo "CANONICAL_ROWS=${EXPECTED_ROWS}"
echo "CANONICAL_UNIQUE_ENCOUNTERS=${EXPECTED_ROWS}"
echo "CANONICAL_ENCOUNTER_DQ=PASS"
echo "PROCESSING_READBACK=PASS"
echo "RAW_PUBLISHED=NO"
echo "POSTGRESQL_WRITE=NO"
echo "PHASE3C_TOUCHED=NO"
echo
echo "RUN_ID=${RUN_ID}"
echo "PROCESSING_DATA_URI=${PROCESSING_DATA_URI}"
echo "STATE_FILE=${STATE_FILE}"
echo "============================================================"
