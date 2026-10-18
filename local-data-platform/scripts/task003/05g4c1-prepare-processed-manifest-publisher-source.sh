#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT="${HEALTHCARE_PROJECT_ROOT:-/data/spark/healthcare-data-platform}"
SOURCE="${BASH_SOURCE[0]:-}"
STAGE=''

echo '#### TASK003 STEP05G4C1 PROCESSED MANIFEST PUBLISHER SOURCE OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  [[ -z "$STAGE" ]] || rm -rf -- "$STAGE"

  echo "INSTALL_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G4C1 PROCESSED MANIFEST PUBLISHER SOURCE OUTPUT END ####'
  exit "$rc"
}

trap finish EXIT

[[ -n "$SOURCE" && -f "$SOURCE" ]] || {
  echo 'ERROR: installer must run from saved Bash file'
  exit 2
}

cd "$ROOT"

MANIFEST_DIR="$ROOT/runtime/reports/task003/step05/processed-manifest-builds/visit-proc-20261009t192437z-2081886"

for path in \
  "$MANIFEST_DIR/manifest.json" \
  "$MANIFEST_DIR/run-state.json" \
  "$ROOT/runtime/reports/task003/step05/processed-plans/visit-proc-20261009t192437z-2081886/plan.json"
do
  [[ -s "$path" && ! -L "$path" ]] || {
    echo "ERROR: prerequisite missing or unsafe: $path"
    exit 2
  }
done

STAGE=$(
  mktemp -d \
    /data/spark/temp_shell/g4c1.XXXXXXXX
)

mkdir -p \
  "$STAGE/spark/apps/visit" \
  "$STAGE/tests/task003"

cat > "$STAGE/spark/apps/visit/publish_processed_manifest.py" <<'PY_APP'
"""TASK-003 final APPROVED Manifest write-once publisher.

This is the final Processed publication gate.

Safety properties:
- validates the immutable G4A APPROVED Manifest;
- validates DQ remotely before Manifest creation;
- manifest.json is written only after DQ is present and byte-verified;
- manifest.json is create-only (overwrite=False);
- an existing Manifest is accepted only when byte-identical;
- Manifest is immediately read back and SHA256 verified;
- DQ is re-read after Manifest publication;
- no PostgreSQL mutation;
- no Reservation deletion/release.
"""

import argparse
import hashlib
import json
from pathlib import Path


EXPECTED_RUN_ID = (
    'visit-proc-20261009t192437z-2081886'
)

EXPECTED_MANIFEST_SHA256 = (
    '1435b6c3a98e2320b831faf26e2b8ecf'
    '59472b980b972fab856b35ae4d6829af'
)

EXPECTED_MANIFEST_SIZE_BYTES = 3141

EXPECTED_DQ_SHA256 = (
    '58e0ffc9e9b9a0ef5f34558807297b5a'
    'e2d6545d909fa340b0e2b713346b77c2'
)

EXPECTED_DQ_SIZE_BYTES = 2607


def require(condition, message):
    if not condition:
        raise ValueError(
            'PROCESSED_MANIFEST_PUBLISH_FAILED: '
            + message
        )


def sha256_bytes(blob):
    return hashlib.sha256(
        blob
    ).hexdigest()


def read_mounted_file(path):
    """Read regular files and safe Kubernetes projected files."""

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
        'mounted target is not a regular file: '
        + str(path)
    )

    try:
        resolved.relative_to(
            root
        )

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
    manifest_bytes,
):
    require(
        (
            build_state.get('task'),
            build_state.get('step'),
            build_state.get('status'),
        )
        == (
            'TASK-003',
            'STEP-05G4A',
            'MANIFEST_BUILT_NOT_PUBLISHED',
        ),
        'G4A build state'
    )

    require(
        build_state.get('run_id')
        == EXPECTED_RUN_ID
        == plan.get('run_id'),
        'run identity drift'
    )

    require(
        build_state.get(
            'approval_status'
        )
        == 'APPROVED',
        'Manifest not APPROVED'
    )

    require(
        build_state.get(
            'publication_policy'
        )
        == 'APPROVED_manifest_last',
        'Manifest publication policy drift'
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
            'candidate_published_verified'
        )
        is True,
        'Candidate publication not verified'
    )

    require(
        build_state.get(
            's3_write_verified'
        )
        is True,
        'Processed data S3 verification missing'
    )

    require(
        build_state.get(
            'dq_published'
        )
        is True,
        'DQ not published'
    )

    require(
        build_state.get(
            'dq_readback_verified'
        )
        is True,
        'DQ readback not verified'
    )

    require(
        build_state.get(
            'dq_sha256'
        )
        == EXPECTED_DQ_SHA256,
        'DQ SHA drift'
    )

    require(
        build_state.get(
            'manifest_built'
        )
        is True,
        'Manifest not built'
    )

    require(
        build_state.get(
            'manifest_published'
        )
        is False,
        'Manifest already marked published'
    )

    require(
        build_state.get(
            'manifest_readback_verified'
        )
        is False,
        'Manifest already marked readback verified'
    )

    require(
        build_state.get(
            'reservation_released'
        )
        is False,
        'Reservation released before Manifest publication'
    )

    require(
        build_state.get(
            'postgresql_write'
        )
        is False,
        'unexpected PostgreSQL write'
    )

    actual_sha = sha256_bytes(
        manifest_bytes
    )

    require(
        actual_sha
        == EXPECTED_MANIFEST_SHA256
        == build_state.get(
            'manifest_sha256'
        ),
        'Manifest SHA256 drift'
    )

    require(
        len(manifest_bytes)
        == EXPECTED_MANIFEST_SIZE_BYTES
        == build_state.get(
            'manifest_size_bytes'
        ),
        'Manifest size drift'
    )

    manifest = json.loads(
        manifest_bytes
    )

    require(
        (
            manifest.get('task'),
            manifest.get('step'),
            manifest.get('status'),
        )
        == (
            'TASK-003',
            'STEP-05G4',
            'APPROVED',
        ),
        'Manifest content status'
    )

    require(
        manifest.get(
            'publication_policy'
        )
        == 'APPROVED_manifest_last',
        'Manifest content publication policy'
    )

    require(
        manifest.get('run_id')
        == EXPECTED_RUN_ID,
        'Manifest run identity'
    )

    require(
        manifest['uris']['data']
        == plan.get('data_uri'),
        'data URI drift'
    )

    require(
        manifest['uris']['dq']
        == plan.get('dq_uri')
        == build_state.get('dq_uri'),
        'DQ URI drift'
    )

    require(
        manifest['uris']['manifest']
        == plan.get('manifest_uri')
        == build_state.get('manifest_uri'),
        'Manifest URI drift'
    )

    gate = manifest[
        'approval_gate'
    ]

    require(
        gate.get(
            'processed_data_verified'
        )
        is True,
        'Manifest data gate'
    )

    require(
        gate.get(
            'independent_s3_readback_passed'
        )
        is True,
        'Manifest independent readback gate'
    )

    require(
        gate.get(
            'candidate_published_verified'
        )
        is True,
        'Manifest Candidate gate'
    )

    require(
        gate.get(
            'dq_published'
        )
        is True,
        'Manifest DQ gate'
    )

    require(
        gate.get(
            'dq_readback_verified'
        )
        is True,
        'Manifest DQ readback gate'
    )

    require(
        gate.get(
            'manifest_must_be_last'
        )
        is True,
        'Manifest-last policy missing'
    )

    require(
        gate.get(
            'ready_for_manifest_publication'
        )
        is True,
        'Manifest not ready for publication'
    )

    require(
        gate.get(
            'reservation_must_remain_held_until_manifest_verification'
        )
        is True,
        'Reservation gate drift'
    )

    require(
        gate.get(
            'postgresql_write'
        )
        is False,
        'Manifest claims PostgreSQL write'
    )

    require(
        manifest['artifacts']['dq']['sha256']
        == EXPECTED_DQ_SHA256,
        'Manifest DQ artifact SHA drift'
    )

    require(
        manifest['artifacts']['dq']['size_bytes']
        == EXPECTED_DQ_SIZE_BYTES,
        'Manifest DQ artifact size drift'
    )

    return manifest


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

    stream = fs.open(
        path
    )

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


def publish_manifest(
    spark,
    manifest_bytes,
    plan,
):
    jvm = spark.sparkContext._jvm

    conf = (
        spark.sparkContext
        ._jsc
        .hadoopConfiguration()
    )

    dq_uri = plan[
        'dq_uri'
    ]

    manifest_uri = plan[
        'manifest_uri'
    ]

    dq_path = (
        jvm.org.apache.hadoop.fs.Path(
            canonical_to_s3a(
                dq_uri
            )
        )
    )

    manifest_path = (
        jvm.org.apache.hadoop.fs.Path(
            canonical_to_s3a(
                manifest_uri
            )
        )
    )

    fs = manifest_path.getFileSystem(
        conf
    )

    # Manifest is allowed only after DQ exists.
    require(
        fs.exists(
            dq_path
        ),
        'DQ object absent before Manifest publication'
    )

    dq_before = hadoop_read_all(
        spark,
        fs,
        dq_path,
    )

    require(
        len(dq_before)
        == EXPECTED_DQ_SIZE_BYTES,
        'remote DQ size drift before Manifest'
    )

    require(
        sha256_bytes(
            dq_before
        )
        == EXPECTED_DQ_SHA256,
        'remote DQ SHA drift before Manifest'
    )

    if fs.exists(
        manifest_path
    ):
        existing = hadoop_read_all(
            spark,
            fs,
            manifest_path,
        )

        require(
            existing
            == manifest_bytes,
            'existing Manifest conflicts with approved local artifact'
        )

        publication_status = (
            'REUSED_IDENTICAL'
        )

    else:
        # Final write-once publication.
        # overwrite=False is mandatory.
        output = fs.create(
            manifest_path,
            False,
        )

        try:
            output.write(
                bytearray(
                    manifest_bytes
                )
            )

        finally:
            output.close()

        publication_status = (
            'CREATED'
        )

    require(
        fs.exists(
            manifest_path
        ),
        'Manifest missing after publication'
    )

    persisted_manifest = hadoop_read_all(
        spark,
        fs,
        manifest_path,
    )

    require(
        persisted_manifest
        == manifest_bytes,
        'Manifest readback bytes differ'
    )

    persisted_manifest_sha = (
        sha256_bytes(
            persisted_manifest
        )
    )

    require(
        persisted_manifest_sha
        == EXPECTED_MANIFEST_SHA256,
        'Manifest readback SHA drift'
    )

    require(
        len(
            persisted_manifest
        )
        == EXPECTED_MANIFEST_SIZE_BYTES,
        'Manifest readback size drift'
    )

    # Re-read DQ after final publication.
    dq_after = hadoop_read_all(
        spark,
        fs,
        dq_path,
    )

    require(
        dq_after
        == dq_before,
        'DQ changed during Manifest publication'
    )

    require(
        sha256_bytes(
            dq_after
        )
        == EXPECTED_DQ_SHA256,
        'DQ SHA drift after Manifest publication'
    )

    return {
        'status':
            'MANIFEST_PUBLICATION_PASS',

        'publication_status':
            publication_status,

        'run_id':
            EXPECTED_RUN_ID,

        'dq_uri':
            dq_uri,

        'dq_sha256':
            EXPECTED_DQ_SHA256,

        'dq_size_bytes':
            EXPECTED_DQ_SIZE_BYTES,

        'dq_published':
            True,

        'dq_readback_verified':
            True,

        'manifest_uri':
            manifest_uri,

        'manifest_sha256':
            persisted_manifest_sha,

        'manifest_size_bytes':
            len(
                persisted_manifest
            ),

        'manifest_published':
            True,

        'manifest_readback_verified':
            True,

        'processed_publication_complete':
            True,

        'reservation_release_eligible':
            True,

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
        '--manifest-file',
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

    manifest_bytes = read_mounted_file(
        args.manifest_file
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
        manifest_bytes,
    )

    from pyspark.sql import SparkSession

    spark = (
        SparkSession.builder
        .appName(
            'task003-processed-manifest-publisher'
        )
        .getOrCreate()
    )

    try:
        result = publish_manifest(
            spark,
            manifest_bytes,
            plan,
        )

        print(
            'PROCESSED_MANIFEST_PUBLICATION_RESULT='
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

cat > "$STAGE/tests/task003/test_processed_manifest_publisher.py" <<'PY_TEST'
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(
    0,
    str(ROOT / 'spark/apps/visit')
)

from publish_processed_manifest import (
    EXPECTED_DQ_SHA256,
    EXPECTED_DQ_SIZE_BYTES,
    EXPECTED_MANIFEST_SHA256,
    EXPECTED_MANIFEST_SIZE_BYTES,
    EXPECTED_RUN_ID,
    canonical_to_s3a,
    read_mounted_file,
    validate_publication_inputs,
)


def fixture():
    plan = {
        'run_id':
            EXPECTED_RUN_ID,

        'data_uri':
            's3://health-processed/x/data/',

        'dq_uri':
            's3://health-processed/x/dq/result.json',

        'manifest_uri':
            's3://health-processed/x/manifest.json',
    }

    state = {
        'task':
            'TASK-003',

        'step':
            'STEP-05G4A',

        'status':
            'MANIFEST_BUILT_NOT_PUBLISHED',

        'run_id':
            EXPECTED_RUN_ID,

        'approval_status':
            'APPROVED',

        'publication_policy':
            'APPROVED_manifest_last',

        'processed_data_verified':
            True,

        'candidate_published_verified':
            True,

        's3_write_verified':
            True,

        'dq_published':
            True,

        'dq_readback_verified':
            True,

        'dq_sha256':
            EXPECTED_DQ_SHA256,

        'dq_uri':
            plan['dq_uri'],

        'manifest_built':
            True,

        'manifest_published':
            False,

        'manifest_readback_verified':
            False,

        'manifest_sha256':
            EXPECTED_MANIFEST_SHA256,

        'manifest_size_bytes':
            EXPECTED_MANIFEST_SIZE_BYTES,

        'manifest_uri':
            plan['manifest_uri'],

        'reservation_released':
            False,

        'postgresql_write':
            False,
    }

    return plan, state


class ManifestPublisherTests(
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
                / '..20261009_231500'
            )

            version.mkdir()

            target = (
                version
                / 'manifest.json'
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
                / 'manifest.json'
            )

            projected.symlink_to(
                Path('..data')
                / 'manifest.json'
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
                / 'manifest.json'
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

    def test_manifest_already_marked_published_rejected(self):
        plan, state = fixture()

        state[
            'manifest_published'
        ] = True

        with self.assertRaisesRegex(
            ValueError,
            'already marked published',
        ):
            validate_publication_inputs(
                plan,
                state,
                b'x',
            )

    def test_dq_not_published_rejected(self):
        plan, state = fixture()

        state[
            'dq_published'
        ] = False

        with self.assertRaisesRegex(
            ValueError,
            'DQ not published',
        ):
            validate_publication_inputs(
                plan,
                state,
                b'x',
            )

    def test_dq_readback_not_verified_rejected(self):
        plan, state = fixture()

        state[
            'dq_readback_verified'
        ] = False

        with self.assertRaisesRegex(
            ValueError,
            'DQ readback not verified',
        ):
            validate_publication_inputs(
                plan,
                state,
                b'x',
            )

    def test_reservation_released_rejected(self):
        plan, state = fixture()

        state[
            'reservation_released'
        ] = True

        with self.assertRaisesRegex(
            ValueError,
            'Reservation released',
        ):
            validate_publication_inputs(
                plan,
                state,
                b'x',
            )

    def test_manifest_sha_drift_rejected(self):
        plan, state = fixture()

        blob = (
            b'x'
            * EXPECTED_MANIFEST_SIZE_BYTES
        )

        with self.assertRaisesRegex(
            ValueError,
            'Manifest SHA256 drift',
        ):
            validate_publication_inputs(
                plan,
                state,
                blob,
            )

    def test_s3_write_uses_create_stream(self):
        source = (
            ROOT
            / 'spark/apps/visit/'
            'publish_processed_manifest.py'
        ).read_text()

        self.assertIn(
            'output = fs.create(',
            source,
        )

        self.assertIn(
            'bytearray(',
            source,
        )

        self.assertNotIn(
            'fs.copyFromLocalFile(',
            source,
        )

    def test_manifest_constants_match_real_artifact(self):
        path = (
            ROOT
            / 'runtime/reports/task003/step05/'
            'processed-manifest-builds/'
            'visit-proc-20261009t192437z-2081886/'
            'manifest.json'
        )

        if not path.is_file():
            self.skipTest(
                'real runtime artifact unavailable'
            )

        blob = path.read_bytes()

        self.assertEqual(
            len(blob),
            EXPECTED_MANIFEST_SIZE_BYTES,
        )

        self.assertEqual(
            hashlib.sha256(
                blob
            ).hexdigest(),
            EXPECTED_MANIFEST_SHA256,
        )

    def test_dq_constants(self):
        self.assertEqual(
            EXPECTED_DQ_SIZE_BYTES,
            2607,
        )

        self.assertEqual(
            EXPECTED_DQ_SHA256,
            '58e0ffc9e9b9a0ef5f34558807297b5ae2d6545d909fa340b0e2b713346b77c2',
        )


if __name__ == '__main__':
    unittest.main()
PY_TEST

echo '=== 1. Syntax validation ==='

python3 - "$STAGE" <<'PY_AST'
import ast
import sys
from pathlib import Path

root = Path(sys.argv[1])

for rel in (
    'spark/apps/visit/publish_processed_manifest.py',
    'tests/task003/test_processed_manifest_publisher.py',
):
    ast.parse(
        (root / rel).read_text(),
        filename=rel,
    )

print('MANIFEST_PUBLISHER_PYTHON_AST=PASS')
PY_AST

echo '=== 2. Run Manifest Publisher tests ==='

PYTHONPATH="$STAGE/spark/apps/visit" \
python3 -m unittest discover \
  -s "$STAGE/tests/task003" \
  -p 'test_processed_manifest_publisher.py' \
  -v

echo 'MANIFEST_PUBLISHER_TESTS=PASS'

echo '=== 3. Verify real G4A Manifest artifact ==='

PYTHONPATH="$STAGE/spark/apps/visit" \
python3 - \
  "$ROOT/runtime/reports/task003/step05/processed-plans/visit-proc-20261009t192437z-2081886/plan.json" \
  "$ROOT/runtime/reports/task003/step05/processed-manifest-builds/visit-proc-20261009t192437z-2081886/run-state.json" \
  "$ROOT/runtime/reports/task003/step05/processed-manifest-builds/visit-proc-20261009t192437z-2081886/manifest.json" \
  <<'PY_REAL'
import json
import sys
from pathlib import Path

from publish_processed_manifest import (
    EXPECTED_MANIFEST_SHA256,
    EXPECTED_MANIFEST_SIZE_BYTES,
    sha256_bytes,
    validate_publication_inputs,
)

plan = json.loads(
    Path(sys.argv[1]).read_bytes()
)

state = json.loads(
    Path(sys.argv[2]).read_bytes()
)

manifest_bytes = Path(
    sys.argv[3]
).read_bytes()

manifest = validate_publication_inputs(
    plan,
    state,
    manifest_bytes,
)

assert (
    sha256_bytes(
        manifest_bytes
    )
    == EXPECTED_MANIFEST_SHA256
)

assert (
    len(manifest_bytes)
    == EXPECTED_MANIFEST_SIZE_BYTES
)

print('REAL_MANIFEST_PUBLICATION_INPUT=PASS')
print(
    'MANIFEST_STATUS='
    + manifest['status']
)
print(
    'MANIFEST_PUBLICATION_POLICY='
    + manifest['publication_policy']
)
print(
    'MANIFEST_SHA256='
    + EXPECTED_MANIFEST_SHA256
)
print(
    'MANIFEST_SIZE_BYTES='
    + str(
        EXPECTED_MANIFEST_SIZE_BYTES
    )
)
print(
    'MANIFEST_URI='
    + manifest['uris']['manifest']
)
PY_REAL

echo '=== 4. Publisher safety boundary ==='

python3 - \
  "$STAGE/spark/apps/visit/publish_processed_manifest.py" \
  <<'PY_STATIC'
import sys
from pathlib import Path

source = Path(sys.argv[1]).read_text()

required = (
    'output = fs.create(',
    'bytearray(',
    "'CREATED'",
    "'REUSED_IDENTICAL'",
    'MANIFEST_PUBLICATION_PASS',
    'DQ object absent before Manifest publication',
    'remote DQ SHA drift before Manifest',
    'Manifest readback bytes differ',
    'DQ changed during Manifest publication',
    "'processed_publication_complete':",
    "'reservation_release_eligible':",
    "'reservation_release_requested':",
    "'postgresql_write':",
)

for token in required:
    assert token in source, token

for forbidden in (
    'fs.copyFromLocalFile(',
    'overwrite=True',
    'kubectl delete',
    'INSERT INTO',
    'UPDATE ',
    'DELETE FROM',
):
    assert forbidden not in source, forbidden

assert (
    'output = fs.create('
    in source
)

assert (
    'manifest_path,\n            False'
    in source
)

print('MANIFEST_WRITE_ONCE_POLICY=PASS')
print('MANIFEST_READBACK_SHA_POLICY=PASS')
print('DQ_PRE_AND_POST_VERIFY_POLICY=PASS')
print('RESERVATION_RELEASE_PATH_ABSENT=PASS')
print('DATABASE_MUTATION_ABSENT=PASS')
PY_STATIC

echo '=== 5. Canonical conflict check ==='

FILES=(
  spark/apps/visit/publish_processed_manifest.py
  tests/task003/test_processed_manifest_publisher.py
)

GEN=scripts/task003/05g4c1-prepare-processed-manifest-publisher-source.sh

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

echo '=== 6. Install canonical source ==='

for rel in "${FILES[@]}"; do

  mkdir -p \
    "$(dirname "$ROOT/$rel")"

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

mkdir -p \
  "$ROOT/scripts/task003"

if [[ -f "$ROOT/$GEN" ]]; then
  echo "CANONICAL_GENERATOR_REUSED=$GEN"
else
  install \
    -m 755 \
    "$SOURCE" \
    "$ROOT/$GEN"

  echo "CANONICAL_GENERATOR_READY=$GEN"
fi

echo '=== 7. Final source state ==='

echo 'STEP05G4C1_SOURCE_AND_TESTS=PASS'

echo 'MANIFEST_PUBLISHER_EXECUTED=NO'
echo 'MANIFEST_PUBLISHED=NO'
echo 'MANIFEST_READBACK_VERIFIED=NO'

echo 'RESERVATION_RELEASED=NO'

echo 'K8S_MUTATION=NO'
echo 'S3_MUTATION=NO'
echo 'DATABASE_MUTATION=NO'
echo 'GIT_COMMIT=NO'
