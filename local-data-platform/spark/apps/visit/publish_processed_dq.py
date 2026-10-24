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
        # Write directly from the already-validated in-memory
        # artifact.  Do not use copyFromLocalFile here:
        # Kubernetes projected ConfigMap files resolve through
        # ..data symlinks, which S3A copyFromLocalFile cannot
        # safely relativize.
        output = fs.create(
            dq_path,
            False,
        )

        try:
            output.write(
                bytearray(
                    dq_bytes
                )
            )

        finally:
            output.close()

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
