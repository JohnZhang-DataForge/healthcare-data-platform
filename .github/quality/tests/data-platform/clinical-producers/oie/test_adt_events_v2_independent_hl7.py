"""Parse fresh V2 Node-generated HL7 with external hl7apy v1.3.5.

Synthetic only, GitHub-hosted, no live OIE, PHI, Azure or Kubernetes.
"""
from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

from hl7apy import VALIDATION_LEVEL
from hl7apy.parser import parse_message


ROOT = Path(__file__).resolve().parents[6]

NODE_EMIT = r"""
const m = require("./local-data-platform/apps/clinical_producers/oie/adt_events_v2.js");
const system = "urn:oid:2.16.840.1.113883.6.238";
const patient = {
  resourceType: "Patient", id: "synthetic-person-001",
  birthDate: "1980-01-01", gender: "female",
  name: [{family: "Example", given: ["Test"]}],
  extension: [
    {url: "http://hl7.org/fhir/us/core/StructureDefinition/us-core-race",
     extension: [{url: "ombCategory", valueCoding: {system: system, code: "2106-3"}}]},
    {url: "http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity",
     extension: [{url: "ombCategory", valueCoding: {system: system, code: "2186-5"}}]}
  ]
};
const encounter = {
  resourceType: "Encounter", id: "synthetic-visit-001",
  status: "finished",
  class: {system: "http://terminology.hl7.org/CodeSystem/v3-ActCode", code:"IMP"},
  subject: {reference: "Patient/synthetic-person-001"},
  period: {start: "2026-11-05T07:00:00-05:00",
           end: "2026-11-06T05:00:00-05:00"}
};
const config = {
  hospital_id: "johns-creek-hospital-b", feed_id: "johns-creek-hospital-b-hl7-v2",
  request_id: "synthetic-v2-independent-001", assigning_authority:"JOHNSCREEKB"
};
const bundle = {resourceType:"Bundle", type:"collection",
                entry:[{resource:patient}, {resource:encounter}]};
process.stdout.write(JSON.stringify(m.fhirToHl7AdtEventsV2(bundle, config).messages));
"""


class IndependentHl7ReadbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        out = subprocess.run(
            ["node", "-e", NODE_EMIT], cwd=ROOT, check=True,
            capture_output=True, text=True,
        )
        cls.events = json.loads(out.stdout)

    def test_generated_real_hl7_event_pair(self):
        self.assertEqual([x["event_type"] for x in self.events], ["A01", "A03"])
        self.assertNotEqual(self.events[0]["control_id"], self.events[1]["control_id"])

    def test_parser_interoperability_and_all_source_facts(self):
        for event in self.events:
            raw = event["hl7"]
            self.assertEqual(raw.count("\rMSH|"), 0)
            self.assertTrue(raw.endswith("\r"))
            parsed = parse_message(
                raw, find_groups=False, validation_level=VALIDATION_LEVEL.TOLERANT
            )
            self.assertEqual(parsed.msh.msh_9.to_er7(),
                             f"ADT^{event['event_type']}^ADT_{event['event_type']}")
            self.assertEqual(parsed.msh.msh_12.to_er7(), "2.5.1")
            self.assertEqual(parsed.msh.msh_10.to_er7(), event["control_id"])
            self.assertEqual(parsed.pid.pid_3.to_er7(),
                             "synthetic-person-001^^^JOHNSCREEKB^MR")
            self.assertEqual(parsed.pid.pid_7.to_er7(), "19800101")
            self.assertEqual(parsed.pid.pid_8.to_er7(), "F")
            self.assertEqual(parsed.pid.pid_10.to_er7(), "2106-3^White^CDCREC")
            self.assertEqual(parsed.pid.pid_22.to_er7(),
                             "2186-5^Not Hispanic or Latino^CDCREC")
            self.assertEqual(parsed.pv1.pv1_19.to_er7(),
                             "synthetic-visit-001^^^JOHNSCREEKB^VN")
            self.assertEqual(parsed.pv1.pv1_44.to_er7(), "20261105120000+0000")
            if event["event_type"] == "A03":
                self.assertEqual(parsed.pv1.pv1_45.to_er7(), "20261106100000+0000")
            else:
                self.assertFalse(getattr(parsed.pv1, "pv1_45", None))

    def test_repeat_emits_identical_hl7_bytes(self):
        out = subprocess.run(
            ["node", "-e", NODE_EMIT], cwd=ROOT, check=True,
            capture_output=True, text=True,
        )
        self.assertEqual(out.stdout, json.dumps(self.events, separators=(",", ":")))
        print("OIE_ADT_V2_INDEPENDENT_HL7APY_READBACK_PASS events=2")


if __name__ == "__main__":
    unittest.main()
