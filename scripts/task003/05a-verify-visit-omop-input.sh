#!/usr/bin/env bash
set -Eeuo pipefail

echo "#### TASK003 STEP05A INPUT VERIFY OUTPUT BEGIN ####"
trap 'rc=$?; echo "VERIFY_EXIT_CODE=${rc}"; echo "#### TASK003 STEP05A INPUT VERIFY OUTPUT END ####"; exit "${rc}"' EXIT

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
[[ "$#" -eq 1 ]] || {
    echo "Usage: $0 RAW_RUN_ID"
    exit 2
}

mkdir -p "${ROOT}/runtime/reports/task003/step05"
REPORT="$(mktemp -d "${ROOT}/runtime/reports/task003/step05/input.XXXXXX")"

python3 "${ROOT}/apps/task003/resolve_approved_encounter_raw.py" \
    --project-root "${ROOT}" \
    --raw-run-id "$1" \
    --output "${REPORT}/input-context.json"

echo "LOCAL_APPROVED_RAW_INPUT=PASS"
echo "REMOTE_RAW_REVALIDATION=PENDING"
echo "INPUT_CONTEXT=${REPORT}/input-context.json"
echo "SPARK_APPLICATION_SUBMITTED=NO"
echo "S3_WRITE=NO"
echo "DATABASE_WRITE=NO"
