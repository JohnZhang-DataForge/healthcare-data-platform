"""Create a NEW synthetic OIE V2 HL7/manifest fixture, never use stored P2 data.

Run only for offline CI. Calls the actual repository source Mapper through
Node.js on an entirely synthetic FHIR Bundle. No Blob/OIE/cloud access.
"""
from __future__ import annotations

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
const OID = "urn:oid:2.16.840.1.113883.6.238";
const person = {
 resourceType:"Patient",id:"patient-one",
 name:[{family:"Synthetic",given:["Test"]}],
 birthDate:"1980-01-01",gender:"female",
 extension:[
  {url:"http://hl7.org/fhir/us/core/StructureDefinition/us-core-race",
   extension:[{url:"ombCategory",valueCoding:{system:OID,code:"2028-9"}}]},
  {url:"http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity",
   extension:[{url:"ombCategory",valueCoding:{system:OID,code:"2135-2"}}]}
 ]};
const encounter = {
 resourceType:"Encounter",id:"visit-one",status:"finished",
 class:{system:"http://terminology.hl7.org/CodeSystem/v3-ActCode",code:"IMP"},
 subject:{reference:"Patient/patient-one"},
 period:{start:"2026-11-05T07:00:00-05:00",end:"2026-11-06T05:00:00-05:00"}};
const cfg = {
 hospital_id:"johns-creek-hospital-b",
 feed_id:"johns-creek-hospital-b-hl7-v2",
 request_id:"johnscreek-hl7-gh-12345678901",
 assigning_authority:"JOHNSCREEKB"
};
process.stdout.write(JSON.stringify(
 mapper({resourceType:"Bundle",type:"collection",
         entry:[{resource:person},{resource:encounter}]},cfg).messages
));
"""


def generate(root: Path) -> tuple[Path, Path, str]:
    mapper = REPO / "local-data-platform/apps/clinical_producers/oie/adt_events_v2.js"
    output = subprocess.run(["node", "-e", NODE, str(mapper)],
                            check=True, capture_output=True, text=True, timeout=30)
    messages = json.loads(output.stdout)
    if [message["event_type"] for message in messages] != ["A01", "A03"]:
        raise RuntimeError("SYNTHETIC_OIE_V2_SOURCE_MAPPER_CONTRACT_CHANGED")
    blob_root = root / "staged-local-blob-keys"
    objects = []
    for message in messages:
        key = (f"clinical/v1/{HOSPITAL}/{FEED}/{REQUEST}/HL7_V2/hl7/"
               f"{message['encounter_id']}-{message['event_type']}.hl7")
        raw = message["hl7"].encode("utf-8")
        path = blob_root / key
        path.parent.mkdir(parents=True, exist_ok=True)
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
    manifest_bytes = json.dumps(
        manifest, separators=(",", ":"), sort_keys=True).encode("utf-8")
    path = root / "landing-manifest.json"
    path.write_bytes(manifest_bytes)
    return path, blob_root, hashlib.sha256(manifest_bytes).hexdigest()


if __name__ == "__main__":
    root = Path(sys.argv[1])
    root.mkdir(parents=True, exist_ok=True)
    manifest, blob, sha = generate(root)
    print("HL7_SYNTHETIC_FIXTURE_ONLY=YES")
    print("HL7_SYNTHETIC_MANIFEST_PATH=" + str(manifest))
    print("HL7_SYNTHETIC_BLOB_ROOT=" + str(blob))
    print("HL7_SYNTHETIC_MANIFEST_SHA256=" + sha)
