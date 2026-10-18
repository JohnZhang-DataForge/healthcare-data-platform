#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  echo 'ERROR: execute with bash; do not source'
  return 2
fi

set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT=/data/spark/healthcare-data-platform
WORK="$(mktemp -d /data/spark/temp_shell/task003-06a4-stage.XXXXXX)"

echo '#### TASK003 STEP06A4 PREPARE READONLY PREFLIGHT FREEZE OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT
  rm -rf "$WORK"
  echo "STEP06A4_PREPARE_EXIT_CODE=$rc"
  echo '#### TASK003 STEP06A4 PREPARE READONLY PREFLIGHT FREEZE OUTPUT END ####'
  exit "$rc"
}
trap finish EXIT

mkdir -p \
  "$WORK/apps/task003" \
  "$WORK/spark/contracts/processed" \
  "$WORK/tests/task003" \
  "$WORK/scripts/task003" \
  "$WORK/docs/task003"

cat > "$WORK/spark/contracts/processed/visit-id-readonly-preflight-v1.json" <<'JSON_EOF'
{
  "contract_version": "v1",
  "entity": "visit_occurrence",
  "git_checkpoint": "4e1a7a8d3870141ec0f97ad515e8a0d6f13802d4",
  "run_id": "visit-proc-20261009t192437z-2081886",
  "task": "TASK-003",
  "step": "STEP-06A",
  "candidate": {
    "rows": 5799,
    "unique_business_keys": 5799,
    "referenced_persons": 113,
    "business_key": [
      "source_system",
      "source_encounter_id"
    ],
    "business_key_sha256": "aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e"
  },
  "database_baseline": {
    "visit_map_rows": 0,
    "cdm_visit_rows": 0,
    "person_map_rows": 113
  },
  "sequence": {
    "name": "etl.visit_occurrence_id_map_visit_occurrence_id_seq",
    "last_value": 1,
    "is_called": false,
    "column_default": null,
    "pg_get_serial_sequence_binding": "etl.visit_occurrence_id_map_visit_occurrence_id_seq",
    "automatic_default_nextval": false,
    "explicit_allocation_required": true
  },
  "reconciliation": {
    "existing_candidate_mappings": 0,
    "new_candidate_mappings": 5799,
    "candidate_only_keys": 5799,
    "map_only_synthea_keys": 0
  },
  "fingerprints": {
    "allocation_plan_sha256": "28cf06fecb744c8da477221abde37e7afd72ba7d974ef2c93f847a3d79b63c93",
    "reconciliation_result_sha256": "fb2905064173c564a8074b7f946c976b8d2ea1e0165ce7f2f3f2b3feb258eb31"
  },
  "safety": {
    "s3_read_only": true,
    "database_read_only": true,
    "nextval_called": false,
    "setval_called": false,
    "visit_id_allocation_started": false,
    "visit_id_map_mutated": false,
    "sequence_advanced": false,
    "cdm_visit_occurrence_write": false
  }
}
JSON_EOF

cat > "$WORK/apps/task003/verify_visit_id_readonly_preflight.py" <<'PY_EOF'
#!/usr/bin/env python3

import argparse
import hashlib
import json
from pathlib import Path


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_bytes())


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def validate(
    contract_path,
    baseline_path,
    plan_path,
    reconciliation_state_path,
    reconciliation_result_path,
):
    contract = load(contract_path)
    baseline = load(baseline_path)
    plan = load(plan_path)
    recon_state = load(reconciliation_state_path)
    recon_result = load(reconciliation_result_path)

    expected_git = contract["git_checkpoint"]
    run_id = contract["run_id"]

    require(contract["task"] == "TASK-003", "contract task")
    require(contract["step"] == "STEP-06A", "contract step")

    # STEP06A1
    require(baseline["task"] == "TASK-003", "A1 task")
    require(baseline["step"] == "STEP-06A1", "A1 step")
    require(
        baseline["status"] == "VISIT_ID_ALLOCATION_BASELINE_DISCOVERED",
        "A1 status",
    )
    require(baseline["git_checkpoint"] == expected_git, "A1 git checkpoint")
    require(baseline["processed_publication_complete"] is True, "A1 processed complete")
    require(baseline["processed_prefix_frozen"] is True, "A1 processed frozen")
    require(baseline["processed_reservation_present"] is False, "A1 reservation")
    require(baseline["transaction_read_only"] is True, "A1 read only")
    require(baseline["visit_id_allocation_started"] is False, "A1 allocation")
    require(baseline["visit_id_map_mutated"] is False, "A1 map mutation")
    require(baseline["sequence_advanced"] is False, "A1 sequence")
    require(baseline["cdm_visit_occurrence_write"] is False, "A1 CDM write")
    require(baseline["s3_mutation"] is False, "A1 S3")

    # STEP06A2
    plan_sha = sha256_file(plan_path)
    require(
        plan_sha == contract["fingerprints"]["allocation_plan_sha256"],
        "A2 plan SHA",
    )
    require(plan["task"] == "TASK-003", "A2 task")
    require(plan["step"] == "STEP-06A2", "A2 step")
    require(plan["status"] == "VISIT_ID_ALLOCATION_PLAN_READY", "A2 status")
    require(plan["run_id"] == run_id, "A2 run")
    require(plan["git_checkpoint"] == expected_git, "A2 git")

    candidate = plan["source_candidate"]
    expected_candidate = contract["candidate"]

    require(candidate["rows"] == expected_candidate["rows"], "candidate rows")
    require(
        candidate["unique_business_keys"]
        == expected_candidate["unique_business_keys"],
        "candidate keys",
    )
    require(
        candidate["referenced_persons"]
        == expected_candidate["referenced_persons"],
        "candidate persons",
    )
    require(candidate["frozen"] is True, "candidate frozen")

    db = plan["database_snapshot"]
    expected_db = contract["database_baseline"]

    require(db["visit_map_rows"] == expected_db["visit_map_rows"], "map rows")
    require(db["cdm_visit_rows"] == expected_db["cdm_visit_rows"], "cdm rows")
    require(db["person_map_rows"] == expected_db["person_map_rows"], "person rows")

    seq = plan["sequence"]
    expected_seq = contract["sequence"]

    require(seq["name"] == expected_seq["name"], "sequence name")
    require(seq["last_value_direct"] == expected_seq["last_value"], "sequence value")
    require(seq["is_called"] == expected_seq["is_called"], "sequence is_called")
    require(
        seq["pg_get_serial_sequence_binding"]
        == expected_seq["pg_get_serial_sequence_binding"],
        "sequence binding",
    )
    require(seq["column_default"] is None, "sequence column default")
    require(seq["automatic_default_nextval"] is False, "automatic nextval")
    require(seq["explicit_allocation_required"] is True, "explicit allocation")

    preview = plan["allocation_preview"]

    require(preview["existing_candidate_mappings"] == 0, "A2 existing")
    require(preview["new_candidate_mappings"] == 5799, "A2 new")
    require(preview["predicted_first_new_id"] == 1, "A2 first ID")
    require(preview["predicted_last_new_id"] == 5799, "A2 last ID")
    require(preview["prediction_is_non_authoritative"] is True, "A2 authority")

    plan_safety = plan["safety"]

    require(plan_safety["transaction_read_only"] is True, "A2 read only")
    require(plan_safety["nextval_called"] is False, "A2 nextval")
    require(plan_safety["sequence_advanced"] is False, "A2 sequence advance")
    require(plan_safety["visit_id_map_mutated"] is False, "A2 map mutation")
    require(plan_safety["cdm_visit_occurrence_write"] is False, "A2 CDM write")
    require(plan_safety["s3_mutation"] is False, "A2 S3 mutation")

    # STEP06A3
    result_sha = sha256_file(reconciliation_result_path)

    require(
        result_sha == contract["fingerprints"]["reconciliation_result_sha256"],
        "A3 result SHA",
    )
    require(recon_state["task"] == "TASK-003", "A3 state task")
    require(recon_state["step"] == "STEP-06A3", "A3 state step")
    require(
        recon_state["status"]
        == "VISIT_ID_BUSINESS_KEY_RECONCILIATION_VERIFIED",
        "A3 state status",
    )
    require(recon_state["run_id"] == run_id, "A3 state run")
    require(recon_state["git_checkpoint"] == expected_git, "A3 state git")
    require(recon_state["allocation_plan_sha256"] == plan_sha, "A3 plan lineage")
    require(
        recon_state["reconciliation_result_sha256"] == result_sha,
        "A3 result lineage",
    )

    require(
        recon_state["candidate_business_key_sha256"]
        == expected_candidate["business_key_sha256"],
        "A3 business key fingerprint",
    )
    require(recon_state["candidate_rows"] == 5799, "A3 rows")
    require(recon_state["candidate_unique_business_keys"] == 5799, "A3 keys")
    require(recon_state["existing_candidate_mappings"] == 0, "A3 existing")
    require(recon_state["new_candidate_mappings"] == 5799, "A3 new")
    require(recon_state["candidate_only_keys"] == 5799, "A3 candidate only")
    require(recon_state["map_only_synthea_keys"] == 0, "A3 map only")

    require(recon_state["s3_read_only"] is True, "A3 S3 read only")
    require(recon_state["database_read_only"] is True, "A3 DB read only")
    require(recon_state["visit_id_allocation_started"] is False, "A3 allocation")
    require(recon_state["visit_id_map_mutated"] is False, "A3 map mutation")
    require(recon_state["sequence_advanced"] is False, "A3 sequence")
    require(recon_state["cdm_visit_occurrence_write"] is False, "A3 CDM")

    require(recon_result["task"] == "TASK-003", "A3 result task")
    require(recon_result["step"] == "STEP-06A3", "A3 result step")
    require(
        recon_result["status"]
        == "VISIT_ID_BUSINESS_KEY_RECONCILIATION_PASS",
        "A3 result status",
    )

    result_candidate = recon_result["candidate"]
    require(result_candidate["rows"] == 5799, "result rows")
    require(result_candidate["unique_business_keys"] == 5799, "result keys")
    require(result_candidate["referenced_persons"] == 113, "result persons")
    require(result_candidate["duplicate_business_key_groups"] == 0, "candidate dupes")
    require(
        result_candidate["business_key_sha256"]
        == expected_candidate["business_key_sha256"],
        "result business key fingerprint",
    )

    db_map = recon_result["database_map"]
    require(db_map["total_rows"] == 0, "result DB map rows")
    require(db_map["synthea_rows"] == 0, "result synthea map rows")
    require(db_map["duplicate_business_key_groups"] == 0, "result map key dupes")
    require(db_map["duplicate_visit_id_groups"] == 0, "result map ID dupes")

    recon = recon_result["reconciliation"]
    require(recon["rows"] == 5799, "reconciliation rows")
    require(recon["existing_mappings"] == 0, "reconciliation existing")
    require(recon["new_mappings"] == 5799, "reconciliation new")
    require(recon["candidate_only_keys"] == 5799, "reconciliation candidate only")
    require(recon["map_only_synthea_keys"] == 0, "reconciliation map only")

    safety = recon_result["safety"]
    require(safety["s3_read_only"] is True, "result S3 read only")
    require(safety["jdbc_read_only"] is True, "result JDBC read only")
    require(safety["nextval_called"] is False, "result nextval")
    require(safety["setval_called"] is False, "result setval")
    require(safety["sequence_advanced"] is False, "result sequence")
    require(safety["visit_id_map_write"] is False, "result map write")
    require(safety["cdm_visit_occurrence_write"] is False, "result CDM write")

    return {
        "task": "TASK-003",
        "step": "STEP-06A4",
        "status": "VISIT_ID_READONLY_PREFLIGHT_FROZEN",
        "run_id": run_id,
        "git_checkpoint": expected_git,
        "candidate_business_key_sha256": expected_candidate["business_key_sha256"],
        "allocation_plan_sha256": plan_sha,
        "reconciliation_result_sha256": result_sha,
        "candidate_rows": 5799,
        "candidate_unique_business_keys": 5799,
        "existing_candidate_mappings": 0,
        "new_candidate_mappings": 5799,
        "predicted_visit_id_range": [1, 5799],
        "predicted_range_authoritative": False,
        "sequence_last_value": 1,
        "sequence_is_called": False,
        "visit_id_allocation_started": False,
        "visit_id_map_mutated": False,
        "sequence_advanced": False,
        "cdm_visit_occurrence_write": False,
        "s3_mutation": False
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--baseline-state", required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--reconciliation-state", required=True)
    parser.add_argument("--reconciliation-result", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = validate(
        args.contract,
        args.baseline_state,
        args.plan,
        args.reconciliation_state,
        args.reconciliation_result,
    )

    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )

    print("VISIT_ID_READONLY_PREFLIGHT_FREEZE=PASS")
    print(
        "CANDIDATE_BUSINESS_KEY_SHA256="
        + result["candidate_business_key_sha256"]
    )
    print(
        "ALLOCATION_PLAN_SHA256="
        + result["allocation_plan_sha256"]
    )
    print(
        "RECONCILIATION_RESULT_SHA256="
        + result["reconciliation_result_sha256"]
    )


if __name__ == "__main__":
    main()
PY_EOF

cat > "$WORK/tests/task003/test_visit_id_readonly_preflight.py" <<'PYTEST_EOF'
#!/usr/bin/env python3

import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "apps/task003/verify_visit_id_readonly_preflight.py"


spec = importlib.util.spec_from_file_location(
    "verify_visit_id_readonly_preflight",
    MODULE,
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class VisitIDReadonlyPreflightTests(unittest.TestCase):

    def test_sha256_file(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "x"
            path.write_bytes(b"abc")

            self.assertEqual(
                mod.sha256_file(path),
                hashlib.sha256(b"abc").hexdigest(),
            )

    def test_require(self):
        mod.require(True, "ok")

        with self.assertRaises(RuntimeError):
            mod.require(False, "expected")


if __name__ == "__main__":
    unittest.main()
PYTEST_EOF

cat > "$WORK/scripts/task003/06a4-verify-visit-id-readonly-preflight.sh" <<'RUNNER_EOF'
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
RUNNER_EOF

cat > "$WORK/docs/task003/TASK003-STEP06A-ReadOnly-Preflight.md" <<'DOC_EOF'
# TASK-003 STEP06A — Visit ID Read-Only Preflight

## Status

STEP06A is complete and frozen as a read-only pre-mutation phase.

No Visit ID has been allocated yet.

## Frozen Candidate

- Run: `visit-proc-20261009t192437z-2081886`
- Rows: `5799`
- Unique business keys: `5799`
- Referenced Persons: `113`
- Business key: `(source_system, source_encounter_id)`
- Business-key SHA256:
  `aa5be446a3fe0ce4688594db45db19a33ad9bb182cca61e6a19cdb69ff74f72e`

## PostgreSQL Baseline

Before allocation:

- `etl.visit_occurrence_id_map`: `0`
- `cdm.visit_occurrence`: `0`
- `etl.person_id_map`: `113`

Sequence:

`etl.visit_occurrence_id_map_visit_occurrence_id_seq`

Observed state:

- `last_value = 1`
- `is_called = false`
- `pg_get_serial_sequence()` binding exists
- column default is `NONE`
- automatic `DEFAULT nextval(...)` is not configured
- explicit controlled allocation is required

## STEP06A2 Allocation Preview

Current snapshot predicts:

- existing mappings: `0`
- new mappings: `5799`
- predicted ID range: `1..5799`

The predicted range is **not authoritative** until mutation-time revalidation and serialization.

Allocation Plan SHA256:

`28cf06fecb744c8da477221abde37e7afd72ba7d974ef2c93f847a3d79b63c93`

## STEP06A3 Exact Business-Key Reconciliation

Real Spark/JDBC reconciliation proved:

- Candidate keys: `5799`
- existing Candidate mappings: `0`
- new Candidate mappings: `5799`
- Candidate-only keys: `5799`
- DB-only Synthea keys: `0`
- duplicate Candidate business-key groups: `0`
- duplicate DB business-key groups: `0`
- duplicate Visit ID groups: `0`

Reconciliation Result SHA256:

`fb2905064173c564a8074b7f946c976b8d2ea1e0165ce7f2f3f2b3feb258eb31`

## Safety State

At STEP06A close:

- S3 access: read only
- PostgreSQL access: read only
- `nextval()` called: NO
- `setval()` called: NO
- Visit ID map mutated: NO
- sequence advanced: NO
- `cdm.visit_occurrence` written: NO

## Next Phase

Before STEP06B performs the first database mutation:

1. Commit this STEP06A freeze source as a Git checkpoint.
2. Revalidate current map/CDM/sequence state at mutation time.
3. Acquire a PostgreSQL serialization/advisory lock.
4. Reconcile the frozen Candidate business-key fingerprint again.
5. Allocate stable IDs transactionally.
6. Verify map coverage and sequence state independently.
7. Keep `cdm.visit_occurrence` loading as a later, separate mutation.
DOC_EOF

echo '=== 1. Validate staged canonical source ==='

python3 -m py_compile \
  "$WORK/apps/task003/verify_visit_id_readonly_preflight.py" \
  "$WORK/tests/task003/test_visit_id_readonly_preflight.py"

bash -n \
  "$WORK/scripts/task003/06a4-verify-visit-id-readonly-preflight.sh"

python3 -m json.tool \
  "$WORK/spark/contracts/processed/visit-id-readonly-preflight-v1.json" \
  >/dev/null

echo 'STAGED_SOURCE_VALIDATION=PASS'

echo '=== 2. Install conflict-safe canonical files ==='

install_one() {
  rel="$1"
  src="$WORK/$rel"
  dst="$ROOT/$rel"

  mkdir -p "$(dirname "$dst")"

  if [[ -e "$dst" ]]; then
    if cmp -s "$src" "$dst"; then
      echo "UNCHANGED=$rel"
      return
    fi

    echo "ERROR: canonical source conflict: $rel"
    exit 1
  fi

  install -m 0644 "$src" "$dst"

  case "$dst" in
    *.sh|*.py)
      chmod 0755 "$dst"
      ;;
  esac

  echo "INSTALLED=$rel"
}

install_one apps/task003/verify_visit_id_readonly_preflight.py
install_one spark/contracts/processed/visit-id-readonly-preflight-v1.json
install_one tests/task003/test_visit_id_readonly_preflight.py
install_one scripts/task003/06a4-verify-visit-id-readonly-preflight.sh
install_one docs/task003/TASK003-STEP06A-ReadOnly-Preflight.md

echo '=== 3. Run unit tests ==='

cd "$ROOT"

python3 -m unittest \
  tests.task003.test_visit_id_readonly_preflight \
  -v

echo 'UNIT_TESTS=PASS'

echo '=== 4. Run canonical evidence verifier ==='

bash "$ROOT/scripts/task003/06a4-verify-visit-id-readonly-preflight.sh"

echo '=== 5. Final generator verdict ==='

echo 'STEP06A4_CANONICAL_SOURCE_PREPARED=PASS'
echo 'CANONICAL_SOURCE_CONFLICT=NO'
echo 'DATABASE_MUTATION=NO'
echo 'S3_MUTATION=NO'
echo 'GIT_COMMIT=NO'
