"""Direct hospital FHIR -> shared immutable Publisher; entirely offline."""
import json
import tempfile
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from apps.clinical_producers.direct_fhir_publisher import (
    DirectFHIRBlocked, prepare_direct_fhir, publish_direct_fhir,
)
from apps.clinical_producers.azure_blob_publisher import (
    BlobSnapshot, BlobAlreadyExists, BlobNotFound,
)
from apps.synthea.synthea_new_generator.generator import (
    COMPLETED, MANIFEST_VERSION, fingerprint, sha256, validate_payload,
)
from apps.synthea.synthea_new_generator.request import (
    SCHEMA_VERSION, normalize, GenerationBlocked,
)


class MemoryBackend:
    def __init__(self):
        self.data = {}
        self.writes = []
        self.reads = []

    def create(self, key, data, metadata, content_type):
        if key in self.data:
            raise BlobAlreadyExists()
        etag = f'"etag-{len(self.data) + 1}"'
        self.data[key] = BlobSnapshot(data, dict(metadata), content_type, etag)
        self.writes.append(key)
        return etag

    def read(self, key):
        self.reads.append(key)
        if key not in self.data:
            raise BlobNotFound()
        return self.data[key]


class DirectFHIRTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.profile = ROOT / "config/synthea-new-generator/atlanta-fhir.json"
        self.request_id = "atlanta-direct-0001"
        request = normalize({
            "schema_version": SCHEMA_VERSION,
            "request_id": self.request_id,
            "generation_mode": "NEW_ONLY",
            "population": 1,
            "state": "Georgia",
            "city": "Atlanta",
            "seed": 12345,
            "reference_date": "20261024",
            "output_formats": ["FHIR_R4"],
        })
        self.folder = self.root / "requests" / self.request_id
        fhir = self.folder / "payload" / "fhir" / "patient.json"
        fhir.parent.mkdir(parents=True)
        self.fhir = fhir
        fhir.write_text(json.dumps({
            "resourceType": "Bundle", "type": "collection",
            "entry": [
                {"fullUrl": "urn:uuid:patient-one",
                 "resource": {"resourceType": "Patient", "id": "one"}},
                {"resource": {"resourceType": "Encounter", "id": "visit-one",
                              "subject": {"reference": "urn:uuid:patient-one"}}},
            ],
        }), encoding="utf-8")
        (self.folder / "request.json").write_text(json.dumps({
            "request": request, "request_sha256": fingerprint(request),
        }), encoding="utf-8")
        actual = validate_payload(self.folder / "payload", request)
        self.manifest = self.folder / "generation-manifest.json"
        self.manifest.write_text(json.dumps({
            "schema_version": MANIFEST_VERSION,
            "request_id": self.request_id,
            "request_sha256": fingerprint(request),
            "status": COMPLETED,
            **actual,
        }), encoding="utf-8")

    def test_plan_reads_original_fhir_bytes_and_real_manifest_sha(self):
        plan, content = prepare_direct_fhir(self.root, self.profile,
                                            self.request_id)
        self.assertEqual(plan["hospital_id"], "demo-atlanta")
        self.assertEqual(plan["target_format"], "FHIR_R4")
        self.assertEqual(plan["source_manifest_sha256"], sha256(self.manifest))
        self.assertEqual(content, {"fhir/patient.json": self.fhir.read_bytes()})

    def test_publishing_retries_with_identical_remote_get_and_last_manifest(self):
        backend = MemoryBackend()
        inputs = (self.root, self.profile, self.request_id)
        first = publish_direct_fhir(*inputs, landing_prefix="healthcare/v1",
                                    backend=backend)
        self.assertEqual(first["status"], "BLOB_MANIFEST_COMMITTED")
        self.assertEqual(len(backend.writes), 2)
        self.assertEqual(backend.writes[-1], first["manifest_key"])
        self.assertEqual(backend.data[first["objects"][0]["blob_key"]].data,
                         self.fhir.read_bytes())
        second = publish_direct_fhir(*inputs, landing_prefix="healthcare/v1",
                                     backend=backend)
        self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])
        self.assertEqual(len(backend.writes), 2)
        self.assertEqual(second["manifest_create_status"], "ALREADY_MATCHING")
        self.assertEqual(second["object_create_statuses"], ["ALREADY_MATCHING"])

    def test_wrong_hospital_profile_route_blocks_before_any_publish(self):
        other = ROOT / "config/synthea-new-generator/johns-creek-hl7.json"
        with self.assertRaisesRegex(DirectFHIRBlocked,
                                    "DIRECT_FHIR_PROFILE_REQUIRED"):
            publish_direct_fhir(self.root, other, self.request_id,
                                landing_prefix="healthcare",
                                backend=MemoryBackend())

    def test_changed_payload_fail_closed_no_network_effect(self):
        self.fhir.write_bytes(self.fhir.read_bytes() + b" ")
        backend = MemoryBackend()
        with self.assertRaises(GenerationBlocked):
            publish_direct_fhir(self.root, self.profile, self.request_id,
                                landing_prefix="healthcare", backend=backend)
        self.assertEqual(backend.writes, [])
        self.assertEqual(backend.reads, [])

    def test_changed_manifest_fail_closed_no_network_effect(self):
        self.manifest.write_bytes(self.manifest.read_bytes() + b" ")
        backend = MemoryBackend()
        with self.assertRaises(GenerationBlocked):
            publish_direct_fhir(self.root, self.profile, self.request_id,
                                landing_prefix="healthcare", backend=backend)
        self.assertEqual(backend.writes, [])

    def test_symlinked_payload_rejected_before_upload(self):
        target = self.root / "outside.json"
        self.fhir.rename(target)
        self.fhir.symlink_to(target)
        with self.assertRaises(GenerationBlocked):
            prepare_direct_fhir(self.root, self.profile, self.request_id)


if __name__ == "__main__":
    unittest.main()
