"""Synthetic OIE persisted-message fixtures for V2 Event Receipt; no live OIE."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT / "local-data-platform"))

from apps.clinical_producers.oie.build_adt_events_v2_channel import CHANNEL_ID
from apps.clinical_producers.oie_event_readback_v2 import (
    OIEV2EventReceipt, OIEV2EventBlocked, fetch_v2_event_readbacks,
)

HOSP = "johns-creek-hospital-b"
FEED = "johns-creek-hospital-b-hl7-v2"
REQUEST = "synthetic-v2-receipts-20261106"
AUTH = "JOHNSCREEKB"
OLD_CHANNEL = "69ace705-a675-45f6-b126-a3b22a65212a"

NODE = r"""
const fn = require("./local-data-platform/apps/clinical_producers/oie/adt_events_v2.js").fhirToHl7AdtEventsV2;
const oid="urn:oid:2.16.840.1.113883.6.238";
const patient={
 resourceType:"Patient",id:"person-one",name:[{family:"Test",given:["Anne"]}],
 birthDate:"1980-01-01",gender:"female",extension:[
 {url:"http://hl7.org/fhir/us/core/StructureDefinition/us-core-race",
  extension:[{url:"ombCategory",valueCoding:{system:oid,code:"2106-3"}}]},
 {url:"http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity",
  extension:[{url:"ombCategory",valueCoding:{system:oid,code:"2186-5"}}]}]};
const visit={
 resourceType:"Encounter",id:"visit-one",status:"finished",
 class:{system:"http://terminology.hl7.org/CodeSystem/v3-ActCode",code:"IMP"},
 subject:{reference:"Patient/person-one"},period:{
 start:"2026-11-05T07:00:00-05:00",end:"2026-11-06T05:00:00-05:00"}};
const cfg={
 hospital_id:"johns-creek-hospital-b",feed_id:"johns-creek-hospital-b-hl7-v2",
 request_id:"synthetic-v2-receipts-20261106",assigning_authority:"JOHNSCREEKB"};
process.stdout.write(JSON.stringify(
 fn({resourceType:"Bundle",entry:[{resource:patient},{resource:visit}]},cfg).messages
));
"""


def fake_persisted(event_bytes, *, msgid, processed="true", channel=CHANNEL_ID):
    root = ET.Element("message")
    ET.SubElement(root, "messageId").text = msgid
    ET.SubElement(root, "channelId").text = channel
    ET.SubElement(root, "processed").text = processed
    source = ET.SubElement(root, "connectorMessage")
    ET.SubElement(source, "metaDataId").text = "0"
    ET.SubElement(source, "status").text = "TRANSFORMED"
    node = ET.SubElement(source, "processedRaw")
    ET.SubElement(node, "content").text = event_bytes.decode("utf-8")
    return ET.tostring(root, encoding="utf-8").replace(b"\r", b"&#13;")


class FakeScopedGetter:
    def __init__(self, data):
        self.data = data
        self.paths = []

    def get(self, path):
        self.paths.append(path)
        return self.data[path]


class V2EventReadbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        response = subprocess.run(["node", "-e", NODE], cwd=ROOT,
                                  capture_output=True, check=True, text=True)
        cls.events = json.loads(response.stdout)
        cls.records = [
            OIEV2EventReceipt("visit-one", "A01", "1001"),
            OIEV2EventReceipt("visit-one", "A03", "1002"),
        ]

    @staticmethod
    def run_scoped(client, records, **kwargs):
        args = {
            "channel_id": CHANNEL_ID,
            "hospital_id": HOSP,
            "feed_id": FEED,
            "request_id": REQUEST,
            "assigning_authority": AUTH,
            "receipts": records,
        }
        args.update(kwargs)
        return fetch_v2_event_readbacks(client, **args)

    @classmethod
    def fake(cls):
        paths = [
            f"/api/channels/{CHANNEL_ID}/messages/{x.message_id}"
            for x in cls.records
        ]
        return FakeScopedGetter({
            paths[0]: fake_persisted(cls.events[0]["hl7"].encode("utf-8"), msgid="1001"),
            paths[1]: fake_persisted(cls.events[1]["hl7"].encode("utf-8"), msgid="1002"),
        })

    def test_two_events_for_one_encounter_are_distinct_and_readable(self):
        client = self.fake()
        result = self.run_scoped(client, self.records)
        self.assertEqual([x.event_type for x in result], ["A01", "A03"])
        self.assertEqual([x.message_id for x in result], ["1001", "1002"])
        self.assertEqual([x.source_encounter_id for x in result], ["visit-one", "visit-one"])
        self.assertNotEqual(result[0].payload_sha256, result[1].payload_sha256)
        self.assertEqual(result[0].patient_id, "person-one")
        self.assertEqual([x.control_id for x in result],
                         [x["control_id"] for x in self.events])
        self.assertEqual(len(client.paths), 2)
        print("OIE_V2_SCOPED_TWO_EVENT_RECEIPTS_OFFLINE_PASS")

    def test_a01_only_is_supported_for_unfinished_visit(self):
        client = self.fake()
        result = self.run_scoped(client, self.records[:1])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].event_type, "A01")

    def test_a03_alone_requires_previously_approved_a01(self):
        client = self.fake()
        with self.assertRaisesRegex(OIEV2EventBlocked, "A03_WITHOUT_APPROVED_A01"):
            self.run_scoped(client, self.records[1:])
        self.assertEqual(client.paths, [])

    def test_duplicate_message_id_or_event_is_rejected_before_network(self):
        client = self.fake()
        for receipts in (
            [self.records[0], OIEV2EventReceipt("visit-one", "A03", "1001")],
            [self.records[0], OIEV2EventReceipt("visit-one", "A01", "1002")],
            [OIEV2EventReceipt("visit-one", "A08", "1001")],
            [OIEV2EventReceipt("../invalid", "A01", "1001")],
            [OIEV2EventReceipt("visit-one", "A01", "-1")],
        ):
            with self.subTest(receipts=receipts):
                with self.assertRaises(OIEV2EventBlocked):
                    self.run_scoped(client, receipts)
                self.assertEqual(client.paths, [])

    def test_legacy_channel_id_cannot_be_reused(self):
        client = self.fake()
        with self.assertRaisesRegex(OIEV2EventBlocked, "UNAPPROVED_CHANNEL"):
            self.run_scoped(client, self.records, channel_id=OLD_CHANNEL)
        self.assertEqual(client.paths, [])

    def test_wrong_event_type_or_control_id_fails_closed(self):
        client = self.fake()
        client.data[f"/api/channels/{CHANNEL_ID}/messages/1002"] = fake_persisted(
            self.events[0]["hl7"].encode("utf-8"), msgid="1002")
        with self.assertRaisesRegex(OIEV2EventBlocked,
                                    "INDEPENDENT_ADT_VERIFICATION_FAILED"):
            self.run_scoped(client, self.records)

        client = self.fake()
        bad = self.events[1]["hl7"].replace("visit-one-A03", "visit-wrong-A03")
        client.data[f"/api/channels/{CHANNEL_ID}/messages/1002"] = fake_persisted(
            bad.encode("utf-8"), msgid="1002")
        with self.assertRaisesRegex(OIEV2EventBlocked, "SOURCE_EVENT_CORRELATION"):
            self.run_scoped(client, self.records)

    def test_wrong_scope_does_not_accept_another_hospital(self):
        client = self.fake()
        with self.assertRaisesRegex(OIEV2EventBlocked, "SOURCE_EVENT_CORRELATION"):
            self.run_scoped(client, self.records, hospital_id="atlanta-hospital-b")

    def test_unprocessed_oie_message_fails_without_disclosing_payload(self):
        client = self.fake()
        client.data[f"/api/channels/{CHANNEL_ID}/messages/1001"] = fake_persisted(
            self.events[0]["hl7"].encode("utf-8"),
            msgid="1001", processed="false")
        with self.assertRaisesRegex(OIEV2EventBlocked,
                                    "PERSISTED_SOURCE_READBACK_FAILED"):
            self.run_scoped(client, self.records)

    def test_network_failure_is_redacted(self):
        class SecretError:
            def get(self, path):
                raise RuntimeError("my-credentials-should-not-appear")
        with self.assertRaisesRegex(OIEV2EventBlocked, "^OIE_V2_SCOPED_GET_FAILED$") as ctx:
            self.run_scoped(SecretError(), self.records[:1])
        self.assertNotIn("credentials", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
