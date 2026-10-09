#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1 GIT_PAGER=cat

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo '#### TASK003 STEP05G1 FORMAL REPLAY VALIDATION OUTPUT BEGIN ####'

REPORT=''

finish() {
  rc=$?
  trap - EXIT
  [[ -z "$REPORT" ]] || echo "VALIDATION_REPORT=$REPORT"
  echo "VERIFY_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G1 FORMAL REPLAY VALIDATION OUTPUT END ####'
  exit "$rc"
}
trap finish EXIT

[[ $# -eq 2 ]] || {
  echo "Usage: $0 STEP05F2_RUN_STATE PROCESSED_RUN_ID"
  exit 2
}

F2_STATE="$1"
RUN_ID="$2"

[[ -s "$F2_STATE" && ! -L "$F2_STATE" ]] || {
  echo 'ERROR: F2 evidence unavailable'
  exit 2
}

[[ "$RUN_ID" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$ && \
   "$RUN_ID" != '.' && "$RUN_ID" != '..' ]] || {
  echo 'ERROR: unsafe run ID'
  exit 2
}

PLAN="$ROOT/runtime/reports/task003/step05/processed-plans/$RUN_ID/plan.json"
PLANNER="$ROOT/scripts/task003/05g1-plan-visit-processed.sh"

[[ -f "$PLANNER" ]] || {
  echo 'ERROR: G1 planner missing'
  exit 2
}

mkdir -p "$ROOT/runtime/reports/task003/step05"
REPORT=$(mktemp -d "$ROOT/runtime/reports/task003/step05/g1-replay.XXXXXXXX")

export VISIT_PROCESSED_RUN_ID="$RUN_ID"

echo '=== 1. First planner invocation ==='

bash "$PLANNER" "$F2_STATE" > "$REPORT/first.log" 2>&1 || {
  cat "$REPORT/first.log"
  exit 1
}

grep -E '^PROCESSED_PLAN_STATUS=|^PLAN_EXIT_CODE=' "$REPORT/first.log"

grep -Eq '^PROCESSED_PLAN_STATUS=(CREATED|REUSED)$' \
  "$REPORT/first.log"

grep -q '^PLAN_EXIT_CODE=0$' "$REPORT/first.log"

[[ -s "$PLAN" && ! -L "$PLAN" ]] || {
  echo 'ERROR: immutable plan missing'
  exit 1
}

SHA_BEFORE=$(sha256sum "$PLAN" | awk '{print $1}')
echo 'FIRST_EXECUTION=PASS'

echo '=== 2. Same-run planner replay ==='

bash "$PLANNER" "$F2_STATE" > "$REPORT/replay.log" 2>&1 || {
  cat "$REPORT/replay.log"
  exit 1
}

grep -E '^PROCESSED_PLAN_STATUS=|^PLAN_EXIT_CODE=' "$REPORT/replay.log"

grep -q '^PROCESSED_PLAN_STATUS=REUSED$' "$REPORT/replay.log"
grep -q '^PLAN_EXIT_CODE=0$' "$REPORT/replay.log"

SHA_AFTER=$(sha256sum "$PLAN" | awk '{print $1}')

[[ "$SHA_BEFORE" == "$SHA_AFTER" ]] || {
  echo 'ERROR: plan changed during replay'
  exit 1
}

echo 'SAME_RUN_REPLAY=PASS'
echo 'PLAN_SHA256_UNCHANGED=PASS'

echo '=== 3. Pinned evidence validation ==='

python3 "$ROOT/apps/task003/verify_visit_processed_plan.py" \
  --root "$ROOT" \
  --f2-state "$F2_STATE" \
  --plan "$PLAN" \
  --run-id "$RUN_ID"

echo 'STEP05G1_FORMAL_VALIDATION=PASS'
echo 'SPARK_APPLICATION_SUBMITTED=NO'
echo 'S3_WRITE=NO'
echo 'DATABASE_WRITE=NO'
