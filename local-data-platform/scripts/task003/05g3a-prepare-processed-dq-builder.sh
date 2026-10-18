#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT="${HEALTHCARE_PROJECT_ROOT:-/data/spark/healthcare-data-platform}"
SOURCE="${BASH_SOURCE[0]:-}"
STAGE=''

echo '#### TASK003 STEP05G3A PROCESSED DQ BUILDER SOURCE OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  [[ -z "$STAGE" ]] || rm -rf -- "$STAGE"

  echo "INSTALL_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G3A PROCESSED DQ BUILDER SOURCE OUTPUT END ####'
  exit "$rc"
}

trap finish EXIT

[[ -n "$SOURCE" && -f "$SOURCE" ]] || {
  echo 'ERROR: installer must run from saved Bash file'
  exit 2
}

cd "$ROOT"

STAGE=$(
  mktemp -d \
    /data/spark/temp_shell/g3a.XXXXXXXX
)

mkdir -p \
  "$STAGE/apps/task003" \
  "$STAGE/tests/task003" \
  "$STAGE/scripts/task003"

# ============================================================
# 1. Pure deterministic DQ builder
# ============================================================

cat > "$STAGE/apps/task003/build_visit_processed_dq.py" <<'PY_APP'
"""Build deterministic TASK-003 Processed Visit Candidate DQ result.

This module does not write S3 or PostgreSQL.

The DQ artifact is derived only from:
- the immutable Processed publication Plan;
- the independently verified persisted-data state/result;
- the approved Git data-verification checkpoint.

Publication of dq/result.json is a separate step.
"""

import hashlib
import json


EXPECTED_GIT_CHECKPOINT = (
    '16b264cd5260b7d4a155e9ffc4d61d165b7c4d21'
)

EXPECTED_ROWS = 5799
EXPECTED_PERSONS = 113
EXPECTED_FIELDS = 36

EXPECTED_PERSON_FINGERPRINT = (
    'e4f63203932043bd7a2a64a5241740'
    'faf93494b7e7421699b5b462583ba5dbb8'
)

EXPECTED_PROCESSING_RUN_ID = (
    'encounter-20261008T234726Z-1658454'
)

EXPECTED_RAW_PUBLISH_RUN_ID = (
    'encounter-raw-20261009T005128Z-1681690'
)

BUSINESS_KEY = [
    'source_system',
    'source_encounter_id',
]


def require(condition, message):
    if not condition:
        raise ValueError(
            'PROCESSED_DQ_BUILD_FAILED: '
            + message
        )


def canonical_json_bytes(value):
    return (
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
        )
        + '\n'
    ).encode('utf-8')


def sha256_bytes(blob):
    return hashlib.sha256(
        blob
    ).hexdigest()


def validate_inputs(
    plan,
    readback_state,
    readback_result,
    readback_result_bytes,
    git_checkpoint,
):
    require(
        git_checkpoint
        == EXPECTED_GIT_CHECKPOINT,
        'Git checkpoint drift'
    )

    require(
        plan.get('run_id')
        == readback_state.get('run_id'),
        'Plan/readback run identity drift'
    )

    require(
        (
            readback_state.get('task'),
            readback_state.get('step'),
            readback_state.get('status'),
        )
        == (
            'TASK-003',
            'STEP-05G2C2C3D2B2',
            'INDEPENDENT_S3_READBACK_PASS',
        ),
        'independent readback state'
    )

    require(
        readback_state.get(
            'validator_spark_state'
        )
        == 'COMPLETED',
        'Validator Spark state'
    )

    require(
        readback_state.get(
            'candidate_published_verified'
        )
        is True,
        'Candidate publication not verified'
    )

    require(
        readback_state.get(
            's3_write_verified'
        )
        is True,
        'S3 write not verified'
    )

    require(
        readback_state.get(
            'dq_published'
        )
        is False,
        'DQ already marked published'
    )

    require(
        readback_state.get(
            'manifest_published'
        )
        is False,
        'Manifest already marked published'
    )

    require(
        readback_state.get(
            'postgresql_write'
        )
        is False,
        'unexpected PostgreSQL write'
    )

    require(
        readback_state.get(
            'reservation_released'
        )
        is False,
        'Reservation already released'
    )

    result_sha = sha256_bytes(
        readback_result_bytes
    )

    require(
        result_sha
        == readback_state.get(
            'validation_result_sha256'
        ),
        'independent validation result SHA drift'
    )

    require(
        readback_result.get('status')
        == 'INDEPENDENT_S3_READBACK_PASS',
        'independent validation result status'
    )

    require(
        readback_result.get('data_uri')
        == plan.get('data_uri'),
        'data URI drift'
    )

    require(
        readback_result.get('rows')
        == EXPECTED_ROWS
        == plan.get('expected_rows'),
        'row count drift'
    )

    require(
        readback_result.get(
            'unique_business_keys'
        )
        == EXPECTED_ROWS,
        'business-key uniqueness drift'
    )

    require(
        readback_result.get(
            'business_key'
        )
        == BUSINESS_KEY,
        'business key drift'
    )

    require(
        readback_result.get(
            'referenced_persons'
        )
        == EXPECTED_PERSONS
        == plan.get('expected_persons'),
        'Person count drift'
    )

    require(
        readback_result.get(
            'contract_field_count'
        )
        == EXPECTED_FIELDS,
        'Contract field count drift'
    )

    require(
        readback_result.get(
            'visit_occurrence_id_present'
        )
        is False,
        'final visit_occurrence_id appeared early'
    )

    require(
        readback_result.get(
            'person_map_fingerprint'
        )
        == EXPECTED_PERSON_FINGERPRINT,
        'Person map fingerprint drift'
    )

    require(
        readback_result.get(
            'processing_run_id'
        )
        == EXPECTED_PROCESSING_RUN_ID,
        'processing_run_id drift'
    )

    require(
        readback_result.get(
            'raw_publish_run_id'
        )
        == EXPECTED_RAW_PUBLISH_RUN_ID,
        'raw_publish_run_id drift'
    )

    require(
        readback_result.get(
            'source_system'
        )
        == 'synthea',
        'source_system drift'
    )

    require(
        readback_result.get(
            'class_counts'
        )
        == plan.get('class_counts'),
        'class distribution drift'
    )

    require(
        readback_result.get(
            's3_write_verified'
        )
        is True,
        'result S3 verification'
    )

    require(
        readback_result.get(
            'candidate_published_verified'
        )
        is True,
        'result Candidate verification'
    )

    require(
        readback_result.get(
            'dq_published'
        )
        is False,
        'result prematurely claims DQ publication'
    )

    require(
        readback_result.get(
            'manifest_published'
        )
        is False,
        'result prematurely claims Manifest publication'
    )

    require(
        readback_result.get(
            'postgresql_write'
        )
        is False,
        'result PostgreSQL write drift'
    )

    dq_uri = plan.get('dq_uri')
    manifest_uri = plan.get(
        'manifest_uri'
    )

    require(
        isinstance(dq_uri, str)
        and dq_uri.endswith(
            '/dq/result.json'
        ),
        'invalid DQ URI'
    )

    require(
        isinstance(manifest_uri, str)
        and manifest_uri.endswith(
            '/manifest.json'
        ),
        'invalid Manifest URI'
    )

    require(
        dq_uri != manifest_uri,
        'DQ/Manifest URI collision'
    )

    return result_sha


def build_dq(
    plan,
    readback_state,
    readback_result,
    readback_result_bytes,
    git_checkpoint,
):
    result_sha = validate_inputs(
        plan,
        readback_state,
        readback_result,
        readback_result_bytes,
        git_checkpoint,
    )

    dq = {
        'schema_version':
            'task003-visit-processed-dq-v1',

        'task':
            'TASK-003',

        'step':
            'STEP-05G3',

        'status':
            'PASS',

        'run_id':
            plan['run_id'],

        'entity':
            'visit_occurrence',

        'source_system':
            'synthea',

        'data_uri':
            plan['data_uri'],

        'dq_uri':
            plan['dq_uri'],

        'manifest_uri':
            plan['manifest_uri'],

        'metrics': {
            'rows':
                EXPECTED_ROWS,

            'unique_business_keys':
                EXPECTED_ROWS,

            'business_key':
                BUSINESS_KEY,

            'referenced_persons':
                EXPECTED_PERSONS,

            'contract_field_count':
                EXPECTED_FIELDS,

            'visit_occurrence_id_present':
                False,

            'class_counts':
                readback_result[
                    'class_counts'
                ],
        },

        'lineage': {
            'processing_run_id':
                EXPECTED_PROCESSING_RUN_ID,

            'raw_publish_run_id':
                EXPECTED_RAW_PUBLISH_RUN_ID,

            'person_map_fingerprint':
                EXPECTED_PERSON_FINGERPRINT,
        },

        'verification': {
            'independent_s3_readback':
                True,

            'candidate_published_verified':
                True,

            's3_write_verified':
                True,

            'writer_database_write':
                False,

            'postgresql_write':
                False,
        },

        'publication_gate': {
            'dq_result_status':
                'PASS',

            'manifest_may_be_published_after_dq':
                True,

            'manifest_published_at_build_time':
                False,

            'reservation_must_remain_held':
                True,
        },

        'evidence': {
            'processed_data_verified_git_commit':
                git_checkpoint,

            'independent_validation_result_sha256':
                result_sha,

            'independent_readback_state_sha256':
                sha256_bytes(
                    canonical_json_bytes(
                        readback_state
                    )
                ),
        },
    }

    return dq
PY_APP

# ============================================================
# 2. Unit tests
# ============================================================

cat > "$STAGE/tests/task003/test_visit_processed_dq_builder.py" <<'PY_TEST'
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(
    0,
    str(ROOT / 'apps/task003')
)

from build_visit_processed_dq import (
    EXPECTED_GIT_CHECKPOINT,
    EXPECTED_PERSON_FINGERPRINT,
    EXPECTED_PROCESSING_RUN_ID,
    EXPECTED_RAW_PUBLISH_RUN_ID,
    build_dq,
    canonical_json_bytes,
    sha256_bytes,
)


CLASS_COUNTS = {
    'ambulatory': 2605,
    'emergency': 334,
    'home': 18,
    'hospice': 10,
    'inpatient': 74,
    'outpatient': 992,
    'snf': 12,
    'urgentcare': 350,
    'virtual': 27,
    'wellness': 1377,
}


def fixtures():
    plan = {
        'run_id':
            'visit-proc-test',

        'data_uri':
            's3://health-processed/x/data/',

        'dq_uri':
            's3://health-processed/x/dq/result.json',

        'manifest_uri':
            's3://health-processed/x/manifest.json',

        'expected_rows':
            5799,

        'expected_persons':
            113,

        'class_counts':
            CLASS_COUNTS,
    }

    result = {
        'status':
            'INDEPENDENT_S3_READBACK_PASS',

        'data_uri':
            plan['data_uri'],

        'rows':
            5799,

        'unique_business_keys':
            5799,

        'business_key': [
            'source_system',
            'source_encounter_id',
        ],

        'referenced_persons':
            113,

        'contract_field_count':
            36,

        'visit_occurrence_id_present':
            False,

        'person_map_fingerprint':
            EXPECTED_PERSON_FINGERPRINT,

        'processing_run_id':
            EXPECTED_PROCESSING_RUN_ID,

        'raw_publish_run_id':
            EXPECTED_RAW_PUBLISH_RUN_ID,

        'source_system':
            'synthea',

        'class_counts':
            CLASS_COUNTS,

        's3_write_verified':
            True,

        'candidate_published_verified':
            True,

        'dq_published':
            False,

        'manifest_published':
            False,

        'postgresql_write':
            False,
    }

    result_bytes = canonical_json_bytes(
        result
    )

    state = {
        'task':
            'TASK-003',

        'step':
            'STEP-05G2C2C3D2B2',

        'status':
            'INDEPENDENT_S3_READBACK_PASS',

        'run_id':
            plan['run_id'],

        'validator_spark_state':
            'COMPLETED',

        'candidate_published_verified':
            True,

        's3_write_verified':
            True,

        'dq_published':
            False,

        'manifest_published':
            False,

        'postgresql_write':
            False,

        'reservation_released':
            False,

        'validation_result_sha256':
            sha256_bytes(
                result_bytes
            ),
    }

    return (
        plan,
        state,
        result,
        result_bytes,
    )


class DQBuilderTests(
    unittest.TestCase
):

    def test_valid_dq(self):
        (
            plan,
            state,
            result,
            result_bytes,
        ) = fixtures()

        dq = build_dq(
            plan,
            state,
            result,
            result_bytes,
            EXPECTED_GIT_CHECKPOINT,
        )

        self.assertEqual(
            dq['status'],
            'PASS',
        )

        self.assertEqual(
            dq['metrics']['rows'],
            5799,
        )

        self.assertTrue(
            dq['verification']
            ['s3_write_verified']
        )

        self.assertFalse(
            dq['publication_gate']
            ['manifest_published_at_build_time']
        )

    def test_stable_output(self):
        args = fixtures()

        one = build_dq(
            *args,
            EXPECTED_GIT_CHECKPOINT,
        )

        two = build_dq(
            *args,
            EXPECTED_GIT_CHECKPOINT,
        )

        self.assertEqual(
            canonical_json_bytes(one),
            canonical_json_bytes(two),
        )

    def test_git_checkpoint_drift(self):
        args = fixtures()

        with self.assertRaisesRegex(
            ValueError,
            'Git checkpoint',
        ):
            build_dq(
                *args,
                '0' * 40,
            )

    def test_row_drift(self):
        (
            plan,
            state,
            result,
            _,
        ) = fixtures()

        result['rows'] = 5798

        result_bytes = canonical_json_bytes(
            result
        )

        state[
            'validation_result_sha256'
        ] = sha256_bytes(
            result_bytes
        )

        with self.assertRaisesRegex(
            ValueError,
            'row count',
        ):
            build_dq(
                plan,
                state,
                result,
                result_bytes,
                EXPECTED_GIT_CHECKPOINT,
            )

    def test_person_fingerprint_drift(self):
        (
            plan,
            state,
            result,
            _,
        ) = fixtures()

        result[
            'person_map_fingerprint'
        ] = '0' * 64

        result_bytes = canonical_json_bytes(
            result
        )

        state[
            'validation_result_sha256'
        ] = sha256_bytes(
            result_bytes
        )

        with self.assertRaisesRegex(
            ValueError,
            'Person map fingerprint',
        ):
            build_dq(
                plan,
                state,
                result,
                result_bytes,
                EXPECTED_GIT_CHECKPOINT,
            )

    def test_class_drift(self):
        (
            plan,
            state,
            result,
            _,
        ) = fixtures()

        result['class_counts'] = (
            copy.deepcopy(
                CLASS_COUNTS
            )
        )

        result[
            'class_counts'
        ]['ambulatory'] -= 1

        result_bytes = canonical_json_bytes(
            result
        )

        state[
            'validation_result_sha256'
        ] = sha256_bytes(
            result_bytes
        )

        with self.assertRaisesRegex(
            ValueError,
            'class distribution',
        ):
            build_dq(
                plan,
                state,
                result,
                result_bytes,
                EXPECTED_GIT_CHECKPOINT,
            )

    def test_manifest_already_published_rejected(self):
        (
            plan,
            state,
            result,
            result_bytes,
        ) = fixtures()

        state[
            'manifest_published'
        ] = True

        with self.assertRaisesRegex(
            ValueError,
            'Manifest already',
        ):
            build_dq(
                plan,
                state,
                result,
                result_bytes,
                EXPECTED_GIT_CHECKPOINT,
            )

    def test_final_visit_id_rejected(self):
        (
            plan,
            state,
            result,
            _,
        ) = fixtures()

        result[
            'visit_occurrence_id_present'
        ] = True

        result_bytes = canonical_json_bytes(
            result
        )

        state[
            'validation_result_sha256'
        ] = sha256_bytes(
            result_bytes
        )

        with self.assertRaisesRegex(
            ValueError,
            'visit_occurrence_id',
        ):
            build_dq(
                plan,
                state,
                result,
                result_bytes,
                EXPECTED_GIT_CHECKPOINT,
            )


if __name__ == '__main__':
    unittest.main()
PY_TEST

# ============================================================
# 3. Canonical local DQ build runner
# ============================================================

cat > "$STAGE/scripts/task003/05g3a-build-processed-dq.sh" <<'RUNNER'
#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo '#### TASK003 STEP05G3A PROCESSED DQ BUILD OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  echo "DQ_BUILD_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G3A PROCESSED DQ BUILD OUTPUT END ####'
  exit "$rc"
}

trap finish EXIT

[[ $# -eq 4 ]] || {
  echo "Usage: $0 PLAN READBACK_STATE READBACK_RESULT GIT_CHECKPOINT"
  exit 2
}

PLAN="$1"
STATE="$2"
RESULT="$3"
CHECKPOINT="$4"

for path in \
  "$PLAN" \
  "$STATE" \
  "$RESULT"
do
  [[ -s "$path" && ! -L "$path" ]] || {
    echo "ERROR: missing or unsafe input: $path"
    exit 2
  }
done

cd "$ROOT"

git cat-file -e \
  "${CHECKPOINT}^{commit}"

git merge-base \
  --is-ancestor \
  "$CHECKPOINT" \
  HEAD

echo "DATA_VERIFIED_GIT_CHECKPOINT=$CHECKPOINT"
echo 'DATA_VERIFIED_CHECKPOINT_ANCESTRY=PASS'

RUN_ID=$(
  python3 -c '
import json,sys
print(json.load(open(sys.argv[1]))["run_id"])
' "$PLAN"
)

[[ "$RUN_ID" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$ ]] || {
  echo 'ERROR: unsafe run ID'
  exit 2
}

OUTDIR="$ROOT/runtime/reports/task003/step05/processed-dq-builds/$RUN_ID"

mkdir -p "$OUTDIR"

DQ_FILE="$OUTDIR/dq-result.json"
STATE_FILE="$OUTDIR/run-state.json"

TMP_DQ=$(
  mktemp \
    "$OUTDIR/.dq-result.XXXXXXXX"
)

TMP_STATE=$(
  mktemp \
    "$OUTDIR/.run-state.XXXXXXXX"
)

cleanup() {
  rm -f \
    "$TMP_DQ" \
    "$TMP_STATE"
}

trap 'cleanup; finish' EXIT

PYTHONPATH="$ROOT/apps/task003" \
python3 - \
  "$PLAN" \
  "$STATE" \
  "$RESULT" \
  "$CHECKPOINT" \
  "$TMP_DQ" \
  <<'PY_BUILD'
import json
import sys
from pathlib import Path

from build_visit_processed_dq import (
    build_dq,
    canonical_json_bytes,
)

plan_path = Path(sys.argv[1])
state_path = Path(sys.argv[2])
result_path = Path(sys.argv[3])
checkpoint = sys.argv[4]
target = Path(sys.argv[5])

plan = json.loads(
    plan_path.read_bytes()
)

state = json.loads(
    state_path.read_bytes()
)

result_bytes = (
    result_path.read_bytes()
)

result = json.loads(
    result_bytes
)

dq = build_dq(
    plan,
    state,
    result,
    result_bytes,
    checkpoint,
)

target.write_bytes(
    canonical_json_bytes(
        dq
    )
)

print('DQ_CONTENT_BUILD=PASS')
print('DQ_STATUS=' + dq['status'])
print('DQ_RUN_ID=' + dq['run_id'])
print('DQ_URI=' + dq['dq_uri'])
print('MANIFEST_URI=' + dq['manifest_uri'])
PY_BUILD

DQ_SHA=$(
  sha256sum "$TMP_DQ" |
  awk '{print $1}'
)

DQ_SIZE=$(
  wc -c \
    < "$TMP_DQ" |
  tr -d ' '
)

echo "DQ_SHA256=$DQ_SHA"
echo "DQ_SIZE_BYTES=$DQ_SIZE"

if [[ -e "$DQ_FILE" ]]; then

  [[ -f "$DQ_FILE" && ! -L "$DQ_FILE" ]] || {
    echo 'ERROR: unsafe existing DQ artifact'
    exit 1
  }

  if cmp -s "$TMP_DQ" "$DQ_FILE"; then
    echo 'DQ_LOCAL_ARTIFACT=REUSED_IDENTICAL'
  else
    echo 'ERROR: conflicting immutable local DQ artifact'
    exit 4
  fi

else
  mv "$TMP_DQ" "$DQ_FILE"
  TMP_DQ=''
  echo 'DQ_LOCAL_ARTIFACT=CREATED'
fi

python3 - \
  "$PLAN" \
  "$STATE" \
  "$RESULT" \
  "$DQ_FILE" \
  "$CHECKPOINT" \
  "$TMP_STATE" \
  <<'PY_STATE'
import hashlib
import json
import sys
from pathlib import Path

plan = Path(sys.argv[1])
readback_state = Path(sys.argv[2])
readback_result = Path(sys.argv[3])
dq = Path(sys.argv[4])
checkpoint = sys.argv[5]
target = Path(sys.argv[6])


def sha(path):
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


dq_obj = json.loads(
    dq.read_bytes()
)

state = {
    'task':
        'TASK-003',

    'step':
        'STEP-05G3A',

    'status':
        'DQ_BUILT_NOT_PUBLISHED',

    'run_id':
        dq_obj['run_id'],

    'data_verified_git_checkpoint':
        checkpoint,

    'plan_sha256':
        sha(plan),

    'independent_readback_state_sha256':
        sha(readback_state),

    'independent_validation_result_sha256':
        sha(readback_result),

    'dq_result_sha256':
        sha(dq),

    'dq_result_size_bytes':
        dq.stat().st_size,

    'dq_uri':
        dq_obj['dq_uri'],

    'manifest_uri':
        dq_obj['manifest_uri'],

    'processed_data_verified':
        True,

    's3_write_verified':
        True,

    'candidate_published_verified':
        True,

    'dq_published':
        False,

    'manifest_published':
        False,

    'reservation_released':
        False,

    'postgresql_write':
        False,
}

target.write_text(
    json.dumps(
        state,
        indent=2,
        sort_keys=True,
    )
    + '\n'
)

print('DQ_BUILD_STATE=PASS')
PY_STATE

if [[ -e "$STATE_FILE" ]]; then

  [[ -f "$STATE_FILE" && ! -L "$STATE_FILE" ]] || {
    echo 'ERROR: unsafe existing DQ state'
    exit 1
  }

  if cmp -s "$TMP_STATE" "$STATE_FILE"; then
    echo 'DQ_BUILD_STATE_ARTIFACT=REUSED_IDENTICAL'
  else
    echo 'ERROR: conflicting immutable DQ build state'
    exit 4
  fi

else
  mv "$TMP_STATE" "$STATE_FILE"
  TMP_STATE=''
  echo 'DQ_BUILD_STATE_ARTIFACT=CREATED'
fi

echo "DQ_LOCAL_FILE=$DQ_FILE"
echo "DQ_BUILD_STATE_FILE=$STATE_FILE"

echo 'STEP05G3A_PROCESSED_DQ_BUILD=PASS'

echo 'PROCESSED_DATA_VERIFIED=YES'
echo 'S3_WRITE_VERIFIED=YES'
echo 'CANDIDATE_PUBLISHED_VERIFIED=YES'

echo 'DQ_BUILT=YES'
echo 'DQ_PUBLISHED=NO'
echo 'MANIFEST_PUBLISHED=NO'

echo 'RESERVATION_RELEASED=NO'
echo 'S3_MUTATION=NO'
echo 'DATABASE_WRITE=NO'
RUNNER

# ============================================================
# 4. Static checks / tests
# ============================================================

echo '=== 1. Syntax and unit tests ==='

python3 - "$STAGE" <<'PY_AST'
import ast
import sys
from pathlib import Path

root = Path(sys.argv[1])

for rel in (
    'apps/task003/build_visit_processed_dq.py',
    'tests/task003/test_visit_processed_dq_builder.py',
):
    ast.parse(
        (root / rel).read_text(),
        filename=rel,
    )

print('PROCESSED_DQ_PYTHON_AST=PASS')
PY_AST

bash -n \
  "$STAGE/scripts/task003/05g3a-build-processed-dq.sh"

echo 'PROCESSED_DQ_RUNNER_BASH_SYNTAX=PASS'

PYTHONPATH="$STAGE/apps/task003" \
python3 -m unittest discover \
  -s "$STAGE/tests/task003" \
  -p 'test_visit_processed_dq_builder.py' \
  -v

echo 'PROCESSED_DQ_TESTS=PASS'

echo '=== 2. Publication boundary checks ==='

python3 - "$STAGE" <<'PY_STATIC'
import sys
from pathlib import Path

root = Path(sys.argv[1])

app = (
    root
    / 'apps/task003/build_visit_processed_dq.py'
).read_text()

runner = (
    root
    / 'scripts/task003/05g3a-build-processed-dq.sh'
).read_text()

required = (
    'DQ_BUILT_NOT_PUBLISHED',
    'DQ_PUBLISHED=NO',
    'MANIFEST_PUBLISHED=NO',
    'RESERVATION_RELEASED=NO',
    'S3_MUTATION=NO',
)

for token in required:
    assert token in runner, token

for source in (
    app,
    runner,
):
    for forbidden in (
        'aws s3 cp',
        'aws s3api put-object',
        'kubectl create',
        'kubectl apply',
        'kubectl delete',
        'INSERT INTO',
        'UPDATE ',
        'DELETE FROM',
    ):
        assert forbidden not in source, forbidden

assert (
    'manifest_may_be_published_after_dq'
    in app
)

assert (
    "'manifest_published_at_build_time':"
    in app
)

print('DQ_BUILD_ONLY_BOUNDARY=PASS')
print('S3_MUTATION_PATH_ABSENT=PASS')
print('DATABASE_MUTATION_PATH_ABSENT=PASS')
print('MANIFEST_LAST_POLICY_PRESENT=PASS')
PY_STATIC

# ============================================================
# 5. Install canonical source + generator
# ============================================================

echo '=== 3. Canonical conflict check ==='

FILES=(
  apps/task003/build_visit_processed_dq.py
  tests/task003/test_visit_processed_dq_builder.py
  scripts/task003/05g3a-build-processed-dq.sh
)

GEN=scripts/task003/05g3a-prepare-processed-dq-builder.sh

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
  ! cmp -s "$SOURCE" "$ROOT/$GEN"
}; then
  echo "ERROR: canonical generator conflict: $GEN"
  exit 1
fi

echo '=== 4. Install canonical source ==='

for rel in "${FILES[@]}"; do

  mkdir -p \
    "$(dirname "$ROOT/$rel")"

  if [[ -f "$ROOT/$rel" ]] &&
     cmp -s "$STAGE/$rel" "$ROOT/$rel"
  then
    echo "CANONICAL_SOURCE_REUSED=$rel"
  else
    install \
      -m 755 \
      "$STAGE/$rel" \
      "$ROOT/$rel"

    case "$rel" in
      *.py)
        chmod 644 "$ROOT/$rel"
        ;;
    esac

    echo "CANONICAL_SOURCE_READY=$rel"
  fi

done

if [[ -f "$ROOT/$GEN" ]]; then
  echo "CANONICAL_GENERATOR_REUSED=$GEN"
else
  install \
    -m 755 \
    "$SOURCE" \
    "$ROOT/$GEN"

  echo "CANONICAL_GENERATOR_READY=$GEN"
fi

echo 'STEP05G3A_SOURCE_AND_TESTS=PASS'

echo 'DQ_PUBLISHED=NO'
echo 'MANIFEST_PUBLISHED=NO'
echo 'S3_MUTATION=NO'
echo 'DATABASE_MUTATION=NO'
echo 'GIT_COMMIT=NO'
