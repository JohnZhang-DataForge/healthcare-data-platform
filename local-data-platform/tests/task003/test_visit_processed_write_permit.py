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
