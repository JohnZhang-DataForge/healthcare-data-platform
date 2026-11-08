"""Fresh synthetic FHIR -> real OIE V2 mapper -> HL7 Raw + manifest.

Offline integration fixture only, no Synthea/JVM generation and NO real
OIE POST, Blob PUT, Fabric or Silver. Patient count 1 preserves the former
single-person regression; count 10 tests a separate multi-patient Candidate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parents[4]
REQUEST = "johnscreek-hl7-gh-12345678901"
SOURCE_SHA = "a" * 64
HOSPITAL = "johns-creek-hospital-b"
FEED = "johns-creek-hospital-b-hl7-v2"

NODE = r"""
const mapper = require(process.argv[1]).fhirToHl7AdtEventsV2;
const count = Number(process.argv[2] || "1");
if (![1,10].includes(count)) throw new Error("UNAPPROVED_SYNTHETIC_COUNT");
const OID = "urn:oid:2.16.840.1.113883.6.238";
const races = ["2028-9", "2106-3", "2054-5"];
const ethnicities = ["2135-2", "2186-5"];
const cfg = {
 hospital_id:"johns-creek-hospital-b",
 feed_id:"johns-creek-hospital-b-hl7-v2",
 request_id:"johnscreek-hl7-gh-12345678901",
 assigning_authority:"JOHNSCREEKB"
};
let messages=[];
for (let i=1;i<=count;i++){
 const ix=String(i).padStart(2,"0");
 const pid=count===1 ? "patient-one" : "patient-"+ix;
 const eid=count===1 ? "visit-one" : "visit-"+ix;
 const code=count===1 ? "2028-9" : races[(i-1)%races.length];
 const ethnicity=count===1 ? "2135-2" : ethnicities[(i-1)%2];
 const birth=count===1 ? "1980-01-01" :
  String(1970+i)+"-"+String(1+(i%12)).padStart(2,"0")+"-15";
 const status=(count===1 || i%3!==0) ? "finished" : "in-progress";
 const person = {
  resourceType:"Patient", id:pid,
  name:[{family:"Synthetic",given:["Test"]}],
  birthDate:birth,gender:i%2===0?"male":"female",
  extension:[
   {url:"http://hl7.org/fhir/us/core/StructureDefinition/us-core-race",
    extension:[{url:"ombCategory",valueCoding:{system:OID,code:code}}]},
   {url:"http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity",
    extension:[{url:"ombCategory",valueCoding:{system:OID,code:ethnicity}}]}
  ]};
 const encounter = {
  resourceType:"Encounter",id:eid,status:status,
  class:{system:"http://terminology.hl7.org/CodeSystem/v3-ActCode",code:"IMP"},
  subject:{reference:"Patient/"+pid},
  period:{start:"2026-11-05T07:00:00-05:00"}};
 if(status==="finished") encounter.period.end="2026-11-06T05:00:00-05:00";
 const out=mapper({resourceType:"Bundle",type:"collection",
  entry:[{resource:person},{resource:encounter}]},cfg);
 if (out.messages.length !== (status==="finished" ? 2:1)) {
   throw new Error("UNEXPECTED_V2_ELIGIBILITY");
 }
 if (out.messages[0].event_type!=="A01" ||
     (status==="finished" && out.messages[1].event_type!=="A03")) {
   throw new Error("UNEXPECTED_V2_A01_A03_ORDER");
 }
 messages.push(...out.messages);
}
process.stdout.write(JSON.stringify(messages));
"""


def generate(root: Path, *, patients: int = 1) -> tuple[Path, Path, str]:
    if type(patients) is not int or patients not in (1, 10):
        raise ValueError("UNAPPROVED_SYNTHETIC_POPULATION")
    mapper = REPO / "local-data-platform/apps/clinical_producers/oie/adt_events_v2.js"
    output = subprocess.run(
        ["node", "-e", NODE, str(mapper), str(patients)],
        check=True, capture_output=True, text=True, timeout=30)
    messages = json.loads(output.stdout)
    expected_types = ([["A01","A03"]] if patients == 1 else [
        ["A01","A03"] if i % 3 else ["A01"] for i in range(1, 11)])
    expected = [typ for group in expected_types for typ in group]
    if [m["event_type"] for m in messages] != expected:
        raise RuntimeError("SYNTHETIC_OIE_V2_SOURCE_MAPPER_CONTRACT_CHANGED")
    if len({m["control_id"] for m in messages}) != len(messages):
        raise RuntimeError("SYNTHETIC_OIE_V2_DUPLICATE_CONTROL_ID")

    blob_root = root / "staged-local-blob-keys"
    objects = []
    for message in messages:
        key = (f"clinical/v1/{HOSPITAL}/{FEED}/{REQUEST}/HL7_V2/hl7/"
               f"{message['encounter_id']}-{message['event_type']}.hl7")
        raw = message["hl7"].encode("utf-8")
        path = blob_root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            raise RuntimeError("SYNTHETIC_OIE_V2_DUPLICATE_BLOB_PATH")
        path.write_bytes(raw)
        objects.append({
            "blob_key": key, "sha256": hashlib.sha256(raw).hexdigest(),
            "size_bytes": len(raw), "source_event_id": message["control_id"],
            "etag": '"new-synthetic-fixture-not-azure"',
            "version_id": None,
        })
    manifest = {
        "schema_version": "healthcare-azure-blob-landing-manifest-v1",
        "hospital_id": HOSPITAL, "feed_id": FEED, "request_id": REQUEST,
        "source_manifest_sha256": SOURCE_SHA,
        "target_format": "HL7_V2", "skipped_non_admissions": 0,
        "objects": objects,
    }
    raw = json.dumps(
        manifest, separators=(",", ":"), sort_keys=True).encode("utf-8")
    path = root / "landing-manifest.json"
    if path.exists():
        raise RuntimeError("SYNTHETIC_OIE_V2_MANIFEST_EXISTS")
    path.write_bytes(raw)
    return path, blob_root, hashlib.sha256(raw).hexdigest()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--patients", type=int, choices=(1, 10), default=1)
    options = ap.parse_args()
    options.root.mkdir(parents=True, exist_ok=False)
    manifest, blob, sha = generate(options.root, patients=options.patients)
    print("HL7_SYNTHETIC_FIXTURE_ONLY=YES")
    print("HL7_SYNTHETIC_PATIENTS=" + str(options.patients))
    print("HL7_SYNTHETIC_EVENTS=" + str(
        2 if options.patients == 1 else 17))
    print("HL7_SYNTHETIC_MANIFEST_PATH=" + str(manifest))
    print("HL7_SYNTHETIC_BLOB_ROOT=" + str(blob))
    print("HL7_SYNTHETIC_MANIFEST_SHA256=" + sha)
