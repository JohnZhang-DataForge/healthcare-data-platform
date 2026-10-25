"""Offline immutable Azure Blob Publisher tests; no network, Azure, or K8s."""
import hashlib
import json
import time
from types import ModuleType
from unittest.mock import patch
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from apps.clinical_producers.blob_publish_contract import VERSION
from apps.clinical_producers.azure_blob_publisher import (
    AzureSDKBlobBackend, BlobAlreadyExists, BlobNotFound, BlobSnapshot,
    PublishBlocked, publish_immutable,
)


def request_plan(n=2):
    content = {}
    objects = []
    for i in range(n):
        name = f"fhir/patient-{i:03d}.json"
        raw = json.dumps({"resourceType": "Bundle", "entry": [],
                          "id": f"patient-{i}"}, sort_keys=True).encode()
        content[name] = raw
        objects.append({"name": name, "size_bytes": len(raw),
                        "sha256": hashlib.sha256(raw).hexdigest(),
                        "source_event_id": None})
    return ({
        "schema_version": VERSION,
        "hospital_id": "atlanta-hospital-a",
        "feed_id": "atlanta-hospital-a-fhir-r4",
        "request_id": "atlanta-20261024-0002",
        "source_manifest_sha256": "a" * 64,
        "target_format": "FHIR_R4",
        "verification_state": "SOURCE_HANDOFF_VERIFIED",
        "skipped_non_admissions": 0,
        "objects": objects,
    }, content)


class TemporaryStorageTokenTests(unittest.TestCase):
    def test_factory_fences_token_expiry_and_target(self):
        import sys
        core = ModuleType("azure.core")
        credential_mod = ModuleType("azure.core.credentials")
        class AccessToken:
            def __init__(self, token, expires_on):
                self.token, self.expires_on = token, expires_on
        credential_mod.AccessToken = AccessToken
        sdk = ModuleType("azure.storage.blob")
        class BlobServiceClient:
            def __init__(self, *, account_url, credential):
                self.account_url = account_url
                self.credential = credential
            def get_container_client(self, container):
                self.container = container
                return self
        sdk.BlobServiceClient = BlobServiceClient
        fake_modules = {
            "azure": ModuleType("azure"),
            "azure.core": core,
            "azure.core.credentials": credential_mod,
            "azure.storage": ModuleType("azure.storage"),
            "azure.storage.blob": sdk,
        }
        good = dict(account_url="https://johnzhang.blob.core.windows.net",
                    container="landing",
                    access_token="FAKE_STORAGE_ACCESS_TOKEN_" + "X"*96,
                    expires_on=int(time.time())+3600)
        with patch.dict(sys.modules, fake_modules):
            backend = AzureSDKBlobBackend.from_temporary_access_token(**good)
            self.assertEqual(backend._container.account_url,good["account_url"])
            self.assertEqual(backend._container.container, "landing")
            credential = backend._container.credential
            issued = credential.get_token("https://storage.azure.com/.default")
            self.assertEqual(issued.token,good["access_token"])
            self.assertEqual(issued.expires_on,good["expires_on"])
            with self.assertRaisesRegex(PublishBlocked, "INVALID_TEMPORARY_AZURE_TOKEN_SCOPE"):
                credential.get_token("https://management.azure.com/.default")
            for override,error in (
                ({"expires_on":int(time.time())+60}, "TEMPORARY_TOKEN_EXPIRY_OUT_OF_BOUNDS"),
                ({"expires_on":int(time.time())+7201}, "TEMPORARY_TOKEN_EXPIRY_OUT_OF_BOUNDS"),
                ({"expires_on":"not-integer"}, "TEMPORARY_TOKEN_EXPIRY_OUT_OF_BOUNDS"),
                ({"access_token":"fake token with spaces"}, "INVALID_TEMPORARY_AZURE_STORAGE_TOKEN"),
                ({"account_url":"http://johnzhang.blob.core.windows.net"}, "INVALID_AZURE_ACCOUNT_URL"),
                ({"container":"BadContainer"}, "INVALID_CONTAINER"),
            ):
                with self.subTest(error=error, override=override):
                    with self.assertRaisesRegex(PublishBlocked,error):
                        AzureSDKBlobBackend.from_temporary_access_token(
                            **{**good,**override})


class OfflineBlobBackend:
    def __init__(self):
        self.blobs = {}
        self.writes = []
        self.reads = []
        self.counter = 0
        self.fail_on_create = None
        self.fail_after_create = None
        self.fail_on_read = None
        self.corrupt_on_read = None
        self.secret = "never-log-this-secret"

    def create(self, key, data, metadata, content_type):
        if key in self.blobs:
            raise BlobAlreadyExists()
        if self.fail_on_create and self.fail_on_create in key:
            raise RuntimeError("403 " + self.secret)
        self.counter += 1
        snapshot = BlobSnapshot(
            bytes(data), dict(metadata), content_type,
            f'"etag-{self.counter}"', f"version-{self.counter}")
        self.blobs[key] = snapshot
        self.writes.append(key)
        if self.fail_after_create and self.fail_after_create in key:
            raise RuntimeError("response lost; write may have completed")
        return snapshot.etag

    def read(self, key):
        self.reads.append(key)
        if self.fail_on_read and self.fail_on_read in key:
            raise RuntimeError("credential " + self.secret)
        if key not in self.blobs:
            raise BlobNotFound()
        snapshot = self.blobs[key]
        if self.corrupt_on_read and self.corrupt_on_read in key:
            return BlobSnapshot(b"corrupt", snapshot.metadata,
                                snapshot.content_type, snapshot.etag,
                                snapshot.version_id)
        return snapshot


class PublisherTests(unittest.TestCase):
    def test_upload_get_manifest_last_and_response_receipts(self):
        p, data = request_plan()
        backend = OfflineBlobBackend()
        result = publish_immutable(p, data, landing_prefix="healthcare/v1",
                                   backend=backend)
        self.assertEqual(result["status"], "BLOB_MANIFEST_COMMITTED")
        self.assertEqual(result["object_create_statuses"], ["CREATED", "CREATED"])
        self.assertEqual(len(backend.writes), 3)
        self.assertEqual(backend.writes[-1], result["manifest_key"])
        self.assertTrue(result["manifest_key"] in backend.reads)
        self.assertTrue(all(key in backend.reads for key in backend.writes))
        self.assertEqual(len(result["manifest_sha256"]), 64)
        manifest = json.loads(backend.blobs[result["manifest_key"]].data)
        self.assertEqual(manifest["source_manifest_sha256"], "a" * 64)
        self.assertEqual(manifest["objects"][0]["version_id"], "version-1")
        self.assertEqual(set(item["etag"] for item in manifest["objects"]),
                         {'"etag-1"', '"etag-2"'})

    def test_prefix_containing_format_name_is_safe(self):
        p, data = request_plan(1)
        backend = OfflineBlobBackend()
        receipt = publish_immutable(p, data,
                                    landing_prefix="healthcare/FHIR_R4/archive",
                                    backend=backend)
        self.assertEqual(receipt["status"], "BLOB_MANIFEST_COMMITTED")
        self.assertTrue(receipt["objects"][0]["blob_key"].endswith(
            "/FHIR_R4/fhir/patient-000.json"))

    def test_repeat_is_immutable_and_reads_every_object(self):
        p, data = request_plan()
        backend = OfflineBlobBackend()
        first = publish_immutable(p, data, landing_prefix="healthcare/v1",
                                  backend=backend)
        writes = list(backend.writes)
        backend.reads.clear()
        again = publish_immutable(p, data, landing_prefix="healthcare/v1",
                                  backend=backend)
        self.assertEqual(writes, backend.writes)
        self.assertEqual(first["manifest_sha256"], again["manifest_sha256"])
        self.assertEqual(first["manifest_etag"], again["manifest_etag"])
        self.assertEqual(again["manifest_create_status"], "ALREADY_MATCHING")
        self.assertEqual(again["object_create_statuses"],
                         ["ALREADY_MATCHING"] * 2)
        self.assertTrue(all(key in backend.reads for key in writes))

    def test_changed_manifest_same_request_holds_before_any_write(self):
        p, data = request_plan()
        backend = OfflineBlobBackend()
        publish_immutable(p, data, landing_prefix="healthcare", backend=backend)
        writes = list(backend.writes)
        changed = dict(p, source_manifest_sha256="b" * 64)
        with self.assertRaisesRegex(PublishBlocked,
                                    "IMMUTABLE_REQUEST_CONFLICT"):
            publish_immutable(changed, data, landing_prefix="healthcare",
                              backend=backend)
        self.assertEqual(backend.writes, writes)

    def test_content_conflict_does_not_overwrite_or_commit(self):
        p, data = request_plan()
        backend = OfflineBlobBackend()
        key = "healthcare/atlanta-hospital-a/atlanta-hospital-a-fhir-r4/" + (
            p["request_id"] + "/FHIR_R4/fhir/patient-000.json")
        backend.blobs[key] = BlobSnapshot(b"malicious", {"kind": "data"},
                                          "application/fhir+json", '"old"')
        with self.assertRaisesRegex(PublishBlocked,
                                    "REMOTE_SHA256_OR_METADATA_CONFLICT"):
            publish_immutable(p, data, landing_prefix="healthcare",
                              backend=backend)
        self.assertEqual(backend.blobs[key].data, b"malicious")
        self.assertNotIn("landing-manifest.json",
                         "\n".join(backend.blobs))

    def test_source_tampering_has_zero_network_effect(self):
        p, data = request_plan()
        backend = OfflineBlobBackend()
        data["fhir/patient-000.json"] = b"tampered"
        with self.assertRaisesRegex(ValueError, "SOURCE_BYTES_MISMATCH"):
            publish_immutable(p, data, landing_prefix="healthcare",
                              backend=backend)
        self.assertEqual(backend.reads, [])
        self.assertEqual(backend.writes, [])

    def test_partial_create_fail_resumes_by_get_with_no_overwrite(self):
        p, data = request_plan()
        backend = OfflineBlobBackend()
        backend.fail_on_create = "patient-001"
        with self.assertRaisesRegex(PublishBlocked,
                                    "REMOTE_CONDITIONAL_CREATE_FAILED"):
            publish_immutable(p, data, landing_prefix="healthcare",
                              backend=backend)
        self.assertEqual(len(backend.writes), 1)
        backend.fail_on_create = None
        response = publish_immutable(p, data, landing_prefix="healthcare",
                                     backend=backend)
        self.assertEqual(response["status"], "BLOB_MANIFEST_COMMITTED")
        self.assertEqual(response["object_create_statuses"],
                         ["ALREADY_MATCHING", "CREATED"])
        self.assertEqual(len(backend.writes), 3)

    def test_lost_ack_after_create_requires_retry_no_false_success(self):
        p, data = request_plan(1)
        backend = OfflineBlobBackend()
        backend.fail_after_create = "patient-000"
        with self.assertRaisesRegex(PublishBlocked,
                                    "REMOTE_CONDITIONAL_CREATE_FAILED"):
            publish_immutable(p, data, landing_prefix="healthcare",
                              backend=backend)
        self.assertEqual(len(backend.writes), 1)
        backend.fail_after_create = None
        receipt = publish_immutable(p, data, landing_prefix="healthcare",
                                    backend=backend)
        self.assertEqual(receipt["object_create_statuses"],
                         ["ALREADY_MATCHING"])
        self.assertEqual(backend.writes[-1], receipt["manifest_key"])

    def test_manifest_write_lost_ack_retry_rechecks_all_remote(self):
        p, data = request_plan(1)
        backend = OfflineBlobBackend()
        backend.fail_after_create = "landing-manifest.json"
        with self.assertRaisesRegex(PublishBlocked,
                                    "REMOTE_CONDITIONAL_CREATE_FAILED"):
            publish_immutable(p, data, landing_prefix="healthcare",
                              backend=backend)
        self.assertEqual(len(backend.writes), 2)
        backend.fail_after_create = None
        res = publish_immutable(p, data, landing_prefix="healthcare",
                                backend=backend)
        self.assertEqual(res["manifest_create_status"], "ALREADY_MATCHING")
        self.assertEqual(len(backend.writes), 2)

    def test_bad_get_cannot_commit(self):
        p, data = request_plan(1)
        backend = OfflineBlobBackend()
        backend.corrupt_on_read = "patient-000"
        with self.assertRaisesRegex(PublishBlocked,
                                    "REMOTE_SHA256_OR_METADATA_CONFLICT"):
            publish_immutable(p, data, landing_prefix="healthcare",
                              backend=backend)
        self.assertEqual(len(backend.writes), 1)

    def test_get_failure_is_redacted_and_never_commits(self):
        p, data = request_plan(1)
        backend = OfflineBlobBackend()
        backend.fail_on_read = "patient-000"
        with self.assertRaises(PublishBlocked) as exc:
            publish_immutable(p, data, landing_prefix="healthcare",
                              backend=backend)
        self.assertNotIn(backend.secret, str(exc.exception))
        self.assertEqual(len(backend.writes), 1)

    def test_bad_remote_metadata_does_not_count_as_matching(self):
        p, data = request_plan(1)
        backend = OfflineBlobBackend()
        done = publish_immutable(p, data, landing_prefix="healthcare",
                                 backend=backend)
        key = done["objects"][0]["blob_key"]
        saved = backend.blobs[key]
        backend.blobs[key] = BlobSnapshot(saved.data, {"sha256": saved.metadata["sha256"]},
                                          saved.content_type, saved.etag,
                                          saved.version_id)
        with self.assertRaisesRegex(PublishBlocked,
                                    "REMOTE_SHA256_OR_METADATA_CONFLICT"):
            publish_immutable(p, data, landing_prefix="healthcare",
                              backend=backend)

    def test_skip_only_hl7_cannot_make_fake_manifest(self):
        p, _ = request_plan(0)
        p["target_format"] = "HL7_V2"
        p["verification_state"] = "OIE_HL7_READBACK_VERIFIED"
        p["skipped_non_admissions"] = 30
        backend = OfflineBlobBackend()
        with self.assertRaisesRegex(PublishBlocked, "NO_PUBLISHABLE_OBJECTS"):
            publish_immutable(p, {}, landing_prefix="healthcare",
                              backend=backend)
        self.assertEqual(backend.writes, [])

    def test_authorization_failure_redacted(self):
        p, data = request_plan(1)
        backend = OfflineBlobBackend()
        backend.fail_on_create = "patient-000"
        with self.assertRaises(PublishBlocked) as exc:
            publish_immutable(p, data, landing_prefix="healthcare",
                              backend=backend)
        self.assertNotIn(backend.secret, str(exc.exception))
        self.assertEqual(backend.writes, [])

    def test_sdk_backend_constructor_is_side_effect_free(self):
        backend = AzureSDKBlobBackend(container_client=object())
        self.assertIsNotNone(backend)


if __name__ == "__main__":
    unittest.main()
