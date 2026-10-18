import ast
import hashlib
import json
import sys
import unittest

from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(
    0,
    str(ROOT / 'spark/apps/visit')
)

from processed_visit_writer_core import (
    validate_permit,
    person_snapshot_fingerprint,
    sha,
)


def encode(value):
    return (json.dumps(value, sort_keys=True) + '\n').encode()


class WriterCoreTests(unittest.TestCase):

    def setUp(self):
        self.plan = dict(
            status='PLANNED',
            run_id='visit-test',
            persisted=False,
            published=False,
            visit_ids_allocated=0,
            postgresql_write=False,
            base_uri=(
                's3://health-processed/'
                'contract_version=v1/'
                'entity=visit_occurrence/'
                'source=synthea/'
                'source_version=v3.3.0/'
                'ingest_date=2026-10-08/'
                'batch_id=test/'
                'raw_publish_run_id=raw-test/'
                'run_id=visit-test'
            ),
        )

        self.plan['data_uri'] = self.plan['base_uri'] + '/data/'
        self.plan_bytes = encode(self.plan)

        self.intent = dict(
            run_id='visit-test',
            plan_sha256=sha(self.plan_bytes),
            write_authorized=False,
        )
        self.intent_bytes = encode(self.intent)

        self.record = dict(
            write_intent_sha256=sha(self.intent_bytes),
            plan_sha256=sha(self.plan_bytes),
            run_id='visit-test',
            bucket='health-processed',
            prefix=(
                self.plan['base_uri']
                .split('health-processed/', 1)[1] + '/'
            ),
            write_authorized=False,
            mode='EXCLUSIVE_CREATE_ONLY',
        )

        self.request = dict(
            kind='ConfigMap',
            immutable=True,
            metadata={
                'name': 'visit-proc-lock-example',
                'namespace': 'dw-spark',
            },
            data={
                'reservation.json': json.dumps(self.record)
            },
        )
        self.request_bytes = encode(self.request)

        self.listing_bytes = encode({
            'RequestCharged': None
        })

        now = datetime(
            2026, 10, 9, 20, 0,
            tzinfo=timezone.utc,
        )
        self.now = now

        self.permit = dict(
            task='TASK-003',
            step='STEP-05G2C2C',
            status='AUTHORIZED_FOR_SINGLE_WRITE',
            write_authorized=True,
            reservation_created_by_k8s_create=True,
            reservation_verified=True,
            fresh_s3_relist_passed=True,
            fresh_prefix_classification='EMPTY',
            candidate_published=False,
            postgresql_write=False,
            run_id='visit-test',
            data_uri=self.plan['data_uri'],
            plan_sha256=sha(self.plan_bytes),
            intent_sha256=sha(self.intent_bytes),
            reservation_spec_sha256=sha(self.request_bytes),
            fresh_listing_sha256=sha(self.listing_bytes),
            reservation_name=self.request['metadata']['name'],
            reservation_uid='123e4567-e89b-12d3-a456-426614174000',
            reservation_resource_version='1234567',
            issued_at_utc=(
                now - timedelta(seconds=10)
            ).isoformat(),
            expires_at_utc=(
                now + timedelta(seconds=90)
            ).isoformat(),
        )

    def check(self):
        return validate_permit(
            self.permit,
            self.plan_bytes,
            self.intent_bytes,
            self.request_bytes,
            self.listing_bytes,
            self.now,
        )

    def test_valid_short_lived_permit(self):
        self.assertEqual(self.check(), self.plan)

    def test_absent_lock_denied(self):
        self.permit['reservation_verified'] = False
        with self.assertRaises(ValueError):
            self.check()

    def test_unapproved_listing_denied(self):
        self.permit['fresh_s3_relist_passed'] = False
        with self.assertRaises(ValueError):
            self.check()

    def test_listing_not_empty_denied(self):
        self.listing_bytes = encode({
            'Contents': [
                {'Key': 'foreign', 'Size': 2}
            ],
            'KeyCount': 1,
        })

        self.permit['fresh_listing_sha256'] = sha(
            self.listing_bytes
        )

        with self.assertRaises(ValueError):
            self.check()

    def test_expired_denied(self):
        self.permit['expires_at_utc'] = (
            self.now - timedelta(seconds=1)
        ).isoformat()

        with self.assertRaises(ValueError):
            self.check()

    def test_excessive_lifetime_denied(self):
        self.permit['expires_at_utc'] = (
            self.now + timedelta(seconds=400)
        ).isoformat()

        with self.assertRaises(ValueError):
            self.check()

    def test_plan_drift_denied(self):
        self.plan['run_id'] = 'different'
        self.plan_bytes = encode(self.plan)

        with self.assertRaises(ValueError):
            self.check()

    def test_intent_drift_denied(self):
        self.intent['run_id'] = 'different'
        self.intent_bytes = encode(self.intent)

        with self.assertRaises(ValueError):
            self.check()

    def test_reservation_drift_denied(self):
        self.request['metadata']['name'] = 'different'
        self.request_bytes = encode(self.request)

        with self.assertRaises(ValueError):
            self.check()

    def test_valid_person_fingerprint_is_order_independent(self):
        people = [
            ('synthea', 'a', 1),
            ('synthea', 'b', 2),
        ]

        self.assertEqual(
            person_snapshot_fingerprint(people),
            person_snapshot_fingerprint(
                list(reversed(people))
            ),
        )

    def test_duplicate_person_denied(self):
        with self.assertRaises(ValueError):
            person_snapshot_fingerprint([
                ('synthea', 'a', 1),
                ('synthea', 'a', 2),
            ])

    def test_no_automatic_spark_or_s3_actions_on_import(self):
        path = (
            ROOT /
            'spark/apps/visit/processed_visit_writer_core.py'
        )
        source = path.read_text()
        tree = ast.parse(source)

        self.assertFalse(
            any(
                isinstance(n, ast.Call)
                for n in tree.body
            )
        )
        self.assertNotIn(
            "mode('overwrite')",
            source,
        )


if __name__ == '__main__':
    unittest.main()
