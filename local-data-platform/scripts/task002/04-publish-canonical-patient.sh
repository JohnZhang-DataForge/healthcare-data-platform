#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/data/spark/healthcare-data-platform}"

TASK001_REPORT="${PROJECT_ROOT}/runtime/reports/task001/step05/task001-final-validation.json"
STEP03_ROOT="${PROJECT_ROOT}/runtime/reports/task002/step03"
STEP04_ROOT="${PROJECT_ROOT}/runtime/reports/task002/step04"

APP_SOURCE="${PROJECT_ROOT}/spark/apps/person/publish_canonical_patient.py"
COMMON_MANIFEST="${PROJECT_ROOT}/spark/common/batch_manifest.py"
COMMON_GATE="${PROJECT_ROOT}/spark/common/canonical_gate.py"
CONTRACT="${PROJECT_ROOT}/spark/contracts/canonical/patient-v1.json"

TEMPLATE="${PROJECT_ROOT}/spark/manifests/task002/person-canonical-raw-publish.yaml.tpl"

CONFIGMAP_NAME="task002-person-raw-publish-app"

mkdir -p "${STEP04_ROOT}"


echo "============================================================"
echo "Healthcare Data Platform V2.1"
echo "TASK-002 / STEP 04"
echo "Canonical Patient Gate + Raw Publish"
echo "============================================================"
echo


# ============================================================
# 1. Validate permanent source
# ============================================================

for file in \
    "${TASK001_REPORT}" \
    "${APP_SOURCE}" \
    "${COMMON_MANIFEST}" \
    "${COMMON_GATE}" \
    "${CONTRACT}" \
    "${TEMPLATE}"
do
    if [[ ! -f "${file}" ]]; then
        echo "ERROR: missing ${file}"
        exit 1
    fi
done


# ============================================================
# 2. Resolve latest verified STEP 03 run
# ============================================================

readarray -t STEP03_VALUES < <(
python3 - "${STEP03_ROOT}" <<'PY'
import json
import sys
from pathlib import Path


root = Path(sys.argv[1])

candidates = []

for path in root.glob(
    "*/run-state.json"
):
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
        and data.get("step") == "STEP-03"
        and data.get("status") == "PASS"
        and data.get("entity") == "patient"
        and data.get("canonical_version") == "v1"
        and data.get("canonical_rows") == 113
        and data.get("raw_published") is False
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
        "No verified TASK-002 STEP-03 "
        "run-state.json found."
    )


_, path, data = max(
    candidates,
    key=lambda item: item[0],
)


print(data["batch_id"])
print(data["run_id"])
print(data["processing_data_uri"])
print(data["canonical_rows"])
print(path)
PY
)


BATCH_ID="${STEP03_VALUES[0]}"
PROCESSING_RUN_ID="${STEP03_VALUES[1]}"
PROCESSING_DATA_URI="${STEP03_VALUES[2]}"
EXPECTED_ROWS="${STEP03_VALUES[3]}"
STEP03_STATE_FILE="${STEP03_VALUES[4]}"


# ============================================================
# 3. Resolve authoritative TASK-001 context
# ============================================================

readarray -t TASK001_VALUES < <(
python3 - \
    "${TASK001_REPORT}" \
    "${BATCH_ID}" <<'PY'

import json
import re
import sys
from pathlib import Path


report = json.loads(
    Path(sys.argv[1]).read_text(
        encoding="utf-8"
    )
)

expected_batch = sys.argv[2]

if report.get("status") != "PASS":
    raise SystemExit(
        "TASK-001 is not PASS."
    )

if report.get("batch_id") != expected_batch:
    raise SystemExit(
        "TASK-001 / STEP-03 batch mismatch."
    )

if (
    report["manifest"]["status"]
    != "INTAKE_VERIFIED"
):
    raise SystemExit(
        "TASK-001 manifest not verified."
    )


landing = report["landing_uri"]

match = re.search(
    r"/source=([^/]+)/"
    r"source_version=([^/]+)/"
    r"ingest_date=([^/]+)/"
    r"batch_id=([^/]+)/?$",
    landing,
)

if not match:
    raise SystemExit(
        "Unable to parse TASK-001 landing URI."
    )


manifest_uri = report["manifest_uri"]

if not manifest_uri.startswith(
    "s3://"
):
    raise SystemExit(
        "Unexpected TASK-001 manifest URI."
    )


print(match.group(1))
print(match.group(2))
print(match.group(3))
print(manifest_uri)
print(
    "s3a://"
    + manifest_uri[len("s3://"):]
)
print(report["manifest_sha256"])
PY
)


SOURCE="${TASK001_VALUES[0]}"
SOURCE_VERSION="${TASK001_VALUES[1]}"
INGEST_DATE="${TASK001_VALUES[2]}"
INPUT_MANIFEST_S3="${TASK001_VALUES[3]}"
INPUT_MANIFEST_S3A="${TASK001_VALUES[4]}"
INPUT_MANIFEST_SHA256="${TASK001_VALUES[5]}"


# ============================================================
# 4. Create isolated Raw publish run
# ============================================================

UTC_STAMP="$(
    date -u +%Y%m%dT%H%M%SZ
)"

RAW_RUN_ID="patient-raw-${UTC_STAMP}-$$"

APP_NAME="task002-person-raw-${UTC_STAMP,,}-$$"

APP_NAME="$(
    printf '%s' "${APP_NAME}" \
    | tr -cd 'a-z0-9-'
)"


RAW_BASE_KEY="canonical_version=v1/entity=patient/source=${SOURCE}/source_version=${SOURCE_VERSION}/ingest_date=${INGEST_DATE}/batch_id=${BATCH_ID}/run_id=${RAW_RUN_ID}"

RAW_BASE_S3="s3://health-raw/${RAW_BASE_KEY}"

RAW_DATA_S3="${RAW_BASE_S3}/data/"
RAW_DATA_S3A="s3a://health-raw/${RAW_BASE_KEY}/data/"

DQ_URI="${RAW_BASE_S3}/dq/result.json"
RAW_MANIFEST_URI="${RAW_BASE_S3}/manifest.json"


RUN_DIR="${STEP04_ROOT}/${RAW_RUN_ID}"

mkdir -p "${RUN_DIR}"

RENDERED="${RUN_DIR}/sparkapplication.yaml"
DRIVER_LOG="${RUN_DIR}/driver.log"
DQ_FILE="${RUN_DIR}/dq-result.json"
MANIFEST_FILE="${RUN_DIR}/manifest.json"
STATE_FILE="${RUN_DIR}/run-state.json"


echo "Source:"
echo "  ${SOURCE}"

echo
echo "Batch ID:"
echo "  ${BATCH_ID}"

echo
echo "Processing Run:"
echo "  ${PROCESSING_RUN_ID}"

echo
echo "Processing Input:"
echo "  ${PROCESSING_DATA_URI}"

echo
echo "Raw Publish Run:"
echo "  ${RAW_RUN_ID}"

echo
echo "Raw Data:"
echo "  ${RAW_DATA_S3}"

echo


# ============================================================
# 5. S3 utility Pod
# ============================================================

UTILITY_POD="task002-raw-publisher-$$"

cleanup() {
    kubectl delete pod \
        "${UTILITY_POD}" \
        -n dw-spark \
        --ignore-not-found=true \
        >/dev/null 2>&1 || true
}

trap cleanup EXIT


cat <<YAML | kubectl apply -f - >/dev/null
apiVersion: v1
kind: Pod

metadata:
  name: ${UTILITY_POD}
  namespace: dw-spark

  labels:
    healthcare-task: task002
    healthcare-purpose: raw-publisher

spec:
  restartPolicy: Never

  containers:
    - name: aws
      image: amazon/aws-cli:2.31.13

      command:
        - /bin/sh
        - -c

      args:
        - |
          sleep 3600

      envFrom:
        - secretRef:
            name: dw-spark-s3-secret
YAML


echo "[1/8] Waiting for S3 utility Pod..."

for _ in $(seq 1 60)
do
    READY="$(
        kubectl get pod \
            "${UTILITY_POD}" \
            -n dw-spark \
            -o jsonpath='{.status.containerStatuses[0].ready}' \
            2>/dev/null \
        || true
    )"

    if [[ "${READY}" == "true" ]]; then
        break
    fi

    sleep 2
done


if [[ "${READY:-}" != "true" ]]; then
    echo "ERROR: S3 utility Pod not ready."

    kubectl describe pod \
        "${UTILITY_POD}" \
        -n dw-spark \
        || true

    exit 1
fi

echo "PASS"
echo


# ============================================================
# 6. health-raw bucket / prefix preflight
# ============================================================

echo "[2/8] Raw destination preflight..."


if ! kubectl exec \
    "${UTILITY_POD}" \
    -n dw-spark \
    -- \
    aws \
      --endpoint-url \
      http://dw-seaweedfs-s3.dw-seaweedfs.svc.cluster.local:8333 \
      s3api head-bucket \
      --bucket health-raw \
      >/dev/null 2>&1
then

    kubectl exec \
        "${UTILITY_POD}" \
        -n dw-spark \
        -- \
        aws \
          --endpoint-url \
          http://dw-seaweedfs-s3.dw-seaweedfs.svc.cluster.local:8333 \
          s3api create-bucket \
          --bucket health-raw \
          >/dev/null
fi


EXISTING="$(
    kubectl exec \
        "${UTILITY_POD}" \
        -n dw-spark \
        -- \
        aws \
          --endpoint-url \
          http://dw-seaweedfs-s3.dw-seaweedfs.svc.cluster.local:8333 \
          s3api list-objects-v2 \
          --bucket health-raw \
          --prefix "${RAW_BASE_KEY}/" \
          --query 'length(Contents)' \
          --output text \
        2>/dev/null \
    || true
)"


case "${EXISTING}" in
    ""|None|0)
        ;;
    *)
        echo "ERROR:"
        echo "Raw run prefix already contains objects."
        echo "COUNT=${EXISTING}"
        exit 1
        ;;
esac

echo "PASS"
echo


# ============================================================
# 7. Publish Spark source ConfigMap
# ============================================================

echo "[3/8] Raw publisher ConfigMap..."

kubectl create configmap \
    "${CONFIGMAP_NAME}" \
    -n dw-spark \
    --from-file=publish_canonical_patient.py="${APP_SOURCE}" \
    --from-file=batch_manifest.py="${COMMON_MANIFEST}" \
    --from-file=canonical_gate.py="${COMMON_GATE}" \
    --from-file=patient-v1.json="${CONTRACT}" \
    --dry-run=client \
    -o yaml \
| kubectl apply \
    -f -

echo "PASS"
echo


# ============================================================
# 8. Render SparkApplication
# ============================================================

echo "[4/8] Render SparkApplication..."

python3 - \
    "${TEMPLATE}" \
    "${RENDERED}" \
    "${APP_NAME}" \
    "${CONFIGMAP_NAME}" \
    "${INPUT_MANIFEST_S3A}" \
    "${BATCH_ID}" \
    "${PROCESSING_RUN_ID}" \
    "${PROCESSING_DATA_URI}" \
    "${RAW_DATA_S3A}" <<'PY'

import sys
from pathlib import Path


(
    template,
    output,
    app_name,
    configmap_name,
    input_manifest,
    batch_id,
    processing_run_id,
    processing_data_uri,
    raw_data_uri,
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

    "__INPUT_MANIFEST_URI__":
        input_manifest,

    "__BATCH_ID__":
        batch_id,

    "__PROCESSING_RUN_ID__":
        processing_run_id,

    "__PROCESSING_DATA_URI__":
        processing_data_uri,

    "__RAW_DATA_URI__":
        raw_data_uri,
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
# 9. Submit SparkApplication
# ============================================================

echo "[5/8] Submit Canonical Gate SparkApplication..."

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
# 10. Wait for Spark completion
# ============================================================

echo "[6/8] Wait for Canonical Gate..."

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
    echo "Canonical Gate SparkApplication failed."
    exit 1
fi


for marker in \
    'CANONICAL_GATE=PASS' \
    'RAW_WRITE=PASS' \
    'RAW_READBACK=PASS' \
    'RAW_DATA_PUBLISHED=PASS' \
    'RAW_MANIFEST_PUBLISHED=NO' \
    'POSTGRESQL_TOUCHED=NO'
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


RAW_ROWS="$(
    grep '^RAW_ROWS=' \
        "${DRIVER_LOG}" \
    | tail -1 \
    | cut -d= -f2
)"


RAW_UNIQUE_KEYS="$(
    grep '^RAW_UNIQUE_KEYS=' \
        "${DRIVER_LOG}" \
    | tail -1 \
    | cut -d= -f2
)"


if [[ "${RAW_ROWS}" != "${EXPECTED_ROWS}" ]]; then
    echo "ERROR: Raw row count mismatch."
    exit 1
fi


if [[ "${RAW_UNIQUE_KEYS}" != "${EXPECTED_ROWS}" ]]; then
    echo "ERROR: Raw unique-key mismatch."
    exit 1
fi


echo "SPARK_CANONICAL_GATE=PASS"
echo


# ============================================================
# 11. Build DQ + final manifest locally
# ============================================================

echo "[7/8] Build DQ result and Raw manifest..."

python3 - \
    "${DQ_FILE}" \
    "${MANIFEST_FILE}" \
    "${BATCH_ID}" \
    "${SOURCE}" \
    "${SOURCE_VERSION}" \
    "${INGEST_DATE}" \
    "${PROCESSING_RUN_ID}" \
    "${RAW_RUN_ID}" \
    "${INPUT_MANIFEST_S3}" \
    "${INPUT_MANIFEST_SHA256}" \
    "${PROCESSING_DATA_URI}" \
    "${RAW_DATA_S3}" \
    "${DQ_URI}" \
    "${RAW_ROWS}" <<'PY'

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


(
    dq_file,
    manifest_file,
    batch_id,
    source,
    source_version,
    ingest_date,
    processing_run_id,
    raw_run_id,
    input_manifest_uri,
    input_manifest_sha256,
    processing_data_uri,
    raw_data_uri,
    dq_uri,
    rows,
) = sys.argv[1:]


now = (
    datetime.now(timezone.utc)
    .replace(microsecond=0)
    .isoformat()
    .replace("+00:00", "Z")
)


try:
    revision = (
        subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        .strip()
    )
except Exception:
    revision = None


try:
    dirty = bool(
        subprocess.check_output(
            ["git", "status", "--porcelain"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        .strip()
    )
except Exception:
    dirty = True


dq = {
    "dq_version":
        "1.0",

    "task":
        "TASK-002",

    "entity":
        "patient",

    "gate":
        "canonical_admission",

    "status":
        "PASS",

    "batch_id":
        batch_id,

    "processing_run_id":
        processing_run_id,

    "raw_publish_run_id":
        raw_run_id,

    "checks": {
        "schema":
            "PASS",

        "required_fields":
            "PASS",

        "primary_key_uniqueness":
            "PASS",

        "lineage_metadata":
            "PASS",

        "row_reconciliation":
            "PASS",

        "raw_readback":
            "PASS",
    },

    "input_rows":
        int(rows),

    "accepted_rows":
        int(rows),

    "rejected_rows":
        0,

    "checked_at":
        now,
}


manifest = {
    "manifest_version":
        "1.0",

    "layer":
        "canonical_raw",

    "status":
        "APPROVED",

    "entity":
        "patient",

    "canonical_version":
        "v1",

    "source":
        source,

    "source_version":
        source_version,

    "ingest_date":
        ingest_date,

    "batch_id":
        batch_id,

    "processing_run_id":
        processing_run_id,

    "raw_publish_run_id":
        raw_run_id,

    "input_manifest_uri":
        input_manifest_uri,

    "input_manifest_sha256":
        input_manifest_sha256,

    "processing_data_uri":
        processing_data_uri,

    "raw_data_uri":
        raw_data_uri,

    "dq_uri":
        dq_uri,

    "output_rows":
        int(rows),

    "dq_status":
        "PASS",

    "code_revision":
        revision,

    "working_tree_clean":
        not dirty,

    "published_at":
        now,
}


Path(dq_file).write_text(
    json.dumps(
        dq,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)


Path(manifest_file).write_text(
    json.dumps(
        manifest,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
PY


python3 -m json.tool \
    "${DQ_FILE}" \
    >/dev/null

python3 -m json.tool \
    "${MANIFEST_FILE}" \
    >/dev/null

echo "PASS"
echo


# ============================================================
# 12. Publish DQ first, manifest LAST
# ============================================================

echo "[8/8] Publish DQ and final manifest..."


kubectl exec -i \
    "${UTILITY_POD}" \
    -n dw-spark \
    -- \
    aws \
      --endpoint-url \
      http://dw-seaweedfs-s3.dw-seaweedfs.svc.cluster.local:8333 \
      s3 cp \
      - \
      "${DQ_URI}" \
      >/dev/null \
    < "${DQ_FILE}"


kubectl exec \
    "${UTILITY_POD}" \
    -n dw-spark \
    -- \
    aws \
      --endpoint-url \
      http://dw-seaweedfs-s3.dw-seaweedfs.svc.cluster.local:8333 \
      s3api head-object \
      --bucket health-raw \
      --key "${RAW_BASE_KEY}/dq/result.json" \
      >/dev/null


echo "DQ_PUBLISHED=PASS"


# Commit boundary: manifest is deliberately LAST.

kubectl exec -i \
    "${UTILITY_POD}" \
    -n dw-spark \
    -- \
    aws \
      --endpoint-url \
      http://dw-seaweedfs-s3.dw-seaweedfs.svc.cluster.local:8333 \
      s3 cp \
      - \
      "${RAW_MANIFEST_URI}" \
      >/dev/null \
    < "${MANIFEST_FILE}"


kubectl exec \
    "${UTILITY_POD}" \
    -n dw-spark \
    -- \
    aws \
      --endpoint-url \
      http://dw-seaweedfs-s3.dw-seaweedfs.svc.cluster.local:8333 \
      s3api head-object \
      --bucket health-raw \
      --key "${RAW_BASE_KEY}/manifest.json" \
      >/dev/null


echo "RAW_MANIFEST_PUBLISHED=PASS"


# ============================================================
# 13. Persist local Step 04 state
# ============================================================

python3 - \
    "${STATE_FILE}" \
    "${BATCH_ID}" \
    "${PROCESSING_RUN_ID}" \
    "${RAW_RUN_ID}" \
    "${APP_NAME}" \
    "${RAW_DATA_S3}" \
    "${DQ_URI}" \
    "${RAW_MANIFEST_URI}" \
    "${RAW_ROWS}" <<'PY'

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


(
    output,
    batch_id,
    processing_run_id,
    raw_run_id,
    spark_application,
    raw_data_uri,
    dq_uri,
    manifest_uri,
    rows,
) = sys.argv[1:]


state = {
    "task":
        "TASK-002",

    "step":
        "STEP-04",

    "status":
        "PASS",

    "entity":
        "patient",

    "canonical_version":
        "v1",

    "batch_id":
        batch_id,

    "processing_run_id":
        processing_run_id,

    "raw_publish_run_id":
        raw_run_id,

    "spark_application":
        spark_application,

    "raw_data_uri":
        raw_data_uri,

    "dq_uri":
        dq_uri,

    "raw_manifest_uri":
        manifest_uri,

    "raw_rows":
        int(rows),

    "dq_status":
        "PASS",

    "raw_status":
        "APPROVED",

    "postgresql_touched":
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


cleanup
trap - EXIT


echo
echo "============================================================"
echo "TASK-002 STEP 04 RESULT"
echo "============================================================"
echo
echo "STEP04=PASS"
echo "SPARK_APPLICATION=COMPLETED"
echo "CANONICAL_GATE=PASS"
echo "RAW_ROWS=${RAW_ROWS}"
echo "RAW_UNIQUE_KEYS=${RAW_UNIQUE_KEYS}"
echo "DQ_PUBLISHED=PASS"
echo "RAW_MANIFEST_PUBLISHED=PASS"
echo "RAW_STATUS=APPROVED"
echo "POSTGRESQL_TOUCHED=NO"
echo "PHASE3C_TOUCHED=NO"
echo
echo "PROCESSING_RUN_ID=${PROCESSING_RUN_ID}"
echo "RAW_PUBLISH_RUN_ID=${RAW_RUN_ID}"
echo "RAW_DATA_URI=${RAW_DATA_S3}"
echo "DQ_URI=${DQ_URI}"
echo "RAW_MANIFEST_URI=${RAW_MANIFEST_URI}"
echo "STATE_FILE=${STATE_FILE}"
echo "============================================================"
