#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  echo 'ERROR: execute with bash; do not source'
  return 2
fi

set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT=/data/spark/healthcare-data-platform

FAILED_REPORT="$ROOT/runtime/reports/task003/step06/visit-id-allocation.20261010t141014z.2485209"
RECOVERY_REPORT="$ROOT/runtime/reports/task003/step06/visit-id-allocation-recovery.20261010t141250z.2486206"

APP="$ROOT/apps/task003/verify_visit_id_allocation_recovery.py"

AMENDMENT="$ROOT/spark/contracts/processed/visit-id-allocation-recovery-amendment-v1.json"

RECOVERY="$RECOVERY_REPORT/run-state.json"

FAILED_SQL="$FAILED_REPORT/allocation.sql"
FAILED_INTENT="$FAILED_REPORT/mutation-intent.json"
FAILED_OUTPUT="$FAILED_REPORT/psql-output.txt"

IDENTITY_STATE="$RECOVERY_REPORT/identity-state.txt"
DB_STATE="$RECOVERY_REPORT/database-state.txt"
MAP_READBACK="$RECOVERY_REPORT/map-readback.tsv"

OUTDIR="$ROOT/runtime/reports/task003/step06/allocation-recovery-canonical-verification"
OUTPUT="$OUTDIR/run-state.json"

echo '#### TASK003 STEP06B4B-R1 CANONICAL RECOVERY VERIFY OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  echo "STEP06B4B_R1_CANONICAL_VERIFY_EXIT_CODE=$rc"
  echo '#### TASK003 STEP06B4B-R1 CANONICAL RECOVERY VERIFY OUTPUT END ####'
  exit "$rc"
}

trap finish EXIT

mkdir -p "$OUTDIR"

cd "$ROOT"

for file in \
  "$APP" \
  "$AMENDMENT" \
  "$RECOVERY" \
  "$FAILED_SQL" \
  "$FAILED_INTENT" \
  "$FAILED_OUTPUT" \
  "$IDENTITY_STATE" \
  "$DB_STATE" \
  "$MAP_READBACK"
do
  [[ -s "$file" && ! -L "$file" ]] || {
    echo "ERROR: missing recovery gate input: $file"
    exit 1
  }
done

python3 "$APP" \
  --amendment "$AMENDMENT" \
  --recovery "$RECOVERY" \
  --failed-sql "$FAILED_SQL" \
  --failed-intent "$FAILED_INTENT" \
  --failed-output "$FAILED_OUTPUT" \
  --identity-state "$IDENTITY_STATE" \
  --db-state "$DB_STATE" \
  --map-readback "$MAP_READBACK" \
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
    == "VISIT_ID_ALLOCATION_RECOVERY_CANONICAL_GATE_PASS"
)

assert state["committed_visit_map_rows"] == 0
assert state["sequence_last_value"] == 1
assert state["sequence_is_called"] is True
assert state["sequence_value_1_consumed"] is True

assert state["predicted_next_sequence_value"] == 2
assert state["predicted_next_value_authoritative"] is False

assert state["identity_generation"] == "ALWAYS"

assert (
    state["explicit_id_insert_requirement"]
    == "OVERRIDING SYSTEM VALUE"
)

assert state["old_b4b_rerun_allowed"] is False
assert state["setval_backward_allowed"] is False

assert (
    state["ready_for_corrected_mutation_design"]
    is True
)

print("STEP06B4B_R1_CANONICAL_STATE=PASS")
PY

echo 'STEP06B4B_R1_RECOVERY_CANONICAL_GATE=PASS'

echo 'COMMITTED_VISIT_MAP_ROWS=0'

echo 'SEQUENCE_LAST_VALUE=1'
echo 'SEQUENCE_IS_CALLED=TRUE'
echo 'SEQUENCE_VALUE_1_CONSUMED=YES'

echo 'PREDICTED_NEXT_SEQUENCE_VALUE=2'
echo 'PREDICTED_NEXT_VALUE_AUTHORITATIVE=NO'

echo 'IDENTITY_GENERATION=ALWAYS'
echo 'CORRECTED_INSERT_REQUIRES_OVERRIDING_SYSTEM_VALUE=YES'

echo 'OLD_B4B_RERUN_ALLOWED=NO'
echo 'SETVAL_BACKWARD_ALLOWED=NO'

echo 'READY_FOR_CORRECTED_MUTATION_DESIGN=YES'
