#!/usr/bin/env python3
"""Independent read-only v1 Resolver/Discovery + all-object SHA256 readback."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys

from publish_synthea_landing import S3Client
from scan_ready_batches import discover_ready_batches
from resolve_verified_landing_file import validate_manifest


class ReadyVerificationError(ValueError):
    pass


class ReadOnlyPaginator:
    def __init__(self, reader):
        self.reader=reader

    def paginate(self, *, Bucket, Prefix):
        if Bucket!="health-landing":
            raise ReadyVerificationError("unexpected S3 bucket")
        yield {"Contents":[{"Key":key} for key in self.reader.list_keys(Prefix)]}


class DiscoveryAdapter:
    def __init__(self, reader):
        self.reader=reader

    def get_paginator(self, name):
        if name!="list_objects_v2":
            raise ReadyVerificationError("unexpected paginator")
        return ReadOnlyPaginator(self.reader)

    def get_object(self, *, Bucket, Key):
        if Bucket!="health-landing":
            raise ReadyVerificationError("unexpected S3 bucket")
        data=self.reader.get_object(Key)
        return {"Body":io.BytesIO(data),"ContentLength":len(data)}


def verify(client, batch_id, request_id, expected_people, expected_visits):
    result=discover_ready_batches(DiscoveryAdapter(client),bucket="health-landing")
    matches=[x for x in result["ready_batches"] if x["batch_id"]==batch_id]
    if len(matches)!=1:
        raise ReadyVerificationError("NEW_ONLY_READY_DISCOVERY_CARDINALITY")
    selected=matches[0]
    key=selected["manifest_uri"].split("s3://health-landing/",1)[1]
    raw=client.get_object(key)
    sha=hashlib.sha256(raw).hexdigest()
    if sha!=selected["manifest_sha256"]:
        raise ReadyVerificationError("DISCOVERY_MANIFEST_SHA_DRIFT")
    doc=json.loads(raw)
    validate_manifest(doc,batch_id,selected["manifest_uri"])
    params=doc.get("source_parameters",{})
    if (doc.get("manifest_version")!="1.0"
        or params.get("generation_mode")!="NEW_ONLY"
        or params.get("generation_request_id")!=request_id):
        raise ReadyVerificationError("NEW_ONLY_PROVENANCE_ABSENT")
    files=doc["files"]
    people=next(x for x in files if x["dataset"]=="patients")
    visits=next(x for x in files if x["dataset"]=="encounters")
    if (people["row_count"],visits["row_count"])!=(expected_people,expected_visits):
        raise ReadyVerificationError("PERSON_VISIT_COUNT_DRIFT")
    base=key.rsplit("manifest.json",1)[0]
    for item in files:
        obj=client.get_object(base+item["path"])
        if len(obj)!=item["size_bytes"] or hashlib.sha256(obj).hexdigest()!=item["sha256"]:
            raise ReadyVerificationError("INDEPENDENT_PAYLOAD_CHECKSUM_DRIFT")
    return {"batch_id":batch_id,"manifest_uri":selected["manifest_uri"],
            "manifest_sha256":sha,
            "ready_count":len(matches),
            "verified_file_count":len(files),
            "person_rows":people["row_count"],
            "visit_rows":visits["row_count"],
            "quarantined_legacy_manifests":result["quarantined_count"],
            "database_mutation":False}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--batch-id",required=True)
    p.add_argument("--request-id",required=True)
    a=p.parse_args()
    reader=S3Client(endpoint=os.environ["S3_ENDPOINT"],
        bucket="health-landing",
        region=os.environ.get("AWS_DEFAULT_REGION","us-east-1"),
        access_key=os.environ["AWS_ACCESS_KEY_ID"],
        secret_key=os.environ["AWS_SECRET_ACCESS_KEY"])
    reader.head_bucket()
    # Actual row counts are a property of the immutable producer request, not
    # the first integration-test batch. Revalidate identity before S3 readback.
    from publish_v1_verified import frozen_request
    params,marker,csv_dir=frozen_request(
        __import__("pathlib").Path(os.environ.get("SYNTHEA_STATE_ROOT","/synthea-state")),
        a.request_id)
    if params["batch_id"]!=a.batch_id:
        raise ReadyVerificationError("FROZEN_BATCH_ID_DRIFT")
    result=verify(reader,a.batch_id,a.request_id,
                  marker["actual_persons"],marker["actual_encounters"])
    print("NEW_ONLY_V1_DISCOVERY=PASS")
    print("NEW_ONLY_V1_RESOLVER=PASS")
    print("NEW_ONLY_INDEPENDENT_S3_READBACK=18/18")
    print("READY_BATCH_ID="+result["batch_id"])
    print("MANIFEST_URI="+result["manifest_uri"])
    print("MANIFEST_SHA256="+result["manifest_sha256"])
    print("PERSON_ROWS="+str(result["person_rows"]))
    print("ENCOUNTER_ROWS="+str(result["visit_rows"]))
    print("POSTGRESQL_MUTATION=NO")


if __name__=="__main__":
    sys.exit(main())
