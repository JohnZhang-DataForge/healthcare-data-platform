"""Unit tests for independent, read-only Landing batch discovery."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "landing_discovery"))
sys.path.insert(0, str(ROOT / "apps" / "task004"))
from scan_ready_batches import discover_ready_batches, DiscoveryError
from resolve_verified_landing_file import payload_fingerprint


def ready_manifest(batch_id="demo-001", ingest="2026-10-13"):
    files = [
        {"path": f"payload/csv/file{i:02d}.csv",
         "dataset": f"dataset_{i:02d}",
         "size_bytes": 30, "row_count": 1,
         "sha256": hashlib.sha256(str(i).encode()).hexdigest(),
         "header": ["Id"]}
        for i in range(18)
    ]
    return {
        "manifest_version": "1.0", "status": "INTAKE_VERIFIED",
        "source": "synthea", "source_version": "v3.3.0",
        "batch_id": batch_id, "ingest_date": ingest,
        "landing_uri": (f"s3://health-landing/source=synthea/"
                        f"source_version=v3.3.0/ingest_date={ingest}/batch_id={batch_id}/"),
        "expected_file_count": 18, "files": files,
        "payload_fingerprint": payload_fingerprint(files),
        "verification": {"verified_file_count": 18, "s3_readback": "PASS"},
    }


def key_for(batch, ingest="2026-10-13"):
    return (f"source=synthea/source_version=v3.3.0/"
            f"ingest_date={ingest}/batch_id={batch}/manifest.json")


class FakeBody:
    def __init__(self, data):
        self.data = data

    def read(self, n):
        return self.data[:n]


class FakeS3:
    def __init__(self, pages, documents):
        self.pages = pages
        self.documents = documents
        self.calls = []
        self.gets = []

    def get_paginator(self, name):
        assert name == "list_objects_v2"
        return self

    def paginate(self, **kwargs):
        self.calls.append(kwargs)
        for objects in self.pages:
            yield {"Contents": [{"Key": k} for k in objects]}

    def get_object(self, **kwargs):
        self.gets.append(kwargs)
        data = self.documents[kwargs["Key"]]
        return {"Body": FakeBody(data), "ContentLength": len(data)}


def encoded(d):
    return json.dumps(d, separators=(",", ":")).encode()


class DiscoveryTest(unittest.TestCase):
    def test_pagination_ready_only_and_sorted(self):
        a, b = key_for("b"), key_for("a", "2026-10-12")
        s3 = FakeS3(
            [[a, a.replace("manifest.json", "payload/csv/patients.csv")],
             ["source=synthea/source_version=v3.3.0/partial/file.csv", b]],
            {a: encoded(ready_manifest("b")),
             b: encoded(ready_manifest("a", "2026-10-12"))},
        )
        got = discover_ready_batches(s3)
        self.assertEqual(got["ready_count"], 2)
        self.assertEqual(got["objects_seen"], 4)
        self.assertEqual([x["batch_id"] for x in got["ready_batches"]], ["a", "b"])
        self.assertEqual(got["manifests_seen"], 2)
        self.assertEqual(len(s3.gets), 2)
        self.assertFalse(got["processing_authorized"])
        self.assertFalse(got["database_mutation"])

    def test_no_manifest_means_not_ready(self):
        s3 = FakeS3([["source=synthea/source_version=v3.3.0/partial/patients.csv"]], {})
        self.assertEqual(discover_ready_batches(s3)["ready_count"], 0)
        self.assertEqual(len(s3.gets), 0)

    def test_invalid_ready_manifest_is_blocked(self):
        key = key_for("x")
        for change in [
            lambda x: x.update(status="UPLOADING"),
            lambda x: x.update(batch_id="another"),
            lambda x: x["files"].pop(),
            lambda x: x["verification"].update(s3_readback="FAIL"),
            lambda x: x.update(payload_fingerprint="f" * 64),
        ]:
            with self.subTest(change=change):
                manifest = ready_manifest("x")
                change(manifest)
                with self.assertRaises(DiscoveryError):
                    discover_ready_batches(FakeS3([[key]], {key: encoded(manifest)}))

    def test_same_batch_id_different_dates_is_blocked(self):
        a, b = key_for("x"), key_for("x", "2026-10-14")
        docs = {a: encoded(ready_manifest("x")),
                b: encoded(ready_manifest("x", "2026-10-14"))}
        with self.assertRaisesRegex(DiscoveryError, "same source/batch_id"):
            discover_ready_batches(FakeS3([[a, b]], docs))

    def test_manifest_size_limit_and_malformed_json(self):
        key = key_for("x")
        for body in [b"not-json", b"x" * (1024 * 1024 + 1)]:
            with self.subTest(size=len(body)):
                with self.assertRaises(DiscoveryError):
                    discover_ready_batches(FakeS3([[key]], {key: body}))

    def test_scan_limit_fail_closed(self):
        a, b = key_for("a"), key_for("b")
        docs = {a: encoded(ready_manifest("a")), b: encoded(ready_manifest("b"))}
        with self.assertRaisesRegex(DiscoveryError, "limit exceeded"):
            discover_ready_batches(FakeS3([[a, b]], docs), max_manifests=1)

    def test_unsafe_prefix_rejected(self):
        with self.assertRaises(DiscoveryError):
            discover_ready_batches(FakeS3([[]], {}), prefix="../")


if __name__ == "__main__":
    unittest.main()
