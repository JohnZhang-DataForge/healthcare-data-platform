"""Offline Marquez-exporter contracts: fake GET responses, no shared runtime."""
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from marquez_exporter import (
    ExportError, clean_event, digest, fetch_events, jsonl, normalize, stage, verified_snapshot
)

NS = "synthetic"
RUN_ID = "550e8400-e29b-41d4-a716-446655440000"
SOURCE = "a" * 40
URL = "https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/123456"


def dataset(name, facets=None):
    return {"namespace": NS, "name": name, "facets": facets or {}}


def event(kind="COMPLETE", moment="2026-10-25T11:02:00Z"):
    return {
        "eventType": kind, "eventTime": moment,
        "run": {"runId": RUN_ID, "facets": {"debug": "bearer PRIVATE"}},
        "job": {"namespace": NS, "name": "spark_transform", "facets": {"sql": {"query": "SELECT confidential"}}},
        "inputs": [dataset("landing/patient", {"schema": {"fields": [{"name": "BIRTHDATE", "type": "DATE"}]}})],
        "outputs": [dataset("processing/person", {
            "schema": {"fields": [{"name": "birth_date", "type": "DATE"}]},
            "columnLineage": {"fields": {"birth_date": {"inputFields": [
                {"namespace": NS, "name": "landing/patient", "field": "BIRTHDATE"}
            ]}}}
        })]
    }


def evidence(events, manifest):
    checksum = digest(manifest)
    return {
        "source_commit_sha": SOURCE,
        "source_manifest_sha256": checksum,
        "verification_run_url": URL,
        "independent_readback": {
            "passed": True, "source_commit_sha": SOURCE,
            "source_manifest_sha256": checksum,
            "verification_run_url": URL,
            "export_jsonl_sha256": digest(jsonl(normalize(events))),
            "checked_at": "2026-10-26T12:30:00Z",
            "patient_count": 100, "encounter_count": 4259,
            "dq_checks_passed": 3, "dq_checks_failed": 0,
            "quality_status": "PASS", "source_backend": "LOCAL_K8S",
            "verified_run_ids": [RUN_ID],
            "dataset_layers": {
                "synthetic::landing/patient": "LANDING",
                "synthetic::processing/person": "PROCESSING"
            },
            "hospitals": [{"hospital_ref": "hospital-atlanta",
                           "city": "Atlanta", "source_type": "CSV"}]
        }
    }


class StubHttp:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def __call__(self, req, timeout=15):
        self.calls.append((req.get_method(), req.full_url))
        return io.BytesIO(json.dumps(self.pages[len(self.calls)-1]).encode())


class ExporterTests(unittest.TestCase):
    def setUp(self):
        self.events = [event("START", "2026-10-25T11:00:00Z"), event()]

    def test_pagination_uses_only_get(self):
        fake = StubHttp([{"events": [self.events[0]], "totalCount": 2},
                         {"events": [self.events[1]], "totalCount": 2}])
        self.assertEqual(fetch_events("http://marquez:5000/api/v1", limit=1, opener=fake), self.events)
        self.assertEqual([m for m, _ in fake.calls], ["GET", "GET"])
        self.assertTrue(all("/events/lineage?" in url for _, url in fake.calls))
        self.assertTrue(all("sortDirection=asc" in url for _, url in fake.calls))
        self.assertFalse(any("?sort=" in url for _, url in fake.calls))

    def test_inconsistent_page_is_blocked(self):
        fake = StubHttp([{"events": [self.events[0]], "totalCount": 2},
                         {"events": [self.events[1]], "totalCount": 3}])
        with self.assertRaises(ExportError):
            fetch_events("http://marquez:5000/api/v1", limit=1, opener=fake)

    def test_empty_event_and_truncated_page_are_blocked(self):
        with self.assertRaises(ExportError):
            normalize([])
        with self.assertRaises(ExportError):
            fetch_events("http://marquez:5000/api/v1",
                         opener=StubHttp([{"events": [], "totalCount": 1}]))

    def test_duplicate_inputs_are_stable(self):
        self.assertEqual(jsonl(normalize(self.events)),
                         jsonl(normalize([self.events[1], self.events[0], self.events[0]])))
        self.assertEqual(len(normalize(self.events + self.events)), 2)

    def test_conflicting_same_identity_is_rejected(self):
        conflicting = event()
        conflicting["outputs"][0]["name"] = "processing/other"
        with self.assertRaises(ExportError):
            normalize([event(), conflicting])

    def test_sensitive_facets_are_stripped_without_changing_identities(self):
        result = clean_event(event())
        text = json.dumps(result)
        self.assertNotIn("SELECT confidential", text)
        self.assertNotIn("bearer PRIVATE", text)
        self.assertEqual(result["run"]["runId"], RUN_ID)
        relation = result["outputs"][0]["facets"]["columnLineage"]["fields"]["birth_date"]
        self.assertEqual(relation["inputFields"][0]["field"], "BIRTHDATE")

    def test_private_identifiers_block_not_rewrite(self):
        for name in ("s3://private/patient", "http://10.0.0.3/path",
                     "jdbc:postgresql://db", "localhost:5000",
                     "http://marquez:5000/internal", "table?token=hidden"):
            bad = event()
            bad["inputs"][0]["name"] = name
            with self.subTest(name=name), self.assertRaises(ExportError):
                clean_event(bad)

    def test_column_reference_requires_existing_input(self):
        bad = event()
        bad["outputs"][0]["facets"]["columnLineage"]["fields"]["birth_date"]["inputFields"][0]["name"] = "unknown"
        with self.assertRaises(ExportError):
            clean_event(bad)

    def test_candidate_cannot_publish_or_replace_success(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "new"
            report = stage(path, self.events)
            self.assertEqual(report["status"], "CANDIDATE_ONLY")
            self.assertFalse((path / "data/latest.json").exists())
            self.assertTrue((path / "lineage.candidate.jsonl").exists())
            with self.assertRaises(ExportError):
                stage(path, self.events)

    def test_verified_bundle_schema_and_column_refs(self):
        from jsonschema import Draft202012Validator, FormatChecker
        manifest = b'{"synthetic":true}'
        proof = evidence(self.events, manifest)
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "stage"
            result = stage(path, self.events, evidence=proof, manifest=manifest)
            self.assertEqual(result["status"], "VERIFIED_EXPORT")
            snapshot = json.loads((path / "data/latest.json").read_text())
            schema_path = Path(__file__).resolve().parents[2] / "contracts/snapshot-v1.schema.json"
            schema = json.loads(schema_path.read_text())
            Draft202012Validator(schema, format_checker=FormatChecker()).validate(snapshot)
            self.assertEqual(snapshot["summary"]["patient_count"], 100)
            self.assertEqual(snapshot["summary"]["encounter_count"], 4259)
            self.assertEqual(snapshot["last_success_at"], "2026-10-25T11:02:00.000000Z")
            self.assertEqual(len(snapshot["lineage"]["column_edges"]), 1)
            datasets = {x["dataset_ref"] for x in snapshot["datasets"]}
            runs = {x["run_ref"] for x in snapshot["runs"]}
            for edge in snapshot["lineage"]["column_edges"]:
                self.assertIn(edge["source_dataset_ref"], datasets)
                self.assertIn(edge["target_dataset_ref"], datasets)
                self.assertIn(edge["run_ref"], runs)
            self.assertTrue((path / "data/snapshots" /
                             (snapshot["snapshot_id"] + ".json")).is_file())

    def test_bad_manifest_and_digest_are_rejected(self):
        manifest = b"manifest"
        proof = evidence(self.events, manifest)
        with self.assertRaises(ExportError):
            verified_snapshot(normalize(self.events), proof, b"tampered",
                              digest(jsonl(normalize(self.events))))
        proof["independent_readback"]["export_jsonl_sha256"] = "b" * 64
        with self.assertRaises(ExportError):
            verified_snapshot(normalize(self.events), proof, manifest,
                              digest(jsonl(normalize(self.events))))

    def test_missing_independent_readback_never_creates_stage(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "new"
            with self.assertRaises(ExportError):
                stage(path, self.events, evidence={"source_commit_sha": SOURCE},
                      manifest=b"manifest")
            self.assertFalse(path.exists())

    def test_unverified_run_is_not_misrepresented_as_complete(self):
        manifest = b"manifest"
        proof = evidence(self.events, manifest)
        proof["independent_readback"]["verified_run_ids"] = []
        with self.assertRaises(ExportError):
            verified_snapshot(normalize(self.events), proof, manifest,
                              digest(jsonl(normalize(self.events))))


if __name__ == "__main__":
    unittest.main()
