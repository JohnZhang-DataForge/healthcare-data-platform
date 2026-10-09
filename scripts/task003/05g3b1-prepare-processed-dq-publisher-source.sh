#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT="${HEALTHCARE_PROJECT_ROOT:-/data/spark/healthcare-data-platform}"
SOURCE="${BASH_SOURCE[0]:-}"
STAGE=''

echo '#### TASK003 STEP05G3B1 PROCESSED DQ PUBLISHER SOURCE OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT
  [[ -z "$STAGE" ]] || rm -rf -- "$STAGE"
  echo "INSTALL_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G3B1 PROCESSED DQ PUBLISHER SOURCE OUTPUT END ####'
  exit "$rc"
}
trap finish EXIT

[[ -n "$SOURCE" && -f "$SOURCE" ]] || {
  echo 'ERROR: installer must run from saved Bash file'
  exit 2
}

cd "$ROOT"

for rel in \
  apps/task003/build_visit_processed_dq.py \
  runtime/reports/task003/step05/processed-dq-builds/visit-proc-20261009t192437z-2081886/dq-result.json \
  runtime/reports/task003/step05/processed-dq-builds/visit-proc-20261009t192437z-2081886/run-state.json
do
  [[ -s "$rel" && ! -L "$rel" ]] || {
    echo "ERROR: prerequisite missing or unsafe: $rel"
    exit 2
  }
done

STAGE=$(mktemp -d /data/spark/temp_shell/g3b1.XXXXXXXX)

mkdir -p \
  "$STAGE/spark/apps/visit" \
  "$STAGE/tests/task003"

cat > "$STAGE/spark/apps/visit/publish_processed_dq.py" <<'PY_APP'
"""TASK-003 write-once Processed DQ publisher.

Publishes exactly dq/result.json.

Safety properties:
- validates immutable local G3A build evidence;
- canonical audit URI remains s3://;
- Spark/Hadoop transport uses s3a://;
- manifest.json must be absent before and after publication;
- never overwrites dq/result.json;
- if DQ already exists, only byte-identical reuse is accepted;
- published DQ is immediately read back and SHA256 verified;
- no PostgreSQL mutation;
- no Manifest publication.
"""

import argparse
import hashlib
import json
from pathlib import Path


EXPECTED_DQ_SHA256 = (
    '58e0ffc9e9b9a0ef5f34558807297b5a'
    'e2d6545d909fa340b0e2b713346b77c2'
)

EXPECTED_DQ_SIZE_BYTES = 2607

EXPECTED_RUN_ID = (
    'visit-proc-20261009t192437z-2081886'
)


def require(condition, message):
    if not condition:
        raise ValueError(
            'PROCESSED_DQ_PUBLISH_FAILED: '
            + message
        )


def sha256_bytes(blob):
    return hashlib.sha256(
        blob
    ).hexdigest()


def read_mounted_file(path):
    """Read normal files and safe Kubernetes projected-volume symlinks."""

    path = Path(path)

    try:
        root = path.parent.resolve(
            strict=True
        )

        resolved = path.resolve(
            strict=True
        )

    except (FileNotFoundError, RuntimeError) as exc:
        raise ValueError(
            'Unsafe mounted file: '
            + str(path)
        ) from exc

    require(
        resolved.is_file(),
        'mounted target is not regular file: '
        + str(path)
    )

    try:
        resolved.relative_to(root)

    except ValueError as exc:
        raise ValueError(
            'mounted file escapes directory: '
            + str(path)
        ) from exc

    return resolved.read_bytes()


def canonical_to_s3a(uri):
    require(
        isinstance(uri, str)
        and uri.startswith('s3://'),
        'canonical URI must use s3://'
    )

    return (
        's3a://'
        + uri[len('s3://'):]
    )


def validate_publication_inputs(
    plan,
    build_state,
    dq_bytes,
):
    require(
        (
            build_state.get('task'),
            build_state.get('step'),
            build_state.get('status'),
        )
        == (
            'TASK-003',
            'STEP-05G3A',
            'DQ_BUILT_NOT_PUBLISHED',
        ),
        'G3A build state'
    )

    require(
        build_state.get('run_id')
        == EXPECTED_RUN_ID
        == plan.get('run_id'),
        'run identity drift'
    )

    require(
        build_state.get(
            'processed_data_verified'
        )
        is True,
        'Processed data not verified'
    )

    require(
        build_state.get(
            's3_write_verified'
        )
        is True,
        'Processed S3 data not verified'
    )

    require(
        build_state.get(
            'candidate_published_verified'
        )
        is True,
        'Candidate data not verified'
    )

    require(
        build_state.get(
            'dq_published'
        )
        is False,
        'DQ already marked published'
    )

    require(
        build_state.get(
            'manifest_published'
        )
        is False,
        'Manifest already published'
    )

    require(
        build_state.get(
            'reservation_released'
        )
        is False,
        'Reservation released'
    )

    require(
        build_state.get(
            'postgresql_write'
        )
        is False,
        'unexpected PostgreSQL write'
    )

    actual_sha = sha256_bytes(
        dq_bytes
    )

    require(
        actual_sha
        == EXPECTED_DQ_SHA256
        == build_state.get(
            'dq_result_sha256'
        ),
        'DQ SHA256 drift'
    )

    require(
        len(dq_bytes)
        == EXPECTED_DQ_SIZE_BYTES
        == build_state.get(
            'dq_result_size_bytes'
        ),
        'DQ size drift'
    )

    dq = json.loads(
        dq_bytes
    )

    require(
        (
            dq.get('task'),
            dq.get('step'),
            dq.get('status'),
        )
        == (
            'TASK-003',
            'STEP-05G3',
            'PASS',
        ),
        'DQ content status'
    )

    require(
        dq.get('run_id')
        == EXPECTED_RUN_ID,
        'DQ run identity'
    )

    require(
        dq.get('dq_uri')
        == plan.get('dq_uri')
        == build_state.get('dq_uri'),
        'DQ URI drift'
    )

    require(
        dq.get('manifest_uri')
        == plan.get('manifest_uri')
        == build_state.get(
            'manifest_uri'
        ),
        'Manifest URI drift'
    )

    require(
        dq['publication_gate']
        ['manifest_published_at_build_time']
        is False,
        'DQ claims Manifest already published'
    )

    require(
        dq['publication_gate']
        ['reservation_must_remain_held']
        is True,
        'DQ Reservation gate drift'
    )

    require(
        dq['verification']
        ['s3_write_verified']
        is True,
        'DQ data verification drift'
    )

    require(
        dq['verification']
        ['postgresql_write']
        is False,
        'DQ PostgreSQL state drift'
    )

    return dq


def hadoop_read_all(
    spark,
    fs,
    path,
):
    jvm = spark.sparkContext._jvm
    conf = (
        spark.sparkContext
        ._jsc
        .hadoopConfiguration()
    )

    stream = fs.open(path)
    output = (
        jvm.java.io
        .ByteArrayOutputStream()
    )

    try:
        jvm.org.apache.hadoop.io.IOUtils.copyBytes(
            stream,
            output,
            conf,
            False,
        )

        return bytes(
            output.toByteArray()
        )

    finally:
        stream.close()
        output.close()


def publish_dq(
    spark,
    dq_local_path,
    dq_bytes,
    plan,
):
    jvm = spark.sparkContext._jvm
    conf = (
        spark.sparkContext
        ._jsc
        .hadoopConfiguration()
    )

    dq_uri = plan['dq_uri']
    manifest_uri = plan['manifest_uri']

    dq_transport = canonical_to_s3a(
        dq_uri
    )

    manifest_transport = canonical_to_s3a(
        manifest_uri
    )

    dq_path = (
        jvm.org.apache.hadoop.fs.Path(
            dq_transport
        )
    )

    manifest_path = (
        jvm.org.apache.hadoop.fs.Path(
            manifest_transport
        )
    )

    fs = dq_path.getFileSystem(
        conf
    )

    require(
        not fs.exists(
            manifest_path
        ),
        'Manifest exists before DQ publication'
    )

    publication_status = None

    if fs.exists(dq_path):

        existing = hadoop_read_all(
            spark,
            fs,
            dq_path,
        )

        require(
            existing == dq_bytes,
            'existing DQ object conflicts with local artifact'
        )

        publication_status = (
            'REUSED_IDENTICAL'
        )

    else:
        local_path = (
            jvm.org.apache.hadoop.fs.Path(
                str(
                    Path(
                        dq_local_path
                    ).resolve(
                        strict=True
                    )
                )
            )
        )

        # overwrite=False provides write-once behavior.
        fs.copyFromLocalFile(
            False,
            False,
            local_path,
            dq_path,
        )

        publication_status = (
            'CREATED'
        )

    require(
        fs.exists(dq_path),
        'DQ object missing after publication'
    )

    persisted = hadoop_read_all(
        spark,
        fs,
        dq_path,
    )

    require(
        persisted == dq_bytes,
        'DQ readback bytes differ'
    )

    persisted_sha = sha256_bytes(
        persisted
    )

    require(
        persisted_sha
        == EXPECTED_DQ_SHA256,
        'DQ readback SHA drift'
    )

    require(
        not fs.exists(
            manifest_path
        ),
        'Manifest appeared during DQ publication'
    )

    return {
        'status':
            'DQ_PUBLICATION_PASS',

        'publication_status':
            publication_status,

        'run_id':
            EXPECTED_RUN_ID,

        'dq_uri':
            dq_uri,

        'dq_sha256':
            persisted_sha,

        'dq_size_bytes':
            len(persisted),

        'dq_published':
            True,

        'dq_readback_verified':
            True,

        'manifest_uri':
            manifest_uri,

        'manifest_published':
            False,

        'reservation_release_requested':
            False,

        'postgresql_write':
            False,
    }


def main():
    parser = argparse.ArgumentParser(
        description=__doc__
    )

    parser.add_argument(
        '--dq-file',
        type=Path,
        required=True,
    )

    parser.add_argument(
        '--build-state',
        type=Path,
        required=True,
    )

    parser.add_argument(
        '--plan',
        type=Path,
        required=True,
    )

    args = parser.parse_args()

    dq_bytes = read_mounted_file(
        args.dq_file
    )

    build_state = json.loads(
        read_mounted_file(
            args.build_state
        )
    )

    plan = json.loads(
        read_mounted_file(
            args.plan
        )
    )

    validate_publication_inputs(
        plan,
        build_state,
        dq_bytes,
    )

    from pyspark.sql import SparkSession

    spark = (
        SparkSession.builder
        .appName(
            'task003-processed-dq-publisher'
        )
        .getOrCreate()
    )

    try:
        result = publish_dq(
            spark,
            args.dq_file,
            dq_bytes,
            plan,
        )

        print(
            'PROCESSED_DQ_PUBLICATION_RESULT='
            + json.dumps(
                result,
                sort_keys=True,
            )
        )

    finally:
        spark.stop()


if __name__ == '__main__':
    main()
PY_APP

cat > "$STAGE/tests/task003/test_processed_dq_publisher.py" <<'PY_TEST'
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(
    0,
    str(ROOT / 'spark/apps/visit')
)

from publish_processed_dq import (
    EXPECTED_DQ_SHA256,
    EXPECTED_DQ_SIZE_BYTES,
    EXPECTED_RUN_ID,
    canonical_to_s3a,
    read_mounted_file,
    validate_publication_inputs,
)


def fixture():
    # Fixed-size synthetic bytes are not used for the
    # successful validation test, because production constants
    # intentionally pin the real G3A artifact.
    plan = {
        'run_id':
            EXPECTED_RUN_ID,

        'dq_uri':
            's3://health-processed/x/dq/result.json',

        'manifest_uri':
            's3://health-processed/x/manifest.json',
    }

    state = {
        'task':
            'TASK-003',

        'step':
            'STEP-05G3A',

        'status':
            'DQ_BUILT_NOT_PUBLISHED',

        'run_id':
            EXPECTED_RUN_ID,

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

        'dq_result_sha256':
            EXPECTED_DQ_SHA256,

        'dq_result_size_bytes':
            EXPECTED_DQ_SIZE_BYTES,

        'dq_uri':
            plan['dq_uri'],

        'manifest_uri':
            plan['manifest_uri'],
    }

    return plan, state


class DQPublisherTests(
    unittest.TestCase
):

    def test_uri_conversion(self):
        self.assertEqual(
            canonical_to_s3a(
                's3://health-processed/a'
            ),
            's3a://health-processed/a',
        )

    def test_noncanonical_uri_rejected(self):
        with self.assertRaises(
            ValueError
        ):
            canonical_to_s3a(
                's3a://health-processed/a'
            )

    def test_kubernetes_projected_file_allowed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)

            version = (
                root
                / '..20261009_230000'
            )

            version.mkdir()

            target = (
                version
                / 'dq-result.json'
            )

            target.write_bytes(
                b'hello\n'
            )

            (
                root
                / '..data'
            ).symlink_to(
                version.name,
                target_is_directory=True,
            )

            projected = (
                root
                / 'dq-result.json'
            )

            projected.symlink_to(
                Path('..data')
                / 'dq-result.json'
            )

            self.assertEqual(
                read_mounted_file(
                    projected
                ),
                b'hello\n',
            )

    def test_projected_file_escape_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)

            mount = base / 'mount'
            mount.mkdir()

            outside = (
                base
                / 'outside.json'
            )

            outside.write_bytes(
                b'{}\n'
            )

            link = (
                mount
                / 'dq-result.json'
            )

            link.symlink_to(
                Path('..')
                / 'outside.json'
            )

            with self.assertRaisesRegex(
                ValueError,
                'escapes directory',
            ):
                read_mounted_file(
                    link
                )

    def test_manifest_published_rejected_before_sha(self):
        plan, state = fixture()

        state['manifest_published'] = True

        with self.assertRaisesRegex(
            ValueError,
            'Manifest already published',
        ):
            validate_publication_inputs(
                plan,
                state,
                b'x',
            )

    def test_reservation_released_rejected_before_sha(self):
        plan, state = fixture()

        state['reservation_released'] = True

        with self.assertRaisesRegex(
            ValueError,
            'Reservation released',
        ):
            validate_publication_inputs(
                plan,
                state,
                b'x',
            )

    def test_dq_marked_published_rejected_before_sha(self):
        plan, state = fixture()

        state['dq_published'] = True

        with self.assertRaisesRegex(
            ValueError,
            'DQ already marked published',
        ):
            validate_publication_inputs(
                plan,
                state,
                b'x',
            )

    def test_sha_drift_rejected(self):
        plan, state = fixture()

        with self.assertRaisesRegex(
            ValueError,
            'DQ SHA256 drift',
        ):
            validate_publication_inputs(
                plan,
                state,
                b'x' * EXPECTED_DQ_SIZE_BYTES,
            )

    def test_constants_match_real_artifact(self):
        path = (
            ROOT
            / 'runtime/reports/task003/step05/'
            'processed-dq-builds/'
            'visit-proc-20261009t192437z-2081886/'
            'dq-result.json'
        )

        if not path.is_file():
            self.skipTest(
                'real runtime artifact unavailable'
            )

        blob = path.read_bytes()

        self.assertEqual(
            len(blob),
            EXPECTED_DQ_SIZE_BYTES,
        )

        self.assertEqual(
            hashlib.sha256(
                blob
            ).hexdigest(),
            EXPECTED_DQ_SHA256,
        )


if __name__ == '__main__':
    unittest.main()
PY_TEST

echo '=== 1. Syntax and unit tests ==='

python3 - "$STAGE" <<'PY_AST'
import ast
import sys
from pathlib import Path

root = Path(sys.argv[1])

for rel in (
    'spark/apps/visit/publish_processed_dq.py',
    'tests/task003/test_processed_dq_publisher.py',
):
    ast.parse(
        (root / rel).read_text(),
        filename=rel,
    )

print('DQ_PUBLISHER_PYTHON_AST=PASS')
PY_AST

PYTHONPATH="$STAGE/spark/apps/visit" \
python3 -m unittest discover \
  -s "$STAGE/tests/task003" \
  -p 'test_processed_dq_publisher.py' \
  -v

echo 'DQ_PUBLISHER_TESTS=PASS'

echo '=== 2. Verify against real G3A DQ artifact ==='

PYTHONPATH="$STAGE/spark/apps/visit" \
python3 - \
  "$ROOT/runtime/reports/task003/step05/processed-plans/visit-proc-20261009t192437z-2081886/plan.json" \
  "$ROOT/runtime/reports/task003/step05/processed-dq-builds/visit-proc-20261009t192437z-2081886/run-state.json" \
  "$ROOT/runtime/reports/task003/step05/processed-dq-builds/visit-proc-20261009t192437z-2081886/dq-result.json" \
  <<'PY_REAL'
import json
import sys
from pathlib import Path

from publish_processed_dq import (
    validate_publication_inputs,
)

plan = json.loads(
    Path(sys.argv[1]).read_bytes()
)

state = json.loads(
    Path(sys.argv[2]).read_bytes()
)

dq_bytes = Path(
    sys.argv[3]
).read_bytes()

dq = validate_publication_inputs(
    plan,
    state,
    dq_bytes,
)

print('REAL_DQ_PUBLICATION_INPUT=PASS')
print('DQ_RUN_ID=' + dq['run_id'])
print('DQ_URI=' + dq['dq_uri'])
print('MANIFEST_URI=' + dq['manifest_uri'])
PY_REAL

echo '=== 3. Publisher safety boundary ==='

python3 - \
  "$STAGE/spark/apps/visit/publish_processed_dq.py" \
  <<'PY_STATIC'
import sys
from pathlib import Path

source = Path(sys.argv[1]).read_text()

required = (
    'fs.copyFromLocalFile(',
    "'REUSED_IDENTICAL'",
    "'CREATED'",
    'DQ_PUBLICATION_PASS',
    'Manifest exists before DQ publication',
    'Manifest appeared during DQ publication',
    "'manifest_published':",
    "'postgresql_write':",
)

for token in required:
    assert token in source, token

for forbidden in (
    'overwrite=True',
    'copyFromLocalFile(False, True',
    'manifest_path,',
    '.write.parquet',
    'INSERT INTO',
    'UPDATE ',
    'DELETE FROM',
):
    assert forbidden not in source, forbidden

print('DQ_WRITE_ONCE_POLICY=PASS')
print('DQ_READBACK_SHA_POLICY=PASS')
print('MANIFEST_LAST_POLICY=PASS')
print('DATABASE_MUTATION_ABSENT=PASS')
PY_STATIC

echo '=== 4. Canonical conflict check ==='

FILES=(
  spark/apps/visit/publish_processed_dq.py
  tests/task003/test_processed_dq_publisher.py
)

GEN=scripts/task003/05g3b1-prepare-processed-dq-publisher-source.sh

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

echo '=== 5. Install canonical source ==='

for rel in "${FILES[@]}"; do
  mkdir -p "$(dirname "$ROOT/$rel")"

  if [[ -f "$ROOT/$rel" ]] &&
     cmp -s "$STAGE/$rel" "$ROOT/$rel"
  then
    echo "CANONICAL_SOURCE_REUSED=$rel"
  else
    install \
      -m 644 \
      "$STAGE/$rel" \
      "$ROOT/$rel"

    echo "CANONICAL_SOURCE_READY=$rel"
  fi
done

mkdir -p "$ROOT/scripts/task003"

if [[ -f "$ROOT/$GEN" ]]; then
  echo "CANONICAL_GENERATOR_REUSED=$GEN"
else
  install \
    -m 755 \
    "$SOURCE" \
    "$ROOT/$GEN"

  echo "CANONICAL_GENERATOR_READY=$GEN"
fi

echo 'STEP05G3B1_SOURCE_AND_TESTS=PASS'

echo 'DQ_PUBLISHER_EXECUTED=NO'
echo 'DQ_PUBLISHED=NO'
echo 'MANIFEST_PUBLISHED=NO'
echo 'RESERVATION_RELEASED=NO'

echo 'K8S_MUTATION=NO'
echo 'S3_MUTATION=NO'
echo 'DATABASE_MUTATION=NO'
echo 'GIT_COMMIT=NO'
