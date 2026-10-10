#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  echo 'ERROR: execute with bash; do not source'
  return 2
fi

set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT=/data/spark/healthcare-data-platform

CONTRACT="$ROOT/spark/contracts/processed/visit-id-readonly-preflight-v1.json"
APP="$ROOT/apps/task003/verify_visit_id_readonly_preflight.py"

BASELINE="$ROOT/runtime/reports/task003/step06/visit-id-baseline.20261009T234622Z.2178592/run-state.json"

PLAN="$ROOT/runtime/reports/task003/step06/visit-id-allocation-plans/visit-proc-20261009t192437z-2081886/plan.json"

A3="$ROOT/runtime/reports/task003/step06/visit-id-reconciliation.20261010t004249z-2195105"

A3_STATE="$A3/run-state.json"
A3_RESULT="$A3/reconciliation-result.json"

REPORT="$ROOT/runtime/reports/task003/step06/readonly-preflight-freeze"
OUTPUT="$REPORT/run-state.json"

EXPECTED_HEAD=4e1a7a8d3870141ec0f97ad515e8a0d6f13802d4

echo '#### TASK003 STEP06A4 READONLY PREFLIGHT FREEZE VERIFY OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT
  echo "STEP06A4_VERIFY_EXIT_CODE=$rc"
  echo '#### TASK003 STEP06A4 READONLY PREFLIGHT FREEZE VERIFY OUTPUT END ####'
  exit "$rc"
}
trap finish EXIT

cd "$ROOT"
mkdir -p "$REPORT"

HEAD="$(git rev-parse HEAD)"

echo "CURRENT_HEAD=$HEAD"
echo "EXPECTED_HEAD=$EXPECTED_HEAD"

[[ "$HEAD" == "$EXPECTED_HEAD" ]] || {
  echo 'ERROR: Git HEAD drifted before STEP06 mutation checkpoint'
  exit 1
}

for file in \
  "$CONTRACT" \
  "$APP" \
  "$BASELINE" \
  "$PLAN" \
  "$A3_STATE" \
  "$A3_RESULT"
do
  [[ -s "$file" && ! -L "$file" ]] || {
    echo "ERROR: missing or unsafe evidence/source: $file"
    exit 1
  }
done

python3 "$APP" \
  --contract "$CONTRACT" \
  --baseline-state "$BASELINE" \
  --plan "$PLAN" \
  --reconciliation-state "$A3_STATE" \
  --reconciliation-result "$A3_RESULT" \
  --output "$OUTPUT"

python3 - "$OUTPUT" <<'PY'
import json
import sys
from pathlib import Path

state = json.loads(Path(sys.argv[1]).read_bytes())

assert state["status"] == "VISIT_ID_READONLY_PREFLIGHT_FROZEN"
assert state["candidate_rows"] == 5799
assert state["candidate_unique_business_keys"] == 5799
assert state["existing_candidate_mappings"] == 0
assert state["new_candidate_mappings"] == 5799
assert state["predicted_visit_id_range"] == [1, 5799]
assert state["predicted_range_authoritative"] is False

assert state["candidate_business_key_sha256"] == (
    "aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e"
)

assert state["visit_id_allocation_started"] is False
assert state["visit_id_map_mutated"] is False
assert state["sequence_advanced"] is False
assert state["cdm_visit_occurrence_write"] is False
assert state["s3_mutation"] is False

print("STEP06A_READONLY_PREFLIGHT_STATE=PASS")
PY

echo 'STEP06A4_READONLY_PREFLIGHT_FREEZE=PASS'
echo 'STEP06A_READONLY_PHASE_COMPLETE=YES'
echo 'CANDIDATE_ROWS=5799'
echo 'CANDIDATE_UNIQUE_BUSINESS_KEYS=5799'
echo 'EXISTING_CANDIDATE_MAPPINGS=0'
echo 'NEW_CANDIDATE_MAPPINGS=5799'
echo 'CANDIDATE_BUSINESS_KEY_SHA256=aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e'
echo 'PREDICTED_VISIT_ID_RANGE=1..5799'
echo 'PREDICTED_RANGE_AUTHORITATIVE=NO'
echo 'VISIT_ID_ALLOCATION_STARTED=NO'
echo 'VISIT_ID_MAP_MUTATED=NO'
echo 'SEQUENCE_ADVANCED=NO'
echo 'CDM_VISIT_OCCURRENCE_WRITE=NO'
echo 'S3_MUTATION=NO'
echo 'DATABASE_MUTATION=NO'
echo 'READY_FOR_PRE_MUTATION_GIT_CHECKPOINT=YES'
