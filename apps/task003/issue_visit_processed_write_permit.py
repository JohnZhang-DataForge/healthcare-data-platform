"""Build a short-lived single-write Permit for TASK-003.

This module itself performs no Kubernetes mutation,
no Spark submission, no S3 write and no database write.

The caller must provide a freshly-read live Reservation object.
"""

import argparse
import hashlib
import json

from datetime import (
    datetime,
    timedelta,
    timezone,
)

from pathlib import Path

from inspect_visit_processed_prefix import classify


MAX_TTL_SECONDS = 300
DEFAULT_TTL_SECONDS = 180


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(
            'WRITE_PERMIT_CONFLICT: ' + message
        )


def read_regular(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError(
            'Unsafe evidence path: ' + str(path)
        )

    return path.read_bytes()


def build_permit(
    plan_bytes,
    intent_bytes,
    reservation_spec_bytes,
    c3a_state_bytes,
    c3b_state_bytes,
    live_reservation_bytes,
    fresh_listing_bytes,
    person_snapshot_bytes,
    now=None,
    ttl_seconds=DEFAULT_TTL_SECONDS,
):
    plan = json.loads(plan_bytes)
    intent = json.loads(intent_bytes)
    spec = json.loads(reservation_spec_bytes)
    c3a = json.loads(c3a_state_bytes)
    c3b = json.loads(c3b_state_bytes)
    live = json.loads(live_reservation_bytes)
    listing = json.loads(fresh_listing_bytes)

    require(
        type(ttl_seconds) is int
        and 0 < ttl_seconds <= MAX_TTL_SECONDS,
        'TTL must be between 1 and 300 seconds'
    )

    now = now or datetime.now(timezone.utc)

    require(
        now.tzinfo is not None,
        'timezone-aware current time required'
    )

    now = now.astimezone(timezone.utc)

    # ------------------------------------------------------
    # Plan and Intent
    # ------------------------------------------------------

    require(
        (
            plan.get('task'),
            plan.get('step'),
            plan.get('status'),
        )
        == (
            'TASK-003',
            'STEP-05G1',
            'PLANNED',
        ),
        'G1 plan state'
    )

    require(
        (
            intent.get('task'),
            intent.get('step'),
            intent.get('status'),
        )
        == (
            'TASK-003',
            'STEP-05G2C1',
            'PREFLIGHT_SNAPSHOT_ONLY',
        ),
        'G2C1 Intent state'
    )

    run_id = plan.get('run_id')

    require(
        isinstance(run_id, str)
        and run_id
        and intent.get('run_id') == run_id,
        'run identity'
    )

    require(
        intent.get('plan_sha256')
        == sha(plan_bytes),
        'Intent Plan pin'
    )

    require(
        intent.get('write_authorized') is False,
        'Intent already authorized'
    )

    require(
        plan.get('persisted') is False
        and plan.get('published') is False
        and plan.get('s3_write') is False
        and plan.get('postgresql_write') is False
        and plan.get('visit_ids_allocated') == 0,
        'Plan already mutated'
    )

    # ------------------------------------------------------
    # Reservation Spec
    # ------------------------------------------------------

    require(
        spec.get('apiVersion') == 'v1'
        and spec.get('kind') == 'ConfigMap'
        and spec.get('immutable') is True,
        'Reservation spec'
    )

    metadata = spec.get('metadata', {})

    require(
        metadata.get('namespace') == 'dw-spark',
        'Reservation namespace'
    )

    name = metadata.get('name')

    require(
        isinstance(name, str)
        and name.startswith('visit-proc-lock-'),
        'Reservation name'
    )

    record = json.loads(
        spec['data']['reservation.json']
    )

    require(
        record.get('run_id') == run_id,
        'Reservation run'
    )

    require(
        record.get('plan_sha256')
        == sha(plan_bytes),
        'Reservation Plan pin'
    )

    require(
        record.get('write_intent_sha256')
        == sha(intent_bytes),
        'Reservation Intent pin'
    )

    require(
        record.get('mode')
        == 'EXCLUSIVE_CREATE_ONLY',
        'Reservation mode'
    )

    require(
        record.get('release_policy')
        == 'NO_AUTOMATIC_DELETE',
        'Reservation release policy'
    )

    require(
        record.get('write_authorized') is False,
        'Reservation incorrectly authorized'
    )

    # ------------------------------------------------------
    # C3A acquisition evidence
    # ------------------------------------------------------

    require(
        (
            c3a.get('task'),
            c3a.get('step'),
            c3a.get('status'),
        )
        == (
            'TASK-003',
            'STEP-05G2C2C3A',
            'RESERVATION_ACQUIRED',
        ),
        'C3A state'
    )

    require(
        c3a.get('run_id') == run_id,
        'C3A run'
    )

    require(
        c3a.get('reservation_name') == name,
        'C3A Reservation name'
    )

    require(
        c3a.get('reservation_spec_sha256')
        == sha(reservation_spec_bytes),
        'C3A Reservation Spec pin'
    )

    require(
        c3a.get('plan_sha256')
        == sha(plan_bytes),
        'C3A Plan pin'
    )

    require(
        c3a.get('write_intent_sha256')
        == sha(intent_bytes),
        'C3A Intent pin'
    )

    require(
        c3a.get('reservation_created_by_k8s_create')
        is True
        and c3a.get('reservation_verified') is True,
        'C3A Reservation not verified'
    )

    require(
        c3a.get('fresh_s3_relist_passed') is False
        and c3a.get('write_permit_issued') is False
        and c3a.get('write_authorized') is False,
        'C3A contains premature authorization'
    )

    uid = c3a.get('reservation_uid')
    resource_version = c3a.get(
        'reservation_resource_version'
    )

    require(
        isinstance(uid, str)
        and len(uid) >= 8,
        'C3A UID'
    )

    require(
        isinstance(resource_version, str)
        and resource_version.isdigit(),
        'C3A resourceVersion'
    )

    # ------------------------------------------------------
    # C3B post-lock evidence
    # ------------------------------------------------------

    require(
        (
            c3b.get('task'),
            c3b.get('step'),
            c3b.get('status'),
        )
        == (
            'TASK-003',
            'STEP-05G2C2C3B',
            'POSTLOCK_PREFLIGHT_PASS',
        ),
        'C3B state'
    )

    require(
        c3b.get('run_id') == run_id,
        'C3B run'
    )

    require(
        c3b.get('reservation_name') == name
        and c3b.get('reservation_uid') == uid
        and c3b.get('reservation_resource_version')
        == resource_version,
        'C3B Reservation identity'
    )

    require(
        c3b.get('reservation_spec_sha256')
        == sha(reservation_spec_bytes),
        'C3B Reservation Spec pin'
    )

    require(
        c3b.get('plan_sha256')
        == sha(plan_bytes),
        'C3B Plan pin'
    )

    require(
        c3b.get('write_intent_sha256')
        == sha(intent_bytes),
        'C3B Intent pin'
    )

    require(
        c3b.get('c3a_state_sha256')
        == sha(c3a_state_bytes),
        'C3B C3A pin'
    )

    require(
        c3b.get('fresh_s3_listing_sha256')
        == sha(fresh_listing_bytes),
        'C3B fresh listing pin'
    )

    require(
        c3b.get('fresh_s3_classification')
        == 'EMPTY'
        and c3b.get('fresh_s3_object_count') == 0
        and c3b.get('fresh_s3_relist_passed') is True,
        'C3B S3 state'
    )

    require(
        c3b.get('person_map_fingerprint_captured')
        is True,
        'C3B Person fingerprint not captured'
    )

    require(
        c3b.get('reservation_still_held') is True,
        'C3B Reservation not held'
    )

    require(
        c3b.get('write_permit_issued') is False
        and c3b.get('write_authorized') is False,
        'C3B already authorized'
    )

    # ------------------------------------------------------
    # Live Reservation readback
    # ------------------------------------------------------

    require(
        live.get('apiVersion') == 'v1'
        and live.get('kind') == 'ConfigMap'
        and live.get('immutable') is True,
        'live Reservation object'
    )

    live_meta = live.get('metadata', {})

    require(
        live_meta.get('name') == name
        and live_meta.get('namespace') == 'dw-spark',
        'live Reservation identity'
    )

    require(
        live_meta.get('uid') == uid,
        'live Reservation UID drift'
    )

    require(
        live_meta.get('resourceVersion')
        == resource_version,
        'live Reservation resourceVersion drift'
    )

    require(
        live_meta.get('labels')
        == metadata.get('labels'),
        'live Reservation labels drift'
    )

    require(
        live.get('data', {}).get('reservation.json')
        == spec['data']['reservation.json'],
        'live Reservation payload drift'
    )

    # ------------------------------------------------------
    # Fresh S3 evidence
    # ------------------------------------------------------

    inspection = classify(
        plan,
        listing,
    )

    require(
        inspection['classification'] == 'EMPTY'
        and inspection['object_count'] == 0
        and inspection['new_write_guard'] == 'PASS',
        'fresh S3 prefix is not empty'
    )

    # ------------------------------------------------------
    # Current Person Map fingerprint
    # ------------------------------------------------------

    people = json.loads(
        person_snapshot_bytes
    )

    require(
        isinstance(people, list),
        'Person snapshot'
    )

    require(
        len(people) == plan['expected_persons'],
        'Person count drift'
    )

    identities = set()
    person_ids = set()

    for row in people:
        require(
            isinstance(row, list)
            and len(row) == 3,
            'Person snapshot row'
        )

        source_system, source_person_id, person_id = row

        require(
            source_system == 'synthea',
            'Person source'
        )

        require(
            isinstance(source_person_id, str)
            and source_person_id,
            'Person source ID'
        )

        require(
            type(person_id) is int
            and person_id > 0,
            'OMOP person_id'
        )

        identity = (
            source_system,
            source_person_id,
        )

        require(
            identity not in identities,
            'duplicate source Person'
        )

        require(
            person_id not in person_ids,
            'duplicate OMOP Person'
        )

        identities.add(identity)
        person_ids.add(person_id)

    fingerprint = sha(
        person_snapshot_bytes
    )

    require(
        c3b.get('person_map_fingerprint')
        == fingerprint,
        'Person fingerprint drift'
    )

    require(
        c3b.get('person_map_rows')
        == len(people),
        'Person snapshot count'
    )

    # ------------------------------------------------------
    # Build <=5 minute Permit
    # ------------------------------------------------------

    issued = now

    expires = (
        issued
        + timedelta(
            seconds=ttl_seconds
        )
    )

    permit = {
        'task':
            'TASK-003',

        'step':
            'STEP-05G2C2C',

        'status':
            'AUTHORIZED_FOR_SINGLE_WRITE',

        'write_authorized':
            True,

        'reservation_created_by_k8s_create':
            True,

        'reservation_verified':
            True,

        'fresh_s3_relist_passed':
            True,

        'fresh_prefix_classification':
            'EMPTY',

        'candidate_published':
            False,

        'postgresql_write':
            False,

        'run_id':
            run_id,

        'data_uri':
            plan['data_uri'],

        'plan_sha256':
            sha(plan_bytes),

        'intent_sha256':
            sha(intent_bytes),

        'reservation_spec_sha256':
            sha(reservation_spec_bytes),

        'fresh_listing_sha256':
            sha(fresh_listing_bytes),

        'reservation_name':
            name,

        'reservation_uid':
            uid,

        'reservation_resource_version':
            resource_version,

        'issued_at_utc':
            issued.isoformat(),

        'expires_at_utc':
            expires.isoformat(),

        'person_map_fingerprint':
            fingerprint,

        # Additional audit pins.
        'c3a_state_sha256':
            sha(c3a_state_bytes),

        'c3b_state_sha256':
            sha(c3b_state_bytes),

        'person_map_snapshot_sha256':
            sha(person_snapshot_bytes),

        'ttl_seconds':
            ttl_seconds,
    }

    return permit


def main():
    parser = argparse.ArgumentParser(
        description=__doc__
    )

    parser.add_argument(
        '--root',
        required=True,
        type=Path,
    )

    parser.add_argument(
        '--run-id',
        required=True,
    )

    parser.add_argument(
        '--c3a-report',
        required=True,
        type=Path,
    )

    parser.add_argument(
        '--c3b-report',
        required=True,
        type=Path,
    )

    parser.add_argument(
        '--live-reservation',
        required=True,
        type=Path,
    )

    parser.add_argument(
        '--ttl-seconds',
        type=int,
        default=DEFAULT_TTL_SECONDS,
    )

    parser.add_argument(
        '--output',
        required=True,
        type=Path,
    )

    args = parser.parse_args()

    root = args.root.resolve()

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

    base = (
        root
        / 'runtime/reports/task003/step05'
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

    spec_path = (
        base
        / 'writer-reservations'
        / args.run_id
        / 'reservation-create.json'
    )

    c3a_state = (
        args.c3a_report
        / 'run-state.json'
    )

    c3b_state = (
        args.c3b_report
        / 'run-state.json'
    )

    listing_path = (
        args.c3b_report
        / 'fresh-s3-listing.json'
    )

    person_path = (
        args.c3b_report
        / 'person-map-snapshot.json'
    )

    blobs = [
        read_regular(path)

        for path in (
            plan_path,
            intent_path,
            spec_path,
            c3a_state,
            c3b_state,
            args.live_reservation,
            listing_path,
            person_path,
        )
    ]

    permit = build_permit(
        *blobs,
        ttl_seconds=args.ttl_seconds,
    )

    output = args.output

    require(
        not output.is_symlink(),
        'Permit output cannot be a symlink'
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    permit_bytes = (
        json.dumps(
            permit,
            indent=2,
            sort_keys=True,
        )
        + '\n'
    ).encode('utf-8')

    with output.open('xb') as handle:
        handle.write(
            permit_bytes
        )

    print('WRITE_PERMIT_FILE=' + str(output))

    print(
        'WRITE_PERMIT_SHA256='
        + sha(permit_bytes)
    )

    print(
        'WRITE_PERMIT_TTL_SECONDS='
        + str(
            permit['ttl_seconds']
        )
    )

    print(
        'PERSON_MAP_FINGERPRINT='
        + permit[
            'person_map_fingerprint'
        ]
    )

    print(
        'RESERVATION_UID='
        + permit['reservation_uid']
    )

    print(
        'RESERVATION_RESOURCE_VERSION='
        + permit[
            'reservation_resource_version'
        ]
    )

    print('WRITE_PERMIT_ISSUED=YES')
    print('WRITE_AUTHORIZED=YES')
    print('SPARK_APPLICATION_SUBMITTED=NO')
    print('S3_WRITE=NO')
    print('DATABASE_WRITE=NO')


if __name__ == '__main__':
    main()
