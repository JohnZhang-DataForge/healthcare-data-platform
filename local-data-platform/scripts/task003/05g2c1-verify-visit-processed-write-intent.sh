#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo '#### TASK003 STEP05G2C1 WRITE-INTENT VALIDATION OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT
  echo "VALIDATION_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G2C1 WRITE-INTENT VALIDATION OUTPUT END ####'
  exit "$rc"
}
trap finish EXIT

[[ $# -eq 3 ]] || {
  echo "Usage: $0 F2_RUN_STATE PROCESSED_RUN_ID G2B_REPORT_DIR"
  exit 2
}

F2="$1"
RUN_ID="$2"
G2B="$3"

[[ "$RUN_ID" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$ && \
   "$RUN_ID" != '.' && "$RUN_ID" != '..' ]] || {
  echo 'ERROR: invalid run ID'
  exit 2
}

PLAN="$ROOT/runtime/reports/task003/step05/processed-plans/$RUN_ID/plan.json"

python3 "$ROOT/apps/task003/prepare_visit_processed_write_intent.py" \
  --root "$ROOT" \
  --f2-state "$F2" \
  --plan "$PLAN" \
  --g2b-report "$G2B"

echo 'G2C1_WRITE_INTENT_VALIDATION=PASS'
echo 'SPARK_APPLICATION_SUBMITTED=NO'
echo 'S3_WRITE=NO'
echo 'DATABASE_WRITE=NO'
