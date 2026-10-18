"""Contract checks only: no UPDATE_ONLY/MIX_DATA runtime implementation."""
import importlib.util
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "contracts/synthea/producer-batch-identity-v1.json"
NEW_ONLY = ROOT / "apps/synthea/new_only/generate_new_only.py"
WRITER_PLAN = ROOT / "airflow/dags/task004_cdm_materialization_plan.py"


class ProducerBatchNamingPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads(POLICY.read_text())

    def test_three_exact_and_distinct_independent_producer_prefixes(self):
        modes = {item["mode"]: item for item in self.policy["producer_modes"]}
        self.assertEqual(set(modes), {"NEW_ONLY", "UPDATE_ONLY", "MIX_DATA"})
        self.assertEqual({mode: entry["batch_prefix"] for mode, entry in modes.items()}, {
            "NEW_ONLY": "synthea-new-only-",
            "UPDATE_ONLY": "synthea-update-only-",
            "MIX_DATA": "synthea-mix-data-",
        })
        self.assertEqual(len({m["batch_prefix"] for m in modes.values()}), 3)
        self.assertTrue(all(m["namespace"] == "dw-synthea" for m in modes.values()))

    def test_future_modes_remain_design_only_no_jobs_or_business_code(self):
        modes = {item["mode"]: item for item in self.policy["producer_modes"]}
        for mode in ("UPDATE_ONLY", "MIX_DATA"):
            self.assertEqual(modes[mode]["state"], "DESIGN_ONLY_ON_HOLD")
            self.assertFalse((ROOT / modes[mode]["directory"]).exists(),
                             "Future generator business logic must not be created by naming PR")
        self.assertTrue((ROOT / modes["NEW_ONLY"]["directory"]).is_dir())

    def test_request_id_matches_live_new_only_generation(self):
        spec = importlib.util.spec_from_file_location("synthea_new_only_gener", NEW_ONLY)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        request_id = "gh-38484300008"
        pattern = self.policy["request_id_regex"]
        self.assertIsNotNone(re.fullmatch(pattern, request_id))
        self.assertEqual(mod.new_params(request_id)["batch_id"],
                         self.policy["producer_modes"][0]["batch_prefix"] + request_id)
        self.assertIsNone(re.fullmatch(pattern, "../../invalid"))
        self.assertIsNone(re.fullmatch(pattern, "x"))

    def test_legacy_writer_stays_intentionally_closed_to_new_modes(self):
        legacy = self.policy["legacy"]
        self.assertEqual(legacy["mode"], "LEGACY_AIRFLOW")
        self.assertEqual(legacy["status"], "HISTORICAL_COMPATIBILITY_ONLY")
        plan = WRITER_PLAN.read_text()
        self.assertIn('^task004-airflow-[A-Za-z0-9._-]+$', plan)
        for entry in self.policy["producer_modes"]:
            valid = entry["batch_prefix"] + "gh-38484300008"
            self.assertIsNone(re.fullmatch(legacy["consumer_regex"], valid))
        self.assertIsNotNone(re.fullmatch(legacy["consumer_regex"],
                                         "task004-airflow-historical"))
        self.assertEqual(self.policy["gate"], "EXISTING_TARGET_DRIFT_MUST_REMAIN_ENABLED")
        self.assertEqual(self.policy["authorization"], "BATCH_PREFIX_IS_NOT_AUTHORIZATION")
        self.assertEqual(self.policy["rollout"],
                         "EXPLICIT_VERSIONED_CONSUMER_AND_WRITER_COMPATIBILITY_REQUIRED")


if __name__ == "__main__":
    unittest.main()
