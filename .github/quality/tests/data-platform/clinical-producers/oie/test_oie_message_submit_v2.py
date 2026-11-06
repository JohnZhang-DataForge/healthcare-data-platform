"""Offline V2 one-shot sender tests; fake POST only, no OIE/K8s/Azure."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT / "local-data-platform"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_oie_hl7_publisher_v2 import patient, encounter
from apps.clinical_producers.oie.build_adt_events_v2_channel import (
    CHANNEL_ID, render_channel_v2,
)
from apps.clinical_producers.oie.build_channel import render_channel as legacy_channel_xml
from apps.clinical_producers.oie_message_submit import OIEPostBlocked
from apps.clinical_producers.oie_message_submit_v2 import (
    AUTHORITY, VERSION, ScopedOIEV2Poster,
    prepare_v2_new_events, submit_v2_new_request, verified_v2_post_receipts,
    verify_v2_receipts_against_frozen_source,
)
from apps.clinical_producers.source_handoff import verify_handoff
from apps.synthea.synthea_new_generator.generator import (
    COMPLETED, MANIFEST_VERSION, sha256, validate_payload,
)
from apps.synthea.synthea_new_generator.request import (
    SCHEMA_VERSION, fingerprint, normalize,
)

RUN_ID = "12345678901"
REQUEST = "johnscreek-hl7-gh-" + RUN_ID
LEGACY_CHANNEL = "69ace705-a675-45f6-b126-a3b22a65212a"


class FakePoster:
    def __init__(self, ids=("10001", "10002"), fail_at=None, fail_preflight=False):
        self.ids = list(ids)
        self.fail_at = fail_at
        self.fail_preflight = fail_preflight
        self.sent = []
        self.preflights = []

    def preflight_channel(self, channel_id):
        self.preflights.append(channel_id)
        if self.fail_preflight:
            raise RuntimeError("SECRET_SHOULD_NOT_LEAK")

    def submit(self, channel_id, raw):
        self.sent.append((channel_id, json.loads(raw)))
        if self.fail_at == len(self.sent):
            raise TimeoutError("SECRET_SHOULD_NOT_LEAK")
        return self.ids[len(self.sent) - 1]


class V2SenderTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.profile = ROOT / "local-data-platform/config/synthea-new-generator/johns-creek-hl7.json"
        self.req = normalize({
            "schema_version": SCHEMA_VERSION, "request_id": REQUEST,
            "generation_mode": "NEW_ONLY", "population": 1,
            "state": "Georgia", "city": "Johns Creek", "seed": 67890,
            "reference_date": "20261024", "output_formats": ["FHIR_R4"],
        })
        self.folder = self.root / "requests" / REQUEST
        self.fhir = self.folder / "payload" / "fhir" / "source.json"
        self.fhir.parent.mkdir(parents=True)
        (self.folder / "request.json").write_text(json.dumps({
            "request": self.req, "request_sha256": fingerprint(self.req),
        }))
        self.bundle = {
            "resourceType": "Bundle", "type": "collection",
            "entry": [
                {"resource": patient()},
                {"resource": encounter("visit-one")},
                {"resource": encounter("visit-two", code="AMB")},
            ],
        }
        self.freeze()

    def freeze(self):
        self.fhir.write_text(json.dumps(self.bundle), encoding="utf-8")
        actual = validate_payload(self.folder / "payload", self.req)
        self.manifest = self.folder / "generation-manifest.json"
        self.manifest.write_text(json.dumps({
            "schema_version": MANIFEST_VERSION, "request_id": REQUEST,
            "request_sha256": fingerprint(self.req), "status": COMPLETED,
            **actual,
        }), encoding="utf-8")
        self.source_sha = sha256(self.manifest)

    def prepare(self, **kw):
        args = {"run_id": RUN_ID, "expected_source_manifest_sha256": self.source_sha}
        args.update(kw)
        return prepare_v2_new_events(self.root, self.profile, REQUEST, **args)

    def submit(self, poster=None, **kw):
        args = {
            "run_id": RUN_ID, "channel_id": CHANNEL_ID,
            "expected_source_manifest_sha256": self.source_sha,
            "poster": poster or FakePoster(),
        }
        args.update(kw)
        return submit_v2_new_request(self.root, self.profile, REQUEST, **args)

    def test_event_plan_uses_frozen_manifest_and_two_distinct_event_envelopes(self):
        scope, records = self.prepare()
        self.assertEqual(scope["event_count"], 2)
        self.assertEqual(scope["skipped_non_admissions"], 1)
        self.assertEqual(scope["source_manifest_sha256"], self.source_sha)
        self.assertEqual([(eid, kind) for eid, kind, _ in records],
                         [("visit-one", "A01"), ("visit-one", "A03")])
        self.assertNotEqual(records[0][2], records[1][2])
        self.assertEqual([json.loads(raw)["requested_event_type"]
                          for _, _, raw in records], ["A01", "A03"])
        self.assertTrue(all(json.loads(raw)["request_id"] == REQUEST
                            for _, _, raw in records))
        self.assertEqual(scope["channel_id"], CHANNEL_ID)

    def test_two_distinct_post_acks_bind_exact_receipts_before_scoped_get(self):
        fake = FakePoster()
        doc = self.submit(fake)
        self.assertEqual(fake.preflights, [CHANNEL_ID])
        self.assertEqual([r["requested_event_type"] for _, r in fake.sent],
                         ["A01", "A03"])
        self.assertEqual(doc["schema_version"], VERSION)
        self.assertEqual(doc["event_count"], 2)
        self.assertEqual(doc["skipped_non_admissions"], 1)
        self.assertEqual([x["message_id"] for x in doc["messages"]],
                         ["10001", "10002"])
        handoff = verify_handoff(self.root, self.profile, REQUEST)
        parsed = verified_v2_post_receipts(
            doc, run_id=RUN_ID, request_id=REQUEST, handoff=handoff,
            expected_events=[("visit-one", "A01"), ("visit-one", "A03")])
        self.assertEqual([p.message_id for p in parsed], ["10001", "10002"])

    def test_independent_receipt_verifier_recomputes_frozen_source(self):
        doc = self.submit(FakePoster())
        records = verify_v2_receipts_against_frozen_source(
            self.root, self.profile, REQUEST, run_id=RUN_ID,
            expected_source_manifest_sha256=self.source_sha,
            document=doc,
        )
        self.assertEqual([x.event_type for x in records], ["A01", "A03"])
        doc["skipped_non_admissions"] = 0
        with self.assertRaisesRegex(OIEPostBlocked, "SOURCE_EVENT_COVERAGE_HOLD"):
            verify_v2_receipts_against_frozen_source(
                self.root, self.profile, REQUEST, run_id=RUN_ID,
                expected_source_manifest_sha256=self.source_sha,
                document=doc,
            )

    def test_wrong_channel_manifest_or_run_refuses_all_post(self):
        for kwargs in (
            {"run_id": "23456789012"},
            {"run_id": "not-a-run"},
            {"channel_id": LEGACY_CHANNEL},
            {"expected_source_manifest_sha256": "0" * 64},
        ):
            poster = FakePoster()
            with self.subTest(kwargs=kwargs), self.assertRaises(OIEPostBlocked):
                self.submit(poster, **kwargs)
            self.assertEqual(poster.sent, [])
            self.assertEqual(poster.preflights, [])

    def test_source_file_changed_or_demographic_missing_blocks_before_any_post(self):
        self.fhir.write_bytes(self.fhir.read_bytes() + b" ")
        poster = FakePoster()
        with self.assertRaises(OIEPostBlocked):
            self.submit(poster)
        self.assertEqual(poster.sent, [])

        self.bundle["entry"][0]["resource"]["gender"] = "unknown"
        self.freeze()
        poster = FakePoster()
        with self.assertRaisesRegex(OIEPostBlocked, "OIE_V2_FROZEN_SOURCE_OR_MAPPING_HOLD"):
            self.submit(poster)
        self.assertEqual(poster.sent, [])

    def test_preflight_failure_and_post_timeout_mean_no_auto_retry(self):
        poster = FakePoster(fail_preflight=True)
        with self.assertRaisesRegex(OIEPostBlocked, "PREFLIGHT_HOLD_NO_POST"):
            self.submit(poster)
        self.assertEqual(poster.sent, [])

        poster = FakePoster(fail_at=2)
        with self.assertRaisesRegex(OIEPostBlocked,
                                    "POST_OUTCOME_UNKNOWN_HOLD_NO_RETRY") as ctx:
            self.submit(poster)
        self.assertEqual(len(poster.sent), 2)
        self.assertNotIn("SECRET_SHOULD_NOT_LEAK", str(ctx.exception))

    def test_duplicate_or_invalid_ack_holds_without_unsafe_receipt(self):
        for ids in (("10001", "10001"), ("10001", "NO-ACK")):
            poster = FakePoster(ids=ids)
            with self.subTest(ids=ids), self.assertRaisesRegex(
                    OIEPostBlocked, "INVALID_ACK_HOLD_NO_RETRY"):
                self.submit(poster)
            self.assertEqual(len(poster.sent), 2)

    def test_in_progress_admission_issues_only_a01(self):
        self.bundle["entry"][1]["resource"] = encounter("visit-one", status="in-progress")
        self.freeze()
        scope, rows = self.prepare()
        self.assertEqual(scope["event_count"], 1)
        self.assertEqual([x[1] for x in rows], ["A01"])
        doc = self.submit(FakePoster(ids=("20001",)))
        self.assertEqual([x["event_type"] for x in doc["messages"]], ["A01"])

    def test_tampered_receipt_identity_coverage_and_skips_are_blocked(self):
        good = self.submit(FakePoster())
        handoff = verify_handoff(self.root, self.profile, REQUEST)
        options = [
            ("channel_id", LEGACY_CHANNEL),
            ("source_manifest_sha256", "0" * 64),
            ("run_id", "99999999999"),
            ("skipped_non_admissions", 0),
            ("event_count", 1),
        ]
        for key, value in options:
            doc = copy.deepcopy(good)
            doc[key] = value
            with self.subTest(key=key), self.assertRaises(OIEPostBlocked):
                verified_v2_post_receipts(
                    doc, run_id=RUN_ID, request_id=REQUEST, handoff=handoff,
                    expected_events=[("visit-one", "A01"), ("visit-one", "A03")])
        cases = [
            [{"source_encounter_id": "visit-one", "event_type": "A03", "message_id": "10002"}],
            [good["messages"][0], good["messages"][0]],
            [good["messages"][0], dict(good["messages"][1], message_id="10001")],
            [good["messages"][0], dict(good["messages"][1], event_type="A08")],
            [good["messages"][0], dict(good["messages"][1], source_encounter_id=[])],
        ]
        for messages in cases:
            doc = copy.deepcopy(good)
            doc["messages"] = messages
            doc["event_count"] = len(messages)
            with self.subTest(messages=messages), self.assertRaises(OIEPostBlocked):
                verified_v2_post_receipts(
                    doc, run_id=RUN_ID, request_id=REQUEST, handoff=handoff,
                    expected_events=[("visit-one", "A01"), ("visit-one", "A03")])

    def test_v2_network_scoped_channel_preflight_reuses_existing_http_no_post(self):
        class Response:
            status = 200
            def __init__(self, raw): self.raw = raw
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, count): return self.raw
        class Opener:
            def __init__(self, channel_xml):
                self.channel_xml = channel_xml
                self.calls = []
            def open(self, req, timeout):
                self.calls.append(req)
                if req.full_url.endswith("/status"):
                    return Response(b"<status>STARTED</status>")
                return Response(self.channel_xml.encode("utf-8"))

        scoped = object.__new__(ScopedOIEV2Poster)
        opener = Opener(render_channel_v2())
        scoped._opener = opener
        scoped.preflight_channel(CHANNEL_ID)
        self.assertEqual(len(opener.calls), 2)
        self.assertTrue(all(req.get_method() == "GET" for req in opener.calls))
        self.assertTrue(all("/channels/" + CHANNEL_ID in req.full_url
                            for req in opener.calls))
        with self.assertRaises(OIEPostBlocked):
            scoped.submit(LEGACY_CHANNEL, b"example")
        self.assertEqual(len(opener.calls), 2)

        scoped._opener = Opener(legacy_channel_xml())
        with self.assertRaisesRegex(OIEPostBlocked, "OIE_CHANNEL_CONFIG_DRIFT_HOLD"):
            scoped.preflight_channel(CHANNEL_ID)
        self.assertEqual(len(scoped._opener.calls), 1)

        # An unexpected V2 OIE destination can have side effects. Do not POST
        # into a Channel whose writer/route differs from reviewed version.
        import xml.etree.ElementTree as ET
        tampered = ET.fromstring(render_channel_v2())
        destination = tampered.find("destinationConnectors/connector/properties")
        self.assertIsNotNone(destination)
        destination.set("class", "UNAPPROVED_SINK")
        scoped._opener = Opener(ET.tostring(tampered, encoding="unicode"))
        with self.assertRaisesRegex(OIEPostBlocked, "OIE_CHANNEL_CONFIG_DRIFT_HOLD"):
            scoped.preflight_channel(CHANNEL_ID)
        self.assertEqual(len(scoped._opener.calls), 1)


if __name__ == "__main__":
    unittest.main()
