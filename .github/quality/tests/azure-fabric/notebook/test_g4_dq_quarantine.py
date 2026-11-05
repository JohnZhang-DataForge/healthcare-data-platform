"""G4.c DQ native Quarantine only: offline negative write, replay and readback."""
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "azure-fabric/notebook-development"))
import fhir_ingest_notebook as nb
from test_g4_silver_delta import G4Offline, Frame
import test_g4_silver_delta as source_fixture_module


class G4DQOffline(unittest.TestCase):
    def setUp(self):
        with patch.object(source_fixture_module, "REQUEST", "atlanta-fhir-gh-41599999999"):
            self.fixture = G4Offline()
            self.fixture.setUp()
        self.spark = self.fixture.spark
        self.finding = SimpleNamespace(
            classification="QUARANTINED",
            reason="PATIENT_CANONICAL_V1_INCOMPATIBLE",
            detail="FHIR_DATE_REQUIRED", resource_type="Patient",
            resource_id="missing-dob",
            source_file=self.fixture.sources[0].source_file)
        self.params = {**self.fixture.params,
                       "mode": "SILVER_DQ_QUARANTINE_WRITE",
                       "derivation_sha": "a" * 64}

    def prepared(self, spark, *, context, manifest_bytes, source_objects,
                 patient_contract_bytes, encounter_contract_bytes):
        p = self.fixture.prepared(
            spark, context=context, manifest_bytes=manifest_bytes,
            source_objects=source_objects,
            patient_contract_bytes=patient_contract_bytes,
            encounter_contract_bytes=encounter_contract_bytes)
        return replace(p, patient_df=Frame(p.patient_df.rows[:-1]),
                       patient_count=99, findings=(self.finding,))

    def execute(self, **updates):
        g = nb.verify_fhir_g4_dq_negative.__globals__
        def persist(df, path):
            if path in self.spark.delta:
                raise FileExistsError("Delta errorifexists")
            self.spark.delta[path] = df
        with patch.dict(g, {
            "read_source_objects_native": lambda *_args, **kw: self.fixture.sources,
            "prepare_batch": self.prepared,
            "_g3_delta_exists": lambda spark, path: path in spark.delta,
            "_write_delta": persist,
            "validate_silver_readback": lambda *_args, **kw: None,
        }):
            return nb.verify_fhir_g4_dq_negative(
                self.spark, **{**self.params, **updates})

    def test_quarantine_first_writer_denies_all_silver_and_approval(self):
        r = self.execute()
        self.assertEqual(r.status, "DQ_QUARANTINED")
        self.assertEqual(r.metrics["patient"], 99)
        paths = nb._g4_paths(self.params["request"])
        self.assertEqual(set(self.spark.delta), {paths["quarantine"]})
        self.assertEqual(self.spark.delta[paths["quarantine"]].count(), 1)
        self.assertEqual(self.spark.delta[paths["quarantine"]].rows[0]["reason"],
                         "PATIENT_CANONICAL_V1_INCOMPATIBLE")

    def test_independent_quarantine_readback_and_same_request_replay_skip(self):
        self.assertEqual(self.execute().status, "DQ_QUARANTINED")
        paths = {p: id(df) for p, df in self.spark.delta.items()}
        self.assertEqual(self.execute(
            mode="SILVER_DQ_READBACK_ONLY", allow_write=False,
            retention_ok=False).status, "DQ_READBACK_VERIFIED")
        self.assertEqual(self.execute().status, "DQ_SKIP_VERIFIED")
        self.assertEqual(paths, {p: id(df) for p, df in self.spark.delta.items()})

    def test_altered_physical_quarantine_or_approval_never_skips(self):
        self.assertEqual(self.execute().status, "DQ_QUARANTINED")
        paths = nb._g4_paths(self.params["request"])
        self.spark.delta[paths["quarantine"]].rows[0]["reason"] = "WRONG"
        self.assertEqual(self.execute(
            mode="SILVER_DQ_READBACK_ONLY", allow_write=False,
            retention_ok=False).status, "VERIFY_READONLY")
        self.spark.delta[paths["approval"]] = Frame([{"status": "SILVER_APPROVED"}])
        self.assertEqual(self.execute().status, "VERIFY_READONLY")

    def test_exact_manifest_source_contract_and_boolean_safety(self):
        cases = (
            ("request", "atlanta-fhir-gh-41552666929"),
            ("mode", "SILVER_WRITE"),
            ("strategy", "HALT"),
            ("manifest_sha", "f" * 64),
            ("derivation_sha", "f" * 64),
            ("allow_write", False), ("retention_ok", False),
            ("source_override", "Files/other"),
            ("patient_contract_json", "{}"),
        )
        for k, v in cases:
            with self.subTest(k=k), self.assertRaises(Exception):
                self.execute(**{k: v})
            self.assertEqual(len(self.spark.delta), 0)

    def test_missing_quarantine_readonly_is_hold_not_approval(self):
        r = self.execute(mode="SILVER_DQ_READBACK_ONLY",
                         allow_write=False, retention_ok=False)
        self.assertEqual(r.status, "HOLD_DQ_NOT_PERSISTED")
        self.assertFalse(self.spark.delta)


if __name__ == "__main__":
    unittest.main()
