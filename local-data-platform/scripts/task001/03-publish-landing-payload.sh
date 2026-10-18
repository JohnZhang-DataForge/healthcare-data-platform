#!/usr/bin/env bash
set -Eeuo pipefail


PROJECT_ROOT="${PROJECT_ROOT:-/data/spark/healthcare-data-platform}"

ENV_FILE="${PROJECT_ROOT}/config/local.env"

GUARD="${PROJECT_ROOT}/apps/task001/landing_guard.py"

DRAFT="${PROJECT_ROOT}/runtime/reports/task001/step01/manifest.draft.json"

REPORT_DIR="${PROJECT_ROOT}/runtime/reports/task001/step03"

mkdir -p "${REPORT_DIR}"


if [[ ! -f "${ENV_FILE}" ]]; then

    echo "ERROR: missing:"
    echo "  ${ENV_FILE}"

    exit 1
fi


if [[ ! -s "${DRAFT}" ]]; then

    echo "ERROR:"
    echo "STEP 01 draft manifest missing:"
    echo "  ${DRAFT}"

    exit 1
fi


set -a

# shellcheck disable=SC1090
source "${ENV_FILE}"

set +a


: "${SYNTHEA_SOURCE_DIR:?missing SYNTHEA_SOURCE_DIR}"
: "${SOURCE_SYSTEM:?missing SOURCE_SYSTEM}"
: "${SOURCE_VERSION:?missing SOURCE_VERSION}"
: "${BATCH_ID:?missing BATCH_ID}"

: "${S3_NAMESPACE:?missing S3_NAMESPACE}"
: "${S3_SECRET_NAME:?missing S3_SECRET_NAME}"
: "${S3_ENDPOINT:?missing S3_ENDPOINT}"
: "${S3_BUCKET_LANDING:?missing S3_BUCKET_LANDING}"


ROOT_PREFIX="source=${SOURCE_SYSTEM}/source_version=${SOURCE_VERSION}/"

DEFAULT_INGEST_DATE="$(
    date -u +%Y-%m-%d
)"


ROOT_KEYS="${REPORT_DIR}/root-keys.txt"

BATCH_KEYS="${REPORT_DIR}/batch-keys-before.txt"

PREFIX_JSON="${REPORT_DIR}/prefix.json"

INSPECT_JSON="${REPORT_DIR}/inspect-before.json"

CHECKSUM_FILE="${REPORT_DIR}/payload.sha256"

EXISTING_MANIFEST="${REPORT_DIR}/existing-manifest.json"

STATE_FILE="${REPORT_DIR}/landing-payload-state.json"


POD="task001-landing-payload-$(date -u +%H%M%S)"

TRANSFER_CONTAINER="transfer"

AWS_CONTAINER="aws-cli"


STEP_SUCCESS=0


cleanup() {

    if [[ "${STEP_SUCCESS}" -eq 1 ]]; then

        kubectl delete pod \
            "${POD}" \
            -n "${S3_NAMESPACE}" \
            --ignore-not-found=true \
            >/dev/null 2>&1 \
            || true

    else

        echo
        echo "NOTE:"
        echo "STEP 03 failed."
        echo "Temporary Pod preserved:"
        echo "  namespace: ${S3_NAMESPACE}"
        echo "  pod      : ${POD}"
        echo
        echo "No existing S3 object was intentionally overwritten."

    fi
}


trap cleanup EXIT


echo "============================================================"
echo "Healthcare Data Platform V2.1"
echo "TASK-001 / STEP 03"
echo "Safe V2 Landing payload publish"
echo "============================================================"
echo


# ============================================================
# 1. Validate local frozen input
# ============================================================

echo "[1/10] Validating STEP 01 source inventory..."

python3 - "${DRAFT}" "${BATCH_ID}" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(
    Path(sys.argv[1]).read_text(
        encoding="utf-8"
    )
)

batch_id = sys.argv[2]

assert data["batch_id"] == batch_id
assert data["status"] == "LOCAL_VALIDATED_NOT_UPLOADED"
assert data["expected_file_count"] == 18
assert len(data["files"]) == 18

print("PASS: draft manifest")
print(f"Batch ID : {data['batch_id']}")
print(f"Files    : {len(data['files'])}/18")
PY


python3 - "${DRAFT}" "${CHECKSUM_FILE}" <<'PY'
import json
import sys
from pathlib import Path

manifest = json.loads(
    Path(sys.argv[1]).read_text(
        encoding="utf-8"
    )
)

target = Path(
    sys.argv[2]
)

with target.open(
    "w",
    encoding="utf-8",
    newline="\n"
) as fh:

    for item in manifest["files"]:

        filename = Path(
            item["path"]
        ).name

        fh.write(
            f"{item['sha256']}  "
            f"{filename}\n"
        )

print(
    f"Checksum file: {target}"
)
PY

echo


# ============================================================
# 2. Start shared transfer / AWS CLI Pod
# ============================================================

echo "[2/10] Starting temporary S3 transfer Pod..."

cat <<EOF_K8S | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: ${POD}
  namespace: ${S3_NAMESPACE}

  labels:
    app: healthcare-task001
    task: landing-payload

spec:
  restartPolicy: Never

  volumes:
    - name: work
      emptyDir: {}

  containers:

    - name: transfer
      image: alpine:3.20

      command:
        - /bin/sh
        - -c

      args:
        - |
          mkdir -p \
            /work/source \
            /work/existing \
            /work/verify

          sleep 3600

      volumeMounts:
        - name: work
          mountPath: /work


    - name: aws-cli
      image: amazon/aws-cli:latest

      command:
        - /bin/sh
        - -c

      args:
        - |
          sleep 3600

      env:

        - name: AWS_ACCESS_KEY_ID
          valueFrom:
            secretKeyRef:
              name: ${S3_SECRET_NAME}
              key: AWS_ACCESS_KEY_ID

        - name: AWS_SECRET_ACCESS_KEY
          valueFrom:
            secretKeyRef:
              name: ${S3_SECRET_NAME}
              key: AWS_SECRET_ACCESS_KEY

        - name: AWS_DEFAULT_REGION
          value: us-east-1

      volumeMounts:
        - name: work
          mountPath: /work
EOF_K8S


kubectl wait \
    --for=condition=Ready \
    "pod/${POD}" \
    -n "${S3_NAMESPACE}" \
    --timeout=120s


echo "PASS: transfer Pod READY"
echo


# ============================================================
# 3. Discover existing batch prefix
# ============================================================

echo "[3/10] Resolving V2 batch prefix..."

kubectl exec \
    -n "${S3_NAMESPACE}" \
    "${POD}" \
    -c "${AWS_CONTAINER}" -- \
    aws \
        --endpoint-url "${S3_ENDPOINT}" \
        s3api \
        list-objects-v2 \
        --bucket "${S3_BUCKET_LANDING}" \
        --prefix "${ROOT_PREFIX}" \
        --query 'Contents[].Key' \
        --output text \
    | tr '\t' '\n' \
    | tr -d '\r' \
    | sed '/^None$/d; /^$/d' \
    | sort \
    > "${ROOT_KEYS}"


python3 "${GUARD}" \
    resolve-prefix \
    --keys "${ROOT_KEYS}" \
    --root-prefix "${ROOT_PREFIX}" \
    --batch-id "${BATCH_ID}" \
    --default-ingest-date "${DEFAULT_INGEST_DATE}" \
    --output "${PREFIX_JSON}"


INGEST_DATE="$(
    python3 - "${PREFIX_JSON}" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(
    Path(sys.argv[1]).read_text(
        encoding="utf-8"
    )
)

print(
    data["ingest_date"]
)
PY
)"


BATCH_PREFIX="$(
    python3 - "${PREFIX_JSON}" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(
    Path(sys.argv[1]).read_text(
        encoding="utf-8"
    )
)

print(
    data["batch_prefix"]
)
PY
)"


LANDING_URI="s3://${S3_BUCKET_LANDING}/${BATCH_PREFIX}"

PAYLOAD_URI="${LANDING_URI}payload/csv/"


echo
echo "Landing batch:"
echo "  ${LANDING_URI}"

echo
echo "Payload target:"
echo "  ${PAYLOAD_URI}"

echo


# ============================================================
# 4. Inspect existing objects
# ============================================================

echo "[4/10] Checking existing objects for conflicts..."

kubectl exec \
    -n "${S3_NAMESPACE}" \
    "${POD}" \
    -c "${AWS_CONTAINER}" -- \
    aws \
        --endpoint-url "${S3_ENDPOINT}" \
        s3api \
        list-objects-v2 \
        --bucket "${S3_BUCKET_LANDING}" \
        --prefix "${BATCH_PREFIX}" \
        --query 'Contents[].Key' \
        --output text \
    | tr '\t' '\n' \
    | tr -d '\r' \
    | sed '/^None$/d; /^$/d' \
    | sort \
    > "${BATCH_KEYS}"


python3 "${GUARD}" \
    inspect-keys \
    --keys "${BATCH_KEYS}" \
    --draft "${DRAFT}" \
    --batch-prefix "${BATCH_PREFIX}" \
    --output "${INSPECT_JSON}"


MANIFEST_PRESENT="$(
    python3 - "${INSPECT_JSON}" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(
    Path(sys.argv[1]).read_text(
        encoding="utf-8"
    )
)

print(
    "YES"
    if data["manifest_present"]
    else "NO"
)
PY
)"


echo


# ============================================================
# 5. Copy local validated source to Pod
# ============================================================

echo "[5/10] Copying local validated payload into shared workspace..."

kubectl cp \
    -c "${TRANSFER_CONTAINER}" \
    "${SYNTHEA_SOURCE_DIR}/." \
    "${S3_NAMESPACE}/${POD}:/work/source"


kubectl cp \
    -c "${TRANSFER_CONTAINER}" \
    "${CHECKSUM_FILE}" \
    "${S3_NAMESPACE}/${POD}:/work/payload.sha256"


echo
echo "Validating copied source..."

kubectl exec \
    -n "${S3_NAMESPACE}" \
    "${POD}" \
    -c "${TRANSFER_CONTAINER}" -- \
    sh -c '
        cd /work/source
        sha256sum -c /work/payload.sha256
    '

echo
echo "PASS: Pod source SHA256 18/18"
echo


# ============================================================
# 6. Validate existing remote payload BEFORE any write
# ============================================================

echo "[6/10] Validating any existing remote payload..."

kubectl exec \
    -n "${S3_NAMESPACE}" \
    "${POD}" \
    -c "${TRANSFER_CONTAINER}" -- \
    sh -c '
        rm -rf /work/existing/*
    '


kubectl exec \
    -n "${S3_NAMESPACE}" \
    "${POD}" \
    -c "${AWS_CONTAINER}" -- \
    aws \
        --endpoint-url "${S3_ENDPOINT}" \
        s3 sync \
        "${PAYLOAD_URI}" \
        /work/existing \
        --only-show-errors


REMOTE_EXISTING_COUNT="$(
    kubectl exec \
        -n "${S3_NAMESPACE}" \
        "${POD}" \
        -c "${TRANSFER_CONTAINER}" -- \
        sh -c '
            find /work/existing \
                -maxdepth 1 \
                -type f \
            | wc -l
        ' \
    | tr -d '\r'
)"


echo "Existing payload objects: ${REMOTE_EXISTING_COUNT}/18"


REUSED_COUNT=0


while read -r EXPECTED_HASH FILE_NAME
do

    if kubectl exec \
        -n "${S3_NAMESPACE}" \
        "${POD}" \
        -c "${TRANSFER_CONTAINER}" -- \
        test -f "/work/existing/${FILE_NAME}"
    then

        ACTUAL_HASH="$(
            kubectl exec \
                -n "${S3_NAMESPACE}" \
                "${POD}" \
                -c "${TRANSFER_CONTAINER}" -- \
                sha256sum \
                    "/work/existing/${FILE_NAME}" \
            | awk '{print $1}' \
            | tr -d '\r'
        )"


        if [[ "${ACTUAL_HASH}" != "${EXPECTED_HASH}" ]]; then

            echo
            echo "CONFLICT:"
            echo "Existing S3 object differs from current batch."
            echo
            echo "File:"
            echo "  ${FILE_NAME}"
            echo
            echo "Expected:"
            echo "  ${EXPECTED_HASH}"
            echo
            echo "Existing S3:"
            echo "  ${ACTUAL_HASH}"
            echo
            echo "No overwrite will be attempted."

            exit 1

        fi


        REUSED_COUNT=$((REUSED_COUNT + 1))

        echo "REUSE ${FILE_NAME}"

    fi

done < "${CHECKSUM_FILE}"


echo
echo "PASS: all existing payload objects match local SHA256."
echo


# ============================================================
# Existing final manifest protection
# ============================================================

if [[ "${MANIFEST_PRESENT}" == "YES" ]]; then

    echo "Existing final manifest detected."
    echo "Validating manifest against local batch..."


    kubectl exec \
        -n "${S3_NAMESPACE}" \
        "${POD}" \
        -c "${AWS_CONTAINER}" -- \
        aws \
            --endpoint-url "${S3_ENDPOINT}" \
            s3 cp \
            "${LANDING_URI}manifest.json" \
            - \
            --only-show-errors \
        > "${EXISTING_MANIFEST}"


    python3 "${GUARD}" \
        compare-manifest \
        --draft "${DRAFT}" \
        --manifest "${EXISTING_MANIFEST}"


    if [[ "${REMOTE_EXISTING_COUNT}" -ne 18 ]]; then

        echo
        echo "ERROR:"
        echo "INTAKE_VERIFIED manifest exists, but payload count is:"
        echo "  ${REMOTE_EXISTING_COUNT}/18"
        echo
        echo "This is treated as data corruption."
        echo "STEP 03 will not repair it automatically."

        exit 1

    fi

fi


# ============================================================
# 7. Upload only missing objects
# ============================================================

echo
echo "[7/10] Uploading missing payload objects..."

UPLOAD_COUNT=0


if [[ "${MANIFEST_PRESENT}" == "YES" ]]; then

    echo "Final INTAKE_VERIFIED manifest already exists."
    echo "No upload is allowed."

else

    while read -r EXPECTED_HASH FILE_NAME
    do

        if kubectl exec \
            -n "${S3_NAMESPACE}" \
            "${POD}" \
            -c "${TRANSFER_CONTAINER}" -- \
            test -f "/work/existing/${FILE_NAME}"
        then

            continue

        fi


        echo "UPLOAD ${FILE_NAME}"


        kubectl exec \
            -n "${S3_NAMESPACE}" \
            "${POD}" \
            -c "${AWS_CONTAINER}" -- \
            aws \
                --endpoint-url "${S3_ENDPOINT}" \
                s3 cp \
                "/work/source/${FILE_NAME}" \
                "${PAYLOAD_URI}${FILE_NAME}" \
                --only-show-errors


        UPLOAD_COUNT=$((UPLOAD_COUNT + 1))

    done < "${CHECKSUM_FILE}"

fi


echo
echo "Uploaded this run : ${UPLOAD_COUNT}"
echo "Reused existing   : ${REUSED_COUNT}"
echo


# ============================================================
# 8. Independently read back payload from S3
# ============================================================

echo "[8/10] Re-reading complete payload from S3..."

kubectl exec \
    -n "${S3_NAMESPACE}" \
    "${POD}" \
    -c "${TRANSFER_CONTAINER}" -- \
    sh -c '
        rm -rf /work/verify/*
    '


kubectl exec \
    -n "${S3_NAMESPACE}" \
    "${POD}" \
    -c "${AWS_CONTAINER}" -- \
    aws \
        --endpoint-url "${S3_ENDPOINT}" \
        s3 sync \
        "${PAYLOAD_URI}" \
        /work/verify \
        --only-show-errors


VERIFY_COUNT="$(
    kubectl exec \
        -n "${S3_NAMESPACE}" \
        "${POD}" \
        -c "${TRANSFER_CONTAINER}" -- \
        sh -c '
            find /work/verify \
                -maxdepth 1 \
                -type f \
            | wc -l
        ' \
    | tr -d '\r'
)"


echo "Downloaded payload files: ${VERIFY_COUNT}/18"


if [[ "${VERIFY_COUNT}" -ne 18 ]]; then

    echo "ERROR:"
    echo "Expected 18 payload objects after upload."
    echo "Found ${VERIFY_COUNT}."

    exit 1

fi


echo
echo "Running S3 read-back SHA256..."

kubectl exec \
    -n "${S3_NAMESPACE}" \
    "${POD}" \
    -c "${TRANSFER_CONTAINER}" -- \
    sh -c '
        cd /work/verify
        sha256sum -c /work/payload.sha256
    '


echo
echo "PASS: S3 read-back SHA256 18/18"
echo


# ============================================================
# 9. Final object inventory
# ============================================================

echo "[9/10] Final S3 inventory..."

FINAL_PAYLOAD_COUNT="$(
    kubectl exec \
        -n "${S3_NAMESPACE}" \
        "${POD}" \
        -c "${AWS_CONTAINER}" -- \
        aws \
            --endpoint-url "${S3_ENDPOINT}" \
            s3api \
            list-objects-v2 \
            --bucket "${S3_BUCKET_LANDING}" \
            --prefix "${BATCH_PREFIX}payload/csv/" \
            --query 'Contents[].Key' \
            --output text \
    | tr '\t' '\n' \
    | tr -d '\r' \
    | sed '/^None$/d; /^$/d' \
    | wc -l \
    | tr -d ' '
)"


echo "S3 payload object count: ${FINAL_PAYLOAD_COUNT}"


if [[ "${FINAL_PAYLOAD_COUNT}" -ne 18 ]]; then

    echo "ERROR:"
    echo "S3 payload object count is not 18."

    exit 1

fi


echo
echo "PASS: exact payload count 18"
echo


# ============================================================
# 10. Write local runtime state
# ============================================================

echo "[10/10] Writing local Step 03 state..."

VERIFIED_AT="$(
    date -u +%Y-%m-%dT%H:%M:%SZ
)"


python3 - \
    "${STATE_FILE}" \
    "${BATCH_ID}" \
    "${INGEST_DATE}" \
    "${LANDING_URI}" \
    "${PAYLOAD_URI}" \
    "${UPLOAD_COUNT}" \
    "${REUSED_COUNT}" \
    "${MANIFEST_PRESENT}" \
    "${VERIFIED_AT}" <<'PY'
import json
import sys
from pathlib import Path

(
    output,
    batch_id,
    ingest_date,
    landing_uri,
    payload_uri,
    uploaded,
    reused,
    manifest_present,
    verified_at
) = sys.argv[1:]

state = {
    "step": "TASK-001-STEP-03",
    "status": "PAYLOAD_VERIFIED",

    "batch_id": batch_id,
    "ingest_date": ingest_date,

    "landing_uri": landing_uri,
    "payload_uri": payload_uri,

    "expected_file_count": 18,
    "verified_file_count": 18,

    "uploaded_this_run": int(uploaded),
    "reused_this_run": int(reused),

    "manifest_present_before_step": (
        manifest_present == "YES"
    ),

    "manifest_published_by_step03": False,

    "intake_verified_by_step03": False,

    "verified_at": verified_at
}

Path(output).write_text(
    json.dumps(
        state,
        indent=2
    ) + "\n",
    encoding="utf-8"
)

print(
    f"State: {output}"
)
PY


STEP_SUCCESS=1


echo
echo "============================================================"
echo "TASK-001 STEP 03 RESULT"
echo "============================================================"
echo
echo "Batch ID:"
echo "  ${BATCH_ID}"
echo
echo "Ingest date:"
echo "  ${INGEST_DATE}"
echo
echo "Landing:"
echo "  ${LANDING_URI}"
echo
echo "Payload:"
echo "  ${PAYLOAD_URI}"
echo
echo "Uploaded this run : ${UPLOAD_COUNT}"
echo "Reused this run   : ${REUSED_COUNT}"
echo
echo "STEP03=PASS"
echo "S3_PAYLOAD_OBJECTS=18/18"
echo "S3_READBACK_SHA256=18/18"
echo "MANIFEST_PUBLISHED=NO"
echo "INTAKE_VERIFIED=NO"
echo "OLD_LANDING_TOUCHED=NO"
echo "OMOP_TOUCHED=NO"
echo "============================================================"
