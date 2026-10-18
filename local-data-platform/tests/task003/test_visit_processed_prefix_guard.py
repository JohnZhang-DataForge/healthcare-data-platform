import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[2] / 'apps/task003')
)

from inspect_visit_processed_prefix import (
    classify,
    PrefixGuardError,
)


class PrefixTests(unittest.TestCase):

    def setUp(self):
        self.base = (
            's3://health-processed/contract_version=v1/'
            'entity=visit_occurrence/source=synthea/'
            'source_version=v3.3.0/'
            'ingest_date=2026-10-08/batch_id=test-batch/'
            'raw_publish_run_id=raw-test/run_id=run-test'
        )

        self.plan = dict(
            task='TASK-003',
            step='STEP-05G1',
            status='PLANNED',
            persisted=False,
            published=False,
            s3_write=False,
            postgresql_write=False,
            visit_ids_allocated=0,
            run_id='run-test',
            base_uri=self.base,
            data_uri=self.base + '/data/',
            dq_uri=self.base + '/dq/result.json',
            manifest_uri=self.base + '/manifest.json',
            publication_policy=dict(
                output_bucket='health-processed',
                publication_gate='APPROVED_manifest_last',
                same_run_conflict='STOP_WITHOUT_OVERWRITE',
                same_run_replay='REUSE_ONLY_IF_VERIFIED_IDENTICAL',
                objects=[
                    'data/',
                    'dq/result.json',
                    'manifest.json'
                ]
            )
        )

        self.prefix = (
            self.base.split('health-processed/', 1)[1] + '/'
        )

    def listing(self, *suffixes):
        return {
            'Contents': [
                {
                    'Key': self.prefix + suffix,
                    'Size': 45
                }
                for suffix in suffixes
            ],
            'KeyCount': len(suffixes),
            'IsTruncated': False
        }

    def test_seaweedfs_empty_without_keycount(self):
        self.assertEqual(
            classify(
                self.plan,
                {'RequestCharged': None}
            )['classification'],
            'EMPTY'
        )

    def test_empty_aws_form(self):
        self.assertEqual(
            classify(
                self.plan,
                self.listing()
            )['new_write_guard'],
            'PASS'
        )

    def test_data_only_blocks_new_write(self):
        result = classify(
            self.plan,
            self.listing('data/part-001.parquet')
        )

        self.assertEqual(
            result['classification'],
            'DATA_PRESENT_UNVERIFIED'
        )
        self.assertEqual(
            result['new_write_guard'],
            'STOP'
        )

    def test_data_and_dq_still_unverified(self):
        result = classify(
            self.plan,
            self.listing(
                'data/part-001.parquet',
                'dq/result.json'
            )
        )

        self.assertEqual(
            result['classification'],
            'DATA_AND_DQ_UNVERIFIED'
        )
        self.assertFalse(result['resume_authorized'])

    def test_manifest_not_automatically_approved(self):
        result = classify(
            self.plan,
            self.listing(
                'data/_SUCCESS',
                'dq/result.json',
                'manifest.json'
            )
        )

        self.assertEqual(
            result['classification'],
            'MANIFEST_PRESENT_UNVERIFIED'
        )
        self.assertFalse(result['publication_verified'])

    def test_reject_dq_alone(self):
        with self.assertRaises(PrefixGuardError):
            classify(
                self.plan,
                self.listing('dq/result.json')
            )

    def test_reject_manifest_without_dq(self):
        with self.assertRaises(PrefixGuardError):
            classify(
                self.plan,
                self.listing(
                    'data/part-001.parquet',
                    'manifest.json'
                )
            )

    def test_reject_foreign_key(self):
        with self.assertRaises(PrefixGuardError):
            classify(
                self.plan,
                {
                    'Contents': [
                        {'Key': 'other/data', 'Size': 5}
                    ],
                    'KeyCount': 1
                }
            )

    def test_reject_unexpected_object(self):
        with self.assertRaises(PrefixGuardError):
            classify(
                self.plan,
                self.listing('unknown.json')
            )

    def test_reject_malformed_response(self):
        for response in (
            {},
            {'error': 'denied'},
            {'Contents': None},
            {'Contents': [], 'KeyCount': True},
        ):
            with self.subTest(response=response):
                with self.assertRaises(PrefixGuardError):
                    classify(self.plan, response)

    def test_reject_contradictory_count(self):
        data = self.listing('data/part-1.parquet')
        data['KeyCount'] = 0

        with self.assertRaises(PrefixGuardError):
            classify(self.plan, data)

    def test_reject_truncation(self):
        data = self.listing()
        data['IsTruncated'] = True

        with self.assertRaises(PrefixGuardError):
            classify(self.plan, data)

    def test_reject_duplicate_key(self):
        with self.assertRaises(PrefixGuardError):
            classify(
                self.plan,
                self.listing('data/p', 'data/p')
            )

    def test_reject_bad_size(self):
        data = self.listing('data/p')
        data['Contents'][0]['Size'] = '2'

        with self.assertRaises(PrefixGuardError):
            classify(self.plan, data)

    def test_reject_wrong_target(self):
        plan = copy.deepcopy(self.plan)

        plan['base_uri'] = plan['base_uri'].replace(
            'health-processed',
            'health-raw'
        )

        with self.assertRaises(PrefixGuardError):
            classify(plan, self.listing())

    def test_reject_published_plan(self):
        plan = copy.deepcopy(self.plan)
        plan['published'] = True

        with self.assertRaises(PrefixGuardError):
            classify(plan, self.listing())


if __name__ == '__main__':
    unittest.main()
