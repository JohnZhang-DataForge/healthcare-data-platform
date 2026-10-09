#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo '#### TASK003 STEP05G2A PREFIX READONLY INSPECTION OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT
  echo "INSPECTION_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G2A PREFIX READONLY INSPECTION OUTPUT END ####'
  exit "$rc"
}
trap finish EXIT

[[ $# -eq 4 ]] || {
  echo "Usage: $0 STEP05F2_STATE PROCESSED_RUN_ID PLAN_JSON S3_LISTING_JSON"
  exit 2
}

F2="$1"
RUN_ID="$2"
PLAN="$3"
LISTING="$4"

[[ -s "$F2" && -s "$PLAN" && -s "$LISTING" ]] || {
  echo 'ERROR: input file missing'
  exit 2
}

# Verify the immutable plan against the exact STEP05F2 evidence.
python3 "$ROOT/apps/task003/verify_visit_processed_plan.py" \
  --root "$ROOT" \
  --f2-state "$F2" \
  --plan "$PLAN" \
  --run-id "$RUN_ID"

# Inspect supplied S3 listing.
# Only EMPTY returns success.
python3 "$ROOT/apps/task003/inspect_visit_processed_prefix.py" \
  --plan "$PLAN" \
  --listing "$LISTING"

echo 'PREFIX_PREFLIGHT=PASS'
echo 'S3_WRITE=NO'
echo 'DATABASE_WRITE=NO'
