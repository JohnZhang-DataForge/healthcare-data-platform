#!/usr/bin/env python3
"""Verify remote Encounter manifest/DQ bytes; does not verify Parquet contents."""
import argparse
import hashlib
import json
from pathlib import Path
from resolve_approved_encounter_raw import require, resolve


def verify_metadata(context, manifest_bytes, dq_bytes):
    for data, key in (
        (manifest_bytes, 'raw_manifest_sha256'),
        (dq_bytes, 'dq_sha256'),
    ):
        require(hashlib.sha256(data).hexdigest(), context[key], key)

    manifest, dq = json.loads(manifest_bytes), json.loads(dq_bytes)
    require(manifest.get('status'), 'APPROVED', 'manifest status')
    require(dq.get('status'), 'PASS', 'DQ status')

    for doc in (manifest, dq):
        for key in (
            'source', 'source_version', 'batch_id', 'ingest_date',
            'processing_run_id', 'raw_publish_run_id',
        ):
            require(doc.get(key), context[key], key)
        require(doc.get('entity'), 'encounter', 'entity')
        require(doc.get('canonical_version'), 'v1', 'canonical version')
        for key in ('expected_rows', 'raw_rows', 'raw_unique_keys'):
            require(doc.get(key), context['expected_rows'], key)

    require(manifest.get('data'), dict(
        uri=context['raw_data_uri'],
        format='parquet',
        row_count=context['expected_rows'],
        primary_key=['source_system', 'source_encounter_id'],
        unique_primary_keys=context['expected_rows'],
    ), 'manifest data')

    require(manifest.get('dq'), dict(
        status='PASS',
        uri=context['dq_uri'],
        sha256=context['dq_sha256'],
        readback_sha256='PASS',
    ), 'manifest DQ link')

    checks = (
        'canonical_schema canonical_required_fields canonical_metadata '
        'canonical_primary_key raw_write raw_readback'
    ).split()
    require(dq.get('checks'), {key: 'PASS' for key in checks}, 'DQ checks')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare', 'verify'))
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--context', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()

    raw = args.context.read_bytes()
    context = json.loads(raw)
    fresh = resolve(args.root, context['raw_publish_run_id'])
    require(context, fresh, 'pinned STEP05A context vs current local evidence')

    saved = args.report / 'input-context.json'
    if args.phase == 'prepare':
        saved.write_bytes(raw)
        plan = '\n'.join([
            context['raw_manifest_uri'] + '\tmanifest.remote.json',
            context['dq_uri'] + '\tdq.remote.json',
        ]) + '\n'
        (args.report / 'download-plan.tsv').write_text(plan)
        print('PINNED_LOCAL_INPUT_REVALIDATED=PASS')
        return

    require(saved.read_bytes(), raw, 'input context unchanged during download')
    verify_metadata(
        context,
        (args.report / 'manifest.remote.json').read_bytes(),
        (args.report / 'dq.remote.json').read_bytes(),
    )

    state = dict(
        task='TASK-003',
        step='STEP-05D',
        status='PASS',
        validation_scope='remote_manifest_and_dq_bytes',
        input_context=context,
        input_context_sha256=hashlib.sha256(raw).hexdigest(),
        remote_metadata_verified=True,
        remote_parquet_verified=False,
        postgresql_write=False,
        s3_write=False,
    )
    (args.report / 'run-state.json').write_text(
        json.dumps(state, indent=2) + '\n'
    )
    print('REMOTE_MANIFEST_SHA256=PASS')
    print('REMOTE_DQ_SHA256=PASS')
    print('REMOTE_METADATA_LINEAGE=PASS')
    print('REMOTE_METADATA_REVALIDATION=PASS')
    print('MANIFEST_DECLARED_ROWS=' + str(context['expected_rows']))
    print('RAW_PUBLISH_RUN_ID=' + context['raw_publish_run_id'])
    print('REMOTE_PARQUET_REVALIDATION=PENDING')


if __name__ == '__main__':
    main()
