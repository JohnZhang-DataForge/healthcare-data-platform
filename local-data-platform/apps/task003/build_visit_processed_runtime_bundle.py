"""Build immutable Visit Processed runtime manifests.

This program does NOT call Kubernetes, Spark, S3 or PostgreSQL.

A later execution step must first:
- create the exclusive Reservation ConfigMap;
- verify its live UID/resourceVersion;
- obtain a fresh EMPTY S3 listing;
- generate a short-lived write permit.

Only then can this builder package the exact source/evidence snapshot
into an immutable runtime ConfigMap manifest and SparkApplication YAML.
"""

import argparse
import hashlib
import json
import re
import sys

from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(
    0,
    str(ROOT / 'spark/apps/visit')
)

sys.path.insert(
    0,
    str(ROOT / 'apps/task003')
)

from plan_visit_processed import save_once
from processed_visit_writer_core import validate_permit


SOURCE_PATHS = {
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

    'run_visit_processed_writer.py':
        'spark/apps/visit/run_visit_processed_writer.py',

    'processed_visit_writer_core.py':
        'spark/apps/visit/processed_visit_writer_core.py',
}


STATIC_ARTIFACTS = {
    'step05f2-run-state.json': 'f2',
    'processed-plan.json': 'plan',
    'processed-write-intent.json': 'intent',
    'reservation-create.json': 'reservation',
}


FUTURE_ARTIFACTS = (
    'fresh-s3-listing.json',
    'write-permit.json',
)


DNS_NAME = re.compile(
    r'^[a-z0-9]([-a-z0-9]*[a-z0-9])?$'
)


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(
            'RUNTIME_BUNDLE_CONFLICT: ' + message
        )


def decode_text(blob, label):
    require(
        b'\x00' not in blob,
        label + ' contains NUL'
    )

    try:
        return blob.decode('utf-8')

    except UnicodeDecodeError as exc:
        raise ValueError(
            'RUNTIME_BUNDLE_CONFLICT: non-UTF8 ' + label
        ) from exc


def safe_kubernetes_name(name):
    require(
        isinstance(name, str)
        and len(name) <= 63
        and DNS_NAME.fullmatch(name),
        'unsafe Kubernetes name'
    )

    return name


def validate_template(template_bytes):
    template = decode_text(
        template_bytes,
        'SparkApplication template'
    )

    require(
        template.count('__APP_NAME__') == 1,
        'app placeholder'
    )

    require(
        template.count('__CONFIGMAP_NAME__') == 1,
        'ConfigMap placeholder'
    )

    without_known = (
        template
        .replace('__APP_NAME__', '')
        .replace('__CONFIGMAP_NAME__', '')
    )

    require(
        '__' not in without_known,
        'unknown template placeholder'
    )

    required = (
        'apiVersion: sparkoperator.k8s.io/v1beta2',
        'kind: SparkApplication',
        'namespace: dw-spark',
        'image: spark:3.5.7-python3',
        (
            'mainApplicationFile: '
            'local:///opt/spark/app/'
            'run_visit_processed_writer.py'
        ),
        'sparkVersion: "3.5.7"',
        'serviceAccount: spark-job',
        'name: dw-spark-s3-secret',
        'name: dw-spark-omop-secret',
        'workload: platform',
        (
            'spark.hadoop.fs.s3a.endpoint: '
            'http://dw-seaweedfs-s3.'
            'dw-seaweedfs.svc.cluster.local:8333'
        ),
        'spark.hadoop.fs.s3a.path.style.access: "true"',
        (
            'spark.hadoop.mapreduce.'
            'fileoutputcommitter.algorithm.version: "2"'
        ),
    )

    for item in required:
        require(
            item in template,
            'template missing: ' + item
        )

    require(
        'restartPolicy:\n    type: Never' in template,
        'restart policy'
    )

    return template


def build_bundle(
    run_id,
    inventory_bytes,
    f2_bytes,
    plan_bytes,
    intent_bytes,
    reservation_bytes,
    listing_bytes,
    permit_bytes,
    source_bytes,
    template_bytes,
    now=None,
):
    inventory = json.loads(inventory_bytes)
    f2 = json.loads(f2_bytes)
    plan = json.loads(plan_bytes)
    intent = json.loads(intent_bytes)
    reservation = json.loads(reservation_bytes)
    permit = json.loads(permit_bytes)

    # Validate JSON before handing bytes to the Writer Core.
    json.loads(listing_bytes)

    require(
        inventory.get('schema')
        == 'task003.visit_processed.bundle_inventory.v1',
        'inventory schema'
    )

    require(
        inventory.get('status')
        == 'SOURCE_INVENTORY_ONLY',
        'inventory status'
    )

    require(
        inventory.get('run_id') == run_id,
        'inventory run'
    )

    require(
        plan.get('run_id')
        == intent.get('run_id')
        == run_id,
        'run identity'
    )

    require(
        inventory.get('reservation_name')
        == reservation['metadata']['name'],
        'inventory reservation name'
    )

    require(
        inventory.get('future_artifacts_required')
        == list(FUTURE_ARTIFACTS),
        'future artifact inventory'
    )

    # This verifies:
    # - live lock fields recorded in permit;
    # - plan / intent / reservation hashes;
    # - fresh S3 listing hash;
    # - listing EMPTY state;
    # - short permit lifetime.
    validate_permit(
        permit,
        plan_bytes,
        intent_bytes,
        reservation_bytes,
        listing_bytes,
        now=now or datetime.now(timezone.utc),
    )

    fingerprint = permit.get(
        'person_map_fingerprint'
    )

    require(
        isinstance(fingerprint, str)
        and len(fingerprint) == 64
        and all(
            char in '0123456789abcdef'
            for char in fingerprint
        ),
        'Person map fingerprint'
    )

    require(
        f2.get('task') == 'TASK-003'
        and f2.get('step') == 'STEP-05F2'
        and f2.get('status') == 'PASS',
        'F2 evidence'
    )

    require(
        plan.get('source_f2_evidence_sha256')
        == sha(f2_bytes),
        'plan F2 pin'
    )

    require(
        intent.get('step05f2_sha256')
        == sha(f2_bytes),
        'intent F2 pin'
    )

    require(
        intent.get('plan_sha256')
        == sha(plan_bytes),
        'intent plan pin'
    )

    require(
        plan.get('expected_rows')
        == f2['result']['candidate_rows'],
        'row pin'
    )

    require(
        plan.get('expected_persons')
        == f2['result']['referenced_persons'],
        'Person pin'
    )

    require(
        set(source_bytes)
        == set(SOURCE_PATHS),
        'source inventory'
    )

    inventory_sources = inventory.get(
        'source_files',
        {}
    )

    require(
        set(inventory_sources)
        == set(SOURCE_PATHS),
        'inventory source catalog'
    )

    for name, repo_path in SOURCE_PATHS.items():
        record = inventory_sources[name]

        require(
            record['repo_path'] == repo_path,
            'repo path ' + name
        )

        require(
            record['sha256']
            == sha(source_bytes[name]),
            'source SHA ' + name
        )

        require(
            record['size_bytes']
            == len(source_bytes[name]),
            'source size ' + name
        )

    static_blobs = {
        'f2': f2_bytes,
        'plan': plan_bytes,
        'intent': intent_bytes,
        'reservation': reservation_bytes,
    }

    inventory_artifacts = inventory.get(
        'static_artifacts',
        {}
    )

    require(
        set(inventory_artifacts)
        == set(STATIC_ARTIFACTS),
        'static artifact catalog'
    )

    for filename, key in STATIC_ARTIFACTS.items():
        record = inventory_artifacts[filename]

        require(
            record['sha256']
            == sha(static_blobs[key]),
            'artifact SHA ' + filename
        )

        require(
            record['size_bytes']
            == len(static_blobs[key]),
            'artifact size ' + filename
        )

    template = validate_template(
        template_bytes
    )

    artifact_bytes = {
        'step05f2-run-state.json':
            f2_bytes,

        'processed-plan.json':
            plan_bytes,

        'processed-write-intent.json':
            intent_bytes,

        'reservation-create.json':
            reservation_bytes,

        'fresh-s3-listing.json':
            listing_bytes,

        'write-permit.json':
            permit_bytes,
    }

    artifact_sha256 = {
        name: sha(blob)
        for name, blob
        in artifact_bytes.items()
    }

    driver_input = {
        'schema':
            'task003.visit_processed.spark_driver.v1',

        'task':
            'TASK-003',

        'step':
            'STEP-05G2C2C',

        'run_id':
            run_id,

        'source_file_sha256':
            f2['input']['mounted_file_sha256'],

        'artifact_sha256':
            artifact_sha256,

        'f2_input':
            f2['input'],

        'expected_rows':
            plan['expected_rows'],

        'expected_persons':
            plan['expected_persons'],

        'expected_class_counts':
            plan['class_counts'],

        'person_map_fingerprint':
            fingerprint,
    }

    driver_input_bytes = (
        json.dumps(
            driver_input,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + '\n'
    ).encode('utf-8')

    configmap_data = {
        name: decode_text(blob, name)
        for name, blob in source_bytes.items()
    }

    configmap_data.update({
        name: decode_text(blob, name)
        for name, blob in artifact_bytes.items()
    })

    configmap_data[
        'processed-writer-input.json'
    ] = decode_text(
        driver_input_bytes,
        'processed-writer-input.json'
    )

    attempt_id = sha(
        inventory_bytes
        + permit_bytes
        + listing_bytes
    )[:24]

    configmap_name = safe_kubernetes_name(
        'visit-proc-runtime-' + attempt_id
    )

    application_name = safe_kubernetes_name(
        'visit-proc-write-' + attempt_id[:20]
    )

    configmap = {
        'apiVersion': 'v1',
        'kind': 'ConfigMap',

        'metadata': {
            'name': configmap_name,
            'namespace': 'dw-spark',

            'labels': {
                'healthcare-task': 'task003',
                'healthcare-purpose':
                    'visit-processed-runtime',
            },
        },

        'immutable': True,

        'data': configmap_data,
    }

    configmap_bytes = (
        json.dumps(
            configmap,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + '\n'
    ).encode('utf-8')

    # Kubernetes objects have a hard size limit.
    # Keep substantial headroom below that limit.
    require(
        len(configmap_bytes) < 750000,
        'ConfigMap JSON exceeds safety budget'
    )

    rendered = (
        template
        .replace(
            '__APP_NAME__',
            application_name
        )
        .replace(
            '__CONFIGMAP_NAME__',
            configmap_name
        )
    )

    require(
        '__' not in rendered,
        'unresolved template placeholder'
    )

    spark_application_bytes = (
        rendered.encode('utf-8')
    )

    state = {
        'task':
            'TASK-003',

        'step':
            'STEP-05G2C2C2B2',

        'status':
            'PREPARED_NOT_CREATED',

        'run_id':
            run_id,

        'attempt_id':
            attempt_id,

        'runtime_configmap_name':
            configmap_name,

        'spark_application_name':
            application_name,

        'runtime_configmap_sha256':
            sha(configmap_bytes),

        'spark_application_sha256':
            sha(spark_application_bytes),

        'write_permit_sha256':
            sha(permit_bytes),

        'fresh_listing_sha256':
            sha(listing_bytes),

        'person_map_fingerprint':
            fingerprint,

        'configmap_created':
            False,

        'spark_application_submitted':
            False,

        's3_write':
            False,

        'postgresql_write':
            False,
    }

    return (
        configmap_bytes,
        spark_application_bytes,
        state,
    )


def read_regular(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError(
            'Missing or unsafe file: ' + str(path)
        )

    return path.read_bytes()


def save_bytes_once(path, blob):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if path.exists():
        if (
            path.is_symlink()
            or path.read_bytes() != blob
        ):
            raise ValueError(
                'Immutable output conflict: '
                + str(path)
            )

        return 'REUSED'

    with path.open('xb') as handle:
        handle.write(blob)

    return 'CREATED'


def main():
    parser = argparse.ArgumentParser(
        description=__doc__
    )

    parser.add_argument(
        '--root',
        type=Path,
        required=True,
    )

    parser.add_argument(
        '--f2-state',
        type=Path,
        required=True,
    )

    parser.add_argument(
        '--run-id',
        required=True,
    )

    parser.add_argument(
        '--fresh-listing',
        type=Path,
        required=True,
    )

    parser.add_argument(
        '--write-permit',
        type=Path,
        required=True,
    )

    args = parser.parse_args()

    require(
        args.run_id
        and len(args.run_id) <= 128
        and all(
            char.isalnum()
            or char in '._-'
            for char in args.run_id
        )
        and args.run_id not in ('.', '..'),
        'unsafe run ID'
    )

    root = args.root.resolve()

    base = (
        root
        / 'runtime/reports/task003/step05'
    )

    inventory_path = (
        base
        / 'processed-bundle-inventories'
        / args.run_id
        / 'source-inventory.json'
    )

    plan_path = (
        base
        / 'processed-plans'
        / args.run_id
        / 'plan.json'
    )

    intent_path = (
        base
        / 'processed-intents'
        / args.run_id
        / 'write-intent.json'
    )

    reservation_path = (
        base
        / 'writer-reservations'
        / args.run_id
        / 'reservation-create.json'
    )

    template_path = (
        root
        / 'spark/manifests/task003/'
        'visit-processed-writer.yaml.tpl'
    )

    source_bytes = {
        name:
            read_regular(root / repo_path)

        for name, repo_path
        in SOURCE_PATHS.items()
    }

    inventory_bytes = read_regular(
        inventory_path
    )

    f2_bytes = read_regular(
        args.f2_state
    )

    plan_bytes = read_regular(
        plan_path
    )

    intent_bytes = read_regular(
        intent_path
    )

    reservation_bytes = read_regular(
        reservation_path
    )

    listing_bytes = read_regular(
        args.fresh_listing
    )

    permit_bytes = read_regular(
        args.write_permit
    )

    template_bytes = read_regular(
        template_path
    )

    (
        configmap_bytes,
        spark_application_bytes,
        state,
    ) = build_bundle(
        args.run_id,
        inventory_bytes,
        f2_bytes,
        plan_bytes,
        intent_bytes,
        reservation_bytes,
        listing_bytes,
        permit_bytes,
        source_bytes,
        template_bytes,
    )

    attempt_id = state['attempt_id']

    output = (
        base
        / 'processed-runtime-bundles'
        / args.run_id
        / attempt_id
    )

    configmap_status = save_bytes_once(
        output / 'runtime-configmap.json',
        configmap_bytes,
    )

    application_status = save_bytes_once(
        output / 'sparkapplication.yaml',
        spark_application_bytes,
    )

    state_status = save_once(
        output / 'bundle-state.json',
        state,
    )

    print(
        'RUNTIME_CONFIGMAP_FILE_STATUS='
        + configmap_status
    )

    print(
        'SPARKAPPLICATION_FILE_STATUS='
        + application_status
    )

    print(
        'BUNDLE_STATE_STATUS='
        + state_status
    )

    print(
        'RUNTIME_ATTEMPT_ID='
        + attempt_id
    )

    print(
        'RUNTIME_CONFIGMAP_NAME='
        + state['runtime_configmap_name']
    )

    print(
        'SPARK_APPLICATION_NAME='
        + state['spark_application_name']
    )

    print(
        'RUNTIME_CONFIGMAP_SHA256='
        + state['runtime_configmap_sha256']
    )

    print(
        'SPARK_APPLICATION_SHA256='
        + state['spark_application_sha256']
    )

    print(
        'RUNTIME_BUNDLE_DIR='
        + str(output)
    )

    print('K8S_CONFIGMAP_CREATED=NO')
    print('SPARK_APPLICATION_SUBMITTED=NO')
    print('S3_WRITE=NO')
    print('DATABASE_WRITE=NO')


if __name__ == '__main__':
    main()
