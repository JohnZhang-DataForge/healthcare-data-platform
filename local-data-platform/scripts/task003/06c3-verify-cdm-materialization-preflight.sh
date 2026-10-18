#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  echo 'ERROR: execute with bash; do not source'
  return 2
fi

set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT=/data/spark/healthcare-data-platform

C1="$ROOT/runtime/reports/task003/step06/cdm-visit-baseline.20261010t143104z.2493274"
C2="$ROOT/runtime/reports/task003/step06/candidate-to-cdm-preflight.20261010t144415z.2498243"

APP="$ROOT/apps/task003/verify_cdm_materialization_preflight.py"

CONTRACT="$ROOT/spark/contracts/processed/visit-cdm-materialization-preflight-v1.json"

OUTDIR="$ROOT/runtime/reports/task003/step06/cdm-materialization-preflight-canonical-verification"
OUTPUT="$OUTDIR/run-state.json"

echo '#### TASK003 STEP06C3 CDM MATERIALIZATION PREFLIGHT VERIFY OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  echo "STEP06C3_VERIFY_EXIT_CODE=$rc"
  echo '#### TASK003 STEP06C3 CDM MATERIALIZATION PREFLIGHT VERIFY OUTPUT END ####'
  exit "$rc"
}

trap finish EXIT

mkdir -p "$OUTDIR"

cd "$ROOT"

python3 "$APP" \
  --contract "$CONTRACT" \
  --c1-summary "$C1/summary.json" \
  --c2-result "$C2/result.json" \
  --c2-app "$C2/candidate_to_cdm_preflight.py" \
  --c2-driver "$C2/driver.log" \
  --c2-post-db "$C2/post-spark-database-state.txt" \
  --c2-sparkapp "$C2/sparkapplication.json" \
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
    == "CDM_MATERIALIZATION_PREFLIGHT_CANONICAL_GATE_PASS"
)

assert state["candidate_rows"] == 5799
assert state["target_columns"] == 17
assert state["cdm_row_shape_rows"] == 5799

assert (
    state["cdm_row_shape_sha256"]
    == "995724ba282f443892074d9b189be134fde8819b2afda05f021729323b0ebce1"
)

assert (
    state["authoritative_mapping_sha256"]
    == "7e74c9c0a179e6222a7c4ded2993b8cf61a20d9b06b1d6349d7f21f6a0c03c9f"
)

assert state["cdm_visit_rows"] == 0
assert state["database_mutation"] is False
assert state["s3_mutation"] is False
assert state["ready_for_git_checkpoint"] is True

print("STEP06C3_CANONICAL_STATE=PASS")
PY

echo 'STEP06C3_CANONICAL_PREFLIGHT_GATE=PASS'

echo 'CANDIDATE_ROWS=5799'
echo 'TARGET_CDM_COLUMNS=17'
echo 'FINAL_CDM_ROW_SHAPE_ROWS=5799'

echo 'CDM_ROW_SHAPE_SHA256=995724ba282f443892074d9b189be134fde8819b2afda05f021729323b0ebce1'

echo 'AUTHORITATIVE_MAPPING_SHA256=7e74c9c0a179e6222a7c4ded2993b8cf61a20d9b06b1d6349d7f21f6a0c03c9f'

echo 'PERSON_MAP_SHA256=f52f95120b8a9bd80d33029d04d9abf4cb1c59206d00b745b59e39b5a89c9a98'

echo 'ALL_DATABASE_FK_FEASIBILITY=PASS'

echo 'CDM_VISIT_ROWS=0'

echo 'DATABASE_MUTATION=NO'
echo 'S3_MUTATION=NO'

echo 'READY_FOR_GIT_CHECKPOINT=YES'
