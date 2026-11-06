"""Offline A01+A03 raw-HL7 plan and Azure Publisher preservation tests.

This uses new synthetic V2 mapper messages, not live OIE data. No Azure SDK
network, credentials, Blob account, K8s, Fabric or real PHI.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT / "local-data-platform"))

from apps.clinical_producers.blob_publish_contract import (
    VERSION as PLAN_VERSION, BlobPlanRejected, verified_plan
)
from apps.clinical_producers.azure_blob_publisher import (
    BlobBackend, BlobSnapshot, BlobNotFound, BlobAlreadyExists,
    PublishBlocked, publish_immutable
)
from apps.clinical_producers.oie.hl7_readback import (
    Hl7ReadbackError, parse_adt_a01, parse_adt_a03
)

NODE_EVENTS = r"""
const fn = require("./local-data-platform/apps/clinical_producers/oie/adt_events_v2.js").fhirToHl7AdtEventsV2;
const oid = "urn:oid:2.16.840.1.113883.6.238";
const person = {resourceType:"Patient", id:"patient-one",
 birthDate:"1980-01-01", gender:"female", name:[{family:"Example",given:["Test"]}],
 extension:[
   {url:"http://hl7.org/fhir/us/core/StructureDefinition/us-core-race",
    extension:[{url:"ombCategory",valueCoding:{system:oid,code:"2106-3"}}]},
   {url:"http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity",
    extension:[{url:"ombCategory",valueCoding:{system:oid,code:"2186-5"}}]}]};
const visit = {resourceType:"Encounter", id:"visit-one", status:"finished",
 class:{system:"http://terminology.hl7.org/CodeSystem/v3-ActCode",code:"IMP"},
 subject:{reference:"Patient/patient-one"},
 period:{start:"2026-11-05T07:00:00-05:00",end:"2026-11-06T05:00:00-05:00"}};
const cfg = {hospital_id:"johns-creek-hospital-b",
feed_id:"johns-creek-hospital-b-hl7-v2", request_id:"synthetic-request-20261106",
assigning_authority:"JOHNSCREEKB"};
process.stdout.write(JSON.stringify(fn({resourceType:"Bundle",entry:[
  {resource:person},{resource:visit}]},cfg).messages));
"""


class InMemoryBlob:
    def __init__(self):
        self.remote = {}

    def create(self, key, data, metadata, content_type):
        if key in self.remote:
            raise BlobAlreadyExists()
        etag = '"' + hashlib.sha256(data).hexdigest()[:12] + '"'
        self.remote[key] = BlobSnapshot(
            data=bytes(data), metadata=dict(metadata),
            content_type=content_type, etag=etag,
        )
        return etag

    def read(self, key):
        if key not in self.remote:
            raise BlobNotFound()
        return self.remote[key]


class SyntheticA03BlobTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        output = subprocess.run(
            ["node", "-e", NODE_EVENTS], cwd=ROOT, check=True,
            capture_output=True, text=True,
        )
        cls.events = json.loads(output.stdout)

    @classmethod
    def build_plan(cls):
        data = {}
        objects = []
        for event in cls.events:
            kind = event["event_type"]
            name = f"hl7/visit-one-{kind}.hl7"
            raw = event["hl7"].encode("utf-8")
            data[name] = raw
            objects.append({
                "name": name, "size_bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "source_event_id": event["control_id"],
            })
        return {
            "schema_version": PLAN_VERSION,
            "hospital_id": "johns-creek-hospital-b",
            "feed_id": "johns-creek-hospital-b-hl7-v2",
            "request_id": "synthetic-request-20261106",
            "source_manifest_sha256": "a" * 64,
            "target_format": "HL7_V2",
            "verification_state": "OIE_HL7_READBACK_VERIFIED",
            "skipped_non_admissions": 0,
            "objects": objects,
        }, data

    def test_new_a03_strict_readback_and_legacy_a01_still_work(self):
        a01, a03 = self.events
        self.assertEqual(parse_adt_a01(a01["hl7"])["control_id"], a01["control_id"])
        parsed = parse_adt_a03(a03["hl7"])
        self.assertEqual(parsed["control_id"], a03["control_id"])
        self.assertEqual(parsed["start_time"], "20261105120000+0000")
        self.assertEqual(parsed["end_time"], "20261106100000+0000")
        self.assertEqual(parsed["patient_id"], "patient-one")
        self.assertEqual(parsed["encounter_id"], "visit-one")
        self.assertEqual(parsed["birth_date"], "19800101")
        self.assertEqual(parsed["race_code"], "2106-3")
        with self.assertRaises(Hl7ReadbackError):
            parse_adt_a03(a01["hl7"])
        print("OFFLINE_A01_A03_SOURCE_READBACK_PASS")

    def test_shared_blob_plan_accepts_distinct_a01_and_a03_immutable_objects(self):
        plan, data = self.build_plan()
        entries = verified_plan(plan, data, landing_prefix="synthetic/hl7")
        self.assertEqual(len(entries), 2)
        self.assertTrue(any(e["blob_key"].endswith("/hl7/visit-one-A03.hl7") for e in entries))

    def test_shared_publisher_manifest_last_replay_is_safe(self):
        plan, data = self.build_plan()
        backend = InMemoryBlob()
        first = publish_immutable(plan, data, landing_prefix="synthetic/hl7", backend=backend)
        self.assertEqual(first["status"], "BLOB_MANIFEST_COMMITTED")
        self.assertEqual(len(first["objects"]), 2)
        manifest = json.loads(backend.read(first["manifest_key"]).data)
        self.assertEqual(len(manifest["objects"]), 2)
        retry = publish_immutable(plan, data, landing_prefix="synthetic/hl7", backend=backend)
        self.assertEqual(retry["manifest_create_status"], "ALREADY_MATCHING")
        self.assertEqual(set(retry["object_create_statuses"]), {"ALREADY_MATCHING"})
        self.assertEqual(len(backend.remote), 3)
        print("OFFLINE_A01_A03_BLOB_MANIFEST_AND_REPLAY_PASS")

    def test_a03_late_or_invalid_discharge_fails_closed(self):
        a03 = self.events[1]["hl7"]
        wrong = a03.replace("20261106100000+0000", "20261104100000+0000")
        with self.assertRaisesRegex(Hl7ReadbackError, "HL7_A03_END_BEFORE_START"):
            parse_adt_a03(wrong)
        missing = a03.replace("|20261106100000+0000\r", "|\r")
        with self.assertRaises(Hl7ReadbackError):
            parse_adt_a03(missing)

    def test_checksum_or_control_id_tampering_rejected_before_writes(self):
        plan, data = self.build_plan()
        changed = dict(data)
        changed["hl7/visit-one-A03.hl7"] = changed["hl7/visit-one-A03.hl7"].replace(
            b"Not Hispanic or Latino", b"Other ethnicity"
        )
        with self.assertRaisesRegex(BlobPlanRejected, "SOURCE_BYTES_MISMATCH"):
            verified_plan(plan, changed, landing_prefix="synthetic/hl7")
        plan["objects"][1]["source_event_id"] = "fake-A03-control"
        with self.assertRaisesRegex(BlobPlanRejected, "HL7_CONTROL_ID_MISMATCH"):
            verified_plan(plan, data, landing_prefix="synthetic/hl7")


if __name__ == "__main__":
    unittest.main()
