#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  echo 'ERROR: execute with bash; do not source'
  return 2
fi

set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT=/data/spark/healthcare-data-platform

PARENT=6d8ef90ac50b4ce96cbde16b7b3c0a68a7574d4a

RUN_ID=visit-proc-20261009t192437z-2081886

APP="$ROOT/apps/task003/verify_visit_id_pre_mutation_gate.py"

CANONICAL_CONTRACT="$ROOT/spark/contracts/processed/visit-id-mutation-contract-v1.json"
CANONICAL_META="$ROOT/spark/contracts/processed/visit-business-key-snapshot-v1.json"

RUNTIME_CONTRACT="$ROOT/runtime/reports/task003/step06/visit-id-mutation-contracts/$RUN_ID/contract.json"

SNAPSHOT_DIR="$ROOT/runtime/reports/task003/step06/visit-id-key-snapshots/$RUN_ID"

SNAPSHOT="$SNAPSHOT_DIR/business-keys.tsv"
RUNTIME_META="$SNAPSHOT_DIR/snapshot.json"

B2_REPORT="$ROOT/runtime/reports/task003/step06/visit-id-key-snapshot-build.20261010t134824z-2476691"

B2_RESULT="$B2_REPORT/result.json"
B2_STATE="$B2_REPORT/run-state.json"

REPORT="$ROOT/runtime/reports/task003/step06/pre-mutation-gate"
OUTPUT="$REPORT/run-state.json"

echo '#### TASK003 STEP06B3 PRE-MUTATION GATE VERIFY OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  echo "STEP06B3_VERIFY_EXIT_CODE=$rc"
  echo '#### TASK003 STEP06B3 PRE-MUTATION GATE VERIFY OUTPUT END ####'
  exit "$rc"
}

trap finish EXIT

cd "$ROOT"

mkdir -p "$REPORT"

HEAD="$(git rev-parse HEAD)"

echo "CURRENT_HEAD=$HEAD"
echo "REQUIRED_PARENT=$PARENT"

git merge-base \
  --is-ancestor \
  "$PARENT" \
  "$HEAD" \
  || {
    echo 'ERROR: STEP06A checkpoint is not an ancestor of current HEAD'
    exit 1
  }

echo 'STEP06A_PARENT_ANCESTRY=PASS'

for file in \
  "$APP" \
  "$CANONICAL_CONTRACT" \
  "$CANONICAL_META" \
  "$RUNTIME_CONTRACT" \
  "$SNAPSHOT" \
  "$RUNTIME_META" \
  "$B2_RESULT" \
  "$B2_STATE"
do
  [[ -s "$file" && ! -L "$file" ]] || {
    echo "ERROR: missing or unsafe gate input: $file"
    exit 1
  }
done

python3 "$APP" \
  --canonical-contract "$CANONICAL_CONTRACT" \
  --canonical-snapshot-meta "$CANONICAL_META" \
  --runtime-contract "$RUNTIME_CONTRACT" \
  --snapshot "$SNAPSHOT" \
  --runtime-snapshot-meta "$RUNTIME_META" \
  --b2-result "$B2_RESULT" \
  --b2-state "$B2_STATE" \
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
    == "VISIT_ID_PRE_MUTATION_GATE_FROZEN"
)

assert state["candidate_rows"] == 5799

assert (
    state[
        "candidate_unique_business_keys"
    ]
    == 5799
)

assert (
    state[
        "candidate_business_key_sha256"
    ]
    == "aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e"
)

assert (
    state[
        "advisory_lock_key"
    ]
    == 5947676943154735385
)

assert (
    state[
        "sequence_gap_policy"
    ]
    == "ACCEPT_GAPS_NEVER_REWIND"
)

assert (
    state[
        "predicted_range_authoritative"
    ]
    is False
)

assert state["advisory_lock_acquired"] is False
assert state["nextval_called"] is False
assert state["setval_called"] is False

assert (
    state[
        "visit_id_allocation_started"
    ]
    is False
)

assert state["visit_id_map_mutated"] is False
assert state["sequence_advanced"] is False

assert (
    state[
        "cdm_visit_occurrence_write"
    ]
    is False
)

print(
    "STEP06B3_GATE_STATE=PASS"
)
PY

echo 'STEP06B3_PRE_MUTATION_GATE=PASS'

echo 'CANDIDATE_ROWS=5799'
echo 'CANDIDATE_UNIQUE_BUSINESS_KEYS=5799'

echo 'CANDIDATE_BUSINESS_KEY_SHA256=aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e'

echo 'MUTATION_CONTRACT_SHA256=58cd44b22eaf15674a7277c51c66418c305bd3743b403c7612d458453d87f9f0'

echo 'SNAPSHOT_METADATA_SHA256=21ac6b5af6f74d3b078b4fbf7fb8ce21b5d5d32af1aaccc5e495e595fc90dbaa'

echo 'ADVISORY_LOCK_KEY=5947676943154735385'

echo 'SEQUENCE_GAP_POLICY=ACCEPT_GAPS_NEVER_REWIND'

echo 'PREDICTED_VISIT_ID_RANGE=1..5799'
echo 'PREDICTED_RANGE_AUTHORITATIVE=NO'

echo 'ADVISORY_LOCK_ACQUIRED=NO'
echo 'NEXTVAL_CALLED=NO'
echo 'SETVAL_CALLED=NO'

echo 'VISIT_ID_ALLOCATION_STARTED=NO'
echo 'VISIT_ID_MAP_MUTATED=NO'
echo 'SEQUENCE_ADVANCED=NO'
echo 'CDM_VISIT_OCCURRENCE_WRITE=NO'

echo 'DATABASE_ACCESS=NONE'
echo 'S3_ACCESS=NONE'
echo 'KUBERNETES_ACCESS=NONE'

echo 'READY_FOR_PRE_MUTATION_GIT_CHECKPOINT=YES'
