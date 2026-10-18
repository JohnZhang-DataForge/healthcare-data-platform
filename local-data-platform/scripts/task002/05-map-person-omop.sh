#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/data/spark/healthcare-data-platform}"

STEP04_ROOT="${PROJECT_ROOT}/runtime/reports/task002/step04"
STEP05_ROOT="${PROJECT_ROOT}/runtime/reports/task002/step05"

APP_SOURCE="${PROJECT_ROOT}/spark/apps/person/map_canonical_patient_to_omop.py"
COMMON_MANIFEST="${PROJECT_ROOT}/spark/common/batch_manifest.py"
COMMON_OMOP="${PROJECT_ROOT}/spark/common/omop.py"
CONTRACT="${PROJECT_ROOT}/spark/contracts/omop/person-v5.4.json"
TEMPLATE="${PROJECT_ROOT}/spark/manifests/task002/person-omop-map.yaml.tpl"

CONFIGMAP_NAME="task002-person-omop-app"

mkdir -p "${STEP05_ROOT}"


echo "============================================================"
echo "Healthcare Data Platform V2.1"
echo "TASK-002 / STEP 05"
echo "Canonical Patient -> OMOP Person"
echo "============================================================"
echo


# ============================================================
# 1. Permanent source validation
# ============================================================

for file in \
    "${APP_SOURCE}" \
    "${COMMON_MANIFEST}" \
    "${COMMON_OMOP}" \
    "${CONTRACT}" \
    "${TEMPLATE}"
do
    if [[ ! -f "${file}" ]]; then
        echo "ERROR: missing ${file}"
        exit 1
    fi
done


# ============================================================
# 2. Resolve latest approved STEP 04 run
# ============================================================

readarray -t VALUES < <(
python3 - "${STEP04_ROOT}" <<'PY'
import json
import re
import sys
from pathlib import Path


root = Path(sys.argv[1])
candidates = []

for path in root.glob("*/run-state.json"):
    try:
        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        continue

    if (
        data.get("task") == "TASK-002"
        and data.get("step") == "STEP-04"
        and data.get("status") == "PASS"
        and data.get("entity") == "patient"
        and data.get("canonical_version") == "v1"
        and data.get("dq_status") == "PASS"
        and data.get("raw_status") == "APPROVED"
        and data.get("postgresql_touched") is False
    ):
        candidates.append(
            (
                path.stat().st_mtime,
                path,
                data,
            )
        )

if not candidates:
    raise SystemExit(
        "No approved TASK-002 STEP-04 run found."
    )

_, state_path, data = max(
    candidates,
    key=lambda item: item[0],
)

raw_data_uri = data["raw_data_uri"]
raw_manifest_uri = data["raw_manifest_uri"]

pattern = (
    r"^s3://health-raw/"
    r"canonical_version=v1/"
    r"entity=patient/"
    r"source=([^/]+)/"
    r"source_version=([^/]+)/"
    r"ingest_date=([^/]+)/"
    r"batch_id=([^/]+)/"
    r"run_id=([^/]+)/data/$"
)

match = re.match(
    pattern,
    raw_data_uri,
)

if not match:
    raise SystemExit(
        "Unable to parse approved Raw URI."
    )

source = match.group(1)
source_version = match.group(2)
ingest_date = match.group(3)
batch_from_uri = match.group(4)
raw_run_id = match.group(5)

if batch_from_uri != data["batch_id"]:
    raise SystemExit(
        "STEP-04 batch mismatch."
    )

def s3a(uri):
    if uri.startswith("s3a://"):
        return uri
    if uri.startswith("s3://"):
        return "s3a://" + uri[5:]
    raise SystemExit(
        f"Unexpected S3 URI: {uri}"
    )

print(data["batch_id"])
print(data["processing_run_id"])
print(raw_run_id)
print(source)
print(source_version)
print(ingest_date)
print(s3a(raw_data_uri))
print(s3a(raw_manifest_uri))
print(data["raw_rows"])
print(state_path)
PY
)


BATCH_ID="${VALUES[0]}"
PROCESSING_RUN_ID="${VALUES[1]}"
RAW_PUBLISH_RUN_ID="${VALUES[2]}"
SOURCE="${VALUES[3]}"
SOURCE_VERSION="${VALUES[4]}"
INGEST_DATE="${VALUES[5]}"
RAW_DATA_URI="${VALUES[6]}"
RAW_MANIFEST_URI="${VALUES[7]}"
EXPECTED_ROWS="${VALUES[8]}"
STEP04_STATE_FILE="${VALUES[9]}"


# ============================================================
# 3. New immutable Processed run
# ============================================================

UTC_STAMP="$(
    date -u +%Y%m%dT%H%M%SZ
)"

OMOP_RUN_ID="person-omop-${UTC_STAMP}-$$"

APP_NAME="task002-person-omop-${UTC_STAMP,,}-$$"

APP_NAME="$(
    printf '%s' "${APP_NAME}" \
    | tr -cd 'a-z0-9-'
)"


OUTPUT_DATA_URI="s3a://health-processed/omop_version=v5.4/dataset=person/source=${SOURCE}/source_version=${SOURCE_VERSION}/ingest_date=${INGEST_DATE}/batch_id=${BATCH_ID}/run_id=${OMOP_RUN_ID}/data/"


RUN_DIR="${STEP05_ROOT}/${OMOP_RUN_ID}"

mkdir -p "${RUN_DIR}"

RENDERED="${RUN_DIR}/sparkapplication.yaml"
DRIVER_LOG="${RUN_DIR}/driver.log"
STATE_FILE="${RUN_DIR}/run-state.json"


echo "Batch ID:"
echo "  ${BATCH_ID}"

echo
echo "Raw Publish Run:"
echo "  ${RAW_PUBLISH_RUN_ID}"

echo
echo "Approved Raw:"
echo "  ${RAW_DATA_URI}"

echo
echo "OMOP Processed Run:"
echo "  ${OMOP_RUN_ID}"

echo
echo "Processed Output:"
echo "  ${OUTPUT_DATA_URI}"

echo


# ============================================================
# 4. Runtime prerequisites
# ============================================================

echo "[1/6] Runtime prerequisites..."

kubectl get secret \
    dw-spark-s3-secret \
    -n dw-spark \
    >/dev/null

kubectl get secret \
    dw-spark-omop-secret \
    -n dw-spark \
    >/dev/null

kubectl get serviceaccount \
    spark-job \
    -n dw-spark \
    >/dev/null

echo "PASS"
echo


# ============================================================
# 5. Application ConfigMap
# ============================================================

echo "[2/6] OMOP Person ConfigMap..."

kubectl create configmap \
    "${CONFIGMAP_NAME}" \
    -n dw-spark \
    --from-file=map_canonical_patient_to_omop.py="${APP_SOURCE}" \
    --from-file=batch_manifest.py="${COMMON_MANIFEST}" \
    --from-file=omop.py="${COMMON_OMOP}" \
    --from-file=person-v5.4.json="${CONTRACT}" \
    --dry-run=client \
    -o yaml \
| kubectl apply \
    -f -

echo "PASS"
echo


# ============================================================
# 6. Render SparkApplication
# ============================================================

echo "[3/6] Render SparkApplication..."

python3 - \
    "${TEMPLATE}" \
    "${RENDERED}" \
    "${APP_NAME}" \
    "${CONFIGMAP_NAME}" \
    "${RAW_MANIFEST_URI}" \
    "${RAW_DATA_URI}" \
    "${OUTPUT_DATA_URI}" <<'PY'

import sys
from pathlib import Path


(
    template,
    output,
    app_name,
    configmap_name,
    raw_manifest_uri,
    raw_data_uri,
    output_data_uri,
) = sys.argv[1:]


text = Path(template).read_text(
    encoding="utf-8"
)

values = {
    "__APP_NAME__":
        app_name,

    "__CONFIGMAP_NAME__":
        configmap_name,

    "__RAW_MANIFEST_URI__":
        raw_manifest_uri,

    "__RAW_DATA_URI__":
        raw_data_uri,

    "__OUTPUT_DATA_URI__":
        output_data_uri,
}

for old, new in values.items():
    text = text.replace(
        old,
        new,
    )

for token in values:
    if token in text:
        raise SystemExit(
            f"Unresolved placeholder: {token}"
        )

Path(output).write_text(
    text,
    encoding="utf-8",
)
PY


kubectl apply \
    --dry-run=client \
    -f "${RENDERED}" \
    >/dev/null

echo "PASS"
echo


# ============================================================
# 7. Submit
# ============================================================

echo "[4/6] Submit OMOP Person SparkApplication..."

kubectl apply \
    -f "${RENDERED}"

DRIVER_POD="${APP_NAME}-driver"

echo


for _ in $(seq 1 90)
do
    if kubectl get pod \
        "${DRIVER_POD}" \
        -n dw-spark \
        >/dev/null 2>&1
    then
        break
    fi

    sleep 2
done


if ! kubectl get pod \
    "${DRIVER_POD}" \
    -n dw-spark \
    >/dev/null 2>&1
then
    echo "ERROR: driver Pod not created."

    kubectl describe sparkapplication \
        "${APP_NAME}" \
        -n dw-spark \
        || true

    exit 1
fi


kubectl get pod \
    "${DRIVER_POD}" \
    -n dw-spark \
    -o wide

echo


# ============================================================
# 8. Wait for completion
# ============================================================

echo "[5/6] Wait for OMOP mapping..."

FINAL_STATE=""

for _ in $(seq 1 180)
do
    FINAL_STATE="$(
        kubectl get sparkapplication \
            "${APP_NAME}" \
            -n dw-spark \
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


echo "FINAL_STATE=${FINAL_STATE:-EMPTY}"
echo


# ============================================================
# 9. Driver log / acceptance
# ============================================================

echo "[6/6] Driver log..."

kubectl logs \
    "${DRIVER_POD}" \
    -n dw-spark \
    > "${DRIVER_LOG}" \
    2>&1 \
    || true

cat "${DRIVER_LOG}"

echo


if [[ "${FINAL_STATE}" != "COMPLETED" ]]; then
    echo "ERROR:"
    echo "OMOP Person SparkApplication failed."
    exit 1
fi


for marker in \
    'RAW_STATUS=APPROVED' \
    'RAW_DQ_STATUS=PASS' \
    'STABLE_PERSON_ID_MAP=PASS' \
    'DEMOGRAPHIC_CONCEPT_VALIDATION=PASS' \
    'OMOP_PERSON_DQ=PASS' \
    'PROCESSED_WRITE=PASS' \
    'PROCESSED_READBACK=PASS' \
    'OMOP_PERSON_MAPPING=PASS' \
    'CDM_PERSON_WRITE=NO' \
    'POSTGRESQL_WRITE=NO'
do
    if ! grep -q \
        "^${marker}$" \
        "${DRIVER_LOG}"
    then
        echo "ERROR:"
        echo "Missing driver marker: ${marker}"
        exit 1
    fi
done


PROCESSED_ROWS="$(
    grep '^PROCESSED_READBACK_ROWS=' \
        "${DRIVER_LOG}" \
    | tail -1 \
    | cut -d= -f2
)"


if [[ "${PROCESSED_ROWS}" != "${EXPECTED_ROWS}" ]]; then
    echo "ERROR:"
    echo "Processed row mismatch."
    echo "Expected=${EXPECTED_ROWS}"
    echo "Actual=${PROCESSED_ROWS}"
    exit 1
fi


# ============================================================
# 10. Persist Step 05 local state
# ============================================================

python3 - \
    "${STATE_FILE}" \
    "${BATCH_ID}" \
    "${PROCESSING_RUN_ID}" \
    "${RAW_PUBLISH_RUN_ID}" \
    "${OMOP_RUN_ID}" \
    "${APP_NAME}" \
    "${OUTPUT_DATA_URI}" \
    "${PROCESSED_ROWS}" <<'PY'

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


(
    output,
    batch_id,
    processing_run_id,
    raw_publish_run_id,
    omop_run_id,
    spark_application,
    output_uri,
    rows,
) = sys.argv[1:]


state = {
    "task":
        "TASK-002",

    "step":
        "STEP-05",

    "status":
        "PASS",

    "entity":
        "person",

    "omop_version":
        "v5.4",

    "batch_id":
        batch_id,

    "processing_run_id":
        processing_run_id,

    "raw_publish_run_id":
        raw_publish_run_id,

    "omop_run_id":
        omop_run_id,

    "spark_application":
        spark_application,

    "processed_data_uri":
        output_uri,

    "processed_rows":
        int(rows),

    "stable_person_id_map":
        "PASS",

    "demographic_concepts":
        "PASS",

    "postgresql_read":
        True,

    "postgresql_write":
        False,

    "cdm_person_write":
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


echo
echo "============================================================"
echo "TASK-002 STEP 05 RESULT"
echo "============================================================"
echo
echo "STEP05=PASS"
echo "SPARK_APPLICATION=COMPLETED"
echo "ENTITY=person"
echo "OMOP_VERSION=v5.4"
echo "PROCESSED_ROWS=${PROCESSED_ROWS}"
echo "STABLE_PERSON_ID_MAP=PASS"
echo "DEMOGRAPHIC_CONCEPT_VALIDATION=PASS"
echo "OMOP_PERSON_DQ=PASS"
echo "PROCESSED_READBACK=PASS"
echo "POSTGRESQL_READ=YES"
echo "POSTGRESQL_WRITE=NO"
echo "CDM_PERSON_WRITE=NO"
echo "PHASE3C_TOUCHED=NO"
echo
echo "RAW_PUBLISH_RUN_ID=${RAW_PUBLISH_RUN_ID}"
echo "OMOP_RUN_ID=${OMOP_RUN_ID}"
echo "PROCESSED_DATA_URI=${OUTPUT_DATA_URI}"
echo "STATE_FILE=${STATE_FILE}"
echo "============================================================"
