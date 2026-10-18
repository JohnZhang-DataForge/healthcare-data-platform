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
