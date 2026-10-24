#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

echo '#### TASK003 STEP05D REMOTE METADATA OUTPUT BEGIN ####'
POD=''
finish() {
    rc=$?
    trap - EXIT
    if [[ -n "${POD}" ]]; then
        if kubectl delete pod "${POD}" -n dw-spark \
            --ignore-not-found --wait=false \
            > "${REPORT}/pod-cleanup.log" 2>&1
        then
            echo 'UTILITY_POD_DELETE_REQUESTED=YES'
        else
            echo "WARNING: cleanup failed; inspect ${REPORT}/pod-cleanup.log"
        fi
    fi
    echo "VERIFY_EXIT_CODE=${rc}"
    echo '#### TASK003 STEP05D REMOTE METADATA OUTPUT END ####'
    exit "${rc}"
}
trap finish EXIT

[[ $# -eq 1 ]] || {
    echo "Usage: $0 STEP05A_INPUT_CONTEXT"
    exit 2
}
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP="${ROOT}/apps/task003/verify_encounter_remote_metadata.py"
TEMPLATE="${ROOT}/spark/manifests/task003/visit-raw-metadata-reader.yaml.tpl"

mkdir -p "${ROOT}/runtime/reports/task003/step05"
REPORT="$(mktemp -d "${ROOT}/runtime/reports/task003/step05/remote-metadata.XXXXXX")"
echo "VERIFY_REPORT=${REPORT}"

python3 "${APP}" prepare \
    --root "${ROOT}" --context "$1" --report "${REPORT}"

kubectl get secret dw-spark-s3-secret -n dw-spark >/dev/null

POD="visit-raw-meta-$(date -u +%Y%m%dt%H%M%Sz)-$$"
sed "s/__POD_NAME__/${POD}/g" "${TEMPLATE}" \
    > "${REPORT}/utility-pod.yaml"

kubectl create -f "${REPORT}/utility-pod.yaml"
kubectl wait --for=condition=Ready \
    "pod/${POD}" -n dw-spark --timeout=180s

while IFS=$'\t' read -r uri filename; do
    kubectl exec -n dw-spark "${POD}" -- \
        aws --no-cli-pager \
        --endpoint-url http://dw-seaweedfs-s3.dw-seaweedfs.svc.cluster.local:8333 \
        s3 cp "${uri}" - --only-show-errors \
        > "${REPORT}/${filename}" \
        2> "${REPORT}/${filename}.stderr.log" || {
            cat "${REPORT}/${filename}.stderr.log"
            exit 1
        }
    echo "REMOTE_DOWNLOADED=${filename}"
done < "${REPORT}/download-plan.tsv"

python3 "${APP}" verify \
    --root "${ROOT}" --context "$1" --report "${REPORT}"

echo "RUN_STATE=${REPORT}/run-state.json"
echo 'SPARK_APPLICATION_SUBMITTED=NO'
echo 'S3_WRITE=NO'
echo 'DATABASE_WRITE=NO'
