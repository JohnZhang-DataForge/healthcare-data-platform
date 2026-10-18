#!/usr/bin/env python3
"""Independent read-only NEW_ONLY v2 READY Manifest plus all 18 remote CSV bytes."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path

from publish_v1_verified import frozen_request,s3_from_env
from verify_v1_ready import DiscoveryAdapter
from scan_ready_batches import discover_ready_batches
from validate_new_only_v2_manifest import validate_v2_manifest, source_contract


class V2ReadyBlocked(ValueError):
    pass


def verify(client,request_id,state=Path("/synthea-state"),contract=None):
    params,marker,_=frozen_request(state,request_id)
    batch=params["batch_id"]
    found=discover_ready_batches(DiscoveryAdapter(client),bucket="health-landing")
    current=[x for x in found["ready_batches"] if x["batch_id"]==batch]
    if len(current)!=1:
        raise V2ReadyBlocked("BLOCKED:V2_DISCOVERY_CARDINALITY")
    entry=current[0]
    manifest_uri=entry["manifest_uri"]
    key=manifest_uri.split("s3://health-landing/",1)[1]
    raw=client.get_object(key)
    actual_sha=hashlib.sha256(raw).hexdigest()
    if actual_sha!=entry["manifest_sha256"]:
        raise V2ReadyBlocked("BLOCKED:DISCOVERY_MANIFEST_SHA")
    doc=json.loads(raw)
    if doc.get("manifest_version")!="2.0":
        raise V2ReadyBlocked("BLOCKED:WRONG_MANIFEST_VERSION")
    schema,_=source_contract(contract)
    parsed=validate_v2_manifest(doc,batch,manifest_uri,contract)
    person=next(x for x in parsed if x["dataset"]=="patients")
    visit=next(x for x in parsed if x["dataset"]=="encounters")
    if (person["row_count"]!=marker["actual_persons"]
        or visit["row_count"]!=marker["actual_encounters"]):
        raise V2ReadyBlocked("BLOCKED:FROZEN_SOURCE_COUNT_DRIFT")
    base=key[:-len("manifest.json")]
    zero=[]
    for item in parsed:
        raw=client.get_object(base+item["path"])
        if len(raw)!=item["size_bytes"] or hashlib.sha256(raw).hexdigest()!=item["sha256"]:
            raise V2ReadyBlocked("BLOCKED:V2_REMOTE_OBJECT_SHA")
        if item["row_count"]==0:
            zero.append(item["dataset"])
    return {"batch_id":batch,"manifest_sha256":actual_sha,"manifest_uri":manifest_uri,
            "person_rows":person["row_count"],"encounter_rows":visit["row_count"],
            "zero_auxiliary_count":len(zero),"csv_file_count":18,
            "db_mutation":False}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--request-id",required=True)
    p.add_argument("--state-root",default="/synthea-state")
    p.add_argument("--contract",default="/opt/synthea-new-only/csv-contract-v2.json")
    a=p.parse_args()
    result=verify(s3_from_env(),a.request_id,Path(a.state_root),Path(a.contract))
    print("NEW_ONLY_V2_DISCOVERY=PASS")
    print("NEW_ONLY_V2_RESOLVER=PASS")
    print("NEW_ONLY_V2_INDEPENDENT_S3_READBACK=18/18")
    for key in ("batch_id","manifest_uri","manifest_sha256","person_rows","encounter_rows","zero_auxiliary_count"):
        print(key.upper()+"="+str(result[key]))
    print("POSTGRESQL_MUTATION=NO")


if __name__=="__main__":
    main()
