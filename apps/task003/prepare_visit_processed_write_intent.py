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
