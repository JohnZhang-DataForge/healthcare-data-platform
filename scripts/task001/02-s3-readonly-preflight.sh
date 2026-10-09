#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/data/spark/healthcare-data-platform}"
ENV_FILE="${PROJECT_ROOT}/config/local.env"

if [[ ! -f "${ENV_FILE}" ]]; then
    echo "ERROR: missing ${ENV_FILE}"
    exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a


: "${SOURCE_SYSTEM:?missing SOURCE_SYSTEM}"
: "${SOURCE_VERSION:?missing SOURCE_VERSION}"
: "${BATCH_ID:?missing BATCH_ID}"

: "${S3_NAMESPACE:?missing S3_NAMESPACE}"
: "${S3_SECRET_NAME:?missing S3_SECRET_NAME}"
: "${S3_ENDPOINT:?missing S3_ENDPOINT}"
: "${S3_BUCKET_LANDING:?missing S3_BUCKET_LANDING}"


STEP01_DRAFT="${PROJECT_ROOT}/runtime/reports/task001/step01/manifest.draft.json"
STEP01_REPORT="${PROJECT_ROOT}/runtime/reports/task001/step01/validation-report.json"

REPORT_DIR="${PROJECT_ROOT}/runtime/reports/task001/step02"
mkdir -p "${REPORT_DIR}"

REMOTE_KEYS="${REPORT_DIR}/remote-v2-keys.txt"
PREFIX_REPORT="${REPORT_DIR}/prefix-analysis.txt"

ROOT_PREFIX="source=${SOURCE_SYSTEM}/source_version=${SOURCE_VERSION}/"

LEGACY_PREFIX="synthea/v3.3.0/seed=20261005/population=100/location=atlanta-georgia/"

POD="task001-s3-preflight-$(date -u +%H%M%S)"

STEP_SUCCESS=0


cleanup() {

    if [[ "${STEP_SUCCESS}" -eq 1 ]]; then

        kubectl delete pod \
            "${POD}" \
            -n "${S3_NAMESPACE}" \
            --ignore-not-found=true \
            >/dev/null 2>&1 || true

    else

        echo
        echo "NOTE:"
        echo "Preflight Pod preserved for troubleshooting:"
        echo "  namespace: ${S3_NAMESPACE}"
        echo "  pod      : ${POD}"

    fi
}

trap cleanup EXIT


echo "============================================================"
echo "Healthcare Data Platform V2.1"
echo "TASK-001 / STEP 02"
echo "SeaweedFS S3 READ-ONLY preflight"
echo "============================================================"
echo


# ============================================================
# 1. Verify STEP 01 frozen result
# ============================================================

echo "[1/7] Checking STEP 01 prerequisite..."

if [[ ! -s "${STEP01_DRAFT}" ]]; then
    echo "ERROR: STEP 01 draft manifest missing."
    exit 1
fi

if [[ ! -s "${STEP01_REPORT}" ]]; then
    echo "ERROR: STEP 01 validation report missing."
    exit 1
fi

python3 - \
    "${STEP01_DRAFT}" \
    "${STEP01_REPORT}" \
    "${BATCH_ID}" <<'PY_CHECK'

import json
import sys
from pathlib import Path

draft_path = Path(sys.argv[1])
report_path = Path(sys.argv[2])
expected_batch = sys.argv[3]

draft = json.loads(
    draft_path.read_text(encoding="utf-8")
)

report = json.loads(
    report_path.read_text(encoding="utf-8")
)

assert draft["batch_id"] == expected_batch
assert draft["status"] == "LOCAL_VALIDATED_NOT_UPLOADED"
assert draft["expected_file_count"] == 18
assert len(draft["files"]) == 18

assert report["status"] == "PASS"
assert report["validated_file_count"] == 18

print("PASS: STEP 01 frozen result valid")
print(f"Batch ID      : {draft['batch_id']}")
print(f"Local files   : {len(draft['files'])}/18")

PY_CHECK

echo


# ============================================================
# 2. Kubernetes metadata
# ============================================================

echo "[2/7] Checking Kubernetes resources..."

echo "Current context:"
kubectl config current-context

echo

kubectl get namespace "${S3_NAMESPACE}"

echo

kubectl get secret \
    "${S3_SECRET_NAME}" \
    -n "${S3_NAMESPACE}" \
    -o custom-columns='NAME:.metadata.name,TYPE:.type' \
    --no-headers

echo

kubectl get svc \
    dw-seaweedfs-s3 \
    -n dw-seaweedfs \
    -o wide

echo

echo "PASS: required Kubernetes metadata exists."
echo


# ============================================================
# 3. Create temporary S3 client
# ============================================================

echo "[3/7] Starting temporary read-only S3 client..."

cat <<EOF_K8S | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: ${POD}
  namespace: ${S3_NAMESPACE}
  labels:
    app: healthcare-task001
    task: s3-preflight
spec:
  restartPolicy: Never

  containers:
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
EOF_K8S


kubectl wait \
    --for=condition=Ready \
    "pod/${POD}" \
    -n "${S3_NAMESPACE}" \
    --timeout=120s

echo
echo "PASS: temporary S3 client READY."
echo


# ============================================================
# 4. Test S3 endpoint + bucket
# ============================================================

echo "[4/7] Checking SeaweedFS S3 endpoint and Landing bucket..."

kubectl exec \
    -n "${S3_NAMESPACE}" \
    "${POD}" \
    -c aws-cli -- \
    aws \
        --endpoint-url "${S3_ENDPOINT}" \
        s3api \
        head-bucket \
        --bucket "${S3_BUCKET_LANDING}"

echo
echo "PASS: s3://${S3_BUCKET_LANDING} accessible."
echo


# ============================================================
# 5. Protect historical Landing baseline
# ============================================================

echo "[5/7] Checking protected historical Landing prefix..."

LEGACY_SAMPLE_COUNT="$(
    kubectl exec \
        -n "${S3_NAMESPACE}" \
        "${POD}" \
        -c aws-cli -- \
        aws \
            --endpoint-url "${S3_ENDPOINT}" \
            s3api \
            list-objects-v2 \
            --bucket "${S3_BUCKET_LANDING}" \
            --prefix "${LEGACY_PREFIX}" \
            --max-keys 1 \
            --query 'KeyCount' \
            --output text \
        | tr -d '\r'
)"


if [[ "${LEGACY_SAMPLE_COUNT}" == "0" || "${LEGACY_SAMPLE_COUNT}" == "None" ]]; then

    echo "ERROR:"
    echo "Protected historical Landing prefix appears empty:"
    echo
    echo "s3://${S3_BUCKET_LANDING}/${LEGACY_PREFIX}"
    echo
    echo "Stopping before any V2 work."

    exit 1

fi


echo "PASS: historical Landing baseline still exists."
echo
echo "Protected prefix:"
echo "  s3://${S3_BUCKET_LANDING}/${LEGACY_PREFIX}"
echo


# ============================================================
# 6. Inspect V2 namespace
# ============================================================

echo "[6/7] Inspecting V2 Landing namespace..."

kubectl exec \
    -n "${S3_NAMESPACE}" \
    "${POD}" \
    -c aws-cli -- \
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
    > "${REMOTE_KEYS}"


REMOTE_COUNT="$(
    wc -l < "${REMOTE_KEYS}" \
    | tr -d ' '
)"


echo "V2 objects currently found: ${REMOTE_COUNT}"
echo


python3 - \
    "${REMOTE_KEYS}" \
    "${ROOT_PREFIX}" \
    "${BATCH_ID}" \
    "${PREFIX_REPORT}" <<'PY_PREFIX'

import sys
from pathlib import Path

keys_file = Path(sys.argv[1])
root_prefix = sys.argv[2]
batch_id = sys.argv[3]
report_file = Path(sys.argv[4])

keys = [
    line.strip()
    for line in keys_file.read_text(
        encoding="utf-8"
    ).splitlines()
    if line.strip()
]

marker = f"/batch_id={batch_id}/"

prefixes = set()

for key in keys:

    if not key.startswith(root_prefix):
        continue

    if marker not in key:
        continue

    before, _ = key.split(
        marker,
        1
    )

    prefix = (
        before
        + marker
    )

    prefixes.add(prefix)


prefixes = sorted(prefixes)

lines = [
    f"V2_BATCH_PREFIX_COUNT={len(prefixes)}"
]

if not prefixes:

    lines.append(
        "V2_EXISTING_PREFIX=<none>"
    )

else:

    for idx, prefix in enumerate(
        prefixes,
        start=1
    ):
        lines.append(
            f"V2_EXISTING_PREFIX_{idx}={prefix}"
        )


report_file.write_text(
    "\n".join(lines) + "\n",
    encoding="utf-8"
)

print("\n".join(lines))


if len(prefixes) > 1:

    print()
    print(
        "ERROR: multiple V2 prefixes exist "
        "for the same batch_id."
    )

    raise SystemExit(2)

PY_PREFIX

echo


# ============================================================
# 7. Final status
# ============================================================

echo "[7/7] STEP 02 summary..."
echo

echo "S3 endpoint:"
echo "  ${S3_ENDPOINT}"

echo

echo "Landing bucket:"
echo "  s3://${S3_BUCKET_LANDING}"

echo

echo "V2 root:"
echo "  s3://${S3_BUCKET_LANDING}/${ROOT_PREFIX}"

echo

cat "${PREFIX_REPORT}"

echo

echo "Remote key inventory:"
echo "  ${REMOTE_KEYS}"

echo

echo "Prefix analysis:"
echo "  ${PREFIX_REPORT}"

echo

echo "No S3 objects were created, modified, or deleted."

STEP_SUCCESS=1

echo
echo "STEP02=PASS"
echo "S3_CONNECTIVITY=PASS"
echo "LANDING_BUCKET=PASS"
echo "LEGACY_LANDING_PROTECTED=PASS"
echo "S3_WRITE=NOT_RUN"
echo "============================================================"

