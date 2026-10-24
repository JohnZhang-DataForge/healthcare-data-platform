"""Offline source-handoff tests: no Synthea JAR, K8s, OIE or Azure required."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from apps.clinical_producers.source_handoff import verify_handoff, VERSION, STATUS
from apps.synthea.synthea_new_generator.generator import (
    COMPLETED, MANIFEST_VERSION, sha256, validate_payload,
)
from apps.synthea.synthea_new_generator.request import (
    GenerationBlocked, SCHEMA_VERSION, fingerprint, normalize,
)


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.profile = ROOT / "config/synthea-new-generator/johns-creek-hl7.json"
        self.request_id = "johns-creek-test-0001"
        self.request = normalize({
            "schema_version": SCHEMA_VERSION,
            "request_id": self.request_id,
            "generation_mode": "NEW_ONLY",
            "population": 1,
            "state": "Georgia",
            "city": "Johns Creek",
            "seed": 67890,
            "reference_date": "20261024",
            "output_formats": ["FHIR_R4"],
        })
        self.folder = self.root / "requests" / self.request_id
        self.fhir = self.folder / "payload" / "fhir" / "patient.json"
        self.fhir.parent.mkdir(parents=True)
        bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [
                {"fullUrl": "urn:uuid:patient-one",
                 "resource": {"resourceType": "Patient", "id": "patient-one"}},
                {"resource": {"resourceType": "Encounter", "id": "enc-one",
                              "subject": {"reference": "urn:uuid:patient-one"},
                              "status": "finished"}},
            ],
        }
        self.fhir.write_text(json.dumps(bundle), encoding="utf-8")
        (self.folder / "request.json").write_text(
            json.dumps({"request": self.request,
                        "request_sha256": fingerprint(self.request)}), encoding="utf-8")
        self.write_manifest()

    def write_manifest(self):
        actual = validate_payload(self.folder / "payload", self.request)
        (self.folder / "generation-manifest.json").write_text(json.dumps({
            "schema_version": MANIFEST_VERSION,
            "request_id": self.request_id,
            "request_sha256": fingerprint(self.request),
            "status": COMPLETED,
            **actual,
        }), encoding="utf-8")

    def inspect(self):
        return verify_handoff(self.root, self.profile, self.request_id)

    def test_verified_hl7_route_is_only_source_handoff(self):
        result = self.inspect()
        self.assertEqual((result["schema_version"], result["status"]), (VERSION, STATUS))
        self.assertEqual((result["hospital_id"], result["target_format"], result["transformer"]),
                         ("demo-johns-creek", "HL7_V2", "OIE"))
        self.assertEqual(result["metrics"]["fhir_encounters"], 1)
        self.assertEqual(result["source_manifest_sha256"],
                         sha256(self.folder / "generation-manifest.json"))
        self.assertEqual(len(result["files"]), 1)
        self.assertFalse((self.folder / "delivery-ready.json").exists())
        self.assertEqual(result, self.inspect())

    def test_changed_fhir_bytes_block(self):
        self.fhir.write_text(self.fhir.read_text() + " ", encoding="utf-8")
        with self.assertRaises(GenerationBlocked):
            self.inspect()

    def test_missing_manifest_blocks(self):
        (self.folder / "generation-manifest.json").unlink()
        with self.assertRaises(GenerationBlocked):
            self.inspect()

    def test_wrong_profile_blocks(self):
        atlanta = ROOT / "config/synthea-new-generator/atlanta-fhir.json"
        with self.assertRaisesRegex(GenerationBlocked, "HANDOFF_PROFILE_REQUEST_MISMATCH"):
            verify_handoff(self.root, atlanta, self.request_id)

    def test_frozen_request_fingerprint_mismatch_blocks(self):
        path = self.folder / "request.json"
        record = json.loads(path.read_text())
        record["request_sha256"] = "0" * 64
        path.write_text(json.dumps(record))
        with self.assertRaisesRegex(GenerationBlocked, "FROZEN_REQUEST_MISMATCH"):
            self.inspect()

    def test_manifest_metric_mismatch_blocks(self):
        path = self.folder / "generation-manifest.json"
        doc = json.loads(path.read_text())
        doc["metrics"]["fhir_encounters"] += 1
        path.write_text(json.dumps(doc))
        with self.assertRaisesRegex(GenerationBlocked, "HANDOFF_MANIFEST_MISMATCH"):
            self.inspect()

    def test_symlink_manifest_blocks(self):
        path = self.folder / "generation-manifest.json"
        original = self.root / "saved.json"
        path.rename(original)
        path.symlink_to(original)
        with self.assertRaisesRegex(GenerationBlocked, "MISSING_OR_UNSAFE_HANDOFF_INPUT"):
            self.inspect()

    def test_directory_symlink_blocks(self):
        real = self.root / "requests"
        moved = self.root / "moved"
        real.rename(moved)
        real.symlink_to(moved, target_is_directory=True)
        with self.assertRaisesRegex(GenerationBlocked, "UNSAFE_HANDOFF_DIRECTORY"):
            self.inspect()

    def test_no_mutation_on_repeated_verification(self):
        paths = [self.fhir, self.folder / "request.json", self.folder / "generation-manifest.json"]
        first = [sha256(p) for p in paths]
        self.inspect()
        self.inspect()
        self.assertEqual(first, [sha256(p) for p in paths])


if __name__ == "__main__":
    unittest.main()
