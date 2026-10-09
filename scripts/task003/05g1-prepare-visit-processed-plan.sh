#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1 GIT_PAGER=cat

ROOT="${HEALTHCARE_PROJECT_ROOT:-/data/spark/healthcare-data-platform}"
STAGE=''

echo '#### TASK003 STEP05G1 PROCESSED PLAN OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT
  [[ -z "$STAGE" ]] || rm -rf -- "$STAGE"
  echo "G1_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G1 PROCESSED PLAN OUTPUT END ####'
  exit "$rc"
}
trap finish EXIT

cd "$ROOT"

for rel in \
  spark/contracts/omop/visit-candidate-v1.json \
  spark/contracts/omop/visit-class-v1.json \
  spark/apps/visit/map_encounter_to_visit_candidate.py \
  scripts/task003/05f2c-validate-visit-candidate.sh
do
  [[ -s "$ROOT/$rel" && ! -L "$ROOT/$rel" ]] || {
    echo "ERROR: missing dependency $rel"
    exit 1
  }
done

STAGE=$(mktemp -d)

mkdir -p \
  "$STAGE/apps/task003" \
  "$STAGE/spark/contracts/processed" \
  "$STAGE/scripts/task003" \
  "$STAGE/tests/task003"

# ========================================================
# 1. Versioned Processed publication policy
# ========================================================

cat > "$STAGE/spark/contracts/processed/visit-candidate-publication-v1.json" <<'JSON_POLICY'
{
  "contract_name": "omop.visit_candidate.processed_publication",
  "contract_version": "v1",
  "input_step": "STEP-05F2",
  "output_bucket": "health-processed",
  "entity": "visit_occurrence",
  "format": "parquet",
  "candidate_contract": "spark/contracts/omop/visit-candidate-v1.json",
  "source_key": [
    "source_system",
    "source_encounter_id"
  ],
  "final_visit_id_allocated": false,
  "publication_gate": "APPROVED_manifest_last",
  "objects": [
    "data/",
    "dq/result.json",
    "manifest.json"
  ],
  "same_run_replay": "REUSE_ONLY_IF_VERIFIED_IDENTICAL",
  "same_run_conflict": "STOP_WITHOUT_OVERWRITE",
  "different_run": "ISOLATED_PREFIX",
  "person_map_snapshot": "REQUIRE_FINGERPRINT_AT_WRITE_TIME",
  "data_validation": "SPARK_READBACK_AND_DQ_BEFORE_MANIFEST",
  "database_write": false
}
JSON_POLICY

# ========================================================
# 2. Pure Python publication planner
# ========================================================

cat > "$STAGE/apps/task003/plan_visit_processed.py" <<'PY_APP'
"""TASK003 STEP05G1: plan-only Processed publication. No remote/DB access."""

import argparse
import hashlib
import json
import re
from pathlib import Path

SEG = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
SHA = re.compile(r"\A[0-9a-f]{64}\Z")


def require(actual, expected, label):
    if type(actual) is not type(expected) or actual != expected:
        raise ValueError(f"{label}: mismatch")


def segment(value, label):
    if (
        not isinstance(value, str)
        or not SEG.fullmatch(value)
        or value in ('.', '..')
    ):
        raise ValueError(f"Invalid path segment: {label}")
    return value


def validate_policy(policy):
    fixed = {
        'contract_name': 'omop.visit_candidate.processed_publication',
        'contract_version': 'v1',
        'input_step': 'STEP-05F2',
        'output_bucket': 'health-processed',
        'entity': 'visit_occurrence',
        'format': 'parquet',
        'candidate_contract': 'spark/contracts/omop/visit-candidate-v1.json',
        'source_key': ['source_system', 'source_encounter_id'],
        'final_visit_id_allocated': False,
        'publication_gate': 'APPROVED_manifest_last',
        'objects': ['data/', 'dq/result.json', 'manifest.json'],
        'same_run_replay': 'REUSE_ONLY_IF_VERIFIED_IDENTICAL',
        'same_run_conflict': 'STOP_WITHOUT_OVERWRITE',
        'different_run': 'ISOLATED_PREFIX',
        'person_map_snapshot': 'REQUIRE_FINGERPRINT_AT_WRITE_TIME',
        'data_validation': 'SPARK_READBACK_AND_DQ_BEFORE_MANIFEST',
        'database_write': False,
    }
    require(policy, fixed, 'Processed publication policy')


def build_plan(state, policy, run_id, evidence_sha):
    validate_policy(policy)
    segment(run_id, 'run_id')

    if not SHA.fullmatch(evidence_sha):
        raise ValueError('Invalid STEP05F2 evidence SHA256')

    for key, expected in {
        'task': 'TASK-003',
        'step': 'STEP-05F2',
        'status': 'PASS',
        'validation_scope': 'in_memory_visit_candidate',
        'ids_allocated': 0,
        's3_write': False,
        'postgresql_write': False,
        'candidate_published': False,
    }.items():
        require(state.get(key), expected, 'F2 state ' + key)

    result = state['result']
    pinned = state['input']
    context = pinned['raw_context']

    for key, expected in {
        'status': 'PASS',
        'step': 'STEP-05F2',
        'candidate_schema': 'PASS',
        'person_mapping': 'PASS',
        'visit_concepts': 'PASS',
        'dates': 'PASS',
        'nullability': 'PASS',
        'deferred_fields': 'PASS',
        'ids_allocated': 0,
        's3_write': False,
        'postgresql_write': False,
        'candidate_published': False,
    }.items():
        require(result.get(key), expected, 'F2 result ' + key)

    require(context['status'], 'PASS', 'APPROVED Raw evidence')
    require(
        result['raw_publish_run_id'],
        context['raw_publish_run_id'],
        'Raw run',
    )
    require(
        result['raw_manifest_sha256'],
        context['raw_manifest_sha256'],
        'Raw manifest',
    )
    require(
        result['dq_sha256'],
        context['dq_sha256'],
        'DQ checksum',
    )
    require(
        result['expected_rows'],
        context['expected_rows'],
        'Expected Raw count',
    )
    require(
        result['mapping_contract_sha256'],
        context['mapping_contract_sha256'],
        'mapping SHA',
    )
    require(
        result['candidate_contract_sha256'],
        pinned['candidate_contract_sha256'],
        'candidate SHA',
    )
    require(
        result['mapper_sha256'],
        pinned['mapper_sha256'],
        'mapper SHA',
    )
    require(
        result['candidate_rows'],
        context['expected_rows'],
        'Candidate count',
    )
    require(
        result['unique_source_keys'],
        context['expected_rows'],
        'Unique keys',
    )
    require(
        result['referenced_persons'],
        pinned['expected_persons'],
        'Person count',
    )
    require(
        result['class_counts'],
        pinned['expected_class_counts'],
        'Class distribution',
    )

    if sum(result['class_counts'].values()) != result['candidate_rows']:
        raise ValueError('Class count mismatch')

    if (
        type(result['candidate_rows']) is not int
        or result['candidate_rows'] <= 0
    ):
        raise ValueError('Invalid candidate count')

    for key in (
        'source',
        'source_version',
        'ingest_date',
        'batch_id',
        'raw_publish_run_id',
    ):
        segment(context[key], key)

    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', context['ingest_date']):
        raise ValueError('Invalid ingest date')

    for value in (
        context['raw_manifest_sha256'],
        context['dq_sha256'],
        context['mapping_contract_sha256'],
        pinned['candidate_contract_sha256'],
        pinned['mapper_sha256'],
    ):
        if not SHA.fullmatch(value):
            raise ValueError('Invalid pinned checksum')

    require(context['source'], 'synthea', 'source')

    base = (
        's3://health-processed/contract_version=v1/entity=visit_occurrence/'
        f"source={context['source']}/source_version={context['source_version']}/"
        f"ingest_date={context['ingest_date']}/batch_id={context['batch_id']}/"
        f"raw_publish_run_id={context['raw_publish_run_id']}/run_id={run_id}"
    )

    return {
        'task': 'TASK-003',
        'step': 'STEP-05G1',
        'status': 'PLANNED',
        'run_id': run_id,
        'source_f2_evidence_sha256': evidence_sha,
        'raw_publish_run_id': context['raw_publish_run_id'],
        'expected_rows': result['candidate_rows'],
        'expected_unique_keys': result['unique_source_keys'],
        'expected_persons': result['referenced_persons'],
        'class_counts': result['class_counts'],
        'contract_sha256': pinned['candidate_contract_sha256'],
        'mapper_sha256': pinned['mapper_sha256'],
        'mapping_contract_sha256': context['mapping_contract_sha256'],
        'raw_manifest_sha256': context['raw_manifest_sha256'],
        'base_uri': base,
        'data_uri': base + '/data/',
        'dq_uri': base + '/dq/result.json',
        'manifest_uri': base + '/manifest.json',
        'publication_policy': policy,
        'person_map_fingerprint': 'PENDING_SPARK_WRITE_STEP',
        'persisted': False,
        'published': False,
        's3_write': False,
        'postgresql_write': False,
        'visit_ids_allocated': 0,
    }


def save_once(path, plan):
    payload = (
        json.dumps(
            plan,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        ) + '\n'
    ).encode()

    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with path.open('xb') as f:
            f.write(payload)
        return 'CREATED'

    except FileExistsError:
        if path.read_bytes() != payload:
            raise ValueError(
                'CONFLICT: same run_id with different plan; never overwrite'
            )
        return 'REUSED'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--f2-state', required=True, type=Path)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()

    root = args.root.resolve()
    f2 = args.f2_state.read_bytes()
    state = json.loads(f2)

    policy = json.loads(
        (
            root
            / 'spark/contracts/processed/visit-candidate-publication-v1.json'
        ).read_bytes()
    )

    pinned = state['input']

    for rel, key in (
        (
            'spark/apps/visit/map_encounter_to_visit_candidate.py',
            'mapper_sha256',
        ),
        (
            'spark/contracts/omop/visit-candidate-v1.json',
            'candidate_contract_sha256',
        ),
    ):
        actual = hashlib.sha256((root / rel).read_bytes()).hexdigest()
        require(actual, pinned[key], 'Current source SHA ' + rel)

    mapping_sha = hashlib.sha256(
        (root / 'spark/contracts/omop/visit-class-v1.json').read_bytes()
    ).hexdigest()

    require(
        mapping_sha,
        pinned['raw_context']['mapping_contract_sha256'],
        'Current mapping SHA',
    )

    plan = build_plan(
        state,
        policy,
        args.run_id,
        hashlib.sha256(f2).hexdigest(),
    )

    target = (
        root
        / 'runtime/reports/task003/step05/processed-plans'
        / args.run_id
        / 'plan.json'
    )

    status = save_once(target, plan)

    print('PROCESSED_PLAN_STATUS=' + status)
    print('EXPECTED_CANDIDATE_ROWS=' + str(plan['expected_rows']))
    print('PLAN_FILE=' + str(target))
    print('PROCESSED_BASE_URI=' + plan['base_uri'])
    print('S3_WRITE=NO')
    print('DATABASE_WRITE=NO')
    print('VISIT_ID_ALLOCATED=NO')


if __name__ == '__main__':
    main()
PY_APP

# ========================================================
# 3. Unit and negative tests
# ========================================================

cat > "$STAGE/tests/task003/test_visit_processed_plan.py" <<'PY_TEST'
"""STEP05G1 plan and conflict policy tests; no cloud dependencies."""

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'apps/task003'))

from plan_visit_processed import build_plan, save_once

POLICY = json.loads(
    (
        ROOT
        / 'spark/contracts/processed/visit-candidate-publication-v1.json'
    ).read_text()
)


def fixture():
    ctx = dict(
        status='PASS',
        source='synthea',
        source_version='v3.3.0',
        batch_id='test-batch',
        ingest_date='2026-10-08',
        raw_publish_run_id='test-raw',
        expected_rows=3,
        raw_manifest_sha256='a' * 64,
        dq_sha256='9' * 64,
        mapping_contract_sha256='b' * 64,
    )

    pinned = dict(
        raw_context=ctx,
        expected_persons=2,
        expected_class_counts={
            'ambulatory': 2,
            'emergency': 1,
        },
        candidate_contract_sha256='c' * 64,
        mapper_sha256='d' * 64,
    )

    result = dict(
        status='PASS',
        step='STEP-05F2',
        candidate_schema='PASS',
        person_mapping='PASS',
        visit_concepts='PASS',
        dates='PASS',
        nullability='PASS',
        deferred_fields='PASS',
        ids_allocated=0,
        s3_write=False,
        postgresql_write=False,
        candidate_published=False,
        raw_publish_run_id='test-raw',
        raw_manifest_sha256='a' * 64,
        dq_sha256='9' * 64,
        expected_rows=3,
        mapping_contract_sha256='b' * 64,
        candidate_contract_sha256='c' * 64,
        mapper_sha256='d' * 64,
        candidate_rows=3,
        unique_source_keys=3,
        referenced_persons=2,
        class_counts={
            'ambulatory': 2,
            'emergency': 1,
        },
    )

    return dict(
        task='TASK-003',
        step='STEP-05F2',
        status='PASS',
        validation_scope='in_memory_visit_candidate',
        ids_allocated=0,
        s3_write=False,
        postgresql_write=False,
        candidate_published=False,
        input=pinned,
        result=result,
    )


class TestG1(unittest.TestCase):

    def plan(self, state=None, run_id='visit-proc-test'):
        return build_plan(
            state or fixture(),
            POLICY,
            run_id,
            'e' * 64,
        )

    def test_valid_and_immutable_layout(self):
        p = self.plan()
        self.assertEqual(p['expected_rows'], 3)
        self.assertTrue(
            p['base_uri'].startswith('s3://health-processed/')
        )
        self.assertEqual(
            p['manifest_uri'],
            p['base_uri'] + '/manifest.json',
        )
        self.assertFalse(p['published'])
        self.assertEqual(p['visit_ids_allocated'], 0)

    def test_same_plan_reuses_without_rewriting(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'plan.json'
            p = self.plan()

            self.assertEqual(save_once(path, p), 'CREATED')
            before = path.read_bytes()
            self.assertEqual(save_once(path, p), 'REUSED')
            self.assertEqual(path.read_bytes(), before)

    def test_same_run_conflict_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'plan.json'
            self.assertEqual(
                save_once(path, self.plan()),
                'CREATED',
            )

            modified = self.plan()
            modified['expected_rows'] += 1

            with self.assertRaisesRegex(ValueError, 'CONFLICT'):
                save_once(path, modified)

    def test_different_run_isolated(self):
        self.assertNotEqual(
            self.plan(run_id='visit-a')['base_uri'],
            self.plan(run_id='visit-b')['base_uri'],
        )

    def test_bad_f2_rejected(self):
        s = fixture()
        s['status'] = 'FAILED'

        with self.assertRaises(ValueError):
            self.plan(s)

    def test_count_drift_rejected(self):
        s = fixture()
        s['result']['candidate_rows'] = 4

        with self.assertRaises(ValueError):
            self.plan(s)

    def test_source_mapping_conflict_rejected(self):
        s = fixture()
        s['result']['mapper_sha256'] = 'f' * 64

        with self.assertRaises(ValueError):
            self.plan(s)

    def test_path_injection_rejected(self):
        for value in ('../escape', 'visit/a', '', '..'):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.plan(run_id=value)

    def test_premature_publication_rejected(self):
        s = fixture()
        s['candidate_published'] = True

        with self.assertRaises(ValueError):
            self.plan(s)

    def test_policy_conflict_rejected(self):
        policy = copy.deepcopy(POLICY)
        policy['same_run_conflict'] = 'OVERWRITE'

        with self.assertRaises(ValueError):
            build_plan(
                fixture(),
                policy,
                'visit-test',
                'e' * 64,
            )


if __name__ == '__main__':
    unittest.main()
PY_TEST

# ========================================================
# 4. Permanent run entry
# ========================================================

cat > "$STAGE/scripts/task003/05g1-plan-visit-processed.sh" <<'RUNNER'
#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo '#### TASK003 STEP05G1 PLAN EXECUTION OUTPUT BEGIN ####'

finish() {
    rc=$?
    trap - EXIT
    echo "PLAN_EXIT_CODE=$rc"
    echo '#### TASK003 STEP05G1 PLAN EXECUTION OUTPUT END ####'
    exit "$rc"
}
trap finish EXIT

[[ $# -eq 1 && -s "$1" ]] || {
    echo "Usage: $0 ABSOLUTE_STEP05F2_RUN_STATE"
    exit 2
}

RUN_ID="${VISIT_PROCESSED_RUN_ID:-visit-proc-$(date -u +%Y%m%dt%H%M%Sz)-$$}"

python3 "$ROOT/apps/task003/plan_visit_processed.py" \
    --root "$ROOT" \
    --f2-state "$1" \
    --run-id "$RUN_ID"

echo "PLANNED_RUN_ID=$RUN_ID"
echo 'SPARK_APPLICATION_SUBMITTED=NO'
echo 'S3_WRITE=NO'
echo 'DATABASE_WRITE=NO'
RUNNER

# ========================================================
# 5. Static validation and tests
# ========================================================

echo '=== 1. Python and Shell syntax ==='

python3 - "$STAGE" <<'PY_PARSE'
import ast
import sys
from pathlib import Path

base = Path(sys.argv[1])

for rel in (
    'apps/task003/plan_visit_processed.py',
    'tests/task003/test_visit_processed_plan.py',
):
    ast.parse(
        (base / rel).read_text(),
        filename=rel,
    )

print('G1_PYTHON_SYNTAX=PASS')
PY_PARSE

bash -n "$STAGE/scripts/task003/05g1-plan-visit-processed.sh"

echo '=== 2. Unit and negative tests ==='

python3 -m unittest discover \
    -s "$STAGE/tests/task003" \
    -p 'test_visit_processed_plan.py' -v

echo 'G1_POLICY_TESTS=PASS'

# ========================================================
# 6. Install permanent canonical source
# ========================================================

FILES=(
    spark/contracts/processed/visit-candidate-publication-v1.json
    apps/task003/plan_visit_processed.py
    tests/task003/test_visit_processed_plan.py
    scripts/task003/05g1-plan-visit-processed.sh
)

GEN=scripts/task003/05g1-prepare-visit-processed-plan.sh

echo '=== 3. Source conflict check ==='

for rel in "${FILES[@]}"; do
    target="$ROOT/$rel"

    if [[ -L "$target" ]] || {
        [[ -e "$target" ]] &&
        ! cmp -s "$STAGE/$rel" "$target"
    }; then
        echo "ERROR: existing source conflicts: $rel"
        exit 1
    fi
done

if [[ -L "$ROOT/$GEN" ]] || {
    [[ -e "$ROOT/$GEN" ]] &&
    ! cmp -s "${BASH_SOURCE[0]}" "$ROOT/$GEN"
}; then
    echo 'ERROR: existing formal generator conflicts'
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

echo 'STEP05G1_SOURCE_AND_TESTS=PASS'
echo 'SPARK_APPLICATION_SUBMITTED=NO'
echo 'S3_WRITE=NO'
echo 'DATABASE_WRITE=NO'
echo 'GIT_COMMIT=NO'
