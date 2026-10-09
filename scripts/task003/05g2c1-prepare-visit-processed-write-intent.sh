#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1 GIT_PAGER=cat

ROOT="${HEALTHCARE_PROJECT_ROOT:-/data/spark/healthcare-data-platform}"
STAGE=''

echo '#### TASK003 STEP05G2C1 WRITE-INTENT SOURCE OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT
  [[ -z "$STAGE" ]] || rm -rf -- "$STAGE"
  echo "INSTALL_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G2C1 WRITE-INTENT SOURCE OUTPUT END ####'
  exit "$rc"
}
trap finish EXIT

for rel in \
  apps/task003/plan_visit_processed.py \
  apps/task003/verify_visit_processed_plan.py \
  apps/task003/inspect_visit_processed_prefix.py \
  tests/task003/test_visit_processed_plan.py \
  spark/contracts/processed/visit-candidate-publication-v1.json
do
  [[ -s "$ROOT/$rel" && ! -L "$ROOT/$rel" ]] || {
    echo "ERROR: missing prerequisite: $rel"
    exit 1
  }
done

STAGE=$(mktemp -d /data/spark/temp_shell/05g2c1-stage.XXXXXXXX)

mkdir -p \
  "$STAGE/apps/task003" \
  "$STAGE/tests/task003" \
  "$STAGE/scripts/task003" \
  "$STAGE/spark/contracts/processed"

# ========================================================
# 1. Versioned Writer safety contract
# ========================================================

cat > "$STAGE/spark/contracts/processed/visit-writer-safety-v1.json" <<'JSON_POLICY'
{
  "contract_name": "omop.visit_candidate.writer_safety",
  "contract_version": "v1",
  "input_preflight": "STEP-05G2B",
  "snapshot_is_write_authorization": false,
  "exclusive_writer_reservation_required": true,
  "relist_s3_after_reservation_required": true,
  "spark_save_mode": "errorifexists",
  "never_overwrite_existing_data": true,
  "data_readback_required": true,
  "dq_and_manifest_deferred_to_publish_steps": true,
  "database_write": false
}
JSON_POLICY

# ========================================================
# 2. Write Intent Python
# ========================================================

cat > "$STAGE/apps/task003/prepare_visit_processed_write_intent.py" <<'PY_APP'
"""Pin G1/G2B evidence for a future writer. Never grants write permission."""

import argparse
import hashlib
import json
from pathlib import Path

from inspect_visit_processed_prefix import classify
from plan_visit_processed import save_once
from verify_visit_processed_plan import verify_plan_bytes

POLICY = {
    'contract_name': 'omop.visit_candidate.writer_safety',
    'contract_version': 'v1',
    'input_preflight': 'STEP-05G2B',
    'snapshot_is_write_authorization': False,
    'exclusive_writer_reservation_required': True,
    'relist_s3_after_reservation_required': True,
    'spark_save_mode': 'errorifexists',
    'never_overwrite_existing_data': True,
    'data_readback_required': True,
    'dq_and_manifest_deferred_to_publish_steps': True,
    'database_write': False,
}


def require(actual, expected, label):
    if type(actual) is not type(expected) or actual != expected:
        raise ValueError('Evidence mismatch: ' + label)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify_snapshot(f2_bytes, plan_bytes, g2b_bytes, listing_bytes,
                    publication_policy, writer_policy):
    require(writer_policy, POLICY, 'writer safety policy')

    f2 = json.loads(f2_bytes)
    plan = json.loads(plan_bytes)
    g2b = json.loads(g2b_bytes)
    listing = json.loads(listing_bytes)

    verify_plan_bytes(
        plan_bytes,
        f2_bytes,
        publication_policy,
        plan['run_id']
    )

    require(
        plan['publication_policy'],
        publication_policy,
        'publication policy'
    )

    for key, value in {
        'task': 'TASK-003',
        'step': 'STEP-05G2B',
        'status': 'PASS',
        'validation_scope': 'remote_s3_prefix_snapshot',
        's3_write': False,
        'postgresql_write': False,
        'spark_application_submitted': False,
        'publication_verified': False,
        'exclusive_writer_lock_acquired': False,
        'write_authorized': False,
    }.items():
        require(g2b.get(key), value, 'G2B.' + key)

    require(
        g2b.get('plan_sha256'),
        sha(plan_bytes),
        'G2B plan SHA'
    )
    require(
        g2b.get('s3_listing_sha256'),
        sha(listing_bytes),
        'G2B listing SHA'
    )

    inspected = classify(plan, listing)

    require(
        g2b.get('inspection'),
        inspected,
        'G2B classification'
    )
    require(
        inspected['classification'],
        'EMPTY',
        'S3 snapshot empty'
    )
    require(
        inspected['new_write_guard'],
        'PASS',
        'G2A guard'
    )

    require(
        plan['expected_rows'],
        f2['result']['candidate_rows'],
        'rows'
    )
    require(
        plan['expected_persons'],
        f2['result']['referenced_persons'],
        'persons'
    )

    if plan['expected_rows'] < 1:
        raise ValueError('Cannot prepare an empty dataset')

    return {
        'task': 'TASK-003',
        'step': 'STEP-05G2C1',
        'status': 'PREFLIGHT_SNAPSHOT_ONLY',
        'run_id': plan['run_id'],
        'base_uri': plan['base_uri'],
        'data_uri': plan['data_uri'],
        'expected_rows': plan['expected_rows'],
        'expected_persons': plan['expected_persons'],
        'expected_class_counts': plan['class_counts'],
        'step05f2_sha256': sha(f2_bytes),
        'plan_sha256': sha(plan_bytes),
        'step05g2b_sha256': sha(g2b_bytes),
        'remote_listing_sha256': sha(listing_bytes),
        'writer_safety_policy': writer_policy,
        'writer_reservation_acquired': False,
        'fresh_s3_relist_passed': False,
        'write_authorized': False,
        'spark_submitted': False,
        's3_write': False,
        'postgresql_write': False,
        'candidate_published': False,
    }


def check_source_pins(root, f2):
    pinned = f2['input']['mounted_file_sha256']

    files = {
        'map_encounter_to_visit_candidate.py':
            'spark/apps/visit/map_encounter_to_visit_candidate.py',
        'validate_visit_candidate_preflight.py':
            'spark/apps/visit/validate_visit_candidate_preflight.py',
        'canonical_gate.py':
            'spark/common/canonical_gate.py',
        'visit_candidate_rules.py':
            'apps/task003/visit_candidate_rules.py',
        'verify_encounter_remote_metadata.py':
            'apps/task003/verify_encounter_remote_metadata.py',
        'resolve_approved_encounter_raw.py':
            'apps/task003/resolve_approved_encounter_raw.py',
        'encounter-v1.json':
            'spark/contracts/canonical/encounter-v1.json',
        'visit-class-v1.json':
            'spark/contracts/omop/visit-class-v1.json',
        'visit-candidate-v1.json':
            'spark/contracts/omop/visit-candidate-v1.json',
    }

    output = {}

    for name, relative in files.items():
        path = root / relative

        if path.is_symlink() or not path.is_file():
            raise ValueError('Missing trusted source: ' + relative)

        actual = sha(path.read_bytes())
        require(actual, pinned[name], 'source SHA: ' + relative)
        output[relative] = actual

    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--f2-state', required=True, type=Path)
    parser.add_argument('--plan', required=True, type=Path)
    parser.add_argument('--g2b-report', required=True, type=Path)
    args = parser.parse_args()

    root = args.root.resolve()
    report = args.g2b_report.resolve()

    inputs = [
        args.f2_state,
        args.plan,
        report / 'run-state.json',
        report / 's3-listing.json',
    ]

    if any(p.is_symlink() or not p.is_file() for p in inputs):
        raise ValueError('Missing or symlinked validation evidence')

    f2_bytes, plan_bytes, g2b_bytes, listing_bytes = [
        p.read_bytes() for p in inputs
    ]

    publication_policy = json.loads((
        root
        / 'spark/contracts/processed/visit-candidate-publication-v1.json'
    ).read_bytes())

    writer_policy_bytes = (
        root / 'spark/contracts/processed/visit-writer-safety-v1.json'
    ).read_bytes()

    writer_policy = json.loads(writer_policy_bytes)

    intent = verify_snapshot(
        f2_bytes,
        plan_bytes,
        g2b_bytes,
        listing_bytes,
        publication_policy,
        writer_policy,
    )

    intent['source_sha256'] = check_source_pins(
        root,
        json.loads(f2_bytes)
    )

    intent['writer_safety_policy_sha256'] = sha(writer_policy_bytes)

    run_id = intent['run_id']

    expected_plan = (
        root / 'runtime/reports/task003/step05/processed-plans'
        / run_id / 'plan.json'
    )

    if args.plan.resolve() != expected_plan.resolve():
        raise ValueError('Unexpected immutable plan path')

    path = (
        root / 'runtime/reports/task003/step05/processed-intents'
        / run_id / 'write-intent.json'
    )

    status = save_once(path, intent)

    print('WRITE_INTENT_STATUS=' + status)
    print('EXPECTED_ROWS=' + str(intent['expected_rows']))
    print('EXPECTED_PERSONS=' + str(intent['expected_persons']))
    print('WRITE_INTENT_SHA256=' + sha(path.read_bytes()))
    print('WRITE_INTENT_FILE=' + str(path))
    print('S3_SNAPSHOT_CHECK=PASS')
    print('WRITER_RESERVATION_ACQUIRED=NO')
    print('FRESH_S3_RELIST_PASSED=NO')
    print('WRITE_AUTHORIZED=NO')
    print('S3_WRITE=NO')
    print('DATABASE_WRITE=NO')


if __name__ == '__main__':
    main()
PY_APP

# ========================================================
# 3. Unit tests
# ========================================================

cat > "$STAGE/tests/task003/test_visit_processed_write_intent.py" <<'PY_TEST'
"""Local Write Intent tests. No external services."""

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'apps/task003'))

from plan_visit_processed import build_plan, save_once
from prepare_visit_processed_write_intent import POLICY, verify_snapshot
from test_visit_processed_plan import fixture


def encoded(value):
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)
        + '\n'
    ).encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


class WriterIntentTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.pub_policy = json.loads((
            ROOT
            / 'spark/contracts/processed/visit-candidate-publication-v1.json'
        ).read_bytes())

    def setUp(self):
        self.f2 = encoded(fixture())

        self.plan = build_plan(
            json.loads(self.f2),
            self.pub_policy,
            'visit-test',
            sha(self.f2)
        )

        self.plan_bytes = encoded(self.plan)
        self.listing_bytes = encoded({'RequestCharged': None})

        self.inspection = {
            'bucket': 'health-processed',
            'prefix':
                self.plan['base_uri'].split('health-processed/', 1)[1] + '/',
            'object_count': 0,
            'data_object_count': 0,
            'dq_object_present': False,
            'manifest_object_present': False,
            'classification': 'EMPTY',
            'new_write_guard': 'PASS',
            'publication_verified': False,
            'resume_authorized': False,
            'concurrent_writer_protection': False,
        }

        self.g2b = {
            'task': 'TASK-003',
            'step': 'STEP-05G2B',
            'status': 'PASS',
            'validation_scope': 'remote_s3_prefix_snapshot',
            's3_write': False,
            'postgresql_write': False,
            'spark_application_submitted': False,
            'publication_verified': False,
            'exclusive_writer_lock_acquired': False,
            'write_authorized': False,
            'plan_sha256': sha(self.plan_bytes),
            's3_listing_sha256': sha(self.listing_bytes),
            'inspection': self.inspection,
        }

    def verify(self):
        return verify_snapshot(
            self.f2,
            self.plan_bytes,
            encoded(self.g2b),
            self.listing_bytes,
            self.pub_policy,
            POLICY,
        )

    def test_snapshot_pass_but_not_authorized(self):
        intent = self.verify()
        self.assertEqual(intent['expected_rows'], 3)
        self.assertFalse(intent['write_authorized'])
        self.assertFalse(intent['writer_reservation_acquired'])

    def test_plan_replay_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'intent.json'

            self.assertEqual(
                save_once(target, self.verify()),
                'CREATED'
            )

            before = target.read_bytes()

            self.assertEqual(
                save_once(target, self.verify()),
                'REUSED'
            )
            self.assertEqual(target.read_bytes(), before)

    def test_refuse_changed_plan(self):
        self.plan['expected_rows'] += 1
        self.plan_bytes = encoded(self.plan)
        self.g2b['plan_sha256'] = sha(self.plan_bytes)

        with self.assertRaises(ValueError):
            self.verify()

    def test_refuse_bad_listing_hash(self):
        self.g2b['s3_listing_sha256'] = '0' * 64

        with self.assertRaises(ValueError):
            self.verify()

    def test_refuse_nonempty_listing(self):
        prefix = self.inspection['prefix']

        self.listing_bytes = encoded({
            'Contents': [
                {
                    'Key': prefix + 'data/part.parquet',
                    'Size': 55
                }
            ],
            'KeyCount': 1
        })

        self.g2b['s3_listing_sha256'] = sha(self.listing_bytes)

        with self.assertRaises(ValueError):
            self.verify()

    def test_refuse_claimed_lock(self):
        self.g2b['exclusive_writer_lock_acquired'] = True

        with self.assertRaises(ValueError):
            self.verify()

    def test_refuse_fabricated_pass(self):
        self.g2b['status'] = 'FAILED'

        with self.assertRaises(ValueError):
            self.verify()

    def test_refuse_policy_weakening(self):
        weaker_policy = copy.deepcopy(POLICY)
        weaker_policy['exclusive_writer_reservation_required'] = False

        with self.assertRaises(ValueError):
            verify_snapshot(
                self.f2,
                self.plan_bytes,
                encoded(self.g2b),
                self.listing_bytes,
                self.pub_policy,
                weaker_policy
            )


if __name__ == '__main__':
    unittest.main()
PY_TEST

# ========================================================
# 4. Permanent runner
# ========================================================

cat > "$STAGE/scripts/task003/05g2c1-verify-visit-processed-write-intent.sh" <<'SH_RUNNER'
#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo '#### TASK003 STEP05G2C1 WRITE-INTENT VALIDATION OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT
  echo "VALIDATION_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G2C1 WRITE-INTENT VALIDATION OUTPUT END ####'
  exit "$rc"
}
trap finish EXIT

[[ $# -eq 3 ]] || {
  echo "Usage: $0 F2_RUN_STATE PROCESSED_RUN_ID G2B_REPORT_DIR"
  exit 2
}

F2="$1"
RUN_ID="$2"
G2B="$3"

[[ "$RUN_ID" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$ && \
   "$RUN_ID" != '.' && "$RUN_ID" != '..' ]] || {
  echo 'ERROR: invalid run ID'
  exit 2
}

PLAN="$ROOT/runtime/reports/task003/step05/processed-plans/$RUN_ID/plan.json"

python3 "$ROOT/apps/task003/prepare_visit_processed_write_intent.py" \
  --root "$ROOT" \
  --f2-state "$F2" \
  --plan "$PLAN" \
  --g2b-report "$G2B"

echo 'G2C1_WRITE_INTENT_VALIDATION=PASS'
echo 'SPARK_APPLICATION_SUBMITTED=NO'
echo 'S3_WRITE=NO'
echo 'DATABASE_WRITE=NO'
SH_RUNNER

# ========================================================
# 5. Static checks and isolated tests
# ========================================================

echo '=== 1. Source syntax ==='

python3 - "$STAGE" <<'PY_AST'
import ast
import sys
from pathlib import Path

root = Path(sys.argv[1])

for relative in (
    'apps/task003/prepare_visit_processed_write_intent.py',
    'tests/task003/test_visit_processed_write_intent.py',
):
    ast.parse(
        (root / relative).read_text(),
        filename=relative
    )

print('PYTHON_SYNTAX=PASS')
PY_AST

bash -n "$STAGE/scripts/task003/05g2c1-verify-visit-processed-write-intent.sh"

echo 'SHELL_SYNTAX=PASS'

for rel in \
  apps/task003/plan_visit_processed.py \
  apps/task003/verify_visit_processed_plan.py \
  apps/task003/inspect_visit_processed_prefix.py \
  tests/task003/test_visit_processed_plan.py \
  spark/contracts/processed/visit-candidate-publication-v1.json
do
  mkdir -p "$STAGE/$(dirname "$rel")"
  cp -- "$ROOT/$rel" "$STAGE/$rel"
done

python3 -m unittest discover \
  -s "$STAGE/tests/task003" \
  -p 'test_visit_processed_write_intent.py' -q

echo 'WRITE_INTENT_TESTS=PASS'

# ========================================================
# 6. Canonical source installation
# ========================================================

FILES=(
  spark/contracts/processed/visit-writer-safety-v1.json
  apps/task003/prepare_visit_processed_write_intent.py
  tests/task003/test_visit_processed_write_intent.py
  scripts/task003/05g2c1-verify-visit-processed-write-intent.sh
)

GEN=scripts/task003/05g2c1-prepare-visit-processed-write-intent.sh

for rel in "${FILES[@]}"; do
  if [[ -L "$ROOT/$rel" ]] || {
    [[ -e "$ROOT/$rel" ]] &&
    ! cmp -s "$STAGE/$rel" "$ROOT/$rel"
  }; then
    echo "ERROR: source conflict: $rel"
    exit 1
  fi
done

if [[ -L "$ROOT/$GEN" ]] || {
  [[ -e "$ROOT/$GEN" ]] &&
  ! cmp -s "${BASH_SOURCE[0]}" "$ROOT/$GEN"
}; then
  echo "ERROR: generator conflict: $GEN"
  exit 1
fi

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

echo 'STEP05G2C1_SOURCE_AND_TESTS=PASS'
echo 'REMOTE_S3_LISTING_EXECUTED=NO'
echo 'WRITER_RESERVATION_ACQUIRED=NO'
echo 'SPARK_APPLICATION_SUBMITTED=NO'
echo 'S3_WRITE=NO'
echo 'DATABASE_WRITE=NO'
