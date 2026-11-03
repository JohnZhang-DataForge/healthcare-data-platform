"""G4 Silver staged Delta orchestration tests; fake Delta IO, real Shared Engine contracts.

All remote storage is mocked. These tests are NOT Fabric cloud acceptance.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from healthcare_data_engine import SourceObject

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "azure-fabric/notebook-development"))
import fhir_ingest_notebook as nb

PATIENT = (ROOT / "local-data-platform/spark/contracts/canonical/patient-v1.json").read_text()
ENCOUNTER = (ROOT / "local-data-platform/spark/contracts/canonical/encounter-v1.json").read_text()
REQUEST = "atlanta-fhir-gh-41552666929"


class Row:
    def __init__(self, fields):
        self.fields = fields

    def asDict(self, recursive=False):
        return dict(self.fields)

    def __getattr__(self, key):
        return self.fields[key]


class Frame:
    def __init__(self, rows, columns=None):
        self.rows = [dict(r) for r in rows]
        self.columns = list(columns if columns is not None else
                            (self.rows[0].keys() if self.rows else []))

    def collect(self):
        return [Row(r) for r in self.rows]

    def count(self):
        return len(self.rows)

    def select(self, *columns):
        return Frame([{c: r[c] for c in columns} for r in self.rows], columns)

    def exceptAll(self, other):
        def hashable(r):
            return tuple(json.dumps(r[c], sort_keys=True, default=str) for c in self.columns)
        left = Counter(hashable(r) for r in self.rows)
        right = Counter(hashable(r) for r in other.rows)
        remain = left - right
        return Frame(
            [dict(zip(self.columns, values)) for values, n in remain.items()
             for _ in range(n)], self.columns)


class Spark:
    def __init__(self, manifest):
        self.manifest = manifest
        self.delta = {}
        self.mode = None

    @property
    def read(self):
        return self

    def format(self, value):
        self.mode = value
        return self

    def load(self, path):
        if self.mode == "binaryFile":
            assert path.endswith("/landing-manifest.json"), path
            return Frame([{"content": self.manifest}])
        if self.mode != "delta":
            raise AssertionError("unexpected Spark source format")
        return self.delta[path]

    def createDataFrame(self, values, schema):
        fields = [p.split()[0] for p in schema.split(", ")]
        return Frame([dict(zip(fields, r)) for r in values], fields)


def source_fixture(tag="original"):
    objects, manifest_entries = [], []
    for i in range(100):
        name = (
            "clinical/v1/atlanta-hospital-a/atlanta-hospital-a-fhir-r4/"
            + REQUEST + f"/FHIR_R4/fhir/patient-{i:03d}.json")
        content = json.dumps({"resourceType": "Patient", "id": f"synthetic-{i}",
                              "marker": tag}, sort_keys=True).encode()
        source = SourceObject.from_bytes(
            name, content, hospital_id="atlanta-hospital-a",
            feed_id="atlanta-hospital-a-fhir-r4", source_system="synthea-fhir")
        objects.append(source)
        manifest_entries.append({
            "blob_key": name, "sha256": source.sha256,
            "size_bytes": source.size_bytes, "source_event_id": None,
            "etag": f'"etag-{i}"', "version_id": None})
    manifest = {
        "schema_version": "healthcare-azure-blob-landing-manifest-v1",
        "hospital_id": "atlanta-hospital-a",
        "feed_id": "atlanta-hospital-a-fhir-r4",
        "request_id": REQUEST,
        "source_manifest_sha256": "a" * 64, "target_format": "FHIR_R4",
        "skipped_non_admissions": 0,
        "objects": manifest_entries}
    raw = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    return raw, hashlib.sha256(raw).hexdigest(), tuple(objects)


class G4Offline(unittest.TestCase):
    def setUp(self):
        self.raw, self.sha, self.sources = source_fixture()
        self.spark = Spark(self.raw)
        self.params = dict(
            request=REQUEST, manifest_sha=self.sha, mode="SILVER_WRITE",
            allow_write=True, retention_ok=True,
            strategy="DELTA_RAW_SNAPSHOT_V1", manifest_override="",
            source_override="", target_override="",
            patient_contract_json=PATIENT, encounter_contract_json=ENCOUNTER)
        self.calls = 0
        self.findings = ()

    def prepared(self, spark, *, context, manifest_bytes, source_objects,
                 patient_contract_bytes, encounter_contract_bytes):
        self.calls += 1
        self.assertEqual(len(source_objects), 100)
        self.assertEqual(hashlib.sha256(manifest_bytes).hexdigest(), self.sha)
        self.assertEqual(patient_contract_bytes, PATIENT.encode())
        self.assertEqual(encounter_contract_bytes, ENCOUNTER.encode())
        rows_p = [{"source_record_id": f"patient-{i:03d}",
                   "source_batch_id": context.source_batch_id,
                   "processing_run_id": context.processing_run_id,
                   "processed_at": str(context.processed_at)} for i in range(100)]
        rows_e = [{"source_encounter_id": f"encounter-{i:03d}",
                   "source_batch_id": context.source_batch_id,
                   "processing_run_id": context.processing_run_id,
                   "processed_at": str(context.processed_at)} for i in range(121)]
        return nb.PreparedBatch(
            patient_df=Frame(rows_p), encounter_df=Frame(rows_e),
            patient_count=100, encounter_count=121, findings=self.findings,
            source_batch_id=context.source_batch_id,
            processing_version=context.processing_version,
            publication_id="a" * 64, manifest_sha256=context.manifest_sha256,
            source_receipts=nb.verify_source_objects(manifest_bytes, source_objects, context))

    def execute(self, **kwargs):
        params = {**self.params, **kwargs}
        g = nb.verify_fhir_g4_silver.__globals__
        def write(df, path):
            if path in self.spark.delta:
                raise FileExistsError("errorifexists")
            self.spark.delta[path] = df
        with patch.dict(g, {
            "read_source_objects_native": lambda *_args, **_kw: self.sources,
            "prepare_batch": self.prepared,
            "validate_silver_readback": lambda *_args, **_kw: None,
            "_g3_delta_exists": lambda spark, path: path in spark.delta,
            "_write_delta": write,
        }):
            return nb.verify_fhir_g4_silver(self.spark, **params)

    def test_physical_paths_stable_and_path_traversal_rejected(self):
        paths = nb._g4_paths(REQUEST)
        self.assertEqual(paths["bronze"], nb._g3_receipt_path(REQUEST))
        self.assertTrue(paths["patient"].endswith("/canonical_patient"))
        self.assertTrue(paths["encounter"].endswith("/canonical_encounter"))
        self.assertTrue(paths["approval"].endswith("/silver_approval"))
        self.assertTrue(paths["quarantine"].endswith("/quarantine"))
        self.assertIn("/" + REQUEST + "/processing=", paths["patient"])
        for bad in ("../sibling", "atlanta-fhir-gh-123/evil", ""):
            with self.subTest(bad=bad), self.assertRaisesRegex(
                    RuntimeError, "HOLD_G3_UNAPPROVED_REQUEST_NAMESPACE"):
                nb._g4_paths(bad)

    def test_fail_closed_parameter_and_contract_checks_before_source_read(self):
        cases = (
            ("mode", "CANONICAL_READONLY"),
            ("strategy", "HALT"),
            ("manifest_override", "{}"),
            ("source_override", "Files/somewhere-else"),
            ("target_override", "Tables/other"),
            ("allow_write", False),
            ("allow_write", "true"),
            ("retention_ok", False),
            ("manifest_sha", "bad"),
            ("patient_contract_json", "{}"),
            ("encounter_contract_json", "{}"),
        )
        for key, value in cases:
            with self.subTest(key=key), self.assertRaises(Exception):
                self.execute(**{key: value})
            self.assertFalse(self.spark.delta)
            self.assertEqual(self.calls, 0)

    def test_first_write_separate_readback_and_same_request_replay(self):
        a = self.execute()
        self.assertEqual(a.status, "SILVER_APPROVED")
        self.assertEqual((a.metrics["patient"], a.metrics["encounter"],
                          a.metrics["quarantine_or_reject"]), (100, 121, 0))
        paths = nb._g4_paths(REQUEST)
        self.assertEqual(set(self.spark.delta), {
            paths[k] for k in ("bronze", "patient", "encounter", "approval")})
        self.assertEqual(self.spark.delta[paths["bronze"]].count(), 100)
        self.assertTrue(all(len(r["source_payload"]) == r["source_size_bytes"]
                            for r in self.spark.delta[paths["bronze"]].rows))
        self.assertEqual(self.spark.delta[paths["approval"]].rows[0]["status"],
                         "SILVER_APPROVED")
        sizes = {k: id(self.spark.delta[v]) for k, v in paths.items()
                 if v in self.spark.delta}
        b = self.execute(mode="SILVER_READBACK_ONLY",
                         allow_write=False, retention_ok=False)
        self.assertEqual(b.status, "SILVER_SKIP_VERIFIED")
        c = self.execute()
        self.assertEqual(c.status, "SILVER_SKIP_VERIFIED")
        self.assertEqual(sizes, {k: id(self.spark.delta[v]) for k, v in paths.items()
                                 if v in self.spark.delta})

    def test_same_request_manifest_drift_holds_without_new_path(self):
        self.assertEqual(self.execute().status, "SILVER_APPROVED")
        self.raw, self.sha, self.sources = source_fixture(tag="drift")
        self.spark.manifest = self.raw
        result = self.execute(manifest_sha=self.sha)
        self.assertEqual(result.status, "HOLD_REQUEST_DRIFT")
        self.assertEqual(len(self.spark.delta), 4)

    def test_readback_only_missing_target_holds_and_never_writes(self):
        result = self.execute(mode="SILVER_READBACK_ONLY",
                              allow_write=False, retention_ok=False)
        self.assertEqual(result.status, "HOLD_SILVER_NOT_FOUND")
        self.assertFalse(self.spark.delta)

    def test_partial_unknown_ack_approval_missing_stays_readonly(self):
        paths = nb._g4_paths(REQUEST)
        self.spark.delta[paths["bronze"]] = Frame([{"source_path": "corrupt"}])
        outcome = self.execute()
        self.assertEqual(outcome.status, "HOLD_REQUEST_DRIFT")
        self.assertEqual(set(self.spark.delta), {paths["bronze"]})

    def test_corrupt_saved_bytes_and_approval_rejected(self):
        self.assertEqual(self.execute().status, "SILVER_APPROVED")
        paths = nb._g4_paths(REQUEST)
        self.spark.delta[paths["bronze"]].rows[0]["source_payload"] = b"tampered"
        self.assertEqual(self.execute(mode="SILVER_READBACK_ONLY",
                                      allow_write=False, retention_ok=False).status,
                         "HOLD_REQUEST_DRIFT")

    def test_missing_approval_fence_never_resumes_partial_writes(self):
        self.assertEqual(self.execute().status, "SILVER_APPROVED")
        paths = nb._g4_paths(REQUEST)
        del self.spark.delta[paths["approval"]]
        self.assertEqual(self.execute().status, "VERIFY_READONLY")
        self.assertNotIn(paths["approval"], self.spark.delta)

    def test_dq_quarantine_written_but_approval_denied(self):
        from types import SimpleNamespace
        self.findings = (SimpleNamespace(classification="QUARANTINE",
                                         reason="FHIR_MISSING_DOB", detail="source missing",
                                         resource_type="Patient", resource_id="p1",
                                         source_file="example.json"),)
        outcome = self.execute()
        self.assertEqual(outcome.status, "HOLD_DQ")
        paths = nb._g4_paths(REQUEST)
        self.assertEqual(set(self.spark.delta), {paths["quarantine"]})
        self.assertEqual(self.spark.delta[paths["quarantine"]].count(), 1)
        self.assertNotIn(paths["approval"], self.spark.delta)

    def test_corrupt_approval_count_never_skips(self):
        self.assertEqual(self.execute().status, "SILVER_APPROVED")
        paths = nb._g4_paths(REQUEST)
        self.spark.delta[paths["approval"]].rows[0]["patient_count"] = 9
        self.assertEqual(self.execute(mode="SILVER_READBACK_ONLY",
                                      allow_write=False, retention_ok=False).status,
                         "VERIFY_READONLY")


if __name__ == "__main__":
    unittest.main()
