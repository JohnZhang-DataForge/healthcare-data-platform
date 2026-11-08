"""Synthetic-only contract and adverse tests for scoped Azure HL7 GET adapter.

No Azure SDK credentials, network, Blob uploads, OIE operations or live PHI.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from dataclasses import replace

ROOT = Path(__file__).resolve().parents[5]
sys.path[:0] = [
    str(ROOT / "local-data-platform/spark/apps/hl7"),
    str(ROOT / ".github/quality/fixtures/hl7"),
]
from generate_oie_v2_sample import generate, REQUEST, SOURCE_SHA
from azure_blob_readback import (
    AzureGetOnly, Snapshot, _metadata, _sha,
    _validate_cloud, stage_exact_readback,
)
from landing_intake import FEED, HOSPITAL, ROOT_PREFIX, verified_seed_rows


class FakeExactGet:
    def __init__(self, snapshots):
        self.snapshots = snapshots
        self.calls = []
        self.second_manifest = None

    def read(self, key):
        self.calls.append(key)
        if key.endswith("/landing-manifest.json") and self.calls.count(key) == 2:
            if self.second_manifest is not None:
                return self.second_manifest
        return self.snapshots[key]


class ScopedAzureReadbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        manifest, blobs, sha = generate(self.work / "fixture")
        self.manifest = json.loads(manifest.read_bytes())
        self.manifest_key = f"{ROOT_PREFIX}/{REQUEST}/landing-manifest.json"
        self.docs = {}
        raw = manifest.read_bytes()
        self.docs[self.manifest_key] = Snapshot(
            raw, _metadata(sha, len(raw), REQUEST, SOURCE_SHA, kind="manifest"),
            "application/json", '"manifest-synthetic-etag"', None)
        for obj in self.manifest["objects"]:
            key = obj["blob_key"]
            payload = (blobs / key).read_bytes()
            self.docs[key] = Snapshot(
                payload,
                _metadata(obj["sha256"], obj["size_bytes"],
                          REQUEST, SOURCE_SHA, kind="data",
                          source_event_id=obj["source_event_id"]),
                "application/hl7-v2", obj["etag"], obj["version_id"])
        self.reader = FakeExactGet(self.docs)
        self.args = dict(
            request_id=REQUEST, manifest_key=self.manifest_key,
            manifest_sha256=sha, source_sha256=SOURCE_SHA,
            expected_objects=2, output_root=self.work / "verified-readback",
            ingest_date="2026-11-07", processing_run_id="scoped-get-001",
            processed_at="2026-11-07 13:00:00")

    def stage(self):
        return stage_exact_readback(self.reader, **self.args)

    def rewrite_manifest(self, obj):
        raw = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
        sha = hashlib.sha256(raw).hexdigest()
        self.docs[self.manifest_key] = replace(
            self.docs[self.manifest_key], data=raw,
            metadata=_metadata(sha, len(raw), REQUEST, SOURCE_SHA, kind="manifest"))
        self.args["manifest_sha256"] = sha

    def assert_hold(self, phrase):
        with self.assertRaisesRegex(ValueError, phrase):
            self.stage()
        self.assertFalse(self.args["output_root"].exists())

    def test_exact_get_manifest_first_and_last_and_local_clinical_contract(self):
        state = self.stage()
        self.assertEqual(state["status"], "EXACT_GET_LOCAL_STAGED")
        self.assertEqual(state["objects"], 2)
        keys = [o["blob_key"] for o in self.manifest["objects"]]
        self.assertEqual(self.reader.calls, [self.manifest_key, *keys, self.manifest_key])
        dst = self.args["output_root"]
        actual = verified_seed_rows(
            (dst / "landing-manifest.json").read_bytes(),
            dst / "staged-local-blob-keys",
            manifest_sha256=self.args["manifest_sha256"],
            source_sha256=SOURCE_SHA, request_id=REQUEST,
            ingest_date=self.args["ingest_date"],
            processing_run_id=self.args["processing_run_id"],
            processed_at=self.args["processed_at"])
        self.assertEqual([x["event_type"] for x in actual], ["A01", "A03"])
        self.assertEqual({x["race_code"] for x in actual}, {"2028-9"})
        self.assertEqual({x["ethnicity_code"] for x in actual}, {"2135-2"})

    def test_exact_replay_skips_without_new_cloud_get(self):
        self.stage()
        before = len(self.reader.calls)
        self.assertEqual(self.stage()["status"], "ALREADY_MATCHING_LOCAL_REPLAY_SKIP")
        self.assertEqual(len(self.reader.calls), before)

    def test_changed_staged_file_holds_without_replacing_it(self):
        self.stage()
        path = self.args["output_root"] / "staged-local-blob-keys" / self.manifest["objects"][0]["blob_key"]
        path.write_bytes(path.read_bytes() + b"mutation")
        with self.assertRaisesRegex(ValueError, "LOCAL_REPLAY_HOLD"):
            self.stage()
        self.assertTrue(path.read_bytes().endswith(b"mutation"))

    def test_wrong_expected_count_blocks_before_object_get(self):
        self.args["expected_objects"] = 42
        self.assert_hold("EXACT_OBJECT_COUNT_HOLD")
        self.assertEqual(self.reader.calls, [self.manifest_key])

    def test_unpinned_manifest_key_rejected_without_network(self):
        self.args["manifest_key"] += ".evil"
        self.assert_hold("OUT_OF_BAND_SOURCE_PIN_REQUIRED")
        self.assertFalse(self.reader.calls)

    def test_wrong_manifest_sha_rejects_before_any_event_get(self):
        self.args["manifest_sha256"] = "0" * 64
        self.assert_hold("REMOTE_BYTES_OR_PROVENANCE_HOLD")
        self.assertEqual(self.reader.calls, [self.manifest_key])

    def test_foreign_key_rejected_before_object_get(self):
        doc = json.loads(json.dumps(self.manifest))
        doc["objects"][0]["blob_key"] = "foreign/data.hl7"
        self.rewrite_manifest(doc)
        self.assert_hold("FOREIGN_OR_DUPLICATE_OBJECT_HOLD")
        self.assertEqual(self.reader.calls, [self.manifest_key])

    def test_missing_object_bytes_blocks_without_publishing(self):
        key = self.manifest["objects"][0]["blob_key"]
        self.docs[key] = replace(self.docs[key], data=self.docs[key].data + b"tamper")
        self.assert_hold("REMOTE_BYTES_OR_PROVENANCE_HOLD")
        self.assertEqual(len(self.reader.calls), 2)

    def test_changed_etag_or_version_id_blocks(self):
        key = self.manifest["objects"][0]["blob_key"]
        for change in ({"etag": '"changed"'}, {"version_id": "another-version"}):
            with self.subTest(change=change):
                reader = FakeExactGet(dict(self.docs))
                reader.snapshots[key] = replace(reader.snapshots[key], **change)
                with self.assertRaisesRegex(ValueError, "REMOTE_BYTES_OR_PROVENANCE_HOLD"):
                    stage_exact_readback(reader, **self.args)
                self.assertFalse(self.args["output_root"].exists())

    def test_changed_remote_metadata_or_content_type_blocks(self):
        key = self.manifest["objects"][0]["blob_key"]
        for change in ({"metadata": {"kind": "forged"}},
                       {"content_type": "text/plain"}):
            with self.subTest(change=change):
                reader = FakeExactGet(dict(self.docs))
                reader.snapshots[key] = replace(reader.snapshots[key], **change)
                with self.assertRaisesRegex(ValueError, "REMOTE_BYTES_OR_PROVENANCE_HOLD"):
                    stage_exact_readback(reader, **self.args)
                self.assertFalse(self.args["output_root"].exists())

    def test_changed_remote_manifest_after_object_reads_holds(self):
        self.reader.second_manifest = replace(
            self.docs[self.manifest_key], etag='"changed"')
        self.assert_hold("REMOTE_BYTES_OR_PROVENANCE_HOLD")
        self.assertEqual(len(self.reader.calls), 4)

    def test_symlink_output_parent_rejected_before_network(self):
        link = self.work / "symlink-parent"
        link.symlink_to(self.work / "fixture", target_is_directory=True)
        self.args["output_root"] = link / "sink"
        self.assert_hold("OUTPUT_PARENT_HOLD")
        self.assertFalse(self.reader.calls)

    def test_processing_metadata_rejected_before_any_remote_get(self):
        self.args["processed_at"] = "not-a-timestamp"
        self.assert_hold("PROCESSING_METADATA_HOLD")
        self.assertFalse(self.reader.calls)

    def test_public_writable_staging_parent_rejected_before_get(self):
        public = self.work / "world-readable"
        public.mkdir(mode=0o755)
        public.chmod(0o755)
        self.args["output_root"] = public / "staged"
        self.assert_hold("OUTPUT_PARENT_NOT_PRIVATE_HOLD")
        self.assertFalse(self.reader.calls)

    def test_cloud_account_allowlist_rejects_sas_and_unsafe_hosts(self):
        _validate_cloud("https://trusted123.blob.core.windows.net", "landing-test")
        for account in (
            "http://trusted123.blob.core.windows.net",
            "https://trusted123.blob.core.windows.net/?sig=secret",
            "https://trusted123.blob.core.windows.net.evil.example",
            "https://localhost", "https://trusted123.blob.core.windows.net:443",
        ):
            with self.subTest(account=account), self.assertRaises(ValueError):
                _validate_cloud(account, "landing-test")

    def test_no_sdk_dependency_in_offline_reader_or_nonread_methods(self):
        self.assertFalse(hasattr(self.reader, "list_blobs"))
        self.assertFalse(hasattr(self.reader, "upload_blob"))
        self.assertFalse(hasattr(self.reader, "delete_blob"))
        with self.assertRaisesRegex(ValueError, "SCOPED_AZURE_IDENTITY_REQUIRED"):
            AzureGetOnly.from_env({
                "AZURE_BLOB_ACCOUNT_URL": "https://trusted123.blob.core.windows.net",
                "AZURE_BLOB_CONTAINER": "landing-test",
            })


if __name__ == "__main__":
    unittest.main()
