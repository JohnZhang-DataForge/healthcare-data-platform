#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1 GIT_PAGER=cat

ROOT="${HEALTHCARE_PROJECT_ROOT:-/data/spark/healthcare-data-platform}"
STAGE=''

echo '#### TASK003 STEP05G2A S3 PREFIX GUARD SOURCE OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT
  [[ -z "$STAGE" ]] || rm -rf -- "$STAGE"
  echo "G2A_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G2A S3 PREFIX GUARD SOURCE OUTPUT END ####'
  exit "$rc"
}
trap finish EXIT

for f in \
  apps/task003/plan_visit_processed.py \
  apps/task003/verify_visit_processed_plan.py \
  scripts/task003/05g1-verify-visit-processed-plan.sh \
  spark/contracts/processed/visit-candidate-publication-v1.json
do
  [[ -s "$ROOT/$f" && ! -L "$ROOT/$f" ]] || {
    echo "ERROR: missing G1 prerequisite: $f"
    exit 1
  }
done

STAGE=$(mktemp -d /data/spark/temp_shell/05g2a-stage.XXXXXXXX)

mkdir -p \
  "$STAGE/apps/task003" \
  "$STAGE/tests/task003" \
  "$STAGE/scripts/task003"

# ========================================================
# 1. S3 prefix inspection Python
# ========================================================

cat > "$STAGE/apps/task003/inspect_visit_processed_prefix.py" <<'PY_APP'
"""Fail-closed S3 prefix inspection for Processed Visit.

Only examines a supplied S3 list-objects-v2 response.
Does not authorize publication, resume, overwrite or concurrency.
"""

import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit


class PrefixGuardError(ValueError):
    pass


def require(condition, label):
    if not condition:
        raise PrefixGuardError(label)


def get_prefix(plan):
    require(isinstance(plan, dict), 'plan must be an object')

    for name, expected in (
        ('task', 'TASK-003'),
        ('step', 'STEP-05G1'),
        ('status', 'PLANNED'),
        ('persisted', False),
        ('published', False),
        ('s3_write', False),
        ('postgresql_write', False),
        ('visit_ids_allocated', 0),
    ):
        require(
            type(plan.get(name)) is type(expected)
            and plan[name] == expected,
            'unsafe plan field: ' + name
        )

    policy = plan.get('publication_policy')
    require(isinstance(policy, dict), 'missing policy')

    require(
        policy.get('output_bucket') == 'health-processed',
        'bucket policy'
    )
    require(
        policy.get('publication_gate') == 'APPROVED_manifest_last',
        'gate policy'
    )
    require(
        policy.get('same_run_conflict') == 'STOP_WITHOUT_OVERWRITE',
        'conflict policy'
    )
    require(
        policy.get('same_run_replay') == 'REUSE_ONLY_IF_VERIFIED_IDENTICAL',
        'replay policy'
    )
    require(
        policy.get('objects') == [
            'data/', 'dq/result.json', 'manifest.json'
        ],
        'object layout'
    )

    run_id = plan.get('run_id')
    require(
        isinstance(run_id, str)
        and run_id
        and '/' not in run_id
        and run_id not in ('.', '..'),
        'unsafe run ID'
    )

    base = plan.get('base_uri')
    require(isinstance(base, str), 'missing base URI')

    parsed = urlsplit(base)

    require(
        parsed.scheme == 's3'
        and parsed.netloc == 'health-processed',
        'unexpected S3 bucket'
    )
    require(
        not parsed.query and not parsed.fragment,
        'unexpected S3 URL suffix'
    )

    key = parsed.path.lstrip('/')
    parts = key.split('/')

    require(len(parts) == 8, 'unexpected prefix components')

    require(
        parts[0:3] == [
            'contract_version=v1',
            'entity=visit_occurrence',
            'source=synthea'
        ],
        'unexpected processed layout'
    )

    require(
        parts[-1] == 'run_id=' + run_id,
        'run identity differs from prefix'
    )

    require(
        all(
            part and part not in ('.', '..')
            and '\\' not in part
            for part in parts
        ),
        'invalid prefix segment'
    )

    require(
        key and not key.endswith('/'),
        'base URI must not end in slash'
    )

    for field, suffix in (
        ('data_uri', '/data/'),
        ('dq_uri', '/dq/result.json'),
        ('manifest_uri', '/manifest.json'),
    ):
        require(
            plan.get(field) == base + suffix,
            'invalid plan target: ' + field
        )

    return 'health-processed', key + '/'


def classify(plan, listing):
    bucket, prefix = get_prefix(plan)

    require(
        isinstance(listing, dict),
        'listing must be an object'
    )

    # SeaweedFS may return {"RequestCharged": null}
    # for an empty result. Do not require KeyCount.
    require(
        any(
            k in listing
            for k in ('Contents', 'KeyCount', 'RequestCharged')
        ),
        'invalid S3 listing: no recognized fields'
    )

    require(
        listing.get('IsTruncated', False) is False,
        'truncated listing; refuse partial evidence'
    )

    require(
        not listing.get('NextContinuationToken'),
        'unconsumed listing page'
    )

    contents = listing.get('Contents', [])

    require(
        isinstance(contents, list),
        'invalid Contents'
    )

    if 'KeyCount' in listing:
        count = listing['KeyCount']
        require(
            type(count) is int and count == len(contents),
            'inconsistent KeyCount'
        )

    keys = set()
    data_count = 0
    dq_present = False
    manifest_present = False

    for obj in contents:
        require(
            isinstance(obj, dict),
            'invalid S3 object'
        )

        key = obj.get('Key')
        size = obj.get('Size')

        require(
            isinstance(key, str)
            and key.startswith(prefix),
            'unexpected object key'
        )

        require(
            type(size) is int and size >= 0,
            'invalid S3 object size'
        )

        require(
            key not in keys,
            'duplicate S3 object key'
        )
        keys.add(key)

        suffix = key[len(prefix):]

        require(
            suffix
            and '//' not in suffix
            and all(
                p not in ('.', '..')
                for p in suffix.split('/')
            ),
            'invalid key suffix'
        )

        if suffix.startswith('data/'):
            data_count += 1

        elif suffix == 'dq/result.json':
            dq_present = True

        elif suffix == 'manifest.json':
            manifest_present = True

        else:
            raise PrefixGuardError(
                'unexpected object under run prefix: '
                + suffix
            )

    require(
        not dq_present or data_count > 0,
        'DQ exists without any data objects'
    )

    require(
        not manifest_present
        or (dq_present and data_count > 0),
        'manifest exists without complete expected layout'
    )

    if not contents:
        state = 'EMPTY'

    elif manifest_present:
        state = 'MANIFEST_PRESENT_UNVERIFIED'

    elif dq_present:
        state = 'DATA_AND_DQ_UNVERIFIED'

    else:
        state = 'DATA_PRESENT_UNVERIFIED'

    return {
        'bucket': bucket,
        'prefix': prefix,
        'object_count': len(contents),
        'data_object_count': data_count,
        'dq_object_present': dq_present,
        'manifest_object_present': manifest_present,
        'classification': state,
        'new_write_guard': (
            'PASS' if state == 'EMPTY' else 'STOP'
        ),
        'publication_verified': False,
        'resume_authorized': False,
        'concurrent_writer_protection': False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--listing', type=Path, required=True)
    args = parser.parse_args()

    result = classify(
        json.loads(args.plan.read_bytes()),
        json.loads(args.listing.read_bytes())
    )

    print(
        'PROCESSED_PREFIX_CLASSIFICATION='
        + result['classification']
    )
    print(
        'PREFIX_OBJECT_COUNT='
        + str(result['object_count'])
    )
    print(
        'PREFIX_NEW_WRITE_GUARD='
        + result['new_write_guard']
    )

    print('PUBLISHED_VERIFIED=NO')
    print('RESUME_AUTHORIZED=NO')
    print('CONCURRENT_WRITER_PROTECTION=NOT_ESTABLISHED')

    if result['new_write_guard'] != 'PASS':
        raise SystemExit(3)


if __name__ == '__main__':
    main()
PY_APP

# ========================================================
# 2. Positive and negative tests
# ========================================================

cat > "$STAGE/tests/task003/test_visit_processed_prefix_guard.py" <<'PY_TEST'
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[2] / 'apps/task003')
)

from inspect_visit_processed_prefix import (
    classify,
    PrefixGuardError,
)


class PrefixTests(unittest.TestCase):

    def setUp(self):
        self.base = (
            's3://health-processed/contract_version=v1/'
            'entity=visit_occurrence/source=synthea/'
            'source_version=v3.3.0/'
            'ingest_date=2026-10-08/batch_id=test-batch/'
            'raw_publish_run_id=raw-test/run_id=run-test'
        )

        self.plan = dict(
            task='TASK-003',
            step='STEP-05G1',
            status='PLANNED',
            persisted=False,
            published=False,
            s3_write=False,
            postgresql_write=False,
            visit_ids_allocated=0,
            run_id='run-test',
            base_uri=self.base,
            data_uri=self.base + '/data/',
            dq_uri=self.base + '/dq/result.json',
            manifest_uri=self.base + '/manifest.json',
            publication_policy=dict(
                output_bucket='health-processed',
                publication_gate='APPROVED_manifest_last',
                same_run_conflict='STOP_WITHOUT_OVERWRITE',
                same_run_replay='REUSE_ONLY_IF_VERIFIED_IDENTICAL',
                objects=[
                    'data/',
                    'dq/result.json',
                    'manifest.json'
                ]
            )
        )

        self.prefix = (
            self.base.split('health-processed/', 1)[1] + '/'
        )

    def listing(self, *suffixes):
        return {
            'Contents': [
                {
                    'Key': self.prefix + suffix,
                    'Size': 45
                }
                for suffix in suffixes
            ],
            'KeyCount': len(suffixes),
            'IsTruncated': False
        }

    def test_seaweedfs_empty_without_keycount(self):
        self.assertEqual(
            classify(
                self.plan,
                {'RequestCharged': None}
            )['classification'],
            'EMPTY'
        )

    def test_empty_aws_form(self):
        self.assertEqual(
            classify(
                self.plan,
                self.listing()
            )['new_write_guard'],
            'PASS'
        )

    def test_data_only_blocks_new_write(self):
        result = classify(
            self.plan,
            self.listing('data/part-001.parquet')
        )

        self.assertEqual(
            result['classification'],
            'DATA_PRESENT_UNVERIFIED'
        )
        self.assertEqual(
            result['new_write_guard'],
            'STOP'
        )

    def test_data_and_dq_still_unverified(self):
        result = classify(
            self.plan,
            self.listing(
                'data/part-001.parquet',
                'dq/result.json'
            )
        )

        self.assertEqual(
            result['classification'],
            'DATA_AND_DQ_UNVERIFIED'
        )
        self.assertFalse(result['resume_authorized'])

    def test_manifest_not_automatically_approved(self):
        result = classify(
            self.plan,
            self.listing(
                'data/_SUCCESS',
                'dq/result.json',
                'manifest.json'
            )
        )

        self.assertEqual(
            result['classification'],
            'MANIFEST_PRESENT_UNVERIFIED'
        )
        self.assertFalse(result['publication_verified'])

    def test_reject_dq_alone(self):
        with self.assertRaises(PrefixGuardError):
            classify(
                self.plan,
                self.listing('dq/result.json')
            )

    def test_reject_manifest_without_dq(self):
        with self.assertRaises(PrefixGuardError):
            classify(
                self.plan,
                self.listing(
                    'data/part-001.parquet',
                    'manifest.json'
                )
            )

    def test_reject_foreign_key(self):
        with self.assertRaises(PrefixGuardError):
            classify(
                self.plan,
                {
                    'Contents': [
                        {'Key': 'other/data', 'Size': 5}
                    ],
                    'KeyCount': 1
                }
            )

    def test_reject_unexpected_object(self):
        with self.assertRaises(PrefixGuardError):
            classify(
                self.plan,
                self.listing('unknown.json')
            )

    def test_reject_malformed_response(self):
        for response in (
            {},
            {'error': 'denied'},
            {'Contents': None},
            {'Contents': [], 'KeyCount': True},
        ):
            with self.subTest(response=response):
                with self.assertRaises(PrefixGuardError):
                    classify(self.plan, response)

    def test_reject_contradictory_count(self):
        data = self.listing('data/part-1.parquet')
        data['KeyCount'] = 0

        with self.assertRaises(PrefixGuardError):
            classify(self.plan, data)

    def test_reject_truncation(self):
        data = self.listing()
        data['IsTruncated'] = True

        with self.assertRaises(PrefixGuardError):
            classify(self.plan, data)

    def test_reject_duplicate_key(self):
        with self.assertRaises(PrefixGuardError):
            classify(
                self.plan,
                self.listing('data/p', 'data/p')
            )

    def test_reject_bad_size(self):
        data = self.listing('data/p')
        data['Contents'][0]['Size'] = '2'

        with self.assertRaises(PrefixGuardError):
            classify(self.plan, data)

    def test_reject_wrong_target(self):
        plan = copy.deepcopy(self.plan)

        plan['base_uri'] = plan['base_uri'].replace(
            'health-processed',
            'health-raw'
        )

        with self.assertRaises(PrefixGuardError):
            classify(plan, self.listing())

    def test_reject_published_plan(self):
        plan = copy.deepcopy(self.plan)
        plan['published'] = True

        with self.assertRaises(PrefixGuardError):
            classify(plan, self.listing())


if __name__ == '__main__':
    unittest.main()
PY_TEST

# ========================================================
# 3. Formal S3 listing inspection runner
# ========================================================

cat > "$STAGE/scripts/task003/05g2a-inspect-visit-processed-prefix.sh" <<'SH_RUNNER'
#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo '#### TASK003 STEP05G2A PREFIX READONLY INSPECTION OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT
  echo "INSPECTION_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G2A PREFIX READONLY INSPECTION OUTPUT END ####'
  exit "$rc"
}
trap finish EXIT

[[ $# -eq 4 ]] || {
  echo "Usage: $0 STEP05F2_STATE PROCESSED_RUN_ID PLAN_JSON S3_LISTING_JSON"
  exit 2
}

F2="$1"
RUN_ID="$2"
PLAN="$3"
LISTING="$4"

[[ -s "$F2" && -s "$PLAN" && -s "$LISTING" ]] || {
  echo 'ERROR: input file missing'
  exit 2
}

# Verify the immutable plan against the exact STEP05F2 evidence.
python3 "$ROOT/apps/task003/verify_visit_processed_plan.py" \
  --root "$ROOT" \
  --f2-state "$F2" \
  --plan "$PLAN" \
  --run-id "$RUN_ID"

# Inspect supplied S3 listing.
# Only EMPTY returns success.
python3 "$ROOT/apps/task003/inspect_visit_processed_prefix.py" \
  --plan "$PLAN" \
  --listing "$LISTING"

echo 'PREFIX_PREFLIGHT=PASS'
echo 'S3_WRITE=NO'
echo 'DATABASE_WRITE=NO'
SH_RUNNER

# ========================================================
# 4. Syntax and tests
# ========================================================

echo '=== 1. Syntax and negative tests ==='

python3 - "$STAGE" <<'PY_AST'
import ast
import sys
from pathlib import Path

base = Path(sys.argv[1])

for rel in (
    'apps/task003/inspect_visit_processed_prefix.py',
    'tests/task003/test_visit_processed_prefix_guard.py',
):
    ast.parse(
        (base / rel).read_text(),
        filename=rel
    )

print('PYTHON_AST=PASS')
PY_AST

bash -n \
  "$STAGE/scripts/task003/05g2a-inspect-visit-processed-prefix.sh"

PYTHONPATH="$STAGE/apps/task003" \
python3 -m unittest discover \
  -s "$STAGE/tests/task003" \
  -p 'test_visit_processed_prefix_guard.py' -v

echo 'PREFIX_GUARD_TESTS=PASS'

# ========================================================
# 5. Canonical source installation
# ========================================================

echo '=== 2. Canonical source conflict check ==='

FILES=(
  apps/task003/inspect_visit_processed_prefix.py
  tests/task003/test_visit_processed_prefix_guard.py
  scripts/task003/05g2a-inspect-visit-processed-prefix.sh
)

GEN=scripts/task003/05g2a-prepare-visit-processed-prefix-guard.sh

for rel in "${FILES[@]}"; do
  if [[ -L "$ROOT/$rel" ]] || {
    [[ -e "$ROOT/$rel" ]] &&
    ! cmp -s "$STAGE/$rel" "$ROOT/$rel"
  }; then
    echo "ERROR: existing canonical file conflicts: $rel"
    exit 1
  fi
done

if [[ -L "$ROOT/$GEN" ]] || {
  [[ -e "$ROOT/$GEN" ]] &&
  ! cmp -s "${BASH_SOURCE[0]}" "$ROOT/$GEN"
}; then
  echo "ERROR: existing formal generator conflicts: $GEN"
  exit 1
fi

echo '=== 3. Install canonical files ==='

for rel in "${FILES[@]}"; do
  mkdir -p "$(dirname "$ROOT/$rel")"

  mode=644
  [[ "$rel" != *.sh ]] || mode=755

  install -m "$mode" "$STAGE/$rel" "$ROOT/$rel"
  echo "CANONICAL_SOURCE_READY=$rel"
done

mkdir -p "$ROOT/scripts/task003"

if [[ "${BASH_SOURCE[0]}" -ef "$ROOT/$GEN" ]]; then
  echo "CANONICAL_GENERATOR_REUSED=$GEN"
else
  install -m 755 "${BASH_SOURCE[0]}" "$ROOT/$GEN"
  echo "CANONICAL_GENERATOR_READY=$GEN"
fi

echo 'STEP05G2A_SOURCE_AND_TESTS=PASS'
echo 'REMOTE_S3_LISTING_EXECUTED=NO'
echo 'SPARK_APPLICATION_SUBMITTED=NO'
echo 'S3_WRITE=NO'
echo 'DATABASE_WRITE=NO'
echo 'GIT_COMMIT=NO'
