"""Offline end-to-end NEW OIE receipt -> actual HL7 bytes -> immutable Blob tests.

This uses the existing Synthea frozen-source fixtures, real adapter validation
and fake OIE/Azure backends. It never contacts shared OIE or Azure endpoints.
"""
from contextlib import redirect_stderr
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import test_oie_hl7_publisher as fixtures
import test_oie_persisted_readback as oie_fixtures
from apps.clinical_producers.hl7_blob_runtime import (
    HL7RuntimeBlocked, RECEIPT_VERSION, load_new_request_receipts,
    publish_hl7_from_new_receipts, main,
)
from apps.clinical_producers.oie_persisted_readback import OIEReadbackBlocked

RUN_ID = "12345678901"
REQUEST = "johnscreek-hl7-gh-" + RUN_ID
CHANNEL = fixtures.CHANNEL
ENV = {
    "AZURE_BLOB_ACCOUNT_URL": "https://synthetic.blob.core.windows.net",
    "AZURE_BLOB_CONTAINER": "landing",
    "AZURE_TENANT_ID": "test-tenant",
    "AZURE_CLIENT_ID": "test-client",
    "AZURE_CLIENT_SECRET": "test-secret-not-for-logs",
}


class HL7BlobRuntimeTests(unittest.TestCase):
    def setUp(self):
        # The existing verified FHIR/HL7 fixture is adapted to a fresh run ID,
        # without changing mainline test contracts or weakening source checks.
        id_patch = patch.object(fixtures, "REQUEST", REQUEST)
        control_patch = patch.object(fixtures, "CONTROL", "-".join((
            fixtures.HOSP, fixtures.FEED, REQUEST, "enc-one", "A01")))
        id_patch.start()
        control_patch.start()
        self.addCleanup(control_patch.stop)
        self.addCleanup(id_patch.stop)
        self.source = fixtures.OIEAdapterTests()
        self.source.setUp()
        self.addCleanup(self.source.doCleanups)
        self.receipt = self.source.root / "new-oie-receipts.json"
        self.write_receipt()
        self.paths = []
        self.factory_calls = []
        self.backend = fixtures.FakeBackend()

    def write_receipt(self, **updates):
        obj = {
            "schema_version": RECEIPT_VERSION,
            "run_id": RUN_ID,
            "request_id": REQUEST,
            "hospital_id": fixtures.HOSP,
            "feed_id": fixtures.FEED,
            "source_manifest_sha256": fixtures.sha256(self.source.manifest),
            "channel_id": CHANNEL,
            "messages": [
                {"encounter_id": "enc-one", "message_id": "1001"},
                {"encounter_id": "enc-two", "message_id": "1002"},
            ],
        }
        obj.update(updates)
        self.receipt.write_text(json.dumps(obj), encoding="utf-8")

    def client(self):
        records = {
            f"/api/channels/{CHANNEL}/messages/1001":
                oie_fixtures.record(fixtures.sample_hl7()),
            f"/api/channels/{CHANNEL}/messages/1002":
                oie_fixtures.record(fixtures.SKIP_MARKER, msgid="1002"),
        }

        class FakeClient:
            def get(inner, path):
                self.paths.append(path)
                return records[path]
        return FakeClient()

    def factory(self, **options):
        self.factory_calls.append(options)
        return self.backend

    def run_publish(self, **overrides):
        params = {
            "receipt_path": self.receipt,
            "run_id": RUN_ID,
            "channel_id": CHANNEL,
            "assigning_authority": fixtures.AUTH,
            "expected_source_manifest_sha256": fixtures.sha256(self.source.manifest),
            "landing_prefix": "clinical/v1",
            "oie_client": self.client(),
            "env": ENV,
            "backend_factory": self.factory,
        }
        params.update(overrides)
        return publish_hl7_from_new_receipts(
            self.source.root, self.source.profile, REQUEST, **params)

    def test_verified_oie_bytes_and_immutable_manifest_last_retry(self):
        first = self.run_publish()
        self.assertEqual(first["status"], "BLOB_MANIFEST_COMMITTED")
        self.assertEqual(len(first["objects"]), 1)
        self.assertEqual(len(self.backend.writes), 2)
        self.assertEqual(self.backend.writes[-1], first["manifest_key"])
        self.assertEqual(first["objects"][0]["sha256"],
                         fixtures.hashlib.sha256(fixtures.sample_hl7()).hexdigest())
        self.assertEqual(self.backend.remote[first["objects"][0]["blob_key"]].data,
                         fixtures.sample_hl7())
        second = self.run_publish()
        self.assertEqual(second["manifest_create_status"], "ALREADY_MATCHING")
        self.assertEqual(len(self.backend.writes), 2)
        self.assertEqual(len(self.paths), 4)
        self.assertEqual(len(self.factory_calls), 2)

    def test_wrong_source_pin_rejects_before_oie_or_azure(self):
        with self.assertRaisesRegex(HL7RuntimeBlocked, "PINNED_SOURCE"):
            self.run_publish(expected_source_manifest_sha256="a" * 64)
        self.assertEqual(self.paths, [])
        self.assertEqual(self.factory_calls, [])

    def test_cross_run_or_wrong_source_receipts_rejected_pre_io(self):
        for updates in (
            {"run_id": "98765432109"},
            {"hospital_id": "atlanta-hospital-a"},
            {"source_manifest_sha256": "b" * 64},
            {"channel_id": "00000000-0000-4000-8000-000000000000"},
            {"messages": [{"encounter_id": "enc-one", "message_id": "1001"}]},
            {"messages": [
                {"encounter_id": "enc-one", "message_id": "1001"},
                {"encounter_id": "enc-two", "message_id": "1001"}]},
        ):
            with self.subTest(updates=updates):
                self.write_receipt(**updates)
                with self.assertRaises(HL7RuntimeBlocked):
                    self.run_publish()
                self.assertEqual(self.paths, [])
                self.assertEqual(self.factory_calls, [])
        self.write_receipt()

    def test_symlink_duplicate_keys_and_invalid_run_hold(self):
        duplicate = '{"schema_version":"a","schema_version":"b"}'
        self.receipt.write_text(duplicate)
        with self.assertRaises(HL7RuntimeBlocked):
            self.run_publish()
        self.write_receipt()
        unsafe = self.source.root / "receipt-link.json"
        unsafe.symlink_to(self.receipt)
        with self.assertRaises(HL7RuntimeBlocked):
            self.run_publish(receipt_path=unsafe)
        with self.assertRaises(HL7RuntimeBlocked):
            self.run_publish(run_id="99999999999")
        self.assertEqual(self.paths, [])
        self.assertEqual(self.factory_calls, [])

    def test_missing_and_corrupt_oie_message_never_write_azure(self):
        with self.assertRaises(OIEReadbackBlocked):
            self.run_publish(oie_client=type("BadClient", (), {
                "get": lambda self, path: b"<message/>"})())
        self.assertEqual(self.factory_calls, [])
        self.assertEqual(self.backend.writes, [])

    def test_missing_azure_identity_after_oie_validation_still_no_write(self):
        with self.assertRaisesRegex(HL7RuntimeBlocked, "SCOPED_AZURE"):
            self.run_publish(env={})
        self.assertEqual(len(self.paths), 2)
        self.assertEqual(self.factory_calls, [])

    def test_skip_only_never_creates_manifest(self):
        doc = json.loads(self.source.fhir.read_text())
        doc["entry"][1]["resource"]["class"]["code"] = "AMB"
        self.source.fhir.write_text(json.dumps(doc), encoding="utf-8")
        req = json.loads((self.source.folder / "request.json").read_text())["request"]
        self.source.manifest.write_text(json.dumps({
            "schema_version": fixtures.MANIFEST_VERSION,
            "request_id": REQUEST,
            "request_sha256": fixtures.fingerprint(req),
            "status": fixtures.COMPLETED,
            **fixtures.validate_payload(self.source.folder / "payload", req),
        }), encoding="utf-8")
        self.write_receipt()
        class BothSkip:
            def get(inner, path):
                msg = path.rsplit("/", 1)[-1]
                return oie_fixtures.record(fixtures.SKIP_MARKER, msgid=msg)
        with self.assertRaisesRegex(fixtures.OIEDeliveryBlocked,
                                    "NO_OIE_ADT_A01_TO_PUBLISH"):
            self.run_publish(oie_client=BothSkip())
        self.assertEqual(self.factory_calls, [])

    def test_cli_failure_message_cannot_disclose_secrets(self):
        err = StringIO()
        with redirect_stderr(err):
            code = main(["--state-root", str(self.source.root),
                         "--profile", str(self.source.profile),
                         "--request-id", REQUEST, "--receipts", str(self.receipt),
                         "--run-id", RUN_ID, "--channel-id", CHANNEL,
                         "--assigning-authority", fixtures.AUTH,
                         "--expected-source-manifest-sha256", "f" * 64,
                         "--landing-prefix", "clinical/v1"])
        self.assertEqual(code, 1)
        self.assertEqual(err.getvalue().strip(),
                         "HL7_BLOB_PUBLISH_RESULT=BLOCKED_FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main()
