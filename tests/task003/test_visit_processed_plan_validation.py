"""STEP05G1 immutable evidence validation, including negative cases."""
import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'apps/task003'))

from plan_visit_processed import build_plan
from verify_visit_processed_plan import verify_plan_bytes
from test_visit_processed_plan import fixture


class TestPlanEvidence(unittest.TestCase):

    def setUp(self):
        self.f2 = fixture()
        self.raw_f2 = json.dumps(self.f2).encode()
        self.policy = json.loads((
            ROOT
            / 'spark/contracts/processed/visit-candidate-publication-v1.json'
        ).read_text())

        self.run_id = 'visit-proc-fixture'
        self.plan = build_plan(
            self.f2,
            self.policy,
            self.run_id,
            hashlib.sha256(self.raw_f2).hexdigest(),
        )
        self.plan_bytes = (
            json.dumps(
                self.plan,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            ) + '\n'
        ).encode()

    def verify(self, plan=None, f2=None, policy=None, run_id=None):
        return verify_plan_bytes(
            self.plan_bytes if plan is None else plan,
            self.raw_f2 if f2 is None else f2,
            self.policy if policy is None else policy,
            self.run_id if run_id is None else run_id,
        )

    def test_valid(self):
        self.assertEqual(self.verify(), self.plan)

    def test_tampered_plan_rejected(self):
        modified = copy.deepcopy(self.plan)
        modified['published'] = True
        raw = (
            json.dumps(modified, indent=2, sort_keys=True) + '\n'
        ).encode()

        with self.assertRaisesRegex(ValueError, 'CONFLICT'):
            self.verify(plan=raw)

    def test_f2_evidence_drift_rejected(self):
        changed_f2 = json.dumps(self.f2, indent=2).encode()

        with self.assertRaisesRegex(ValueError, 'CONFLICT'):
            self.verify(f2=changed_f2)

    def test_wrong_run_rejected(self):
        with self.assertRaisesRegex(ValueError, 'CONFLICT'):
            self.verify(run_id='other-run')

    def test_policy_drift_rejected(self):
        changed = copy.deepcopy(self.policy)
        changed['same_run_conflict'] = 'OVERWRITE'

        with self.assertRaises(ValueError):
            self.verify(policy=changed)


if __name__ == '__main__':
    unittest.main()
