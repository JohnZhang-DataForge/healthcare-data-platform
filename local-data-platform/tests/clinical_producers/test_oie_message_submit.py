"""Offline new Johns Creek FHIR->scoped OIE POST receipts and fail-closed tests."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import test_oie_hl7_publisher as fixtures
from apps.clinical_producers.oie_message_submit import (
    OIEPostBlocked, ScopedOIEPoster, prepare_new_fhir_events,
    submit_new_fhir_request, RECEIPT_VERSION,
)

RUN_ID = "12345678901"
REQUEST = "johnscreek-hl7-gh-" + RUN_ID
CHANNEL = fixtures.CHANNEL
MANIFEST = None


class FakePoster:
    def __init__(self, fail_at=None, ids=("20001", "20002")):
        self.sent = []
        self.fail_at = fail_at
        self.ids = ids

    def submit(self, channel_id, event):
        self.sent.append((channel_id, json.loads(event)))
        if self.fail_at == len(self.sent):
            raise TimeoutError("UNSAFE_CREDENTIAL_OR_FHIR_IN_EXCEPTION")
        return self.ids[len(self.sent) - 1]


class OIEMessageSubmitTests(unittest.TestCase):
    def setUp(self):
        id_patch = patch.object(fixtures, "REQUEST", REQUEST)
        ctrl_patch = patch.object(fixtures, "CONTROL", "-".join((
            fixtures.HOSP, fixtures.FEED, REQUEST, "enc-one", "A01")))
        id_patch.start()
        ctrl_patch.start()
        self.addCleanup(ctrl_patch.stop)
        self.addCleanup(id_patch.stop)
        self.source = fixtures.OIEAdapterTests()
        self.source.setUp()
        self.addCleanup(self.source.doCleanups)
        self.manifest_sha = fixtures.sha256(self.source.manifest)

    def submit(self, poster=None, **kwargs):
        options = {"run_id": RUN_ID, "channel_id": CHANNEL,
                   "expected_source_manifest_sha256": self.manifest_sha,
                   "poster": poster or FakePoster()}
        options.update(kwargs)
        return submit_new_fhir_request(
            self.source.root, self.source.profile, REQUEST, **options)

    def test_two_new_fhir_encounters_produce_exact_unique_post_receipts(self):
        poster = FakePoster()
        doc = self.submit(poster)
        self.assertEqual(doc["schema_version"], RECEIPT_VERSION)
        self.assertEqual(doc["run_id"], RUN_ID)
        self.assertEqual(doc["request_id"], REQUEST)
        self.assertEqual(doc["hospital_id"], fixtures.HOSP)
        self.assertEqual(doc["feed_id"], fixtures.FEED)
        self.assertEqual(doc["source_manifest_sha256"], self.manifest_sha)
        self.assertEqual(doc["channel_id"], CHANNEL)
        self.assertEqual(doc["messages"], [
            {"encounter_id": "enc-one", "message_id": "20001"},
            {"encounter_id": "enc-two", "message_id": "20002"}])
        self.assertEqual(len(poster.sent), 2)
        self.assertEqual([e["bundle"]["entry"][1]["resource"]["id"]
                          for _, e in poster.sent], ["enc-one", "enc-two"])
        self.assertTrue(all(c == CHANNEL for c, _ in poster.sent))
        self.assertTrue(all(e["request_id"] == REQUEST for _, e in poster.sent))
        self.assertFalse(any("rawPatientName" in str(e) for _, e in poster.sent))

    def test_wrong_run_pin_profile_channel_rejected_before_post(self):
        for changes in (
            {"run_id": "98765432109"},
            {"expected_source_manifest_sha256": "0" * 64},
            {"channel_id": "not-a-uuid"},
            {"run_id": "ci-source"},
        ):
            with self.subTest(changes=changes):
                poster = FakePoster()
                with self.assertRaises(OIEPostBlocked):
                    self.submit(poster, **changes)
                self.assertEqual(poster.sent, [])

    def test_tamper_frozen_fhir_blocks_before_any_post(self):
        raw = self.source.fhir.read_bytes()
        self.source.fhir.write_bytes(raw + b" ")
        poster = FakePoster()
        with self.assertRaises(OIEPostBlocked):
            self.submit(poster)
        self.assertEqual(poster.sent, [])

    def test_bad_source_count_blocks_before_any_post(self):
        # Manifest itself must remain valid; no caller may ignore a partial
        # event list or bypass frozen source handoff.
        with patch("apps.clinical_producers.oie_message_submit.events_from_bundle",
                   return_value=[]):
            poster = FakePoster()
            with self.assertRaisesRegex(OIEPostBlocked, "FHIR_ENCOUNTER_COUNT_INVALID"):
                self.submit(poster)
            self.assertEqual(poster.sent, [])

    def test_post_timeout_holds_without_retry_or_complete_receipt(self):
        poster = FakePoster(fail_at=2)
        with self.assertRaisesRegex(OIEPostBlocked,
                                    "OIE_POST_OUTCOME_UNKNOWN_HOLD_NO_RETRY") as ctx:
            self.submit(poster)
        self.assertEqual(len(poster.sent), 2)
        self.assertNotIn("UNSAFE_CREDENTIAL", str(ctx.exception))

    def test_duplicate_or_missing_ack_holds_no_retry(self):
        for ids in (("20001", "20001"), ("20001", "garbage")):
            poster = FakePoster(ids=ids)
            with self.assertRaisesRegex(OIEPostBlocked,
                                        "OIE_POST_RECEIPT_INVALID_HOLD_NO_RETRY"):
                self.submit(poster)
            self.assertEqual(len(poster.sent), 2)

    def test_scoped_http_post_is_only_to_exact_oie_channel_and_no_retry(self):
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, size): return b"<long>20001</long>"
        class Opener:
            def __init__(self): self.calls = []
            def open(self, req, timeout):
                self.calls.append(req)
                return Response()
        poster = object.__new__(ScopedOIEPoster)
        fake = Opener()
        poster._opener = fake
        message_id = poster.submit(CHANNEL, b'{"request_id":"synthetic-test"}')
        self.assertEqual(message_id, "20001")
        self.assertEqual(len(fake.calls), 1)
        request = fake.calls[0]
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.full_url,
            "https://oie-debug.dw-oie.svc.cluster.local:8443/api/channels/"
            + CHANNEL + "/messages")
        for cid, raw in (("bad", b"test"), (CHANNEL, b""), (CHANNEL, b"x" * 131073)):
            with self.assertRaises(OIEPostBlocked):
                poster.submit(cid, raw)
        self.assertEqual(len(fake.calls), 1)

    def test_ambiguous_post_network_result_does_not_expose_body(self):
        class BrokenOpener:
            def open(self, req, timeout):
                raise RuntimeError("URI_USER_SECRET_IN_EXCEPTION")
        poster = object.__new__(ScopedOIEPoster)
        poster._opener = BrokenOpener()
        with self.assertRaisesRegex(OIEPostBlocked,
                                    "OIE_POST_OUTCOME_UNKNOWN_HOLD_NO_RETRY") as ctx:
            poster.submit(CHANNEL, b'{"Patient":"hidden"}')
        self.assertNotIn("URI_USER_SECRET", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
