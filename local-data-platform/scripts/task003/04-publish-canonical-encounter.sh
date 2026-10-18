#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="/data/spark/healthcare-data-platform"
# TASK003_RESUME_ENTRY
if [[ "$#" -gt 0 ]]; then
    if [[ "$#" -eq 2 && "$1" == "--resume-run" ]]; then
        exec "${ROOT}/scripts/task003/04-resume-canonical-encounter-publish.sh" "$2"
    fi
    echo "Usage: $0 [--resume-run encounter-raw-YYYYMMDDTHHMMSSZ-PID]"
    exit 2
fi

STEP03_ROOT="${ROOT}/runtime/reports/task003/step03"
STEP04_ROOT="${ROOT}/runtime/reports/task003/step04"

RESOLVER="${ROOT}/apps/resolve_verified_intake_file.py"

APP_SOURCE="${ROOT}/spark/apps/publish_canonical_entity.py"
COMMON_MANIFEST="${ROOT}/spark/common/batch_manifest.py"
COMMON_GATE="${ROOT}/spark/common/canonical_gate.py"

CONTRACT="${ROOT}/spark/contracts/canonical/encounter-v1.json"
TEMPLATE="${ROOT}/spark/manifests/common/canonical-raw-publish.yaml.tpl"

NS="dw-spark"

S3_ENDPOINT="http://dw-seaweedfs-s3.dw-seaweedfs.svc.cluster.local:8333"

mkdir -p "${STEP04_ROOT}"

UTILITY_POD=""

cleanup() {
    if [[ -n "${UTILITY_POD}" ]]; then
        kubectl delete pod \
          "${UTILITY_POD}" \
          -n "${NS}" \
          --ignore-not-found \
          --wait=false \
          >/dev/null 2>&1 \
          || true
    fi
}

echo "#### TASK003 STEP04 RUN OUTPUT BEGIN ####"
step04_finish() {
    rc=$?
    trap - EXIT
    cleanup
    echo "RUN_EXIT_CODE=${rc}"
    echo "#### TASK003 STEP04 RUN OUTPUT END ####"
    exit "${rc}"
}
trap step04_finish EXIT


echo "============================================================"
echo "TASK-003 / STEP 04"
echo "Canonical Encounter Gate -> health-raw"
echo "============================================================"
echo


# ============================================================
# 1. Runtime prerequisites
# ============================================================

echo "[1/9] Runtime prerequisites..."

for file in \
  "${RESOLVER}" \
  "${APP_SOURCE}" \
  "${COMMON_MANIFEST}" \
  "${COMMON_GATE}" \
  "${CONTRACT}" \
  "${TEMPLATE}"
do
    [[ -s "${file}" ]] || {
        echo "ERROR: missing required file:"
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
# 2. Resolve latest verified STEP03 Encounter run
# ============================================================

echo "[2/9] Resolve latest verified STEP03..."

readarray -t STEP03_VALUES < <(
python3 - "${STEP03_ROOT}" <<'PY'
import json
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

    if not (
        data.get("task") == "TASK-003"
        and data.get("step") == "STEP-03"
        and data.get("status") == "PASS"
        and data.get("entity") == "encounter"
        and data.get("canonical_version") == "v1"
        and data.get("raw_published") is False
        and data.get("postgresql_write") is False
    ):
        continue

    candidates.append(
        (
            path.stat().st_mtime,
            path,
            data,
        )
    )

if not candidates:
    raise SystemExit(
        "No verified TASK-003 STEP03 "
        "Encounter run-state found."
    )

candidates.sort(
    key=lambda x: x[0],
    reverse=True,
)

_, path, data = candidates[0]

required = [
    "batch_id",
    "run_id",
    "processing_data_uri",
    "canonical_rows",
    "source",
    "source_version",
    "ingest_date",
    "source_file",
    "source_file_sha256",
    "source_file_size_bytes",
    "intake_manifest_uri",
    "intake_manifest_sha256",
]

for name in required:
    if name not in data:
        raise SystemExit(
            f"STEP03 state missing {name}"
        )

values = [
    data["batch_id"],
    data["run_id"],
    data["processing_data_uri"],
    data["canonical_rows"],
    data["source"],
    data["source_version"],
    data["ingest_date"],
    data["source_file"],
    data["source_file_sha256"],
    data["source_file_size_bytes"],
    data["intake_manifest_uri"],
    data["intake_manifest_sha256"],
    str(path),
]

for value in values:
    print(value)
PY
)

BATCH_ID="${STEP03_VALUES[0]}"
PROCESSING_RUN_ID="${STEP03_VALUES[1]}"
PROCESSING_DATA_URI="${STEP03_VALUES[2]}"
STEP03_ROWS="${STEP03_VALUES[3]}"

STEP03_SOURCE="${STEP03_VALUES[4]}"
STEP03_SOURCE_VERSION="${STEP03_VALUES[5]}"
STEP03_INGEST_DATE="${STEP03_VALUES[6]}"

STEP03_SOURCE_FILE="${STEP03_VALUES[7]}"
STEP03_SOURCE_SHA="${STEP03_VALUES[8]}"
STEP03_SOURCE_SIZE="${STEP03_VALUES[9]}"

STEP03_MANIFEST_URI="${STEP03_VALUES[10]}"
STEP03_MANIFEST_SHA="${STEP03_VALUES[11]}"

STEP03_STATE_FILE="${STEP03_VALUES[12]}"

echo "BATCH_ID=${BATCH_ID}"
echo "PROCESSING_RUN_ID=${PROCESSING_RUN_ID}"
echo "PROCESSING_DATA_URI=${PROCESSING_DATA_URI}"
echo "STEP03_ROWS=${STEP03_ROWS}"
echo "STEP03_STATE_FILE=${STEP03_STATE_FILE}"

echo "PASS"
echo


# ============================================================
# 3. Re-resolve authoritative TASK001 lineage
# ============================================================

echo "[3/9] Revalidate TASK-001 Encounter lineage..."

readarray -t SOURCE_VALUES < <(
    "${RESOLVER}" \
      encounters \
      --format json \
    | python3 -c '
import json
import sys

d = json.load(sys.stdin)

for value in [
    d["manifest_status"],
    d["manifest_uri"],
    d["manifest_sha256"],
    d["source"],
    d["source_version"],
    d["batch_id"],
    d["ingest_date"],
    d["path"],
    d["row_count"],
    d["size_bytes"],
    d["sha256"],
]:
    print(value)
'
)

MANIFEST_STATUS="${SOURCE_VALUES[0]}"
INPUT_MANIFEST_S3="${SOURCE_VALUES[1]}"
INPUT_MANIFEST_SHA256="${SOURCE_VALUES[2]}"

SOURCE="${SOURCE_VALUES[3]}"
SOURCE_VERSION="${SOURCE_VALUES[4]}"
SOURCE_BATCH_ID="${SOURCE_VALUES[5]}"
INGEST_DATE="${SOURCE_VALUES[6]}"

SOURCE_FILE="${SOURCE_VALUES[7]}"
EXPECTED_ROWS="${SOURCE_VALUES[8]}"
SOURCE_FILE_SIZE_BYTES="${SOURCE_VALUES[9]}"
SOURCE_FILE_SHA256="${SOURCE_VALUES[10]}"

INPUT_MANIFEST_S3A="$(
    printf '%s' "${INPUT_MANIFEST_S3}" \
    | sed 's#^s3://#s3a://#'
)"

[[ "${MANIFEST_STATUS}" == "INTAKE_VERIFIED" ]] || {
    echo "ERROR: intake manifest not verified."
    exit 1
}

[[ "${SOURCE_BATCH_ID}" == "${BATCH_ID}" ]] || {
    echo "ERROR: STEP03/TASK001 batch mismatch."
    exit 1
}

[[ "${SOURCE}" == "${STEP03_SOURCE}" ]] || {
    echo "ERROR: source mismatch."
    exit 1
}

[[ "${SOURCE_VERSION}" == "${STEP03_SOURCE_VERSION}" ]] || {
    echo "ERROR: source_version mismatch."
    exit 1
}

[[ "${INGEST_DATE}" == "${STEP03_INGEST_DATE}" ]] || {
    echo "ERROR: ingest_date mismatch."
    exit 1
}

[[ "${SOURCE_FILE}" == "${STEP03_SOURCE_FILE}" ]] || {
    echo "ERROR: source_file mismatch."
    exit 1
}

[[ "${SOURCE_FILE_SHA256}" == "${STEP03_SOURCE_SHA}" ]] || {
    echo "ERROR: source SHA mismatch."
    exit 1
}

[[ "${SOURCE_FILE_SIZE_BYTES}" == "${STEP03_SOURCE_SIZE}" ]] || {
    echo "ERROR: source size mismatch."
    exit 1
}

[[ "${EXPECTED_ROWS}" == "${STEP03_ROWS}" ]] || {
    echo "ERROR: row count mismatch."
    exit 1
}

[[ "${INPUT_MANIFEST_S3}" == "${STEP03_MANIFEST_URI}" ]] || {
    echo "ERROR: manifest URI mismatch."
    exit 1
}

[[ "${INPUT_MANIFEST_SHA256}" == "${STEP03_MANIFEST_SHA}" ]] || {
    echo "ERROR: manifest SHA mismatch."
    exit 1
}

echo "MANIFEST_STATUS=${MANIFEST_STATUS}"
echo "EXPECTED_ROWS=${EXPECTED_ROWS}"
echo "SOURCE_FILE_SHA256=${SOURCE_FILE_SHA256}"
echo "LINEAGE_REVALIDATION=PASS"
echo


# ============================================================
# 4. Allocate isolated Raw publish run
# ============================================================

echo "[4/9] Allocate immutable Raw publish run..."

UTC_STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

RAW_RUN_ID="encounter-raw-${UTC_STAMP}-$$"

APP_NAME="task003-encounter-raw-${UTC_STAMP,,}-$$"

CONFIGMAP_NAME="task003-encounter-raw-app-${UTC_STAMP,,}-$$"

RAW_BASE_KEY="canonical_version=v1/entity=encounter/source=${SOURCE}/source_version=${SOURCE_VERSION}/ingest_date=${INGEST_DATE}/batch_id=${BATCH_ID}/run_id=${RAW_RUN_ID}"

RAW_BASE_S3="s3://health-raw/${RAW_BASE_KEY}"

RAW_DATA_S3="${RAW_BASE_S3}/data/"
RAW_DATA_S3A="s3a://health-raw/${RAW_BASE_KEY}/data/"

DQ_URI="${RAW_BASE_S3}/dq/result.json"
RAW_MANIFEST_URI="${RAW_BASE_S3}/manifest.json"

RUN_DIR="${STEP04_ROOT}/${RAW_RUN_ID}"

RENDERED="${RUN_DIR}/sparkapplication.yaml"
DRIVER_LOG="${RUN_DIR}/driver.log"

DQ_FILE="${RUN_DIR}/dq-result.json"
MANIFEST_FILE="${RUN_DIR}/manifest.json"

REMOTE_DQ_FILE="${RUN_DIR}/dq-result.remote.json"
REMOTE_MANIFEST_FILE="${RUN_DIR}/manifest.remote.json"

STATE_FILE="${RUN_DIR}/run-state.json"

mkdir -p "${RUN_DIR}"

echo "RAW_PUBLISH_RUN_ID=${RAW_RUN_ID}"
echo "RAW_DATA_URI=${RAW_DATA_S3}"
echo "DQ_URI=${DQ_URI}"
echo "RAW_MANIFEST_URI=${RAW_MANIFEST_URI}"

echo "PASS"
echo


# ============================================================
# 5. Start S3 utility Pod + Raw prefix guard
# ============================================================

echo "[5/9] Raw prefix guard..."

UTILITY_POD="task003-raw-publisher-${UTC_STAMP,,}-$$"

cat <<YAML \
| kubectl apply -f - >/dev/null
apiVersion: v1
kind: Pod
metadata:
  name: ${UTILITY_POD}
  namespace: ${NS}
  labels:
    healthcare-task: task003
    healthcare-purpose: raw-publisher
spec:
  restartPolicy: Never

  containers:
    - name: aws
      image: amazon/aws-cli:2.15.57
      imagePullPolicy: IfNotPresent

      command:
        - /bin/sh
        - -c
        - sleep 3600

      envFrom:
        - secretRef:
            name: dw-spark-s3-secret
YAML


kubectl wait \
  --for=condition=Ready \
  "pod/${UTILITY_POD}" \
  -n "${NS}" \
  --timeout=180s \
  >/dev/null


EXISTING_KEYS="$(
    kubectl exec \
      -n "${NS}" \
      "${UTILITY_POD}" \
      -- \
      aws \
        --endpoint-url "${S3_ENDPOINT}" \
        s3api list-objects-v2 \
        --bucket health-raw \
        --prefix "${RAW_BASE_KEY}/" \
        --query 'Contents[].Key' \
        --output text \
    | tr -d '\r'
)"


if [[ -n "${EXISTING_KEYS}" ]] \
   && [[ "${EXISTING_KEYS}" != "None" ]]
then
    echo "ERROR:"
    echo "Raw run prefix already contains objects:"
    echo "${EXISTING_KEYS}"
    exit 1
fi


echo "RAW_PREFIX_EMPTY=PASS"
echo


# ============================================================
# 6. ConfigMap + render generic SparkApplication
# ============================================================

echo "[6/9] Build Canonical Gate SparkApplication..."


kubectl create configmap \
    "${CONFIGMAP_NAME}" \
    -n "${NS}" \
    --from-file=publish_canonical_entity.py="${APP_SOURCE}" \
    --from-file=batch_manifest.py="${COMMON_MANIFEST}" \
    --from-file=canonical_gate.py="${COMMON_GATE}" \
    --from-file=encounter-v1.json="${CONTRACT}" \
    --dry-run=client \
    -o yaml \
| kubectl apply -f - \
    >/dev/null


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
    source,
    destination,
    app_name,
    configmap_name,
    manifest_uri,
    batch_id,
    processing_run_id,
    processing_uri,
    raw_uri,
) = sys.argv[1:]


text = Path(source).read_text(
    encoding="utf-8"
)


replacements = {
    "__APP_NAME__":
        app_name,

    "__TASK_LABEL__":
        "task003",

    "__CONFIGMAP_NAME__":
        configmap_name,

    "__INPUT_MANIFEST_URI__":
        manifest_uri,

    "__BATCH_ID__":
        batch_id,

    "__PROCESSING_RUN_ID__":
        processing_run_id,

    "__PROCESSING_DATA_URI__":
        processing_uri,

    "__RAW_DATA_URI__":
        raw_uri,

    "__CONTRACT_FILE__":
        "encounter-v1.json",

    "__ENTITY__":
        "encounter",

    "__DATASET__":
        "encounters",

    "__SOURCE_FILE_NAME__":
        "encounters.csv",

    "__EXPECTED_ADAPTER_NAME__":
        "synthea_encounter_adapter",

    "__ADAPTER_VERSION__":
        "v1",

    "__CANONICAL_VERSION__":
        "v1",
}


for old, new in replacements.items():
    text = text.replace(
        old,
        new,
    )


unresolved = [
    line
    for line in text.splitlines()
    if "__" in line
]


if unresolved:
    raise SystemExit(
        "Unresolved template placeholders:\n"
        + "\n".join(unresolved)
    )


Path(destination).write_text(
    text,
    encoding="utf-8",
)
PY


kubectl apply \
  --dry-run=client \
  -f "${RENDERED}" \
  >/dev/null


echo "CONFIGMAP=${CONFIGMAP_NAME}"
echo "SPARKAPPLICATION_RENDER=PASS"
echo


# ============================================================
# 7. Submit generic Canonical Gate SparkApplication
# ============================================================

echo "[7/9] Submit Canonical Gate SparkApplication..."


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
    tail -300 "${DRIVER_LOG}" || true

    echo
    echo "ERROR:"
    echo "Canonical Gate SparkApplication failed."

    exit 1
fi


REQUIRED_MARKERS=(
    "INPUT_MANIFEST_STATUS=INTAKE_VERIFIED"

    "EXPECTED_ROWS=${EXPECTED_ROWS}"

    "SOURCE_FILE_SHA256=${SOURCE_FILE_SHA256}"

    "CANONICAL_SCHEMA=PASS"

    "CANONICAL_REQUIRED_FIELDS=PASS"

    "CANONICAL_METADATA=PASS"

    "CANONICAL_GATE_ROWS=${EXPECTED_ROWS}"

    "CANONICAL_GATE_UNIQUE_KEYS=${EXPECTED_ROWS}"

    "CANONICAL_GATE=PASS"

    "RAW_WRITE=PASS"

    "RAW_READBACK=PASS"

    "RAW_ROWS=${EXPECTED_ROWS}"

    "RAW_UNIQUE_KEYS=${EXPECTED_ROWS}"

    "RAW_DATA_PUBLISHED=PASS"

    "RAW_MANIFEST_PUBLISHED=NO"

    "POSTGRESQL_WRITE=NO"

    "GENERIC_CANONICAL_PUBLISHER=PASS"
)


for marker in "${REQUIRED_MARKERS[@]}"
do
    if ! grep -Fxq \
      "${marker}" \
      "${DRIVER_LOG}"
    then
        echo
        echo "ERROR:"
        echo "Missing Spark marker:"
        echo "  ${marker}"
        echo
        tail -300 "${DRIVER_LOG}" || true
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


if [[ "${RAW_ROWS}" != "${EXPECTED_ROWS}" ]]
then
    echo "ERROR:"
    echo "Raw row count mismatch."
    exit 1
fi


if [[ "${RAW_UNIQUE_KEYS}" != "${EXPECTED_ROWS}" ]]
then
    echo "ERROR:"
    echo "Raw unique key count mismatch."
    exit 1
fi


echo "SPARK_CANONICAL_GATE=PASS"
echo "RAW_ROWS=${RAW_ROWS}"
echo "RAW_UNIQUE_KEYS=${RAW_UNIQUE_KEYS}"
echo

# TASK003_STEP04B1C_BEGIN
# ============================================================
# 8. Build + publish DQ, verify S3 bytes before approval
# ============================================================
echo "[8/9] Build + publish DQ..."
EVIDENCE_BUILDER="${ROOT}/apps/task003/build_encounter_raw_evidence.py"
[[ -s "${EVIDENCE_BUILDER}" ]] || { echo "ERROR: missing evidence builder"; exit 1; }

export BATCH_ID PROCESSING_RUN_ID PROCESSING_DATA_URI STEP03_STATE_FILE
export SOURCE SOURCE_VERSION INGEST_DATE SOURCE_FILE SOURCE_FILE_SHA256
export SOURCE_FILE_SIZE_BYTES INPUT_MANIFEST_S3 INPUT_MANIFEST_SHA256
export EXPECTED_ROWS RAW_ROWS RAW_UNIQUE_KEYS RAW_RUN_ID RAW_BASE_S3
export RAW_DATA_S3 DQ_URI RAW_MANIFEST_URI DRIVER_LOG DQ_FILE
export REMOTE_DQ_FILE MANIFEST_FILE REMOTE_MANIFEST_FILE STATE_FILE
export APP_NAME CONFIGMAP_NAME CONTRACT

# Single writer, isolated run prefix. Never reuse or overwrite a metadata key.
publish_json_once() {
    local local_file="$1" uri="$2" remote_file="$3" label="$4"
    local key="${uri#s3://health-raw/}" found local_sha remote_sha
    [[ "${uri}" == "${RAW_BASE_S3}/"* ]] || {
        echo "ERROR: unexpected publication target: ${uri}"; return 1;
    }
    if ! found="$(kubectl exec -n "${NS}" "${UTILITY_POD}" -- \
        aws --endpoint-url "${S3_ENDPOINT}" s3api list-objects-v2 \
        --bucket health-raw --prefix "${key}" --output json)"; then
        echo "ERROR: ${label} existence check failed"; return 1
    fi
    printf '%s' "${found}" | python3 "${EVIDENCE_BUILDER}" empty-listing
    kubectl exec -i -n "${NS}" "${UTILITY_POD}" -- \
        aws --endpoint-url "${S3_ENDPOINT}" s3 cp - "${uri}" \
        --content-type application/json --only-show-errors < "${local_file}"
    kubectl exec -n "${NS}" "${UTILITY_POD}" -- \
        aws --endpoint-url "${S3_ENDPOINT}" s3 cp "${uri}" - \
        --only-show-errors > "${remote_file}"
    local_sha="$(sha256sum "${local_file}")"
    remote_sha="$(sha256sum "${remote_file}")"
    [[ "${local_sha%% *}" == "${remote_sha%% *}" ]] || {
        echo "ERROR: ${label} S3 readback SHA256 mismatch"; return 1;
    }
    echo "${label}_PUBLISHED=PASS"
    echo "${label}_READBACK_SHA256=PASS"
}

python3 "${EVIDENCE_BUILDER}" dq
publish_json_once "${DQ_FILE}" "${DQ_URI}" "${REMOTE_DQ_FILE}" DQ
echo

# ============================================================
# 9. Publish Raw manifest LAST, then local acceptance state
# ============================================================
echo "[9/9] Publish approved Raw manifest LAST..."
# Builder refuses to approve if the remote DQ is missing or different.
python3 "${EVIDENCE_BUILDER}" manifest
publish_json_once "${MANIFEST_FILE}" "${RAW_MANIFEST_URI}" \
    "${REMOTE_MANIFEST_FILE}" RAW_MANIFEST
# Recheck both remote JSON documents before atomically writing PASS state.
python3 "${EVIDENCE_BUILDER}" state

echo "STEP04=PASS"
echo "SPARK_APPLICATION=COMPLETED"
echo "CANONICAL_GATE=PASS"
echo "RAW_ROWS=${RAW_ROWS}"
echo "RAW_UNIQUE_KEYS=${RAW_UNIQUE_KEYS}"
echo "RAW_STATUS=APPROVED"
echo "RAW_PUBLISH_RUN_ID=${RAW_RUN_ID}"
echo "RAW_DATA_URI=${RAW_DATA_S3}"
echo "RAW_MANIFEST_URI=${RAW_MANIFEST_URI}"
echo "RUN_STATE=${STATE_FILE}"
echo "POSTGRESQL_WRITE=NO"
echo "PHASE3C_TOUCHED=NO"
# TASK003_STEP04B1C_END
