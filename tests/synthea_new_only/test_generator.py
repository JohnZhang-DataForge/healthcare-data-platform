"""NEW_ONLY immutable request, local contract and collision safety."""
import csv
import datetime as dt
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps/synthea/new_only"))
from generate_new_only import (STATES, GateError, new_params, freeze_params,
                                validate_csv, guarded_registry_write, command)

CONTRACT = ROOT / "contracts/synthea/v3.3.0/csv-contract.json"


class GeneratorTests(unittest.TestCase):
    def test_random_params_valid_and_utc_frozen(self):
        p = new_params("probe-20261013-12345678", dt.datetime(2026, 10, 13, 19, 30,
                                                              tzinfo=dt.timezone(dt.timedelta(hours=-4))))
        self.assertEqual(p["reference_date"], "20261013")
        self.assertEqual(p["batch_id"], "synthea-new-only-probe-20261013-12345678")
        self.assertIn(p["state"], STATES)
        self.assertEqual(len(STATES), 50)
        self.assertTrue(1 <= p["target_population"] <= 100)
        self.assertGreater(p["seed"], 0)
        self.assertGreater(p["clinician_seed"], 0)

    def test_same_request_params_are_immutable(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Path(tmp)
            a = freeze_params(r, "req-12345678")
            b = freeze_params(r, "req-12345678",
                              dt.datetime(2027, 1, 1, tzinfo=dt.timezone.utc))
            self.assertEqual(a, b)
            self.assertEqual(b["reference_date"], a["reference_date"])
            self.assertEqual(b["seed"], a["seed"])
            with self.assertRaises(GateError):
                freeze_params(r, "../../other")

    def test_synthea_argv_uses_fixed_reference_and_no_overflow(self):
        p = new_params("req-12345678")
        cmd = command(p, Path("/opt/synthea/synthea.jar"), Path("/synthea-state/out"))
        self.assertEqual(cmd[cmd.index("-o") + 1], "false")
        self.assertEqual(cmd[cmd.index("-r") + 1], p["reference_date"])
        self.assertEqual(cmd[cmd.index("-e") + 1], p["reference_date"])
        self.assertEqual(cmd[cmd.index("-p") + 1], str(p["target_population"]))

    def test_persisted_registry_rejects_cross_request_collision(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            guarded_registry_write(p, "req-a", ["abc", "def"])
            guarded_registry_write(p, "req-a", ["abc", "def"])
            with self.assertRaises(GateError):
                guarded_registry_write(p, "req-b", ["def", "ghi"])
            with self.assertRaises(GateError):
                guarded_registry_write(p, "req-a", ["abc"])
            guarded_registry_write(p, "req-c", ["ghi"])

    def test_real_v1_headers_optional_zero_with_new_only_local_gate(self):
        import json
        spec = json.loads(CONTRACT.read_text())
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            for item in spec["files"]:
                with (p / item["filename"]).open("w", newline="") as f:
                    w = csv.writer(f)
                    w.writerow(item["header"])
                    if item["filename"] == "patients.csv":
                        values = [""] * len(item["header"])
                        values[item["header"].index("Id")] = "unique-person-id"
                        w.writerow(values)
                    if item["filename"] == "encounters.csv":
                        values = [""] * len(item["header"])
                        values[item["header"].index("Id")] = "unique-encounter"
                        values[item["header"].index("PATIENT")] = "unique-person-id"
                        w.writerow(values)
            output = validate_csv(p, CONTRACT)
            self.assertEqual(output["actual_persons"], 1)
            self.assertEqual(output["actual_encounters"], 1)
            self.assertEqual(len(output["files"]), 18)
            self.assertFalse(output["publication_eligible"])
            # Any source-ID mismatch must remain fail-closed.
            with (p / "encounters.csv").open("w", newline="") as f:
                w = csv.writer(f)
                h = next(x["header"] for x in spec["files"] if x["filename"] == "encounters.csv")
                w.writerow(h)
                values = [""] * len(h)
                values[h.index("PATIENT")] = "not-in-patients"
                w.writerow(values)
            with self.assertRaises(GateError):
                validate_csv(p, CONTRACT)


if __name__ == "__main__":
    unittest.main()
