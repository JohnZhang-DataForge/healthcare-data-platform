#!/usr/bin/env bash
set -Eeuo pipefail
echo "#### TASK003 STEP04 RESUME OUTPUT BEGIN ####"
ROOT="/data/spark/healthcare-data-platform"
NS="dw-spark"
S3_ENDPOINT="http://dw-seaweedfs-s3.dw-seaweedfs.svc.cluster.local:8333"
UTILITY_POD=""
SESSION=""

finish() {
    rc=$?
    trap - EXIT
    if [[ -n "${UTILITY_POD}" ]]; then
        kubectl delete pod "${UTILITY_POD}" -n "${NS}" --ignore-not-found \
          --wait=false >/dev/null 2>&1 || true
    fi
    echo "RESUME_EXIT_CODE=${rc}"
    echo "RESUME_EVIDENCE=${SESSION}"
    echo "#### TASK003 STEP04 RESUME OUTPUT END ####"
    exit "${rc}"
}
trap finish EXIT

[[ "$#" -eq 1 && "$1" =~ ^encounter-raw-[0-9]{8}T[0-9]{6}Z-[0-9]+$ ]] || {
    echo "Usage: $0 encounter-raw-YYYYMMDDTHHMMSSZ-PID"; exit 2;
}
RAW_RUN_ID="$1"
RUN_DIR="${ROOT}/runtime/reports/task003/step04/${RAW_RUN_ID}"
[[ -s "${RUN_DIR}/dq-result.json" ]] || { echo "ERROR: draft DQ missing"; exit 1; }

STAMP="$(date -u +%Y%m%dT%H%M%SZ)-$$"
SESSION="${RUN_DIR}/resume-${STAMP}"
mkdir -p "${SESSION}"
exec 8>"${RUN_DIR}/resume.lock"
flock -n 8 || { echo "ERROR: another recovery is running"; exit 1; }

EVIDENCE_BUILDER="${ROOT}/apps/task003/build_encounter_raw_evidence.py"
RECOVERY_HELPER="${ROOT}/apps/task003/resolve_encounter_raw_resume.py"
APP_NAME="task003-encounter-raw-${RAW_RUN_ID#encounter-raw-}"
APP_NAME="${APP_NAME,,}"

echo "[1/4] Revalidate original completed Spark run and TASK001 lineage..."
kubectl get sparkapplication "${APP_NAME}" -n "${NS}" -o json > "${SESSION}/sparkapplication.json"
kubectl logs -n "${NS}" "${APP_NAME}-driver" > "${SESSION}/driver.log"
"${ROOT}/apps/resolve_verified_intake_file.py" encounters --format json > "${SESSION}/intake.json"
python3 "${RECOVERY_HELPER}" context "${ROOT}" "${RAW_RUN_ID}" "${SESSION}" > "${SESSION}/verified.env"
source "${SESSION}/verified.env"
echo "RESUME_LINEAGE_AND_SPARK_GATE=PASS"

echo "[2/4] Verify original Raw objects remain unchanged..."
UTILITY_POD="task003-raw-resume-${STAMP,,}"
cat <<YAML | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: ${UTILITY_POD}
  namespace: ${NS}
  labels:
    healthcare-task: task003
    healthcare-purpose: raw-resume
spec:
  restartPolicy: Never
  containers:
    - name: aws
      image: amazon/aws-cli:2.15.57
      imagePullPolicy: IfNotPresent
      command: ["/bin/sh", "-c", "sleep 600"]
      envFrom:
        - secretRef:
            name: dw-spark-s3-secret
YAML

kubectl wait --for=condition=Ready "pod/${UTILITY_POD}" -n "${NS}" --timeout=180s
RAW_KEY="${RAW_BASE_S3#s3://health-raw/}"
kubectl exec -n "${NS}" "${UTILITY_POD}" -- aws --endpoint-url "${S3_ENDPOINT}" \
  s3api list-objects-v2 --bucket health-raw --prefix "${RAW_KEY}/data/" \
  --output json > "${SESSION}/data-inventory.json"
python3 "${RECOVERY_HELPER}" inventory "${ROOT}" "${RAW_RUN_ID}" "${SESSION}"

publish_or_reuse_json() {
    local local_file="$1" uri="$2" remote_file="$3" label="$4"
    local key="${uri#s3://health-raw/}" listing="${remote_file}.listing" count
    [[ "${uri}" == "${RAW_BASE_S3}/"* ]] || return 1

    kubectl exec -n "${NS}" "${UTILITY_POD}" -- aws --endpoint-url "${S3_ENDPOINT}" \
      s3api list-objects-v2 --bucket health-raw --prefix "${key}" --output json > "${listing}"
    count="$(python3 "${RECOVERY_HELPER}" metadata-count "${listing}" "${key}")"

    if [[ "${count}" == "0" ]]; then
        python3 "${EVIDENCE_BUILDER}" empty-listing < "${listing}"
        kubectl exec -i -n "${NS}" "${UTILITY_POD}" -- aws --endpoint-url "${S3_ENDPOINT}" \
          s3 cp - "${uri}" --content-type application/json --only-show-errors < "${local_file}"
    fi

    kubectl exec -n "${NS}" "${UTILITY_POD}" -- aws --endpoint-url "${S3_ENDPOINT}" \
      s3 cp "${uri}" - --only-show-errors > "${remote_file}"

    cmp -s "${local_file}" "${remote_file}" || {
        echo "ERROR: ${label} content conflict or readback mismatch"; return 1;
    }
    echo "${label}_PUBLISHED=PASS"
    echo "${label}_READBACK_SHA256=PASS"
    echo "${label}_EXISTING_OBJECTS_REUSED=${count}"
}

echo "[3/4] Publish or verify DQ..."
python3 "${EVIDENCE_BUILDER}" dq
publish_or_reuse_json "${DQ_FILE}" "${DQ_URI}" "${REMOTE_DQ_FILE}" DQ

echo "[4/4] Publish approved manifest LAST and validate state..."
python3 "${EVIDENCE_BUILDER}" manifest
publish_or_reuse_json "${MANIFEST_FILE}" "${RAW_MANIFEST_URI}" "${REMOTE_MANIFEST_FILE}" RAW_MANIFEST
python3 "${EVIDENCE_BUILDER}" state

echo "STEP04=PASS"
echo "SPARK_APPLICATION=COMPLETED"
echo "CANONICAL_GATE=PASS"
echo "RAW_ROWS=${RAW_ROWS}"
echo "RAW_UNIQUE_KEYS=${RAW_UNIQUE_KEYS}"
echo "RAW_STATUS=APPROVED"
echo "RAW_PUBLISH_RUN_ID=${RAW_RUN_ID}"
echo "RUN_STATE=${STATE_FILE}"
echo "SPARK_APPLICATION_SUBMITTED=NO"
echo "RAW_PARQUET_REWRITTEN=NO"
echo "POSTGRESQL_WRITE=NO"
echo "PHASE3C_TOUCHED=NO"
