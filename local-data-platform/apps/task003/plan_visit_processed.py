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
