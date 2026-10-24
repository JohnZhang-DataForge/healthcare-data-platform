"""Azurite-only SDK adapter integration (never uses shared Azure resources)."""
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from apps.clinical_producers.azure_blob_publisher import (
    AzureSDKBlobBackend, PublishBlocked, publish_immutable,
)
from apps.clinical_producers.blob_publish_contract import VERSION


@unittest.skipUnless(os.environ.get("AZURITE_ONLY") == "1",
                     "requires isolated CI Azurite service")
class AzuritePublisherTests(unittest.TestCase):
    def setUp(self):
        from azure.storage.blob import BlobServiceClient
        self.service = BlobServiceClient.from_connection_string(
            "UseDevelopmentStorage=true")
        self.container = "producer-test-" + uuid.uuid4().hex[:20]
        self.service.create_container(self.container)
        self.backend = AzureSDKBlobBackend(
            self.service.get_container_client(self.container))
        raw = json.dumps({"resourceType": "Bundle", "entry": []},
                         sort_keys=True).encode()
        self.raw = raw
        self.plan = {
            "schema_version": VERSION,
            "hospital_id": "demo-atlanta",
            "feed_id": "demo-atlanta-fhir-r4",
            "request_id": "atlanta-azurite-0001",
            "source_manifest_sha256": "c" * 64,
            "target_format": "FHIR_R4",
            "verification_state": "SOURCE_HANDOFF_VERIFIED",
            "skipped_non_admissions": 0,
            "objects": [{
                "name": "fhir/encounter.json",
                "size_bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "source_event_id": None,
            }],
        }

    def tearDown(self):
        # Only deletes the uniquely named ephemeral local Azurite container.
        self.service.delete_container(self.container)
        self.service.close()

    def test_real_sdk_if_none_match_get_manifest_last_and_repeat(self):
        args = dict(landing_prefix="healthcare/test", backend=self.backend)
        first = publish_immutable(self.plan,
                                  {"fhir/encounter.json": self.raw}, **args)
        second = publish_immutable(self.plan,
                                   {"fhir/encounter.json": self.raw}, **args)
        self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])
        self.assertEqual(second["object_create_statuses"], ["ALREADY_MATCHING"])
        self.assertEqual(second["manifest_create_status"], "ALREADY_MATCHING")
        manifest = self.backend.read(first["manifest_key"])
        self.assertEqual(hashlib.sha256(manifest.data).hexdigest(),
                         first["manifest_sha256"])
        self.assertEqual(json.loads(manifest.data)["objects"][0]["sha256"],
                         hashlib.sha256(self.raw).hexdigest())
        new_plan = dict(self.plan, source_manifest_sha256="d" * 64)
        with self.assertRaisesRegex(PublishBlocked, "IMMUTABLE_REQUEST_CONFLICT"):
            publish_immutable(new_plan, {"fhir/encounter.json": self.raw},
                              **args)

    def test_existing_wrong_bytes_fail_closed_and_no_manifest(self):
        data_key = ("healthcare/test/demo-atlanta/demo-atlanta-fhir-r4/"
                    "atlanta-azurite-0001/FHIR_R4/fhir/encounter.json")
        self.service.get_blob_client(self.container, data_key).upload_blob(
            b"conflict", overwrite=False)
        with self.assertRaisesRegex(PublishBlocked,
                                    "REMOTE_SHA256_OR_METADATA_CONFLICT"):
            publish_immutable(self.plan, {"fhir/encounter.json": self.raw},
                              landing_prefix="healthcare/test",
                              backend=self.backend)
        objects = list(self.service.get_container_client(self.container)
                       .list_blobs())
        self.assertEqual(len(objects), 1)
        self.assertEqual(objects[0].name, data_key)


if __name__ == "__main__":
    unittest.main()
