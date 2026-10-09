import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps/task003"))

from build_visit_writer_reservation import build_resource
from prepare_visit_processed_write_intent import POLICY


def pack(value):
    return (json.dumps(value, sort_keys=True) + "\n").encode()


class ReservationTests(unittest.TestCase):

    def setUp(self):
        base = (
            "s3://health-processed/contract_version=v1/"
            "entity=visit_occurrence/source=synthea/"
            "source_version=v3.3.0/ingest_date=2026-10-08/"
            "batch_id=batch-test/raw_publish_run_id=raw-test/"
            "run_id=run-test"
        )

        self.plan = {
            "task": "TASK-003",
            "step": "STEP-05G1",
            "status": "PLANNED",
            "run_id": "run-test",
            "base_uri": base,
            "data_uri": base + "/data/",
            "dq_uri": base + "/dq/result.json",
            "manifest_uri": base + "/manifest.json",
            "publication_policy": {
                "output_bucket": "health-processed",
                "publication_gate": "APPROVED_manifest_last",
                "same_run_conflict": "STOP_WITHOUT_OVERWRITE",
                "same_run_replay":
                    "REUSE_ONLY_IF_VERIFIED_IDENTICAL",
                "objects": [
                    "data/",
                    "dq/result.json",
                    "manifest.json",
                ],
            },
            "persisted": False,
            "published": False,
            "s3_write": False,
            "postgresql_write": False,
            "visit_ids_allocated": 0,
            "expected_rows": 3,
            "expected_persons": 2,
            "class_counts": {
                "emergency": 1,
                "ambulatory": 2,
            },
        }

        self.policy_bytes = pack(POLICY)
        self.plan_bytes = pack(self.plan)

        self.intent = {
            "task": "TASK-003",
            "step": "STEP-05G2C1",
            "status": "PREFLIGHT_SNAPSHOT_ONLY",
            "run_id": "run-test",
            "base_uri": base,
            "data_uri": base + "/data/",
            "expected_rows": 3,
            "expected_persons": 2,
            "expected_class_counts": self.plan["class_counts"],
            "plan_sha256":
                hashlib.sha256(self.plan_bytes).hexdigest(),
            "writer_safety_policy": POLICY,
            "writer_safety_policy_sha256":
                hashlib.sha256(self.policy_bytes).hexdigest(),
            "writer_reservation_acquired": False,
            "fresh_s3_relist_passed": False,
            "write_authorized": False,
            "spark_submitted": False,
            "s3_write": False,
            "postgresql_write": False,
            "candidate_published": False,
            "source_sha256": {
                "mapper": "a" * 64
            },
        }

    def build(self):
        return build_resource(
            pack(self.intent),
            self.plan_bytes,
            self.policy_bytes,
        )

    def test_deterministic_request_not_acquired(self):
        first = self.build()
        second = self.build()

        self.assertEqual(first, second)
        self.assertEqual(first["kind"], "ConfigMap")
        self.assertTrue(first["immutable"])
        self.assertEqual(
            first["metadata"]["namespace"],
            "dw-spark",
        )
        self.assertLessEqual(
            len(first["metadata"]["name"]), 63
        )

        record = json.loads(
            first["data"]["reservation.json"]
        )
        self.assertFalse(record["write_authorized"])
        self.assertEqual(
            record["mode"], "EXCLUSIVE_CREATE_ONLY"
        )
        self.assertEqual(
            record["release_policy"], "NO_AUTOMATIC_DELETE"
        )

    def test_plan_drift_rejected(self):
        self.plan["expected_rows"] += 1
        self.plan_bytes = pack(self.plan)

        with self.assertRaises(ValueError):
            self.build()

    def test_intent_cannot_claim_lock(self):
        self.intent["writer_reservation_acquired"] = True

        with self.assertRaises(ValueError):
            self.build()

    def test_intent_cannot_claim_write(self):
        self.intent["write_authorized"] = True

        with self.assertRaises(ValueError):
            self.build()

    def test_source_hash_required(self):
        self.intent["source_sha256"] = {}

        with self.assertRaises(ValueError):
            self.build()

    def test_policy_weakening_rejected(self):
        weaker = copy.deepcopy(POLICY)
        weaker["exclusive_writer_reservation_required"] = False
        self.intent["writer_safety_policy"] = weaker

        with self.assertRaises(ValueError):
            self.build()

    def test_run_identity_drift_rejected(self):
        self.intent["run_id"] = "other-run"

        with self.assertRaises(ValueError):
            self.build()

    def test_wrong_s3_prefix_rejected(self):
        self.intent["base_uri"] = (
            self.intent["base_uri"].replace(
                "health-processed", "health-raw"
            )
        )

        with self.assertRaises(ValueError):
            self.build()

    def test_distinct_run_has_distinct_lock(self):
        first = self.build()["metadata"]["name"]

        self.plan["run_id"] = "run-test-2"
        self.plan["base_uri"] = (
            self.plan["base_uri"].replace(
                "run-test", "run-test-2"
            )
        )

        self.plan["data_uri"] = (
            self.plan["base_uri"] + "/data/"
        )
        self.plan["dq_uri"] = (
            self.plan["base_uri"] + "/dq/result.json"
        )
        self.plan["manifest_uri"] = (
            self.plan["base_uri"] + "/manifest.json"
        )

        self.plan_bytes = pack(self.plan)

        self.intent["run_id"] = "run-test-2"
        self.intent["base_uri"] = self.plan["base_uri"]
        self.intent["data_uri"] = self.plan["data_uri"]
        self.intent["plan_sha256"] = (
            hashlib.sha256(self.plan_bytes).hexdigest()
        )

        self.assertNotEqual(
            first,
            self.build()["metadata"]["name"],
        )


if __name__ == "__main__":
    unittest.main()
