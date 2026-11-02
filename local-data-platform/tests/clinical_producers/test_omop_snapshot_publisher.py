"""Pure offline OMOP snapshot publisher/runtime fault tests. No live PG/K8s/Azure."""
from pathlib import Path
import json
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from apps.clinical_producers.azure_blob_publisher import (
    BlobAlreadyExists, BlobNotFound, BlobSnapshot, PublishBlocked,
)
from apps.clinical_producers.omop_snapshot_publisher import (
    BLOB_PREFIX, publish_omop_dump,
)
from apps.clinical_producers.omop_snapshot_runtime import (
    publish_from_stage, read_staged_dump, backend_from_env,
)

DUMP = b"PGDMP" + b"synthetic-cdm-dump-bytes"
SID = "omop-20261102-offline-a"
ROOT = f"{BLOB_PREFIX}/{SID}"
AZURE_SCOPE = {
    "AZURE_BLOB_ACCOUNT_URL": "https://example.blob.core.windows.net",
    "AZURE_BLOB_CONTAINER": "landing",
    "AZURE_TENANT_ID": "stub-tenant",
    "AZURE_CLIENT_ID": "stub-client",
    "AZURE_CLIENT_SECRET": "stub-secret",
}


class FakeBackend:
    def __init__(self):
        self.items = {}
        self.created = []
        self.block_create = None
        self.block_read = None

    def create(self, key, data, metadata, content_type):
        if key == self.block_create:
            raise RuntimeError("PRIVATE_AZURE_ERROR")
        if key in self.items:
            raise BlobAlreadyExists()
        etag = f"etag-{len(self.items) + 1}"
        self.items[key] = BlobSnapshot(data, dict(metadata), content_type, etag)
        self.created.append(key)
        return etag

    def read(self, key):
        if key == self.block_read:
            raise RuntimeError("PRIVATE_AZURE_ERROR")
        if key not in self.items:
            raise BlobNotFound()
        return self.items[key]


class OmopSnapshotTests(unittest.TestCase):
    def test_commits_dump_then_manifest_and_retries_identically(self):
        backend = FakeBackend()
        first = publish_omop_dump(SID, DUMP, backend=backend)
        self.assertEqual(first["status"], "OMOP_SNAPSHOT_MANIFEST_COMMITTED")
        self.assertEqual(backend.created, [
            ROOT + "/omop-cdm.dump", ROOT + "/snapshot-manifest.json"])
        manifest = json.loads(backend.items[backend.created[-1]].data)
        self.assertEqual(manifest["postgres_schema"], "cdm")
        self.assertEqual(manifest["objects"][0]["size_bytes"], len(DUMP))
        second = publish_omop_dump(SID, DUMP, backend=backend)
        self.assertEqual(second["object_create_status"], "ALREADY_MATCHING")
        self.assertEqual(second["manifest_create_status"], "ALREADY_MATCHING")
        self.assertEqual(len(backend.created), 2)

    def test_invalid_sources_do_not_touch_backend(self):
        for sid, data, prefix in [
            ("../other", DUMP, BLOB_PREFIX),
            (SID, b"not-pg-custom", BLOB_PREFIX),
            (SID, b"", BLOB_PREFIX),
            (SID, DUMP, "landing"),
            (SID, DUMP, "omop/../landing"),
        ]:
            with self.subTest(sid=sid, prefix=prefix):
                backend = FakeBackend()
                with self.assertRaises(PublishBlocked):
                    publish_omop_dump(sid, data, backend=backend, prefix=prefix)
                self.assertEqual(backend.created, [])

    def test_existing_committed_snapshot_conflict_before_any_new_write(self):
        backend = FakeBackend()
        publish_omop_dump(SID, DUMP, backend=backend)
        with self.assertRaisesRegex(PublishBlocked, "IMMUTABLE_SNAPSHOT_CONFLICT"):
            publish_omop_dump(SID, DUMP + b"changed", backend=backend)
        self.assertEqual(len(backend.created), 2)

    def test_preexisting_different_data_does_not_overwrite_or_commit(self):
        backend = FakeBackend()
        backend.items[ROOT + "/omop-cdm.dump"] = BlobSnapshot(
            DUMP + b"other", {}, "application/octet-stream", "etag-old")
        with self.assertRaises(PublishBlocked):
            publish_omop_dump(SID, DUMP, backend=backend)
        self.assertNotIn(ROOT + "/snapshot-manifest.json", backend.items)

    def test_remote_modified_metadata_is_blocked(self):
        backend = FakeBackend()
        publish_omop_dump(SID, DUMP, backend=backend)
        key = ROOT + "/omop-cdm.dump"
        old = backend.items[key]
        backend.items[key] = BlobSnapshot(
            old.data, {"tampered": "yes"}, old.content_type, old.etag)
        with self.assertRaises(PublishBlocked):
            publish_omop_dump(SID, DUMP, backend=backend)

    def test_manifest_get_failure_fails_closed(self):
        backend = FakeBackend()
        backend.block_read = ROOT + "/snapshot-manifest.json"
        with self.assertRaisesRegex(PublishBlocked, "PREFLIGHT_FAILED"):
            publish_omop_dump(SID, DUMP, backend=backend)
        self.assertEqual(backend.created, [])

    def test_partial_publish_can_resume_with_identical_bytes(self):
        backend = FakeBackend()
        backend.block_create = ROOT + "/snapshot-manifest.json"
        with self.assertRaises(PublishBlocked):
            publish_omop_dump(SID, DUMP, backend=backend)
        self.assertEqual(backend.created, [ROOT + "/omop-cdm.dump"])
        backend.block_create = None
        result = publish_omop_dump(SID, DUMP, backend=backend)
        self.assertEqual(result["object_create_status"], "ALREADY_MATCHING")
        self.assertEqual(result["manifest_create_status"], "CREATED")

    def test_staged_file_and_scope_before_azure_factory(self):
        backend = FakeBackend()
        called = []
        def factory(**kwargs):
            called.append(kwargs)
            return backend
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "omop-cdm.dump"
            path.write_bytes(DUMP)
            receipt = publish_from_stage(
                path, SID, env=AZURE_SCOPE, backend_factory=factory)
            self.assertEqual(receipt["status"], "OMOP_SNAPSHOT_MANIFEST_COMMITTED")
            self.assertEqual(len(called), 1)
            bad = Path(temp) / "bad.dump"
            bad.write_bytes(b"bad bytes")
            with self.assertRaises(PublishBlocked):
                publish_from_stage(
                    bad, SID, env=AZURE_SCOPE, backend_factory=factory)
            self.assertEqual(len(called), 1)
            link = Path(temp) / "link.dump"
            link.symlink_to(path)
            with self.assertRaises(PublishBlocked):
                read_staged_dump(link)

    def test_credential_modes_are_strictly_fenced(self):
        with self.assertRaises(PublishBlocked):
            backend_from_env({})
        with self.assertRaisesRegex(PublishBlocked, "CONFLICTING"):
            backend_from_env({**AZURE_SCOPE, "AZURE_STORAGE_BEARER_TOKEN": "secret"})
        with self.assertRaisesRegex(PublishBlocked, "UNSUPPORTED"):
            backend_from_env({**AZURE_SCOPE, "AZURE_AUTH_MODE": "default-credential"})
        with self.assertRaisesRegex(PublishBlocked, "CONFLICTING"):
            backend_from_env({**AZURE_SCOPE, "AZURE_AUTH_MODE": "temporary-access-token",
                              "AZURE_STORAGE_BEARER_TOKEN": "fake",
                              "AZURE_STORAGE_TOKEN_EXPIRES_ON": "1799999999"})

    def test_job_template_is_readonly_and_scoped_to_dw_synthea(self):
        file = (Path(__file__).resolve().parents[2] /
                "kubernetes/manifests/synthea/blob-publisher/publish-omop-snapshot-job.yaml.tpl")
        raw = file.read_text()
        self.assertIn("namespace: dw-synthea", raw)
        self.assertIn("--schema=cdm", raw)
        self.assertIn("--format=custom", raw)
        self.assertIn("default_transaction_read_only=on", raw)
        self.assertIn("omop-snapshot-reader", raw)
        self.assertIn("azure-blob-publisher-identity", raw)
        self.assertIn("emptyDir:", raw)
        self.assertIn("readOnly: true", raw)
        self.assertNotIn("claimName:", raw)
        self.assertNotIn("overwrite=True", raw)


if __name__ == "__main__":
    unittest.main()
