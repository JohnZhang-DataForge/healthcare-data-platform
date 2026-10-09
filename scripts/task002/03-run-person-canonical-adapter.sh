#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/data/spark/healthcare-data-platform}"

TASK001_REPORT="${PROJECT_ROOT}/runtime/reports/task001/step05/task001-final-validation.json"

APP_SOURCE="${PROJECT_ROOT}/spark/apps/person/synthea_patient_adapter.py"
COMMON_SOURCE="${PROJECT_ROOT}/spark/common/batch_manifest.py"
CONTRACT="${PROJECT_ROOT}/spark/contracts/canonical/patient-v1.json"

TEMPLATE="${PROJECT_ROOT}/spark/manifests/task002/person-canonical-adapter.yaml.tpl"

REPORT_ROOT="${PROJECT_ROOT}/runtime/reports/task002/step03"

CONFIGMAP_NAME="task002-person-canonical-app"


echo "============================================================"
echo "Healthcare Data Platform V2.1"
echo "TASK-002 / STEP 03"
echo "Synthea Patient -> Canonical Processing"
echo "============================================================"
echo


# ============================================================
# 1. Permanent-source validation
# ============================================================

for file in \
  "${TASK001_REPORT}" \
  "${APP_SOURCE}" \
  "${COMMON_SOURCE}" \
  "${CONTRACT}" \
  "${TEMPLATE}"
do
    if [[ ! -f "${file}" ]]; then
        echo "ERROR: missing ${file}"
        exit 1
    fi
done


# ============================================================
# 2. Resolve TASK-001 runtime context
# ============================================================

readarray -t VALUES < <(
python3 - "${TASK001_REPORT}" <<'PY'
import json
import re
import sys
from pathlib import Path

report = json.loads(
    Path(sys.argv[1]).read_text(
        encoding="utf-8"
    )
)

if report["status"] != "PASS":
    raise SystemExit(
        "TASK-001 is not PASS."
    )

if (
    report["manifest"]["status"]
    != "INTAKE_VERIFIED"
):
    raise SystemExit(
        "TASK-001 manifest is not "
        "INTAKE_VERIFIED."
    )

landing_uri = report["landing_uri"]

match = re.search(
    r"/source=([^/]+)/"
    r"source_version=([^/]+)/"
    r"ingest_date=([^/]+)/"
    r"batch_id=([^/]+)/?$",
    landing_uri,
)

if not match:
    raise SystemExit(
        "Unable to parse landing URI."
    )

source = match.group(1)
source_version = match.group(2)
ingest_date = match.group(3)
batch_id = match.group(4)

manifest_uri = report["manifest_uri"]

if not manifest_uri.startswith(
    "s3://"
):
    raise SystemExit(
        "Unexpected manifest URI."
    )

manifest_s3a = (
    "s3a://"
    + manifest_uri[len("s3://"):]
)

print(source)
print(source_version)
print(ingest_date)
print(batch_id)
print(manifest_s3a)
PY
)


SOURCE="${VALUES[0]}"
SOURCE_VERSION="${VALUES[1]}"
INGEST_DATE="${VALUES[2]}"
BATCH_ID="${VALUES[3]}"
MANIFEST_URI="${VALUES[4]}"


UTC_STAMP="$(
    date -u +%Y%m%dT%H%M%SZ
)"

RUN_ID="patient-${UTC_STAMP}-$$"

APP_NAME="task002-person-${UTC_STAMP,,}-$$"

APP_NAME="$(
    printf '%s' "${APP_NAME}" \
    | tr -cd 'a-z0-9-'
)"


PROCESSING_DATA_URI="s3a://health-processing/source=${SOURCE}/source_version=${SOURCE_VERSION}/ingest_date=${INGEST_DATE}/batch_id=${BATCH_ID}/entity=patient/run_id=${RUN_ID}/work/normalized/data/"


RUN_DIR="${REPORT_ROOT}/${RUN_ID}"

mkdir -p "${RUN_DIR}"


RENDERED="${RUN_DIR}/sparkapplication.yaml"
DRIVER_LOG="${RUN_DIR}/driver.log"
STATE_FILE="${RUN_DIR}/run-state.json"


echo "Batch ID:"
echo "  ${BATCH_ID}"

echo
echo "Run ID:"
echo "  ${RUN_ID}"

echo
echo "Manifest:"
echo "  ${MANIFEST_URI}"

echo
echo "Processing output:"
echo "  ${PROCESSING_DATA_URI}"

echo


# ============================================================
# 3. Publish application source ConfigMap
# ============================================================

echo "[1/6] Application ConfigMap..."

kubectl create configmap \
  "${CONFIGMAP_NAME}" \
  -n dw-spark \
  --from-file=synthea_patient_adapter.py="${APP_SOURCE}" \
  --from-file=batch_manifest.py="${COMMON_SOURCE}" \
  --from-file=patient-v1.json="${CONTRACT}" \
  --dry-run=client \
  -o yaml \
| kubectl apply \
  -f -

echo "PASS"
echo


# ============================================================
# 4. Render SparkApplication
# ============================================================

echo "[2/6] Render SparkApplication..."

python3 - \
  "${TEMPLATE}" \
  "${RENDERED}" \
  "${APP_NAME}" \
  "${CONFIGMAP_NAME}" \
  "${MANIFEST_URI}" \
  "${BATCH_ID}" \
  "${RUN_ID}" \
  "${PROCESSING_DATA_URI}" <<'PY'

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

text = Path(template).read_text(
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

for key in values:
    if key in text:
        raise SystemExit(
            f"Unresolved placeholder: {key}"
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
# 5. Submit
# ============================================================

echo "[3/6] Submit SparkApplication..."

kubectl apply \
  -f "${RENDERED}"

echo


# ============================================================
# 6. Wait for driver
# ============================================================

echo "[4/6] Wait for driver..."

DRIVER_POD="${APP_NAME}-driver"

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
# 7. Wait for Spark completion
# ============================================================

echo "[5/6] Wait for SparkApplication..."

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
# 8. Driver log + acceptance
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
    echo "SparkApplication did not complete."

    kubectl get sparkapplication \
      "${APP_NAME}" \
      -n dw-spark \
      -o wide \
      || true

    exit 1
fi


grep -q \
  '^PERSON_CANONICAL_ADAPTER=PASS$' \
  "${DRIVER_LOG}"


grep -q \
  '^PROCESSING_READBACK=PASS$' \
  "${DRIVER_LOG}"


CANONICAL_ROWS="$(
    grep '^CANONICAL_ROWS=' \
      "${DRIVER_LOG}" \
    | tail -1 \
    | cut -d= -f2
)"


if [[ "${CANONICAL_ROWS}" != "113" ]]; then
    echo "ERROR:"
    echo "Expected canonical rows=113"
    echo "Actual=${CANONICAL_ROWS}"

    exit 1
fi


python3 - \
  "${STATE_FILE}" \
  "${BATCH_ID}" \
  "${RUN_ID}" \
  "${APP_NAME}" \
  "${PROCESSING_DATA_URI}" \
  "${CANONICAL_ROWS}" <<'PY'

import json
import sys
from datetime import (
    datetime,
    timezone,
)
from pathlib import Path

(
    output,
    batch_id,
    run_id,
    app_name,
    processing_uri,
    rows,
) = sys.argv[1:]

state = {
    "task": "TASK-002",
    "step": "STEP-03",
    "status": "PASS",
    "entity": "patient",
    "canonical_version": "v1",
    "batch_id": batch_id,
    "run_id": run_id,
    "spark_application": app_name,
    "processing_data_uri": processing_uri,
    "canonical_rows": int(rows),
    "raw_published": False,
    "postgresql_touched": False,
    "completed_at": (
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
echo "TASK-002 STEP 03 RESULT"
echo "============================================================"
echo
echo "STEP03=PASS"
echo "SPARK_APPLICATION=COMPLETED"
echo "ENTITY=patient"
echo "CANONICAL_VERSION=v1"
echo "CANONICAL_ROWS=${CANONICAL_ROWS}"
echo "PROCESSING_READBACK=PASS"
echo "RAW_PUBLISHED=NO"
echo "POSTGRESQL_TOUCHED=NO"
echo "PHASE3C_TOUCHED=NO"
echo
echo "RUN_ID=${RUN_ID}"
echo "PROCESSING_DATA_URI=${PROCESSING_DATA_URI}"
echo "STATE_FILE=${STATE_FILE}"
echo "============================================================"
