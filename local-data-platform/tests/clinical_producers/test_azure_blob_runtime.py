"""Offline secure launch contract for staged Azure Blob DIRECT FHIR Job."""
from contextlib import redirect_stderr
import hashlib
import time
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(ROOT))
from apps.clinical_producers.azure_blob_runtime import (
    READY_BYTES, PublisherRuntimeBlocked, await_ready, ensure_ready,
    publish_direct_from_stage, main,
)
from apps.clinical_producers.azure_blob_publisher import (
    BlobAlreadyExists, BlobNotFound, BlobSnapshot,
)
from apps.clinical_producers.blob_publish_contract import VERSION

SOURCE_SHA = "a" * 64
SECRET = "THIS_IS_FAKE_AND_MUST_NOT_BE_PRINTED_123"
CONFIG = {
    "AZURE_BLOB_ACCOUNT_URL": "https://example.blob.core.windows.net",
    "AZURE_BLOB_CONTAINER": "landing",
    "AZURE_TENANT_ID": "fake-tenant",
    "AZURE_CLIENT_ID": "fake-client",
    "AZURE_CLIENT_SECRET": SECRET,
}


class FakeBlobBackend:
    def __init__(self):
        self.values = {}
        self.writes = []
    def create(self, key, raw, metadata, content_type):
        if key in self.values:
            raise BlobAlreadyExists()
        etag = f'"fake-{len(self.values)+1}"'
        self.values[key] = BlobSnapshot(raw, dict(metadata), content_type, etag)
        self.writes.append(key)
        return etag
    def read(self, key):
        if key not in self.values:
            raise BlobNotFound()
        return self.values[key]


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.marker = self.root / ".ready"
        self.marker.write_bytes(READY_BYTES)
        self.fhir_bytes = json.dumps({
            "resourceType": "Bundle", "type": "collection", "entry": []
        }, separators=(",", ":")).encode()
        self.plan = {
            "schema_version": VERSION,
            "hospital_id": "atlanta-hospital-a",
            "feed_id": "atlanta-hospital-a-fhir-r4",
            "request_id": "newbatch-00001",
            "source_manifest_sha256": SOURCE_SHA,
            "target_format": "FHIR_R4",
            "verification_state": "SOURCE_HANDOFF_VERIFIED",
            "skipped_non_admissions": 0,
            "objects": [{
                "name": "fhir/patient.json",
                "size_bytes": len(self.fhir_bytes),
                "sha256": hashlib.sha256(self.fhir_bytes).hexdigest(),
                "source_event_id": None,
            }],
        }
        self.backend = FakeBlobBackend()
        self.factories = []

    def run_once(self, **overrides):
        def factory(**kw):
            self.factories.append(kw)
            return self.backend
        kwargs = dict(
            state_root=self.root, profile_path=self.root / "profile.json",
            request_id=self.plan["request_id"], ready_marker=self.marker,
            expected_source_manifest_sha256=SOURCE_SHA,
            landing_prefix="healthcare/v1", env=CONFIG,
            backend_factory=factory,
        )
        kwargs.update(overrides)
        with patch(
            "apps.clinical_producers.azure_blob_runtime.prepare_direct_fhir",
            return_value=(self.plan, {"fhir/patient.json": self.fhir_bytes}),
        ):
            return publish_direct_from_stage(**kwargs)

    def test_ready_marker_exact_bytes_and_timeout(self):
        ensure_ready(self.marker)
        self.marker.write_bytes(b"BLOB_HANDOFF_READY_V1")
        with self.assertRaisesRegex(PublisherRuntimeBlocked,
                                    "HANDOFF_NOT_READY"):
            ensure_ready(self.marker)
        with self.assertRaisesRegex(PublisherRuntimeBlocked,
                                    "HANDOFF_NOT_READY"):
            await_ready(self.marker, 0)
        self.marker.write_bytes(READY_BYTES)
        await_ready(self.marker, 0)
        with self.assertRaisesRegex(PublisherRuntimeBlocked,
                                    "INVALID_HANDOFF_TIMEOUT"):
            await_ready(self.marker, 1801)

    def test_source_sha_mismatch_blocks_before_backend_or_blob_write(self):
        with self.assertRaisesRegex(PublisherRuntimeBlocked,
                                    "PINNED_SOURCE_MANIFEST_MISMATCH"):
            self.run_once(expected_source_manifest_sha256="b" * 64)
        self.assertEqual(self.factories, [])
        self.assertEqual(self.backend.writes, [])

    def test_missing_identity_blocks_after_source_verification(self):
        config = dict(CONFIG)
        del config["AZURE_CLIENT_SECRET"]
        with self.assertRaisesRegex(PublisherRuntimeBlocked,
                                    "MISSING_SCOPED_AZURE_IDENTITY"):
            self.run_once(env=config)
        self.assertFalse(self.factories)

    def test_unverified_or_mutated_bytes_fail_before_sdk(self):
        original = self.plan["objects"][0]["sha256"]
        self.plan["objects"][0]["sha256"] = "c" * 64
        with self.assertRaisesRegex(Exception, "SOURCE_BYTES_MISMATCH"):
            self.run_once()
        self.assertEqual(self.backend.writes, [])
        self.assertEqual(self.factories, [])
        self.plan["objects"][0]["sha256"] = original

    def test_immutable_upload_manifest_last_and_safe_retry(self):
        first = self.run_once()
        self.assertEqual(first["status"], "BLOB_MANIFEST_COMMITTED")
        self.assertEqual(self.backend.writes[-1], first["manifest_key"])
        self.assertEqual(len(self.backend.writes), 2)
        self.assertEqual(self.factories[0]["client_secret"], SECRET)
        second = self.run_once()
        self.assertEqual(second["manifest_create_status"], "ALREADY_MATCHING")
        self.assertEqual(second["manifest_sha256"], first["manifest_sha256"])
        self.assertEqual(len(self.backend.writes), 2)

    def test_invalid_landing_prefix_and_symlink_marker_block(self):
        with self.assertRaisesRegex(Exception, "INVALID_LANDING_PREFIX"):
            self.run_once(landing_prefix="../wrong")
        self.assertFalse(self.factories)
        self.marker.unlink()
        self.marker.symlink_to(self.root / "other-file")
        with self.assertRaisesRegex(PublisherRuntimeBlocked,
                                    "HANDOFF_NOT_READY"):
            self.run_once()

    def test_main_failure_does_not_print_secrets_or_exception_string(self):
        stderr = StringIO()
        with patch(
            "apps.clinical_producers.azure_blob_runtime.await_ready",
            side_effect=RuntimeError(SECRET),
        ), redirect_stderr(stderr):
            rc = main([
                "--state-root", str(self.root),
                "--profile", str(self.root / "profile.json"),
                "--request-id", self.plan["request_id"],
                "--ready-marker", str(self.marker),
                "--expected-source-manifest-sha256", SOURCE_SHA,
                "--landing-prefix", "healthcare/v1",
            ])
        self.assertEqual(rc, 1)
        self.assertIn("BLOCKED_FAIL_CLOSED", stderr.getvalue())
        self.assertNotIn(SECRET, stderr.getvalue())

    def test_direct_readonly_pvc_mode_no_staging_marker(self):
        self.marker.unlink()
        receipt = self.run_once(ready_marker=None, direct_readonly_source=True)
        self.assertEqual(receipt["status"], "BLOB_MANIFEST_COMMITTED")
        self.assertEqual(len(self.backend.writes), 2)

    def test_no_implicit_staging_bypass_or_conflicting_modes(self):
        with self.assertRaisesRegex(PublisherRuntimeBlocked,
                                    "HANDOFF_READY_MARKER_REQUIRED"):
            self.run_once(ready_marker=None)
        with self.assertRaisesRegex(PublisherRuntimeBlocked,
                                    "CONFLICTING_SOURCE_MODES"):
            self.run_once(direct_readonly_source=True)
        self.assertEqual(self.backend.writes, [])

    def test_temporary_storage_token_mode_needs_no_client_secret(self):
        config = {
            "AZURE_AUTH_MODE": "temporary-access-token",
            "AZURE_BLOB_ACCOUNT_URL": CONFIG["AZURE_BLOB_ACCOUNT_URL"],
            "AZURE_BLOB_CONTAINER": "landing",
            "AZURE_STORAGE_BEARER_TOKEN": "TEST_TOKEN_ONLY_" + "a" * 90,
            "AZURE_STORAGE_TOKEN_EXPIRES_ON": str(int(time.time()) + 3600),
        }
        receipt = self.run_once(env=config, ready_marker=None,
                                direct_readonly_source=True)
        self.assertEqual(receipt["status"], "BLOB_MANIFEST_COMMITTED")
        self.assertEqual(len(self.factories), 1)
        self.assertEqual(self.factories[0]["access_token"],
                         config["AZURE_STORAGE_BEARER_TOKEN"])
        self.assertEqual(self.factories[0]["expires_on"],
                         int(config["AZURE_STORAGE_TOKEN_EXPIRES_ON"]))
        self.assertNotIn("client_secret", self.factories[0])

    def test_token_mode_missing_secret_expiry_and_auth_conflict_are_closed(self):
        base = {
            "AZURE_AUTH_MODE": "temporary-access-token",
            "AZURE_BLOB_ACCOUNT_URL": CONFIG["AZURE_BLOB_ACCOUNT_URL"],
            "AZURE_BLOB_CONTAINER": "landing",
            "AZURE_STORAGE_BEARER_TOKEN": "TEST_TOKEN_ONLY_" + "a" * 90,
            "AZURE_STORAGE_TOKEN_EXPIRES_ON": str(int(time.time()) + 3600),
        }
        cases = [
            ({**base, "AZURE_STORAGE_BEARER_TOKEN": ""},
             "MISSING_TEMPORARY_AZURE_STORAGE_TOKEN"),
            ({**base, "AZURE_STORAGE_TOKEN_EXPIRES_ON": "not-a-time"},
             "INVALID_TEMPORARY_TOKEN_EXPIRY"),
            ({**base, "AZURE_CLIENT_SECRET": SECRET},
             "CONFLICTING_AZURE_AUTH_MODES"),
            ({**base, "AZURE_AUTH_MODE": "gibberish"},
             "UNSUPPORTED_AZURE_AUTH_MODE"),
            ({**CONFIG, "AZURE_STORAGE_BEARER_TOKEN": "malicious"},
             "CONFLICTING_AZURE_AUTH_MODES"),
        ]
        for variables, error in cases:
            with self.subTest(error=error):
                with self.assertRaisesRegex(PublisherRuntimeBlocked,error):
                    self.run_once(env=variables)
        self.assertEqual(self.factories, [])
        self.assertEqual(self.backend.writes, [])

    def test_temporary_token_template_requires_one_shot_secret(self):
        tpl = (ROOT / "kubernetes/manifests/synthea/blob-publisher/"
               "publish-direct-fhir-temporary-token-job.yaml.tpl").read_text()
        self.assertIn("namespace: dw-synthea", tpl)
        self.assertIn("activeDeadlineSeconds: 1200", tpl)
        self.assertIn("AZURE_AUTH_MODE", tpl)
        self.assertIn("temporary-access-token", tpl)
        self.assertIn("name: __SESSION_SECRET_NAME__", tpl)
        self.assertIn("key: access-token", tpl)
        self.assertIn("key: expires-on", tpl)
        self.assertIn("claimName: synthea-new-generator-state", tpl)
        self.assertIn("readOnly: true", tpl)
        self.assertIn("__PINNED_SOURCE_MANIFEST_SHA256__", tpl)
        self.assertNotIn("client-secret",tpl)
        self.assertNotIn("dw-az-blob",tpl)

    def test_job_template_mounts_existing_generator_pvc_readonly_same_namespace(self):
        template = (ROOT / "kubernetes/manifests/synthea/blob-publisher/"
                    "publish-direct-fhir-job.yaml.tpl").read_text()
        image = (ROOT / "images/azure-blob-publisher/Dockerfile").read_text()
        self.assertIn("namespace: dw-synthea", template)
        self.assertIn("automountServiceAccountToken: false", template)
        self.assertIn("readOnlyRootFilesystem: true", template)
        self.assertIn("name: generator-source\n          persistentVolumeClaim:", template)
        self.assertIn("claimName: synthea-new-generator-state", template)
        self.assertIn("readOnly: true", template)
        self.assertIn("direct-readonly-pvc", template)
        self.assertIn("name: azure-blob-publisher-identity", template)
        self.assertIn("__PUBLISHER_IMAGE_DIGEST__", template)
        self.assertNotIn("namespace: dw-az-blob", template)
        self.assertNotIn("name: staging", template)
        self.assertNotIn("hostPath:", template)
        self.assertNotIn(SECRET, template)
        self.assertIn("ARG BASE_IMAGE", image)
        self.assertIn("FROM ${BASE_IMAGE}", image)
        self.assertIn("USER 10001:10001", image)
        self.assertNotIn("COPY --from=synthea", image)


if __name__ == "__main__":
    unittest.main()
