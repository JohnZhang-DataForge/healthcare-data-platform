"""Frozen source-manifest to dual persistent OIE message to shared Blob tests.

All sources and OIE replies are synthetic; never contacts worker01 or Azure.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT / "local-data-platform"))

from apps.clinical_producers.azure_blob_publisher import (
    BlobSnapshot, BlobAlreadyExists, BlobNotFound, PublishBlocked,
)
from apps.clinical_producers.oie.build_adt_events_v2_channel import CHANNEL_ID
from apps.clinical_producers.oie_event_readback_v2 import OIEV2EventReceipt
from apps.clinical_producers.oie_hl7_publisher_v2 import (
    OIEV2HandoffBlocked, audit_frozen_adt_profile,
    prepare_oie_hl7_v2, publish_oie_hl7_v2,
)
from apps.synthea.synthea_new_generator.generator import (
    COMPLETED, MANIFEST_VERSION, validate_payload, sha256,
)
from apps.synthea.synthea_new_generator.request import (
    SCHEMA_VERSION, fingerprint, normalize,
)

HOSP = "johns-creek-hospital-b"
FEED = "johns-creek-hospital-b-hl7-v2"
REQUEST = "verified-oie-v2-20261106"
AUTH = "JOHNSCREEKB"
RACE_URL = "http://hl7.org/fhir/us/core/StructureDefinition/us-core-race"
ETHNICITY_URL = "http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity"
CDCREC = "urn:oid:2.16.840.1.113883.6.238"


def patient():
    return {
        "resourceType": "Patient", "id": "person-one",
        "birthDate": "1980-01-01", "gender": "female",
        "name": [{"family": "Test", "given": ["Anne"]}],
        "extension": [
            {"url": RACE_URL, "extension": [
                {"url": "ombCategory", "valueCoding": {"system": CDCREC, "code": "2106-3"}},
            ]},
            {"url": ETHNICITY_URL, "extension": [
                {"url": "ombCategory", "valueCoding": {"system": CDCREC, "code": "2186-5"}},
            ]},
        ],
    }


def encounter(ident, *, code="IMP", status="finished"):
    return {
        "resourceType": "Encounter", "id": ident,
        "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                  "code": code},
        "status": status, "subject": {"reference": "Patient/person-one"},
        "period": {
            "start": "2026-11-05T07:00:00-05:00",
            **({"end": "2026-11-06T05:00:00-05:00"} if status == "finished" else {}),
        },
    }


def encode_oie(raw: bytes, message_id: str):
    root = ET.Element("message")
    ET.SubElement(root, "messageId").text = message_id
    ET.SubElement(root, "channelId").text = CHANNEL_ID
    ET.SubElement(root, "processed").text = "true"
    src = ET.SubElement(root, "connectorMessage")
    ET.SubElement(src, "metaDataId").text = "0"
    ET.SubElement(src, "status").text = "TRANSFORMED"
    ET.SubElement(ET.SubElement(src, "processedRaw"), "content").text = raw.decode("utf-8")
    return ET.tostring(root, encoding="utf-8").replace(b"\r", b"&#13;")


class FakeOIE:
    def __init__(self, payloads):
        self.payloads = payloads
        self.paths = []

    def get(self, path):
        self.paths.append(path)
        return self.payloads[path]


class FakeBlob:
    def __init__(self):
        self.storage = {}
        self.writes = []

    def create(self, key, data, metadata, content_type):
        if key in self.storage:
            raise BlobAlreadyExists()
        etag = '"' + hashlib.sha256(data).hexdigest()[:16] + '"'
        self.storage[key] = BlobSnapshot(
            data=bytes(data), metadata=dict(metadata), content_type=content_type,
            etag=etag,
        )
        self.writes.append(key)
        return etag

    def read(self, key):
        if key not in self.storage:
            raise BlobNotFound()
        return self.storage[key]


NODE = r"""
const fs = require('fs');
const mapper = require('./local-data-platform/apps/clinical_producers/oie/adt_events_v2.js').fhirToHl7AdtEventsV2;
const bundle = JSON.parse(fs.readFileSync(process.argv[1], 'utf8'));
const cfg = {
 hospital_id:"johns-creek-hospital-b",feed_id:"johns-creek-hospital-b-hl7-v2",
 request_id:"verified-oie-v2-20261106",assigning_authority:"JOHNSCREEKB"
};
process.stdout.write(JSON.stringify(mapper(bundle, cfg)));
"""


class FrozenSourceBridgeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.profile = ROOT / "local-data-platform/config/synthea-new-generator/johns-creek-hl7.json"
        self.request = normalize({
            "schema_version": SCHEMA_VERSION, "request_id": REQUEST,
            "generation_mode": "NEW_ONLY", "population": 1,
            "state": "Georgia", "city": "Johns Creek", "seed": 67890,
            "reference_date": "20261024", "output_formats": ["FHIR_R4"],
        })
        self.folder = self.root / "requests" / REQUEST
        self.fhir = self.folder / "payload" / "fhir" / "person-one.json"
        self.fhir.parent.mkdir(parents=True)
        self.bundle = {
            "resourceType": "Bundle", "type": "collection",
            "entry": [
                {"resource": patient()},
                {"resource": encounter("visit-one")},
                {"resource": encounter("visit-two", code="AMB")},
            ],
        }
        (self.folder / "request.json").write_text(json.dumps({
            "request": self.request, "request_sha256": fingerprint(self.request),
        }))
        self.freeze()
        self.sync_oie()

    def freeze(self):
        self.fhir.write_text(json.dumps(self.bundle))
        actual = validate_payload(self.folder / "payload", self.request)
        (self.folder / "generation-manifest.json").write_text(json.dumps({
            "schema_version": MANIFEST_VERSION, "request_id": REQUEST,
            "request_sha256": fingerprint(self.request), "status": COMPLETED,
            **actual,
        }))

    def sync_oie(self):
        generated = subprocess.run(
            ["node", "-e", NODE, str(self.fhir)],
            cwd=ROOT, check=True, capture_output=True, text=True,
        )
        self.events = json.loads(generated.stdout)["messages"]
        self.receipts = []
        payloads = {}
        for index, event in enumerate(self.events):
            mid = str(1001 + index)
            self.receipts.append(OIEV2EventReceipt(event["encounter_id"], event["event_type"], mid))
            payloads[f"/api/channels/{CHANNEL_ID}/messages/{mid}"] = encode_oie(
                event["hl7"].encode("utf-8"), mid,
            )
        self.client = FakeOIE(payloads)

    def prepare(self, **kwargs):
        params = {
            "channel_id": CHANNEL_ID, "assigning_authority": AUTH,
            "receipts": self.receipts, "client": self.client,
        }
        params.update(kwargs)
        return prepare_oie_hl7_v2(self.root, self.profile, REQUEST, **params)

    def publish(self, blob: FakeBlob):
        return publish_oie_hl7_v2(
            self.root, self.profile, REQUEST,
            channel_id=CHANNEL_ID, assigning_authority=AUTH,
            receipts=self.receipts, client=self.client,
            landing_prefix="healthcare/v2", backend=blob,
        )

    def test_profile_source_counts_without_patient_identifiers(self):
        result = audit_frozen_adt_profile(self.root, self.profile, REQUEST)
        self.assertEqual(result["status"], "PROFILE_COMPATIBLE")
        self.assertEqual(result["total_encounters"], 2)
        self.assertEqual(result["a01_eligible"], 1)
        self.assertEqual(result["a03_eligible"], 1)
        self.assertEqual(result["non_admission_skipped"], 1)
        self.assertEqual(result["hold_count"], 0)
        self.assertNotIn("person-one", json.dumps(result))
        self.assertNotIn("visit-one", json.dumps(result))

    def test_source_manifest_ties_both_oie_message_ids_to_two_blob_objects(self):
        plan, source = self.prepare()
        self.assertEqual(len(self.client.paths), 2)
        self.assertEqual(plan["source_manifest_sha256"],
                         sha256(self.folder / "generation-manifest.json"))
        self.assertEqual(plan["skipped_non_admissions"], 1)
        self.assertEqual([x["name"] for x in plan["objects"]],
                         ["hl7/visit-one-A01.hl7", "hl7/visit-one-A03.hl7"])
        self.assertEqual([x["source_event_id"] for x in plan["objects"]],
                         [x["control_id"] for x in self.events])
        self.assertEqual(len(source), 2)
        self.assertNotEqual(*[x["sha256"] for x in plan["objects"]])

    def test_reuse_shared_publisher_manifest_last_and_safe_replay(self):
        backend = FakeBlob()
        first = self.publish(backend)
        self.assertEqual(first["status"], "BLOB_MANIFEST_COMMITTED")
        self.assertEqual(len(backend.writes), 3)
        self.assertEqual(backend.writes[-1], first["manifest_key"])
        manifest = json.loads(backend.read(first["manifest_key"]).data)
        self.assertEqual(manifest["source_manifest_sha256"],
                         sha256(self.folder / "generation-manifest.json"))
        self.assertEqual(len(manifest["objects"]), 2)
        second = self.publish(backend)
        self.assertEqual(len(backend.writes), 3)
        self.assertEqual(second["manifest_create_status"], "ALREADY_MATCHING")
        self.assertEqual(set(second["object_create_statuses"]), {"ALREADY_MATCHING"})

    def test_missing_or_forged_receipts_never_contact_oie_or_blob(self):
        for receipts in (
            self.receipts[:1],
            self.receipts[1:],
            self.receipts + [OIEV2EventReceipt("visit-two", "A01", "1003")],
        ):
            getter = FakeOIE(self.client.payloads)
            with self.subTest(receipts=receipts), self.assertRaisesRegex(
                    OIEV2HandoffBlocked, "INCOMPLETE_OR_UNEXPECTED"):
                self.prepare(receipts=receipts, client=getter)
            self.assertEqual(getter.paths, [])

    def test_wrong_legacy_channel_fails_before_get(self):
        getter = FakeOIE(self.client.payloads)
        with self.assertRaisesRegex(OIEV2HandoffBlocked, "UNAPPROVED_V2_CHANNEL"):
            self.prepare(channel_id="69ace705-a675-45f6-b126-a3b22a65212a", client=getter)
        self.assertEqual(getter.paths, [])

    def test_clinical_fact_tamper_in_persisted_oie_holds_before_blob_write(self):
        cases = (
            (b"19800101", b"19900101"),
            (b"F|", b"M|"),
            (b"2106-3", b"2028-9"),
            (b"2186-5", b"2135-2"),
            (b"20261106100000+0000", b"20261106110000+0000"),
        )
        for old, new in cases:
            getter = FakeOIE(dict(self.client.payloads))
            path = f"/api/channels/{CHANNEL_ID}/messages/1002"
            tampered = self.events[1]["hl7"].encode().replace(old, new)
            getter.payloads[path] = encode_oie(tampered, "1002")
            with self.subTest(field=old), self.assertRaises(OIEV2HandoffBlocked):
                self.prepare(client=getter)

    def test_missing_required_fhir_demographics_yield_source_hold(self):
        self.bundle["entry"][0]["resource"]["extension"] = []
        self.freeze()
        result = audit_frozen_adt_profile(self.root, self.profile, REQUEST)
        self.assertEqual(result["status"], "HOLD")
        self.assertEqual(result["hold_count"], 1)
        self.assertIn("RACE_EXTENSION_MISSING", str(result["hold_reasons"]))
        getter = FakeOIE(self.client.payloads)
        with self.assertRaisesRegex(OIEV2HandoffBlocked, "RACE_EXTENSION_MISSING"):
            self.prepare(client=getter)
        self.assertEqual(getter.paths, [])

    def test_stale_manifest_or_modified_source_blocks_before_get(self):
        self.fhir.write_bytes(self.fhir.read_bytes() + b" ")
        getter = FakeOIE(self.client.payloads)
        with self.assertRaisesRegex(OIEV2HandoffBlocked, "SOURCE_HANDOFF_NOT_VERIFIED"):
            self.prepare(client=getter)
        self.assertEqual(getter.paths, [])

    def test_new_manifest_but_old_oie_patient_fact_holds(self):
        self.bundle["entry"][0]["resource"]["birthDate"] = "1985-01-01"
        self.freeze()
        with self.assertRaisesRegex(OIEV2HandoffBlocked, "SOURCE_CLINICAL_CORRELATION"):
            self.prepare()

    def test_in_progress_a01_without_invented_a03(self):
        self.bundle["entry"][1]["resource"] = encounter("visit-one", status="in-progress")
        self.freeze()
        self.sync_oie()
        plan, data = self.prepare()
        self.assertEqual(len(plan["objects"]), 1)
        self.assertEqual(set(data), {"hl7/visit-one-A01.hl7"})

    def test_mutated_source_during_remote_get_blocks_publication(self):
        class MutatingGetter(FakeOIE):
            def get(g, path):
                value = super().get(path)
                self.fhir.write_bytes(self.fhir.read_bytes() + b" ")
                return value
        getter = MutatingGetter(dict(self.client.payloads))
        with self.assertRaisesRegex(OIEV2HandoffBlocked, "SOURCE_CHANGED_DURING_GET"):
            self.prepare(client=getter)

    def test_persisted_oie_message_missing_fails_closed(self):
        getter = FakeOIE({})
        with self.assertRaisesRegex(OIEV2HandoffBlocked, "PERSISTED_OIE_V2_READBACK_HOLD"):
            self.prepare(client=getter)


if __name__ == "__main__":
    unittest.main()
