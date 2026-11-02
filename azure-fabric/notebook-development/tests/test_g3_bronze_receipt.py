"""G3 Bronze request-scoped Delta receipt logic (offline mock, NOT Fabric proof)."""
from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import json
import unittest
from unittest.mock import patch

from healthcare_data_engine import BatchContext, SourceObject

from pathlib import Path
import sys
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import fhir_ingest_notebook as nb


REQUEST = "atlanta-fhir-gh-40299990001"


def fixture(request=REQUEST, content_tag="a"):
    specs = []
    sources = []
    for i in range(5):
        name = (
            "clinical/v1/atlanta-hospital-a/atlanta-hospital-a-fhir-r4/"
            + request + "/FHIR_R4/fhir/patient-" + str(i) + ".json")
        body = json.dumps({"resourceType": "Patient", "id": str(i), "tag": content_tag}).encode()
        obj = SourceObject.from_bytes(
            name, body, hospital_id="atlanta-hospital-a",
            feed_id="atlanta-hospital-a-fhir-r4", source_system="synthea-fhir")
        sources.append(obj)
        specs.append({
            "blob_key": name, "sha256": obj.sha256, "size_bytes": obj.size_bytes,
            "source_event_id": None, "etag": '"synthetic-etag"', "version_id": None,
        })
    payload = {
        "schema_version": "healthcare-azure-blob-landing-manifest-v1",
        "hospital_id": "atlanta-hospital-a",
        "feed_id": "atlanta-hospital-a-fhir-r4",
        "request_id": request,
        "source_manifest_sha256": "a" * 64,
        "target_format": "FHIR_R4", "skipped_non_admissions": 0,
        "objects": specs,
    }
    raw = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    return raw, hashlib.sha256(raw).hexdigest(), tuple(sources)


class Row:
    def __init__(self, content=None, fields=None):
        self.content = content
        self.fields = fields

    def asDict(self, recursive=False):
        return self.fields


class SparkStub:
    def __init__(self, manifest):
        self.manifest = manifest
        self.delta = {}
        self.format_name = None
        self.path = None

    @property
    def read(self):
        return self

    def format(self, name):
        self.format_name = name
        return self

    def load(self, path):
        self.path = path
        return self

    def select(self, *columns):
        return self

    def collect(self):
        if self.format_name == "binaryFile":
            return [Row(content=self.manifest)]
        if self.format_name == "delta":
            return [Row(fields=r) for r in self.delta[self.path]]
        raise AssertionError("unexpected Spark reader")

    def createDataFrame(self, values, schema):
        keys = [x.split()[0] for x in schema.split(", ")]
        return [dict(zip(keys, v)) for v in values]


class G3OfflineTests(unittest.TestCase):
    def setUp(self):
        self.raw, self.sha, self.objects = fixture()
        self.spark = SparkStub(self.raw)
        self.params = dict(
            request=REQUEST, manifest_sha=self.sha, mode="BRONZE_RECEIPT",
            allow_write=True, retention_ok=True,
            manifest_override="", source_override="", target_override="")

    def execute(self, **updates):
        parameters = dict(self.params, **updates)
        g = nb.verify_fhir_g3_bronze.__globals__
        with patch.dict(g, {
            "_g3_delta_exists": lambda spark, path: path in spark.delta,
            "read_source_objects_native": lambda spark, **kw: self.objects,
            "_write_delta": lambda df, path: self.spark.delta.setdefault(path, df),
        }):
            return nb.verify_fhir_g3_bronze(self.spark, **parameters)

    def test_pinned_path_is_request_scoped_and_traversal_rejected(self):
        self.assertEqual(nb._g3_receipt_path(REQUEST),
                         "Files/bronze/fhir_r4/atlanta-hospital-a/"
                         "atlanta-hospital-a-fhir-r4/" + REQUEST + "/bronze_source_receipt")
        for request in ("../other", "", "atlanta-fhir-gh-123/evil", "another-source"):
            with self.subTest(request=request):
                with self.assertRaisesRegex(RuntimeError, "UNAPPROVED_REQUEST"):
                    nb._g3_receipt_path(request)

    def test_no_read_without_correct_write_and_retention_guards(self):
        for key, value in (
                ("allow_write", False), ("retention_ok", False),
                ("allow_write", "true"), ("manifest_override", "{}"),
                ("source_override", "Files/arbitrary"),
                ("target_override", "Tables/other"),
                ("manifest_sha", "bad")):
            with self.subTest(key=key):
                other = dict(self.params, **{key: value})
                with self.assertRaisesRegex(RuntimeError, "HOLD_G3"):
                    nb.verify_fhir_g3_bronze(object(), **other)

    def test_real_manifest_five_source_sha_and_new_receipt(self):
        result = self.execute()
        self.assertEqual(result.status, "BRONZE_WRITTEN")
        self.assertEqual(result.metrics["source_objects"], 5)
        path = nb._g3_receipt_path(REQUEST)
        self.assertIn(path, self.spark.delta)
        self.assertEqual(len(self.spark.delta[path]), 5)
        self.assertEqual({r["manifest_sha256"] for r in self.spark.delta[path]}, {self.sha})
        self.assertEqual({r["processing_version"] for r in self.spark.delta[path]},
                         {"fhir-bronze-receipt-v1:engine-0.1.1"})

    def test_replay_skip_with_independent_delta_read_and_no_write(self):
        self.assertEqual(self.execute().status, "BRONZE_WRITTEN")
        before = self.spark.delta[nb._g3_receipt_path(REQUEST)]
        self.assertEqual(self.execute().status, "BRONZE_SKIP_VERIFIED")
        self.assertIs(before, self.spark.delta[nb._g3_receipt_path(REQUEST)])
        self.assertEqual(self.execute(mode="BRONZE_READBACK_ONLY",
                                      allow_write=False, retention_ok=False).status,
                         "BRONZE_SKIP_VERIFIED")

    def test_same_request_changed_manifest_must_hold_not_create_second_path(self):
        self.assertEqual(self.execute().status, "BRONZE_WRITTEN")
        self.raw, self.sha, self.objects = fixture(content_tag="changed")
        self.spark.manifest = self.raw
        result = self.execute(manifest_sha=self.sha)
        self.assertEqual(result.status, "HOLD_REQUEST_DRIFT")
        self.assertEqual(len(self.spark.delta), 1)

    def test_unknown_ack_write_may_have_committed_readback_only_recovers(self):
        original = nb._write_delta
        def unknown_ack(df, path):
            self.spark.delta[path] = df
            raise TimeoutError("simulated unknown ACK")
        g = nb.verify_fhir_g3_bronze.__globals__
        with patch.dict(g, {
            "_g3_delta_exists": lambda spark, path: path in spark.delta,
            "read_source_objects_native": lambda spark, **kw: self.objects,
            "_write_delta": unknown_ack,
        }):
            outcome = nb.verify_fhir_g3_bronze(self.spark, **self.params)
        self.assertEqual(outcome.status, "VERIFY_READONLY")
        self.assertEqual(self.execute(mode="BRONZE_READBACK_ONLY",
                                      allow_write=False, retention_ok=False).status,
                         "BRONZE_SKIP_VERIFIED")

    def test_corrupt_or_partial_stored_receipt_never_overwritten(self):
        self.spark.delta[nb._g3_receipt_path(REQUEST)] = [{"source_path": "bad"}]
        self.assertEqual(self.execute().status, "HOLD_REQUEST_DRIFT")
        self.assertEqual(len(self.spark.delta[nb._g3_receipt_path(REQUEST)]), 1)

    def test_readback_only_missing_target_never_writes(self):
        result = self.execute(mode="BRONZE_READBACK_ONLY",
                              allow_write=False, retention_ok=False)
        self.assertEqual(result.status, "HOLD_BRONZE_NOT_FOUND")
        self.assertFalse(self.spark.delta)

    def test_manifest_sha_conflict_before_delta_write(self):
        with self.assertRaisesRegex(ValueError, "MANIFEST_SHA256_CONFLICT_HOLD"):
            self.execute(manifest_sha="f" * 64)
        self.assertFalse(self.spark.delta)


if __name__ == "__main__":
    unittest.main()
