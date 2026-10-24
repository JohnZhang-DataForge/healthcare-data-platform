"""STEP05G1 plan and conflict policy tests; no cloud dependencies."""

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'apps/task003'))

from plan_visit_processed import build_plan, save_once

POLICY = json.loads(
    (
        ROOT
        / 'spark/contracts/processed/visit-candidate-publication-v1.json'
    ).read_text()
)


def fixture():
    ctx = dict(
        status='PASS',
        source='synthea',
        source_version='v3.3.0',
        batch_id='test-batch',
        ingest_date='2026-10-08',
        raw_publish_run_id='test-raw',
        expected_rows=3,
        raw_manifest_sha256='a' * 64,
        dq_sha256='9' * 64,
        mapping_contract_sha256='b' * 64,
    )

    pinned = dict(
        raw_context=ctx,
        expected_persons=2,
        expected_class_counts={
            'ambulatory': 2,
            'emergency': 1,
        },
        candidate_contract_sha256='c' * 64,
        mapper_sha256='d' * 64,
    )

    result = dict(
        status='PASS',
        step='STEP-05F2',
        candidate_schema='PASS',
        person_mapping='PASS',
        visit_concepts='PASS',
        dates='PASS',
        nullability='PASS',
        deferred_fields='PASS',
        ids_allocated=0,
        s3_write=False,
        postgresql_write=False,
        candidate_published=False,
        raw_publish_run_id='test-raw',
        raw_manifest_sha256='a' * 64,
        dq_sha256='9' * 64,
        expected_rows=3,
        mapping_contract_sha256='b' * 64,
        candidate_contract_sha256='c' * 64,
        mapper_sha256='d' * 64,
        candidate_rows=3,
        unique_source_keys=3,
        referenced_persons=2,
        class_counts={
            'ambulatory': 2,
            'emergency': 1,
        },
    )

    return dict(
        task='TASK-003',
        step='STEP-05F2',
        status='PASS',
        validation_scope='in_memory_visit_candidate',
        ids_allocated=0,
        s3_write=False,
        postgresql_write=False,
        candidate_published=False,
        input=pinned,
        result=result,
    )


class TestG1(unittest.TestCase):

    def plan(self, state=None, run_id='visit-proc-test'):
        return build_plan(
            state or fixture(),
            POLICY,
            run_id,
            'e' * 64,
        )

    def test_valid_and_immutable_layout(self):
        p = self.plan()
        self.assertEqual(p['expected_rows'], 3)
        self.assertTrue(
            p['base_uri'].startswith('s3://health-processed/')
        )
        self.assertEqual(
            p['manifest_uri'],
            p['base_uri'] + '/manifest.json',
        )
        self.assertFalse(p['published'])
        self.assertEqual(p['visit_ids_allocated'], 0)

    def test_same_plan_reuses_without_rewriting(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'plan.json'
            p = self.plan()

            self.assertEqual(save_once(path, p), 'CREATED')
            before = path.read_bytes()
            self.assertEqual(save_once(path, p), 'REUSED')
            self.assertEqual(path.read_bytes(), before)

    def test_same_run_conflict_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'plan.json'
            self.assertEqual(
                save_once(path, self.plan()),
                'CREATED',
            )

            modified = self.plan()
            modified['expected_rows'] += 1

            with self.assertRaisesRegex(ValueError, 'CONFLICT'):
                save_once(path, modified)

    def test_different_run_isolated(self):
        self.assertNotEqual(
            self.plan(run_id='visit-a')['base_uri'],
            self.plan(run_id='visit-b')['base_uri'],
        )

    def test_bad_f2_rejected(self):
        s = fixture()
        s['status'] = 'FAILED'

        with self.assertRaises(ValueError):
            self.plan(s)

    def test_count_drift_rejected(self):
        s = fixture()
        s['result']['candidate_rows'] = 4

        with self.assertRaises(ValueError):
            self.plan(s)

    def test_source_mapping_conflict_rejected(self):
        s = fixture()
        s['result']['mapper_sha256'] = 'f' * 64

        with self.assertRaises(ValueError):
            self.plan(s)

    def test_path_injection_rejected(self):
        for value in ('../escape', 'visit/a', '', '..'):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.plan(run_id=value)

    def test_premature_publication_rejected(self):
        s = fixture()
        s['candidate_published'] = True

        with self.assertRaises(ValueError):
            self.plan(s)

    def test_policy_conflict_rejected(self):
        policy = copy.deepcopy(POLICY)
        policy['same_run_conflict'] = 'OVERWRITE'

        with self.assertRaises(ValueError):
            build_plan(
                fixture(),
                policy,
                'visit-test',
                'e' * 64,
            )


if __name__ == '__main__':
    unittest.main()
