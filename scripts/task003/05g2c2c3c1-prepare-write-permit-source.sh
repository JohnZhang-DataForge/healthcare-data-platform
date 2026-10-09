#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT="${HEALTHCARE_PROJECT_ROOT:-/data/spark/healthcare-data-platform}"
SOURCE="${BASH_SOURCE[0]:-}"
STAGE=''

echo '#### TASK003 STEP05G2C2C3C1 WRITE PERMIT SOURCE OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  [[ -z "$STAGE" ]] || rm -rf -- "$STAGE"

  echo "INSTALL_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G2C2C3C1 WRITE PERMIT SOURCE OUTPUT END ####'
  exit "$rc"
}

trap finish EXIT

[[ -n "$SOURCE" && -f "$SOURCE" ]] || {
  echo 'ERROR: execute installer as a saved Bash file'
  exit 2
}

for rel in \
  apps/task003/inspect_visit_processed_prefix.py \
  spark/apps/visit/processed_visit_writer_core.py
do
  [[ -s "$ROOT/$rel" && ! -L "$ROOT/$rel" ]] || {
    echo "ERROR: missing prerequisite: $rel"
    exit 2
  }
done

STAGE=$(mktemp -d /data/spark/temp_shell/g2c2c3c1.XXXXXXXX)

mkdir -p \
  "$STAGE/apps/task003" \
  "$STAGE/tests/task003" \
  "$STAGE/scripts/task003" \
  "$STAGE/spark/apps/visit"

# ==========================================================
# 1. Canonical Permit builder
# ==========================================================

cat > "$STAGE/apps/task003/issue_visit_processed_write_permit.py" <<'PY_APP'
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
PY_APP

# ==========================================================
# 2. Unit tests
# ==========================================================

cat > "$STAGE/tests/task003/test_visit_processed_write_permit.py" <<'PY_TEST'
import copy
import json
import sys
import unittest

from datetime import (
    datetime,
    timezone,
)

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(
    0,
    str(ROOT / 'apps/task003')
)

sys.path.insert(
    0,
    str(ROOT / 'spark/apps/visit')
)


from issue_visit_processed_write_permit import (
    build_permit,
    sha,
)

from processed_visit_writer_core import (
    validate_permit,
)


def pack(value):
    return (
        json.dumps(
            value,
            sort_keys=True,
        )
        + '\n'
    ).encode()


class PermitTests(unittest.TestCase):

    def setUp(self):
        self.now = datetime(
            2026,
            10,
            9,
            21,
            0,
            tzinfo=timezone.utc,
        )

        base = (
            's3://health-processed/'
            'contract_version=v1/'
            'entity=visit_occurrence/'
            'source=synthea/'
            'source_version=v3.3.0/'
            'ingest_date=2026-10-08/'
            'batch_id=test/'
            'raw_publish_run_id=raw-test/'
            'run_id=test-run'
        )

        self.plan = {
            'task':
                'TASK-003',

            'step':
                'STEP-05G1',

            'status':
                'PLANNED',

            'run_id':
                'test-run',

            'base_uri':
                base,

            'data_uri':
                base + '/data/',

            'dq_uri':
                base + '/dq/result.json',

            'manifest_uri':
                base + '/manifest.json',

            'expected_persons':
                2,

            'persisted':
                False,

            'published':
                False,

            's3_write':
                False,

            'postgresql_write':
                False,

            'visit_ids_allocated':
                0,

            'publication_policy': {
                'output_bucket':
                    'health-processed',

                'publication_gate':
                    'APPROVED_manifest_last',

                'same_run_conflict':
                    'STOP_WITHOUT_OVERWRITE',

                'same_run_replay':
                    'REUSE_ONLY_IF_VERIFIED_IDENTICAL',

                'objects': [
                    'data/',
                    'dq/result.json',
                    'manifest.json',
                ],
            },
        }

        self.plan_bytes = pack(
            self.plan
        )

        self.intent = {
            'task':
                'TASK-003',

            'step':
                'STEP-05G2C1',

            'status':
                'PREFLIGHT_SNAPSHOT_ONLY',

            'run_id':
                'test-run',

            'plan_sha256':
                sha(self.plan_bytes),

            'write_authorized':
                False,
        }

        self.intent_bytes = pack(
            self.intent
        )

        prefix = (
            base.split(
                'health-processed/',
                1,
            )[1]
            + '/'
        )

        record = {
            'reservation_schema':
                'task003.visit_processed.'
                'writer_reservation.v1',

            'run_id':
                'test-run',

            'bucket':
                'health-processed',

            'prefix':
                prefix,

            'write_intent_sha256':
                sha(self.intent_bytes),

            'plan_sha256':
                sha(self.plan_bytes),

            'mode':
                'EXCLUSIVE_CREATE_ONLY',

            'on_existing_reservation':
                'STOP_MANUAL_RECONCILIATION',

            'release_policy':
                'NO_AUTOMATIC_DELETE',

            's3_prefix_must_be_relisted_after_create':
                True,

            'write_authorized':
                False,
        }

        self.spec = {
            'apiVersion':
                'v1',

            'kind':
                'ConfigMap',

            'metadata': {
                'name':
                    'visit-proc-lock-test',

                'namespace':
                    'dw-spark',

                'labels': {
                    'healthcare-task':
                        'task003',

                    'healthcare-purpose':
                        'visit-processed-writer-lock',
                },
            },

            'immutable':
                True,

            'data': {
                'reservation.json':
                    json.dumps(
                        record,
                        sort_keys=True,
                        separators=(',', ':'),
                    )
            },
        }

        self.spec_bytes = pack(
            self.spec
        )

        self.c3a = {
            'task':
                'TASK-003',

            'step':
                'STEP-05G2C2C3A',

            'status':
                'RESERVATION_ACQUIRED',

            'run_id':
                'test-run',

            'reservation_name':
                'visit-proc-lock-test',

            'reservation_uid':
                '123e4567-e89b-12d3-a456-426614174000',

            'reservation_resource_version':
                '12345',

            'reservation_spec_sha256':
                sha(self.spec_bytes),

            'plan_sha256':
                sha(self.plan_bytes),

            'write_intent_sha256':
                sha(self.intent_bytes),

            'reservation_created_by_k8s_create':
                True,

            'reservation_verified':
                True,

            'fresh_s3_relist_passed':
                False,

            'write_permit_issued':
                False,

            'write_authorized':
                False,
        }

        self.c3a_bytes = pack(
            self.c3a
        )

        self.listing = {
            'RequestCharged': None
        }

        self.listing_bytes = pack(
            self.listing
        )

        self.people = [
            [
                'synthea',
                'a',
                1,
            ],
            [
                'synthea',
                'b',
                2,
            ],
        ]

        self.people_bytes = json.dumps(
            self.people,
            separators=(',', ':'),
            ensure_ascii=False,
        ).encode()

        fingerprint = sha(
            self.people_bytes
        )

        self.c3b = {
            'task':
                'TASK-003',

            'step':
                'STEP-05G2C2C3B',

            'status':
                'POSTLOCK_PREFLIGHT_PASS',

            'run_id':
                'test-run',

            'reservation_name':
                'visit-proc-lock-test',

            'reservation_uid':
                self.c3a[
                    'reservation_uid'
                ],

            'reservation_resource_version':
                '12345',

            'reservation_spec_sha256':
                sha(self.spec_bytes),

            'plan_sha256':
                sha(self.plan_bytes),

            'write_intent_sha256':
                sha(self.intent_bytes),

            'c3a_state_sha256':
                sha(self.c3a_bytes),

            'fresh_s3_listing_sha256':
                sha(self.listing_bytes),

            'fresh_s3_classification':
                'EMPTY',

            'fresh_s3_object_count':
                0,

            'fresh_s3_relist_passed':
                True,

            'person_map_rows':
                2,

            'person_map_fingerprint':
                fingerprint,

            'person_map_fingerprint_captured':
                True,

            'reservation_still_held':
                True,

            'write_permit_issued':
                False,

            'write_authorized':
                False,
        }

        self.c3b_bytes = pack(
            self.c3b
        )

        self.live = copy.deepcopy(
            self.spec
        )

        self.live['metadata']['uid'] = (
            self.c3a['reservation_uid']
        )

        self.live[
            'metadata'
        ][
            'resourceVersion'
        ] = '12345'

        self.live_bytes = pack(
            self.live
        )

    def build(self, ttl=180):
        return build_permit(
            self.plan_bytes,
            self.intent_bytes,
            self.spec_bytes,
            self.c3a_bytes,
            self.c3b_bytes,
            self.live_bytes,
            self.listing_bytes,
            self.people_bytes,
            now=self.now,
            ttl_seconds=ttl,
        )

    def test_valid_permit_matches_writer_core(self):
        permit = self.build()

        validated = validate_permit(
            permit,
            self.plan_bytes,
            self.intent_bytes,
            self.spec_bytes,
            self.listing_bytes,
            now=self.now,
        )

        self.assertEqual(
            validated,
            self.plan,
        )

        self.assertTrue(
            permit['write_authorized']
        )

        self.assertEqual(
            permit['ttl_seconds'],
            180,
        )

    def test_ttl_over_300_rejected(self):
        with self.assertRaises(ValueError):
            self.build(301)

    def test_zero_ttl_rejected(self):
        with self.assertRaises(ValueError):
            self.build(0)

    def test_live_uid_drift_rejected(self):
        self.live[
            'metadata'
        ][
            'uid'
        ] = 'different-uid'

        self.live_bytes = pack(
            self.live
        )

        with self.assertRaises(ValueError):
            self.build()

    def test_live_resource_version_drift_rejected(self):
        self.live[
            'metadata'
        ][
            'resourceVersion'
        ] = '99999'

        self.live_bytes = pack(
            self.live
        )

        with self.assertRaises(ValueError):
            self.build()

    def test_nonempty_s3_rejected(self):
        prefix = (
            self.plan['base_uri']
            .split(
                'health-processed/',
                1,
            )[1]
            + '/'
        )

        self.listing = {
            'Contents': [
                {
                    'Key':
                        prefix
                        + 'data/part.parquet',

                    'Size':
                        10,
                }
            ],

            'KeyCount':
                1,
        }

        self.listing_bytes = pack(
            self.listing
        )

        self.c3b[
            'fresh_s3_listing_sha256'
        ] = sha(
            self.listing_bytes
        )

        self.c3b_bytes = pack(
            self.c3b
        )

        with self.assertRaises(ValueError):
            self.build()

    def test_person_fingerprint_drift_rejected(self):
        self.people[0][2] = 999

        self.people_bytes = json.dumps(
            self.people,
            separators=(',', ':'),
            ensure_ascii=False,
        ).encode()

        with self.assertRaisesRegex(
            ValueError,
            'fingerprint',
        ):
            self.build()

    def test_c3a_pin_drift_rejected(self):
        self.c3b[
            'c3a_state_sha256'
        ] = '0' * 64

        self.c3b_bytes = pack(
            self.c3b
        )

        with self.assertRaises(ValueError):
            self.build()

    def test_c3b_cannot_be_pre_authorized(self):
        self.c3b[
            'write_authorized'
        ] = True

        self.c3b_bytes = pack(
            self.c3b
        )

        with self.assertRaises(ValueError):
            self.build()

    def test_stable_for_fixed_clock(self):
        self.assertEqual(
            self.build(),
            self.build(),
        )


if __name__ == '__main__':
    unittest.main()
PY_TEST

# ==========================================================
# 3. Formal Permit runner
#
# IMPORTANT:
# Installed now, but DO NOT invoke it in C3C1.
# It will be used immediately before Runtime Bundle creation.
# ==========================================================

cat > "$STAGE/scripts/task003/05g2c2c3c-issue-write-permit.sh" <<'RUNNER'
#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

REPORT=''

echo '#### TASK003 STEP05G2C2C3C WRITE PERMIT OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  [[ -z "$REPORT" ]] || {
    echo "WRITE_PERMIT_REPORT=$REPORT"
  }

  echo "PERMIT_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G2C2C3C WRITE PERMIT OUTPUT END ####'
  exit "$rc"
}

trap finish EXIT

[[ $# -eq 3 ]] || {
  echo "Usage: $0 PROCESSED_RUN_ID C3A_REPORT_DIR C3B_REPORT_DIR"
  exit 2
}

RUN_ID="$1"
C3A_REPORT="$2"
C3B_REPORT="$3"

[[ "$RUN_ID" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$ && \
   "$RUN_ID" != '.' && \
   "$RUN_ID" != '..' ]] || {
  echo 'ERROR: unsafe run ID'
  exit 2
}

BASE="$ROOT/runtime/reports/task003/step05"

SPEC="$BASE/writer-reservations/$RUN_ID/reservation-create.json"

C3A_STATE="$C3A_REPORT/run-state.json"
C3B_STATE="$C3B_REPORT/run-state.json"

for path in \
  "$SPEC" \
  "$C3A_STATE" \
  "$C3B_STATE" \
  "$C3B_REPORT/fresh-s3-listing.json" \
  "$C3B_REPORT/person-map-snapshot.json"
do
  [[ -s "$path" && ! -L "$path" ]] || {
    echo "ERROR: missing Permit prerequisite: $path"
    exit 2
  }
done

LOCK=$(
  python3 - "$SPEC" <<'PY'
import json
import sys
from pathlib import Path

spec = json.loads(
    Path(sys.argv[1]).read_bytes()
)

print(
    spec['metadata']['name']
)
PY
)

[[ "$LOCK" =~ ^visit-proc-lock-[0-9a-f]{32}$ ]] || {
  echo 'ERROR: unsafe Reservation name'
  exit 1
}

# Fresh LIVE Kubernetes read immediately before issuance.
LIVE=$(
  mktemp \
    /data/spark/temp_shell/visit-permit-live.XXXXXXXX.json
)

cleanup() {
  rm -f -- "$LIVE"
}

trap 'cleanup' RETURN

kubectl -n dw-spark \
  get configmap "$LOCK" \
  -o json \
  > "$LIVE"

STAMP=$(date -u +%Y%m%dt%H%M%Sz)

REPORT=$(
  mktemp -d \
    "$BASE/write-permit.${STAMP}.XXXXXXXX"
)

OUTPUT="$REPORT/write-permit.json"

PYTHONPATH="$ROOT/apps/task003:$ROOT/spark/apps/visit" \
python3 "$ROOT/apps/task003/issue_visit_processed_write_permit.py" \
  --root "$ROOT" \
  --run-id "$RUN_ID" \
  --c3a-report "$C3A_REPORT" \
  --c3b-report "$C3B_REPORT" \
  --live-reservation "$LIVE" \
  --ttl-seconds 180 \
  --output "$OUTPUT"

cleanup

echo 'STEP05G2C2C3C_WRITE_PERMIT=PASS'
echo 'RUNTIME_CONFIGMAP_CREATED=NO'
echo 'SPARK_APPLICATION_SUBMITTED=NO'
echo 'S3_WRITE=NO'
echo 'DATABASE_WRITE=NO'
RUNNER

# ==========================================================
# 4. Syntax + tests
# ==========================================================

echo '=== 1. Syntax and Permit compatibility tests ==='

python3 - "$STAGE" <<'PY_AST'
import ast
import sys
from pathlib import Path

base = Path(sys.argv[1])

for rel in (
    'apps/task003/issue_visit_processed_write_permit.py',
    'tests/task003/test_visit_processed_write_permit.py',
):
    ast.parse(
        (base / rel).read_text(),
        filename=rel,
    )

print('WRITE_PERMIT_PYTHON_AST=PASS')
PY_AST

bash -n \
  "$STAGE/scripts/task003/05g2c2c3c-issue-write-permit.sh"

cp \
  "$ROOT/apps/task003/inspect_visit_processed_prefix.py" \
  "$STAGE/apps/task003/inspect_visit_processed_prefix.py"

cp \
  "$ROOT/spark/apps/visit/processed_visit_writer_core.py" \
  "$STAGE/spark/apps/visit/processed_visit_writer_core.py"

PYTHONPATH="$STAGE/apps/task003:$STAGE/spark/apps/visit" \
python3 -m unittest discover \
  -s "$STAGE/tests/task003" \
  -p 'test_visit_processed_write_permit.py' \
  -v

echo 'WRITE_PERMIT_TESTS=PASS'

# ==========================================================
# 5. Static safety checks
# ==========================================================

echo '=== 2. Permit issuance boundary checks ==='

python3 - \
  "$STAGE/apps/task003/issue_visit_processed_write_permit.py" \
  "$STAGE/scripts/task003/05g2c2c3c-issue-write-permit.sh" \
  <<'PY_BOUNDARY'
import sys
from pathlib import Path

py_source = Path(
    sys.argv[1]
).read_text()

runner = Path(
    sys.argv[2]
).read_text()

for required in (
    'MAX_TTL_SECONDS = 300',
    "'AUTHORIZED_FOR_SINGLE_WRITE'",
    "'reservation_uid'",
    "'reservation_resource_version'",
    "'person_map_fingerprint'",
    "'fresh_listing_sha256'",
):
    assert required in py_source, required

for required in (
    'kubectl -n dw-spark',
    'get configmap "$LOCK"',
    '--ttl-seconds 180',
    'SPARK_APPLICATION_SUBMITTED=NO',
    'S3_WRITE=NO',
):
    assert required in runner, required

combined = py_source + runner

for forbidden in (
    'kubectl delete configmap',
    'kubectl create',
    'kubectl apply',
    'aws s3 cp',
    'aws s3 rm',
    'put-object',
    'SparkApplication',
):
    assert forbidden not in combined, forbidden

print('WRITE_PERMIT_BOUNDARY=PASS')
print('MAX_PERMIT_TTL_300_SECONDS=PASS')
print('K8S_MUTATION_ABSENT=PASS')
print('S3_WRITE_ABSENT=PASS')
PY_BOUNDARY

# ==========================================================
# 6. Canonical install
# ==========================================================

echo '=== 3. Canonical source conflict check ==='

FILES=(
  apps/task003/issue_visit_processed_write_permit.py
  tests/task003/test_visit_processed_write_permit.py
  scripts/task003/05g2c2c3c-issue-write-permit.sh
)

GEN=scripts/task003/05g2c2c3c1-prepare-write-permit-source.sh

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

echo '=== 4. Install canonical source ==='

for rel in "${FILES[@]}"; do
  mkdir -p "$(dirname "$ROOT/$rel")"

  mode=644
  [[ "$rel" != *.sh ]] || mode=755

  if [[ -f "$ROOT/$rel" ]] &&
     cmp -s "$STAGE/$rel" "$ROOT/$rel"
  then

    echo "CANONICAL_SOURCE_REUSED=$rel"

  else
    install \
      -m "$mode" \
      "$STAGE/$rel" \
      "$ROOT/$rel"

    echo "CANONICAL_SOURCE_READY=$rel"
  fi
done

if [[ -f "$ROOT/$GEN" ]]; then

  echo "CANONICAL_GENERATOR_REUSED=$GEN"

else
  install \
    -m 755 \
    "$SOURCE" \
    "$ROOT/$GEN"

  echo "CANONICAL_GENERATOR_READY=$GEN"
fi

echo 'STEP05G2C2C3C1_SOURCE_AND_TESTS=PASS'

# Deliberately NOT issued in this step.
echo 'WRITE_PERMIT_ISSUED=NO'
echo 'WRITE_AUTHORIZED=NO'

echo 'K8S_RESOURCE_CREATED=NO'
echo 'RUNTIME_CONFIGMAP_CREATED=NO'
echo 'SPARK_APPLICATION_SUBMITTED=NO'
echo 'S3_WRITE=NO'
echo 'DATABASE_WRITE=NO'
echo 'GIT_COMMIT=NO'
