"""Hosted-only V2 source ACK -> independently fetched HL7 -> immutable Blob CLI.

Uses real production JS to generate FHIR-based HL7 bytes, Fake OIE XML GET,
Fake Azure Blob and temporary frozen synthetic FHIR source. NO runtime writes.
"""
from __future__ import annotations

import copy
from contextlib import redirect_stderr
from io import StringIO
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT / "local-data-platform"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_oie_message_submit_v2 as sender_fixtures
import test_oie_hl7_publisher_v2 as bridge_fixtures
from apps.clinical_producers.oie.build_adt_events_v2_channel import CHANNEL_ID
from apps.clinical_producers.oie_message_submit_v2 import (
    main as sender_main,
)
from apps.clinical_producers.hl7_blob_runtime_v2 import (
    HL7V2RuntimeBlocked, publish_hl7_v2_from_new_receipts,
    main as publisher_main,
)
from apps.clinical_producers.azure_blob_publisher import PublishBlocked

RUN_ID = sender_fixtures.RUN_ID
REQUEST = sender_fixtures.REQUEST
ENV = {
    "AZURE_BLOB_ACCOUNT_URL": "https://synthetic.blob.core.windows.net",
    "AZURE_BLOB_CONTAINER": "landing",
    "AZURE_TENANT_ID": "test-tenant",
    "AZURE_CLIENT_ID": "test-client",
    "AZURE_CLIENT_SECRET": "secret-not-to-log",
}

NODE = r"""
const fs = require('fs');
const raw = JSON.parse(fs.readFileSync(process.argv[1],'utf8'));
const mini = {resourceType:'Bundle',type:'collection',
 entry:[raw.entry[0],raw.entry[1]]};
const mapper = require('./local-data-platform/apps/clinical_producers/oie/adt_events_v2.js').fhirToHl7AdtEventsV2;
const cfg = {hospital_id:'johns-creek-hospital-b',
 feed_id:'johns-creek-hospital-b-hl7-v2',request_id:process.argv[2],
 assigning_authority:'JOHNSCREEKB'};
process.stdout.write(JSON.stringify(mapper(mini,cfg)));
"""


class HL7V2RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.source = sender_fixtures.V2SenderTests()
        self.source.setUp()
        self.addCleanup(self.source.doCleanups)
        self.receipts = self.source.root / "new-oie-v2-receipts.json"
        self.good_receipt = self.source.submit(
            sender_fixtures.FakePoster(ids=("10001", "10002")))
        self.write_receipts(self.good_receipt)
        mapping = subprocess.run(
            ["node", "-e", NODE, str(self.source.fhir), REQUEST],
            cwd=ROOT, capture_output=True, text=True, check=True)
        messages = json.loads(mapping.stdout)["messages"]
        self.assertEqual([m["event_type"] for m in messages], ["A01", "A03"])
        self.client = bridge_fixtures.FakeOIE({
            f"/api/channels/{CHANNEL_ID}/messages/{10001+i}":
                bridge_fixtures.encode_oie(
                    message["hl7"].encode("utf-8"), str(10001+i))
            for i, message in enumerate(messages)
        })
        self.blob = bridge_fixtures.FakeBlob()
        self.factory_calls = []

    def write_receipts(self, document):
        self.receipts.write_text(json.dumps(document), encoding="utf-8")

    def factory(self, **kwargs):
        self.factory_calls.append(kwargs)
        return self.blob

    def publish(self, **overrides):
        options = {
            "receipt_path": self.receipts,
            "run_id": RUN_ID,
            "channel_id": CHANNEL_ID,
            "assigning_authority": "JOHNSCREEKB",
            "expected_source_manifest_sha256": self.source.source_sha,
            "landing_prefix": "healthcare/v2",
            "oie_client": self.client,
            "env": ENV,
            "backend_factory": self.factory,
        }
        options.update(overrides)
        return publish_hl7_v2_from_new_receipts(
            self.source.root, self.source.profile, REQUEST, **options)

    def test_both_events_published_to_shared_blob_once_manifest_last(self):
        first = self.publish()
        self.assertEqual(first["status"], "BLOB_MANIFEST_COMMITTED")
        self.assertEqual(len(first["objects"]), 2)
        self.assertEqual(len(self.client.paths), 2)
        self.assertEqual(len(self.blob.writes), 3)
        self.assertEqual(self.blob.writes[-1], first["manifest_key"])
        manifest = json.loads(self.blob.read(first["manifest_key"]).data)
        self.assertEqual(manifest["skipped_non_admissions"], 1)
        self.assertEqual(
            [x["name"] for x in manifest["objects"]],
            ["hl7/visit-one-A01.hl7", "hl7/visit-one-A03.hl7"])
        second = self.publish()
        self.assertEqual(second["manifest_create_status"], "ALREADY_MATCHING")
        self.assertEqual(len(self.blob.writes), 3)
        self.assertEqual(len(self.factory_calls), 2)

    def test_wrong_pin_old_channel_or_authority_reject_before_oie_get(self):
        for changes in (
            {"expected_source_manifest_sha256": "0" * 64},
            {"channel_id": sender_fixtures.LEGACY_CHANNEL},
            {"assigning_authority": "SOMEOTHERSOURCE"},
        ):
            with self.subTest(changes=changes), self.assertRaises(HL7V2RuntimeBlocked):
                self.publish(**changes)
            self.assertEqual(self.client.paths, [])
            self.assertEqual(self.factory_calls, [])

    def test_receipt_forgery_and_partial_event_set_hold_without_get_or_blob(self):
        for key, value in (
            ("run_id", "23456789012"),
            ("source_manifest_sha256", "0" * 64),
            ("channel_id", sender_fixtures.LEGACY_CHANNEL),
            ("event_count", 1),
            ("skipped_non_admissions", 0),
            ("messages", self.good_receipt["messages"][:1]),
            ("messages", [
                self.good_receipt["messages"][0],
                dict(self.good_receipt["messages"][1], message_id="10001")]),
        ):
            changed = copy.deepcopy(self.good_receipt)
            changed[key] = value
            self.write_receipts(changed)
            with self.subTest(key=key), self.assertRaises(HL7V2RuntimeBlocked):
                self.publish()
            self.assertEqual(self.client.paths, [])
            self.assertEqual(self.factory_calls, [])
        self.write_receipts(self.good_receipt)

    def test_bad_oie_persisted_bytes_hold_before_blob_identity_construction(self):
        fake = bridge_fixtures.FakeOIE(dict(self.client.payloads))
        fake.payloads[f"/api/channels/{CHANNEL_ID}/messages/10002"] = (
            bridge_fixtures.encode_oie(b"MSH|bad-hl7", "10002"))
        with self.assertRaisesRegex(HL7V2RuntimeBlocked, "SOURCE_OR_PERSISTED_GET_HOLD"):
            self.publish(oie_client=fake)
        self.assertEqual(self.factory_calls, [])
        self.assertEqual(self.blob.writes, [])

    def test_recheck_frozen_source_after_receipts_rejects_modification(self):
        self.source.fhir.write_bytes(self.source.fhir.read_bytes() + b" ")
        with self.assertRaises(HL7V2RuntimeBlocked):
            self.publish()
        self.assertEqual(self.client.paths, [])
        self.assertEqual(self.factory_calls, [])

    def test_no_azure_identity_or_temporary_token_fails_before_backend(self):
        for scope in (
            {}, dict(ENV, AZURE_STORAGE_BEARER_TOKEN="bad-token"),
            dict(ENV, AZURE_AUTH_MODE="temporary-access-token"),
        ):
            with self.subTest(scope=list(scope)), self.assertRaisesRegex(
                    HL7V2RuntimeBlocked, "SCOPED_AZURE_IDENTITY_REQUIRED"):
                self.publish(env=scope)
            self.assertEqual(self.factory_calls, [])
        self.assertEqual(self.blob.writes, [])

    def test_receipt_symlink_or_duplicate_json_keys_reject_without_get(self):
        self.receipts.write_text('{"schema_version":"a","schema_version":"b"}')
        with self.assertRaises(HL7V2RuntimeBlocked):
            self.publish()
        self.assertEqual(self.client.paths, [])
        self.receipts.unlink()
        self.receipts.symlink_to(self.source.fhir)
        with self.assertRaises(HL7V2RuntimeBlocked):
            self.publish()
        self.assertEqual(self.client.paths, [])

    def test_cli_entrypoints_deny_unapproved_or_missing_identities(self):
        args = [
            "--state-root", str(self.source.root),
            "--profile", str(self.source.profile),
            "--request-id", REQUEST, "--run-id", RUN_ID,
            "--channel-id", CHANNEL_ID,
            "--expected-source-manifest-sha256", self.source.source_sha,
        ]
        with redirect_stderr(StringIO()) as err:
            self.assertEqual(sender_main(args), 1)
        self.assertEqual(err.getvalue().strip(), "OIE_V2_POST_RESULT=HOLD_NO_RETRY")
        with redirect_stderr(StringIO()) as err:
            self.assertEqual(publisher_main(
                args + ["--receipts", str(self.receipts),
                        "--landing-prefix", "healthcare/v2",
                        "--assigning-authority", "JOHNSCREEKB"]), 1)
        self.assertEqual(
            err.getvalue().strip(), "OIE_V2_BLOB_PUBLISH_RESULT=BLOCKED_FAIL_CLOSED")

    def test_job_templates_preserve_legacy_and_bounded_identity_scope(self):
        base = ROOT / "local-data-platform/kubernetes/manifests/synthea/blob-publisher"
        for name, entry in (
            ("submit-oie-v2-new-fhir-events-job.yaml.tpl", "oie_message_submit_v2"),
            ("publish-oie-v2-hl7-job.yaml.tpl", "hl7_blob_runtime_v2"),
        ):
            content = (base / name).read_text()
            self.assertIn("apps.clinical_producers." + entry, content)
            self.assertIn("__VERIFIED_OIE_V2_CHANNEL_ID__", content)
            self.assertIn("backoffLimit: 0", content)
            self.assertIn("readOnly: true", content)
            self.assertIn("synthea-new-generator-state", content)
            self.assertIn("namespace: dw-synthea", content)
            self.assertIn("__PINNED_SOURCE_MANIFEST_SHA256__", content)
            self.assertNotIn("kubectl ", content)
        old = (base / "publish-oie-hl7-job.yaml.tpl").read_text()
        self.assertIn("apps.clinical_producers.hl7_blob_runtime", old)
        self.assertNotIn("hl7_blob_runtime_v2", old)


if __name__ == "__main__":
    unittest.main()
