"""Fail-closed S3 prefix inspection for Processed Visit.

Only examines a supplied S3 list-objects-v2 response.
Does not authorize publication, resume, overwrite or concurrency.
"""

import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit


class PrefixGuardError(ValueError):
    pass


def require(condition, label):
    if not condition:
        raise PrefixGuardError(label)


def get_prefix(plan):
    require(isinstance(plan, dict), 'plan must be an object')

    for name, expected in (
        ('task', 'TASK-003'),
        ('step', 'STEP-05G1'),
        ('status', 'PLANNED'),
        ('persisted', False),
        ('published', False),
        ('s3_write', False),
        ('postgresql_write', False),
        ('visit_ids_allocated', 0),
    ):
        require(
            type(plan.get(name)) is type(expected)
            and plan[name] == expected,
            'unsafe plan field: ' + name
        )

    policy = plan.get('publication_policy')
    require(isinstance(policy, dict), 'missing policy')

    require(
        policy.get('output_bucket') == 'health-processed',
        'bucket policy'
    )
    require(
        policy.get('publication_gate') == 'APPROVED_manifest_last',
        'gate policy'
    )
    require(
        policy.get('same_run_conflict') == 'STOP_WITHOUT_OVERWRITE',
        'conflict policy'
    )
    require(
        policy.get('same_run_replay') == 'REUSE_ONLY_IF_VERIFIED_IDENTICAL',
        'replay policy'
    )
    require(
        policy.get('objects') == [
            'data/', 'dq/result.json', 'manifest.json'
        ],
        'object layout'
    )

    run_id = plan.get('run_id')
    require(
        isinstance(run_id, str)
        and run_id
        and '/' not in run_id
        and run_id not in ('.', '..'),
        'unsafe run ID'
    )

    base = plan.get('base_uri')
    require(isinstance(base, str), 'missing base URI')

    parsed = urlsplit(base)

    require(
        parsed.scheme == 's3'
        and parsed.netloc == 'health-processed',
        'unexpected S3 bucket'
    )
    require(
        not parsed.query and not parsed.fragment,
        'unexpected S3 URL suffix'
    )

    key = parsed.path.lstrip('/')
    parts = key.split('/')

    require(len(parts) == 8, 'unexpected prefix components')

    require(
        parts[0:3] == [
            'contract_version=v1',
            'entity=visit_occurrence',
            'source=synthea'
        ],
        'unexpected processed layout'
    )

    require(
        parts[-1] == 'run_id=' + run_id,
        'run identity differs from prefix'
    )

    require(
        all(
            part and part not in ('.', '..')
            and '\\' not in part
            for part in parts
        ),
        'invalid prefix segment'
    )

    require(
        key and not key.endswith('/'),
        'base URI must not end in slash'
    )

    for field, suffix in (
        ('data_uri', '/data/'),
        ('dq_uri', '/dq/result.json'),
        ('manifest_uri', '/manifest.json'),
    ):
        require(
            plan.get(field) == base + suffix,
            'invalid plan target: ' + field
        )

    return 'health-processed', key + '/'


def classify(plan, listing):
    bucket, prefix = get_prefix(plan)

    require(
        isinstance(listing, dict),
        'listing must be an object'
    )

    # SeaweedFS may return {"RequestCharged": null}
    # for an empty result. Do not require KeyCount.
    require(
        any(
            k in listing
            for k in ('Contents', 'KeyCount', 'RequestCharged')
        ),
        'invalid S3 listing: no recognized fields'
    )

    require(
        listing.get('IsTruncated', False) is False,
        'truncated listing; refuse partial evidence'
    )

    require(
        not listing.get('NextContinuationToken'),
        'unconsumed listing page'
    )

    contents = listing.get('Contents', [])

    require(
        isinstance(contents, list),
        'invalid Contents'
    )

    if 'KeyCount' in listing:
        count = listing['KeyCount']
        require(
            type(count) is int and count == len(contents),
            'inconsistent KeyCount'
        )

    keys = set()
    data_count = 0
    dq_present = False
    manifest_present = False

    for obj in contents:
        require(
            isinstance(obj, dict),
            'invalid S3 object'
        )

        key = obj.get('Key')
        size = obj.get('Size')

        require(
            isinstance(key, str)
            and key.startswith(prefix),
            'unexpected object key'
        )

        require(
            type(size) is int and size >= 0,
            'invalid S3 object size'
        )

        require(
            key not in keys,
            'duplicate S3 object key'
        )
        keys.add(key)

        suffix = key[len(prefix):]

        require(
            suffix
            and '//' not in suffix
            and all(
                p not in ('.', '..')
                for p in suffix.split('/')
            ),
            'invalid key suffix'
        )

        if suffix.startswith('data/'):
            data_count += 1

        elif suffix == 'dq/result.json':
            dq_present = True

        elif suffix == 'manifest.json':
            manifest_present = True

        else:
            raise PrefixGuardError(
                'unexpected object under run prefix: '
                + suffix
            )

    require(
        not dq_present or data_count > 0,
        'DQ exists without any data objects'
    )

    require(
        not manifest_present
        or (dq_present and data_count > 0),
        'manifest exists without complete expected layout'
    )

    if not contents:
        state = 'EMPTY'

    elif manifest_present:
        state = 'MANIFEST_PRESENT_UNVERIFIED'

    elif dq_present:
        state = 'DATA_AND_DQ_UNVERIFIED'

    else:
        state = 'DATA_PRESENT_UNVERIFIED'

    return {
        'bucket': bucket,
        'prefix': prefix,
        'object_count': len(contents),
        'data_object_count': data_count,
        'dq_object_present': dq_present,
        'manifest_object_present': manifest_present,
        'classification': state,
        'new_write_guard': (
            'PASS' if state == 'EMPTY' else 'STOP'
        ),
        'publication_verified': False,
        'resume_authorized': False,
        'concurrent_writer_protection': False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--listing', type=Path, required=True)
    args = parser.parse_args()

    result = classify(
        json.loads(args.plan.read_bytes()),
        json.loads(args.listing.read_bytes())
    )

    print(
        'PROCESSED_PREFIX_CLASSIFICATION='
        + result['classification']
    )
    print(
        'PREFIX_OBJECT_COUNT='
        + str(result['object_count'])
    )
    print(
        'PREFIX_NEW_WRITE_GUARD='
        + result['new_write_guard']
    )

    print('PUBLISHED_VERIFIED=NO')
    print('RESUME_AUTHORIZED=NO')
    print('CONCURRENT_WRITER_PROTECTION=NOT_ESTABLISHED')

    if result['new_write_guard'] != 'PASS':
        raise SystemExit(3)


if __name__ == '__main__':
    main()
