#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1 GIT_PAGER=cat
ROOT="${HEALTHCARE_PROJECT_ROOT:-/data/spark/healthcare-data-platform}"
STAGE=''

echo '#### TASK003 STEP05G1B VALIDATOR INSTALL OUTPUT BEGIN ####'
finish() {
  rc=$?
  trap - EXIT
  [[ -z "$STAGE" ]] || rm -rf -- "$STAGE"
  echo "INSTALL_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G1B VALIDATOR INSTALL OUTPUT END ####'
  exit "$rc"
}
trap finish EXIT

cd "$ROOT"
for rel in \
  apps/task003/plan_visit_processed.py \
  scripts/task003/05g1-plan-visit-processed.sh \
  tests/task003/test_visit_processed_plan.py \
  spark/contracts/processed/visit-candidate-publication-v1.json
do
  [[ -s "$rel" && ! -L "$rel" ]] || {
    echo "ERROR: missing dependency $rel"
    exit 1
  }
done

STAGE=$(mktemp -d /data/spark/temp_shell/05g1b-stage.XXXXXXXX)
mkdir -p "$STAGE/apps/task003" "$STAGE/tests/task003" \
         "$STAGE/scripts/task003" "$STAGE/spark/contracts/processed"

cat > "$STAGE/apps/task003/verify_visit_processed_plan.py" <<'PY_VALIDATOR'
"""Verify an immutable STEP05G1 plan against exact STEP05F2 evidence."""
import argparse
import hashlib
import json
from pathlib import Path

from plan_visit_processed import build_plan


def verify_plan_bytes(plan_bytes, f2_bytes, policy, run_id):
    f2 = json.loads(f2_bytes)
    expected = build_plan(
        f2, policy, run_id, hashlib.sha256(f2_bytes).hexdigest()
    )
    expected_bytes = (
        json.dumps(expected, indent=2, sort_keys=True, ensure_ascii=False)
        + '\n'
    ).encode('utf-8')
    if plan_bytes != expected_bytes:
        raise ValueError(
            'CONFLICT: plan differs from pinned STEP05F2 evidence'
        )
    return expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--f2-state', type=Path, required=True)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()

    policy = json.loads((
        args.root
        / 'spark/contracts/processed/visit-candidate-publication-v1.json'
    ).read_bytes())

    plan_bytes = args.plan.read_bytes()
    result = verify_plan_bytes(
        plan_bytes, args.f2_state.read_bytes(), policy, args.run_id
    )

    print('PLAN_EVIDENCE_RECONCILIATION=PASS')
    print('EXPECTED_ROWS=' + str(result['expected_rows']))
    print('EXPECTED_PERSONS=' + str(result['expected_persons']))
    print('PLAN_STATUS=' + result['status'])
    print('PROCESSED_RUN_ID=' + result['run_id'])
    print('PLAN_SHA256=' + hashlib.sha256(plan_bytes).hexdigest())
    print('CANDIDATE_PERSISTED=NO')
    print('CANDIDATE_PUBLISHED=NO')
    print('VISIT_ID_ALLOCATED=NO')


if __name__ == '__main__':
    main()
PY_VALIDATOR

cat > "$STAGE/tests/task003/test_visit_processed_plan_validation.py" <<'PY_TEST'
"""STEP05G1 immutable evidence validation, including negative cases."""
import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'apps/task003'))

from plan_visit_processed import build_plan
from verify_visit_processed_plan import verify_plan_bytes
from test_visit_processed_plan import fixture


class TestPlanEvidence(unittest.TestCase):

    def setUp(self):
        self.f2 = fixture()
        self.raw_f2 = json.dumps(self.f2).encode()
        self.policy = json.loads((
            ROOT
            / 'spark/contracts/processed/visit-candidate-publication-v1.json'
        ).read_text())

        self.run_id = 'visit-proc-fixture'
        self.plan = build_plan(
            self.f2,
            self.policy,
            self.run_id,
            hashlib.sha256(self.raw_f2).hexdigest(),
        )
        self.plan_bytes = (
            json.dumps(
                self.plan,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            ) + '\n'
        ).encode()

    def verify(self, plan=None, f2=None, policy=None, run_id=None):
        return verify_plan_bytes(
            self.plan_bytes if plan is None else plan,
            self.raw_f2 if f2 is None else f2,
            self.policy if policy is None else policy,
            self.run_id if run_id is None else run_id,
        )

    def test_valid(self):
        self.assertEqual(self.verify(), self.plan)

    def test_tampered_plan_rejected(self):
        modified = copy.deepcopy(self.plan)
        modified['published'] = True
        raw = (
            json.dumps(modified, indent=2, sort_keys=True) + '\n'
        ).encode()

        with self.assertRaisesRegex(ValueError, 'CONFLICT'):
            self.verify(plan=raw)

    def test_f2_evidence_drift_rejected(self):
        changed_f2 = json.dumps(self.f2, indent=2).encode()

        with self.assertRaisesRegex(ValueError, 'CONFLICT'):
            self.verify(f2=changed_f2)

    def test_wrong_run_rejected(self):
        with self.assertRaisesRegex(ValueError, 'CONFLICT'):
            self.verify(run_id='other-run')

    def test_policy_drift_rejected(self):
        changed = copy.deepcopy(self.policy)
        changed['same_run_conflict'] = 'OVERWRITE'

        with self.assertRaises(ValueError):
            self.verify(policy=changed)


if __name__ == '__main__':
    unittest.main()
PY_TEST

cat > "$STAGE/scripts/task003/05g1-verify-visit-processed-plan.sh" <<'SH_RUNNER'
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
SH_RUNNER

# Stage existing dependencies for isolated tests.
cp "$ROOT/apps/task003/plan_visit_processed.py" \
   "$STAGE/apps/task003/plan_visit_processed.py"

cp "$ROOT/tests/task003/test_visit_processed_plan.py" \
   "$STAGE/tests/task003/test_visit_processed_plan.py"

cp "$ROOT/spark/contracts/processed/visit-candidate-publication-v1.json" \
   "$STAGE/spark/contracts/processed/visit-candidate-publication-v1.json"

echo '=== 1. Source syntax ==='

python3 - "$STAGE" <<'PY_SYNTAX'
import ast
import sys
from pathlib import Path

p = Path(sys.argv[1])

for f in (
    'apps/task003/verify_visit_processed_plan.py',
    'tests/task003/test_visit_processed_plan_validation.py',
):
    ast.parse((p / f).read_text(), filename=f)

print('PYTHON_SYNTAX=PASS')
PY_SYNTAX

bash -n "$STAGE/scripts/task003/05g1-verify-visit-processed-plan.sh"

echo 'SHELL_SYNTAX=PASS'

echo '=== 2. Positive and negative tests ==='

python3 -m unittest discover \
  -s "$STAGE/tests/task003" \
  -p 'test_visit_processed_plan_validation.py' -q

echo 'NEGATIVE_AND_POSITIVE_TESTS=PASS'

echo '=== 3. Canonical source conflict check ==='

FILES=(
  apps/task003/verify_visit_processed_plan.py
  tests/task003/test_visit_processed_plan_validation.py
  scripts/task003/05g1-verify-visit-processed-plan.sh
)

GEN=scripts/task003/05g1-prepare-visit-processed-plan-validation.sh

for rel in "${FILES[@]}"; do
  if [[ -L "$ROOT/$rel" ]] || {
    [[ -e "$ROOT/$rel" ]] &&
    ! cmp -s "$STAGE/$rel" "$ROOT/$rel"
  }; then
    echo "ERROR: canonical source conflict: $rel"
    exit 1
  fi
done

if [[ -L "$ROOT/$GEN" ]] || {
  [[ -e "$ROOT/$GEN" ]] &&
  ! cmp -s "${BASH_SOURCE[0]}" "$ROOT/$GEN"
}; then
  echo "ERROR: canonical generator conflict: $GEN"
  exit 1
fi

echo '=== 4. Install canonical source ==='

for rel in "${FILES[@]}"; do
  mkdir -p "$(dirname "$ROOT/$rel")"
  mode=644
  [[ "$rel" != *.sh ]] || mode=755

  install -m "$mode" "$STAGE/$rel" "$ROOT/$rel"
  echo "CANONICAL_SOURCE_READY=$rel"
done

if [[ "${BASH_SOURCE[0]}" -ef "$ROOT/$GEN" ]]; then
  echo "CANONICAL_GENERATOR_REUSED=$GEN"
else
  install -m 755 "${BASH_SOURCE[0]}" "$ROOT/$GEN"
  echo "CANONICAL_GENERATOR_READY=$GEN"
fi

echo 'STEP05G1_VALIDATOR_SOURCE=PASS'
echo 'SPARK_APPLICATION_SUBMITTED=NO'
echo 'S3_WRITE=NO'
echo 'DATABASE_WRITE=NO'
echo 'GIT_COMMIT=NO'
