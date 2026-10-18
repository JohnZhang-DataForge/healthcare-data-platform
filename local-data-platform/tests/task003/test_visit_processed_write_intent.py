"""Local Write Intent tests. No external services."""

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'apps/task003'))

from plan_visit_processed import build_plan, save_once
from prepare_visit_processed_write_intent import POLICY, verify_snapshot
from test_visit_processed_plan import fixture


def encoded(value):
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)
        + '\n'
    ).encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


class WriterIntentTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.pub_policy = json.loads((
            ROOT
            / 'spark/contracts/processed/visit-candidate-publication-v1.json'
        ).read_bytes())

    def setUp(self):
        self.f2 = encoded(fixture())

        self.plan = build_plan(
            json.loads(self.f2),
            self.pub_policy,
            'visit-test',
            sha(self.f2)
        )

        self.plan_bytes = encoded(self.plan)
        self.listing_bytes = encoded({'RequestCharged': None})

        self.inspection = {
            'bucket': 'health-processed',
            'prefix':
                self.plan['base_uri'].split('health-processed/', 1)[1] + '/',
            'object_count': 0,
            'data_object_count': 0,
            'dq_object_present': False,
            'manifest_object_present': False,
            'classification': 'EMPTY',
            'new_write_guard': 'PASS',
            'publication_verified': False,
            'resume_authorized': False,
            'concurrent_writer_protection': False,
        }

        self.g2b = {
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
            'plan_sha256': sha(self.plan_bytes),
            's3_listing_sha256': sha(self.listing_bytes),
            'inspection': self.inspection,
        }

    def verify(self):
        return verify_snapshot(
            self.f2,
            self.plan_bytes,
            encoded(self.g2b),
            self.listing_bytes,
            self.pub_policy,
            POLICY,
        )

    def test_snapshot_pass_but_not_authorized(self):
        intent = self.verify()
        self.assertEqual(intent['expected_rows'], 3)
        self.assertFalse(intent['write_authorized'])
        self.assertFalse(intent['writer_reservation_acquired'])

    def test_plan_replay_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'intent.json'

            self.assertEqual(
                save_once(target, self.verify()),
                'CREATED'
            )

            before = target.read_bytes()

            self.assertEqual(
                save_once(target, self.verify()),
                'REUSED'
            )
            self.assertEqual(target.read_bytes(), before)

    def test_refuse_changed_plan(self):
        self.plan['expected_rows'] += 1
        self.plan_bytes = encoded(self.plan)
        self.g2b['plan_sha256'] = sha(self.plan_bytes)

        with self.assertRaises(ValueError):
            self.verify()

    def test_refuse_bad_listing_hash(self):
        self.g2b['s3_listing_sha256'] = '0' * 64

        with self.assertRaises(ValueError):
            self.verify()

    def test_refuse_nonempty_listing(self):
        prefix = self.inspection['prefix']

        self.listing_bytes = encoded({
            'Contents': [
                {
                    'Key': prefix + 'data/part.parquet',
                    'Size': 55
                }
            ],
            'KeyCount': 1
        })

        self.g2b['s3_listing_sha256'] = sha(self.listing_bytes)

        with self.assertRaises(ValueError):
            self.verify()

    def test_refuse_claimed_lock(self):
        self.g2b['exclusive_writer_lock_acquired'] = True

        with self.assertRaises(ValueError):
            self.verify()

    def test_refuse_fabricated_pass(self):
        self.g2b['status'] = 'FAILED'

        with self.assertRaises(ValueError):
            self.verify()

    def test_refuse_policy_weakening(self):
        weaker_policy = copy.deepcopy(POLICY)
        weaker_policy['exclusive_writer_reservation_required'] = False

        with self.assertRaises(ValueError):
            verify_snapshot(
                self.f2,
                self.plan_bytes,
                encoded(self.g2b),
                self.listing_bytes,
                self.pub_policy,
                weaker_policy
            )


if __name__ == '__main__':
    unittest.main()
