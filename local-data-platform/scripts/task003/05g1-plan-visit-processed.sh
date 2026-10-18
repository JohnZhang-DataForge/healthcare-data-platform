#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo '#### TASK003 STEP05G1 PLAN EXECUTION OUTPUT BEGIN ####'

finish() {
    rc=$?
    trap - EXIT
    echo "PLAN_EXIT_CODE=$rc"
    echo '#### TASK003 STEP05G1 PLAN EXECUTION OUTPUT END ####'
    exit "$rc"
}
trap finish EXIT

[[ $# -eq 1 && -s "$1" ]] || {
    echo "Usage: $0 ABSOLUTE_STEP05F2_RUN_STATE"
    exit 2
}

RUN_ID="${VISIT_PROCESSED_RUN_ID:-visit-proc-$(date -u +%Y%m%dt%H%M%Sz)-$$}"

python3 "$ROOT/apps/task003/plan_visit_processed.py" \
    --root "$ROOT" \
    --f2-state "$1" \
    --run-id "$RUN_ID"

echo "PLANNED_RUN_ID=$RUN_ID"
echo 'SPARK_APPLICATION_SUBMITTED=NO'
echo 'S3_WRITE=NO'
echo 'DATABASE_WRITE=NO'
