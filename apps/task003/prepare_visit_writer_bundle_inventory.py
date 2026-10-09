"""Immutable local inventory for a future Spark Runtime Bundle.

No ConfigMap, lock, permit, S3 operation, database operation
or Spark job is created.
"""

import argparse
import ast
import hashlib
import json
from pathlib import Path

from plan_visit_processed import save_once


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
}

DRIVER_PATH = 'spark/apps/visit/run_visit_processed_writer.py'
CORE_PATH = 'spark/apps/visit/processed_visit_writer_core.py'

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


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(ok, reason):
    if not ok:
        raise ValueError('BUNDLE_INVENTORY_CONFLICT: ' + reason)


def driver_inventory(driver_bytes):
    tree = ast.parse(driver_bytes.decode('utf-8'))
    found = {}

    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Name)
                    and target.id in ('MOUNTED_SOURCES', 'ARTIFACTS')
                ):
                    require(
                        target.id not in found,
                        'duplicate driver constant'
                    )
                    found[target.id] = tuple(
                        ast.literal_eval(node.value)
                    )

    require(
        set(found) == {'MOUNTED_SOURCES', 'ARTIFACTS'},
        'driver inventory missing'
    )

    require(
        set(found['MOUNTED_SOURCES']) == set(SOURCE_PATHS),
        'F2 driver mount drift'
    )

    require(
        len(found['MOUNTED_SOURCES']) == len(SOURCE_PATHS),
        'duplicate mount'
    )

    require(
        set(found['ARTIFACTS'])
        == set(STATIC_ARTIFACTS) | set(FUTURE_ARTIFACTS),
        'driver artifact names drift'
    )

    require(
        len(found['ARTIFACTS']) == 6,
        'duplicate driver artifact'
    )

    return found


def build_inventory(
    run_id,
    f2bytes,
    planbytes,
    intentbytes,
    reservationbytes,
    source_bytes,
):
    f2, plan, intent, resource = map(
        json.loads,
        (f2bytes, planbytes, intentbytes, reservationbytes)
    )

    require(
        plan.get('run_id') == intent.get('run_id') == run_id,
        'run identity'
    )

    require(
        (plan.get('task'), plan.get('step'), plan.get('status'))
        == ('TASK-003', 'STEP-05G1', 'PLANNED'),
        'G1 plan'
    )

    require(
        (intent.get('task'), intent.get('step'), intent.get('status'))
        == ('TASK-003', 'STEP-05G2C1', 'PREFLIGHT_SNAPSHOT_ONLY'),
        'G2C1 intent'
    )

    require(
        (f2.get('task'), f2.get('step'), f2.get('status'))
        == ('TASK-003', 'STEP-05F2', 'PASS'),
        'F2 PASS'
    )

    require(
        plan.get('source_f2_evidence_sha256') == sha(f2bytes),
        'plan F2 pin'
    )

    require(
        intent.get('step05f2_sha256') == sha(f2bytes),
        'intent F2 pin'
    )

    require(
        intent.get('plan_sha256') == sha(planbytes),
        'intent plan pin'
    )

    require(
        intent.get('write_authorized') is False
        and intent.get('writer_reservation_acquired') is False,
        'premature write intent'
    )

    require(
        plan.get('published') is False
        and plan.get('persisted') is False,
        'premature plan'
    )

    require(
        resource.get('apiVersion') == 'v1'
        and resource.get('kind') == 'ConfigMap'
        and resource.get('immutable') is True
        and resource.get('metadata', {}).get('namespace') == 'dw-spark',
        'reservation definition'
    )

    record = json.loads(
        resource['data']['reservation.json']
    )

    require(
        record.get('run_id') == run_id
        and record.get('plan_sha256') == sha(planbytes)
        and record.get('write_intent_sha256') == sha(intentbytes),
        'reservation evidence pin'
    )

    require(
        record.get('mode') == 'EXCLUSIVE_CREATE_ONLY'
        and record.get('write_authorized') is False,
        'unsafe reservation policy'
    )

    require(
        set(source_bytes)
        == set(SOURCE_PATHS)
        | {
            'run_visit_processed_writer.py',
            'processed_visit_writer_core.py',
        },
        'source inventory missing or extra'
    )

    expected = f2['input']['mounted_file_sha256']

    require(
        set(expected) == set(SOURCE_PATHS),
        'F2 pinned inventory mismatch'
    )

    require(
        plan.get('expected_rows') == f2['result']['candidate_rows']
        and plan.get('expected_persons')
        == f2['result']['referenced_persons'],
        'F2 counts'
    )

    require(
        intent.get('expected_rows') == plan['expected_rows']
        and intent.get('expected_persons') == plan['expected_persons'],
        'intent counts'
    )

    for name, path in SOURCE_PATHS.items():
        require(
            sha(source_bytes[name]) == expected[name],
            'F2 source SHA: ' + path
        )

        require(
            intent.get('source_sha256', {}).get(path)
            == expected[name],
            'intent source SHA: ' + path
        )

    driver_inventory(
        source_bytes['run_visit_processed_writer.py']
    )

    source_catalog = {}

    for name, blob in source_bytes.items():
        path = SOURCE_PATHS.get(
            name,
            DRIVER_PATH
            if name == 'run_visit_processed_writer.py'
            else CORE_PATH
        )

        source_catalog[name] = {
            'repo_path': path,
            'sha256': sha(blob),
            'size_bytes': len(blob),
        }

    static_blobs = dict(
        f2=f2bytes,
        plan=planbytes,
        intent=intentbytes,
        reservation=reservationbytes,
    )

    artifact_catalog = {
        filename: {
            'sha256': sha(static_blobs[key]),
            'size_bytes': len(static_blobs[key]),
        }
        for filename, key in STATIC_ARTIFACTS.items()
    }

    total = sum(
        value['size_bytes']
        for value in source_catalog.values()
    ) + sum(
        value['size_bytes']
        for value in artifact_catalog.values()
    )

    require(
        total < 650000,
        'static ConfigMap payload too large'
    )

    return {
        'schema':
            'task003.visit_processed.bundle_inventory.v1',
        'task': 'TASK-003',
        'step': 'STEP-05G2C2C2B1',
        'status': 'SOURCE_INVENTORY_ONLY',
        'run_id': run_id,
        'reservation_name':
            resource['metadata']['name'],
        'data_uri': plan['data_uri'],
        'source_files': source_catalog,
        'static_artifacts': artifact_catalog,
        'future_artifacts_required':
            list(FUTURE_ARTIFACTS),
        'future_driver_input_required':
            'processed-writer-input.json',
        'static_payload_bytes': total,
        'configmap_created': False,
        'reservation_acquired': False,
        'permit_issued': False,
        'write_authorized': False,
        'spark_submitted': False,
        's3_write': False,
        'postgresql_write': False,
    }


def read_regular(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError(
            'Missing or symlinked source: ' + str(path)
        )
    return path.read_bytes()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--root', type=Path, required=True
    )
    parser.add_argument(
        '--f2-state', type=Path, required=True
    )
    parser.add_argument(
        '--run-id', required=True
    )

    args = parser.parse_args()

    require(
        args.run_id
        and len(args.run_id) <= 128
        and all(
            c.isalnum() or c in '._-'
            for c in args.run_id
        )
        and args.run_id not in ('.', '..'),
        'unsafe run ID'
    )

    root = args.root.resolve()

    base = (
        root / 'runtime/reports/task003/step05'
    )

    planpath = (
        base / 'processed-plans'
        / args.run_id / 'plan.json'
    )

    intentpath = (
        base / 'processed-intents'
        / args.run_id / 'write-intent.json'
    )

    respath = (
        base / 'writer-reservations'
        / args.run_id / 'reservation-create.json'
    )

    inputs = [
        read_regular(path)
        for path in (
            args.f2_state,
            planpath,
            intentpath,
            respath,
        )
    ]

    file_map = {
        name: read_regular(root / path)
        for name, path in SOURCE_PATHS.items()
    }

    file_map['run_visit_processed_writer.py'] = (
        read_regular(root / DRIVER_PATH)
    )

    file_map['processed_visit_writer_core.py'] = (
        read_regular(root / CORE_PATH)
    )

    inventory = build_inventory(
        args.run_id,
        *inputs,
        file_map,
    )

    output = (
        base / 'processed-bundle-inventories'
        / args.run_id / 'source-inventory.json'
    )

    status = save_once(output, inventory)

    print('BUNDLE_INVENTORY_STATUS=' + status)
    print(
        'BUNDLE_SOURCE_FILE_COUNT='
        + str(len(inventory['source_files']))
    )
    print(
        'BUNDLE_STATIC_ARTIFACT_COUNT='
        + str(len(inventory['static_artifacts']))
    )
    print(
        'BUNDLE_STATIC_PAYLOAD_BYTES='
        + str(inventory['static_payload_bytes'])
    )
    print(
        'BUNDLE_INVENTORY_SHA256='
        + sha(output.read_bytes())
    )
    print('BUNDLE_INVENTORY_FILE=' + str(output))
    print('RUNTIME_PERMIT_REQUIRED=YES')
    print('K8S_CONFIGMAP_CREATED=NO')
    print('K8S_RESERVATION_ACQUIRED=NO')
    print('SPARK_APPLICATION_SUBMITTED=NO')
    print('S3_WRITE=NO')
    print('DATABASE_WRITE=NO')


if __name__ == '__main__':
    main()
