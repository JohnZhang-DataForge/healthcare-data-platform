"""Azurite-only SDK acceptance; NEVER authorizes live Azure or Fabric writes."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
import hashlib
import json
import os
import uuid
import unittest

if os.getenv("AZURITE_ONLY") == "1":
    from azure.storage.blob import BlobServiceClient
else:
    BlobServiceClient = None
from blob_batch_ledger import (
    BlobConflict, StageScope, TargetProof, acquire, finalize, precheck,
)
from azure_blob_backend import AzureBlobBatchBackend
from healthcare_data_engine.models.batch_context import BatchContext


def canonical(obj):
    return (json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n").encode()


@unittest.skipUnless(os.getenv("AZURITE_ONLY") == "1", "Azurite isolated CI only")
class BlobAzuriteTests(unittest.TestCase):
    def setUp(self):
        self.service = BlobServiceClient.from_connection_string(
            os.environ.get("AZURITE_CONNECTION_STRING", "UseDevelopmentStorage=true"),
            retry_total=0)
        container = "blobcontrol" + uuid.uuid4().hex[:12]
        self.client = self.service.create_container(container)
        # Logical production target is deliberately never contacted. The
        # injected ContainerClient is an isolated disposable Azurite container.
        self.backend = AzureBlobBatchBackend(self.client)
        self.payload = b'{"resourceType":"Bundle","entry":[]}'
        self.request = "atlanta-fhir-gh-99999999999"
        self.context = BatchContext(
            hospital_id="atlanta-hospital-a",
            feed_id="atlanta-hospital-a-fhir-r4",
            source_system="FHIR_R4", request_id=self.request,
            manifest_sha256="b"*64, processing_version="0.1.11",
            processing_run_id="azurite-01", source_version="v1",
            source_ingest_date=date(2026, 11, 9),
            processed_at=datetime(2026, 11, 9, tzinfo=timezone.utc))
        root = f"clinical/v1/{self.context.hospital_id}/{self.context.feed_id}/{self.request}"
        payload_key = root + "/FHIR_R4/Bundle-01.json"
        result = self.client.upload_blob(payload_key, self.payload, overwrite=False)
        self.payload_etag = result["etag"]
        self.manifest = {
            "schema_version": "healthcare-azure-blob-landing-manifest-v1",
            "hospital_id": self.context.hospital_id,
            "feed_id": self.context.feed_id,
            "request_id": self.context.request_id,
            "source_manifest_sha256": self.context.manifest_sha256,
            "target_format": "FHIR_R4",
            "objects": [{
                "blob_key": payload_key, "sha256": hashlib.sha256(self.payload).hexdigest(),
                "etag": self.payload_etag, "size_bytes": len(self.payload)
            }]
        }
        raw = canonical(self.manifest)
        manifest_etag = self.client.upload_blob(
            root + "/landing-manifest.json", raw, overwrite=False)["etag"]
        self.scope = StageScope(
            self.context, "SILVER_APPROVED", hashlib.sha256(raw).hexdigest(),
            manifest_etag, "mapper-v1", "0.1.11", "a"*64,
            "synthetic-azurite-approval-987")

    def tearDown(self):
        # Isolated emulator container only; production adapter does not expose DELETE.
        self.client.delete_container()

    def proof(self):
        return TargetProof(self.scope.stage, self.scope.publication_id,
                           "azurite://simulated-target", "f"*64,
                           "2026-11-09T13:00:00Z", "emulated-approval", True)

    def test_atomic_claim_lease_cas_receipt_and_replay(self):
        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(
                lambda owner: acquire(self.backend, self.scope, owner=owner, attempt=1),
                ("azurite-01", "azurite-02")))
        self.assertEqual([x[0] for x in results].count("CLAIMED"), 1)
        claimed = next(item[1] for item in results if item[0] == "CLAIMED")
        self.assertEqual(precheck(self.backend, self.scope), "BUSY")
        self.assertEqual(finalize(self.backend, self.scope, claimed, self.proof()),
                         "VERIFIED_RECEIPT_WRITTEN")
        self.assertEqual(precheck(self.backend, self.scope), "SKIP")
        self.assertEqual(self.backend.read(self.scope.receipt_key).data[:1], b"{")
        self.assertEqual(self.backend.read(self.scope.source_key).data, canonical(self.manifest))
        self.assertEqual(
            self.client.get_blob_client(self.scope.source_key).get_blob_properties().etag,
            self.scope.landing_manifest_etag)
        with self.assertRaises(BlobConflict):
            self.backend.create(self.scope.receipt_key, b"{}")

    def test_stale_etag_and_lease_prevent_mutation(self):
        status, claimed = acquire(self.backend, self.scope, owner="azurite-01", attempt=1)
        self.assertEqual(status, "CLAIMED")
        with self.assertRaises(BlobConflict):
            self.backend.cas_control(self.scope.claim_key, b"{}", '"wrong-etag"',
                                     claimed.lease_id)
        self.assertEqual(finalize(self.backend, self.scope, claimed, self.proof()),
                         "VERIFIED_RECEIPT_WRITTEN")
        with self.assertRaises(Exception):
            self.backend.renew_lease(self.scope.claim_key, claimed.lease_id)


if __name__ == "__main__":
    unittest.main()
