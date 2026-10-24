"""Split verified Synthea FHIR bundles into single-Encounter OIE inputs.

This performs *no* clinical admission classification. OIE owns that logic.
Never modifies upstream files; failed Patient references block processing.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

def events_from_bundle(bundle: dict, request_id: str) -> list[dict]:
    if not isinstance(bundle, dict) or bundle.get("resourceType") != "Bundle":
        raise ValueError("NOT_FHIR_BUNDLE")
    if not isinstance(request_id, str) or not request_id or len(request_id) > 66:
        raise ValueError("INVALID_REQUEST_ID")
    entries = bundle.get("entry")
    if not isinstance(entries, list):
        raise ValueError("MISSING_ENTRIES")
    people = {}
    for row in entries:
        resource = row.get("resource") if isinstance(row, dict) else None
        if not isinstance(resource, dict) or resource.get("resourceType") != "Patient":
            continue
        ident = resource.get("id")
        if not isinstance(ident, str) or not ident:
            raise ValueError("INVALID_PATIENT_ID")
        for key in ("Patient/" + ident, row.get("fullUrl")):
            if key:
                if key in people:
                    raise ValueError("DUPLICATE_PATIENT_REFERENCE")
                people[key] = row
    items = []
    encounter_ids = set()
    for row in entries:
        resource = row.get("resource") if isinstance(row, dict) else None
        if not isinstance(resource, dict) or resource.get("resourceType") != "Encounter":
            continue
        ident = resource.get("id")
        if not isinstance(ident, str) or not ident or ident in encounter_ids:
            raise ValueError("INVALID_OR_DUPLICATE_ENCOUNTER_ID")
        encounter_ids.add(ident)
        reference = resource.get("subject", {}).get("reference")
        if reference not in people:
            raise ValueError("ENCOUNTER_PATIENT_NOT_PRESENT")
        # Preserve original Patient/Encounter resources and fullUrls unchanged.
        source = {"resourceType": "Bundle", "type": "collection",
                  "entry": [people[reference], row]}
        items.append({"request_id": request_id, "bundle": source})
    return items

def main() -> int:
    p=argparse.ArgumentParser(description="Read-only event envelope preparation")
    p.add_argument("--input",required=True,type=Path)
    p.add_argument("--request-id",required=True)
    args=p.parse_args()
    if args.input.is_symlink() or not args.input.is_file():
        raise SystemExit("MISSING_OR_UNSAFE_FHIR_BUNDLE")
    raw=json.loads(args.input.read_text(encoding="utf-8"))
    for event in events_from_bundle(raw,args.request_id):
        print(json.dumps(event,sort_keys=True,separators=(",",":")))
    return 0

if __name__=="__main__":
    sys.exit(main())
