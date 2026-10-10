#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  echo 'ERROR: execute with bash; do not source'
  return 2
fi

set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT=/data/spark/healthcare-data-platform

REPORT="$ROOT/runtime/reports/task003/step06/visit-id-allocation-rehearsal.20261010t140207z.2482042"

APP="$ROOT/apps/task003/verify_visit_id_allocation_rehearsal.py"

STATE="$REPORT/run-state.json"
SQL="$REPORT/rehearsal.sql"
PSQL_OUTPUT="$REPORT/psql-output.txt"
POSTCHECK="$REPORT/post-rehearsal-db-state.txt"

OUTDIR="$ROOT/runtime/reports/task003/step06/rehearsal-canonical-verification"
OUTPUT="$OUTDIR/run-state.json"

echo '#### TASK003 STEP06B4A CANONICAL REHEARSAL VERIFY OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  echo "STEP06B4A_CANONICAL_VERIFY_EXIT_CODE=$rc"
  echo '#### TASK003 STEP06B4A CANONICAL REHEARSAL VERIFY OUTPUT END ####'
  exit "$rc"
}

trap finish EXIT

mkdir -p "$OUTDIR"

cd "$ROOT"

for file in \
  "$APP" \
  "$STATE" \
  "$SQL" \
  "$PSQL_OUTPUT" \
  "$POSTCHECK"
do
  [[ -s "$file" && ! -L "$file" ]] || {
    echo "ERROR: missing or unsafe rehearsal evidence: $file"
    exit 1
  }
done

python3 "$APP" \
  --state "$STATE" \
  --sql "$SQL" \
  --psql-output "$PSQL_OUTPUT" \
  --postcheck "$POSTCHECK" \
  --output "$OUTPUT"

python3 - "$OUTPUT" <<'PY'
import json
import sys
from pathlib import Path


state = json.loads(
    Path(sys.argv[1]).read_bytes()
)

assert (
    state["status"]
    == "VISIT_ID_ALLOCATION_REHEARSAL_VERIFIED"
)

assert state["candidate_rows"] == 5799
assert state["copy_temp_rows"] == 5799

assert (
    state["candidate_business_key_sha256"]
    == "aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e"
)

assert state["transaction_rolled_back"] is True
assert state["irreversible_boundary_crossed"] is False
assert state["nextval_called"] is False
assert state["visit_id_map_mutated"] is False
assert state["sequence_advanced"] is False
assert state["ready_for_first_mutation"] is True

print("STEP06B4A_CANONICAL_STATE=PASS")
PY

echo 'STEP06B4A_REHEARSAL_CANONICAL_GATE=PASS'
echo 'ADVISORY_LOCK_REHEARSAL=PASS'
echo 'TABLE_LOCK_REHEARSAL=PASS'
echo 'COPY_5799_REHEARSAL=PASS'
echo 'BUSINESS_KEY_FINGERPRINT_REHEARSAL=PASS'

echo 'IRREVERSIBLE_BOUNDARY_CROSSED=NO'
echo 'NEXTVAL_CALLED=NO'
echo 'SETVAL_CALLED=NO'

echo 'VISIT_ID_MAP_MUTATED=NO'
echo 'SEQUENCE_ADVANCED=NO'

echo 'READY_FOR_FIRST_VISIT_ID_MUTATION=YES'
