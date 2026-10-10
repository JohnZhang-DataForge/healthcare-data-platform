#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  echo 'ERROR: execute with bash; do not source'
  return 2
fi

set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT=/data/spark/healthcare-data-platform

REPORT="$ROOT/runtime/reports/task003/step06/visit-id-allocation-corrected.20261010t142456z.2490800"

APP="$ROOT/apps/task003/verify_committed_visit_id_mapping.py"

CONTRACT="$ROOT/spark/contracts/processed/visit-id-allocation-result-v1.json"

STATE="$REPORT/run-state.json"
POST_VERIFY="$REPORT/post-commit-verification.json"
TX="$REPORT/transaction-summary.json"
SQL="$REPORT/allocation-corrected.sql"
PSQL_OUTPUT="$REPORT/psql-output.txt"
MAP_READBACK="$REPORT/post-commit-map.tsv"

OUTDIR="$ROOT/runtime/reports/task003/step06/committed-visit-id-mapping-canonical-verification"
OUTPUT="$OUTDIR/run-state.json"

echo '#### TASK003 STEP06B4C COMMITTED MAPPING VERIFY OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  echo "STEP06B4C_VERIFY_EXIT_CODE=$rc"
  echo '#### TASK003 STEP06B4C COMMITTED MAPPING VERIFY OUTPUT END ####'
  exit "$rc"
}

trap finish EXIT

mkdir -p "$OUTDIR"

cd "$ROOT"

for file in \
  "$APP" \
  "$CONTRACT" \
  "$STATE" \
  "$POST_VERIFY" \
  "$TX" \
  "$SQL" \
  "$PSQL_OUTPUT" \
  "$MAP_READBACK"
do
  [[ -s "$file" && ! -L "$file" ]] || {
    echo "ERROR: missing committed-mapping gate input: $file"
    exit 1
  }
done

python3 "$APP" \
  --contract "$CONTRACT" \
  --state "$STATE" \
  --post-verify "$POST_VERIFY" \
  --transaction-summary "$TX" \
  --sql "$SQL" \
  --psql-output "$PSQL_OUTPUT" \
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
    == "COMMITTED_VISIT_ID_MAPPING_CANONICAL_GATE_PASS"
)

assert state["committed_map_rows"] == 5799
assert state["candidate_coverage"] == 5799

assert (
    state["unique_visit_occurrence_ids"]
    == 5799
)

assert state["min_visit_occurrence_id"] == 2
assert state["max_visit_occurrence_id"] == 5800

assert (
    state["mapping_sha256"]
    == "7e74c9c0a179e6222a7c4ded2993b8cf61a20d9b06b1d6349d7f21f6a0c03c9f"
)

assert state["sequence_last_value"] == 5800
assert state["sequence_is_called"] is True

assert (
    state["sequence_value_1_consumed_gap"]
    is True
)

assert state["cdm_visit_rows"] == 0

assert (
    state["cdm_visit_occurrence_write"]
    is False
)

assert state["ready_for_git_checkpoint"] is True

print("STEP06B4C_CANONICAL_STATE=PASS")
PY

echo 'STEP06B4C_COMMITTED_MAPPING_CANONICAL_GATE=PASS'

echo 'COMMITTED_VISIT_MAP_ROWS=5799'
echo 'COMMITTED_CANDIDATE_COVERAGE=5799'
echo 'COMMITTED_UNIQUE_VISIT_IDS=5799'

echo 'COMMITTED_VISIT_ID_RANGE=2..5800'

echo 'AUTHORITATIVE_MAPPING_SHA256=7e74c9c0a179e6222a7c4ded2993b8cf61a20d9b06b1d6349d7f21f6a0c03c9f'

echo 'SEQUENCE_LAST_VALUE=5800'
echo 'SEQUENCE_IS_CALLED=TRUE'
echo 'VISIT_ID_1_GAP_PRESERVED=YES'

echo 'CDM_VISIT_ROWS=0'
echo 'CDM_VISIT_OCCURRENCE_WRITE=NO'

echo 'READY_FOR_GIT_CHECKPOINT=YES'
