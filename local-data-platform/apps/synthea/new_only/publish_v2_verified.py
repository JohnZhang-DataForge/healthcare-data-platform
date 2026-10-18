#!/usr/bin/env python3
"""NEW_ONLY v2 immutable S3 publisher; standalone from legacy v1 Publisher.

A zero-row auxiliary file is valid only if it retains its exact CSV header.
This code never executes Generator, Airflow, PostgreSQL or old v1 publisher.
"""
from __future__ import annotations
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

from publish_v1_verified import frozen_request, s3_from_env
from prepublish_gate import audit_local
from publish_synthea_landing import (
    S3Client, PublishError, canonical_json_bytes, build_final_manifest,
    resolve_batch_prefix, inspect_batch_keys, expected_payload_keys,
    sha256_bytes, sha256_file,
)
from validate_new_only_v2_manifest import (
    validate_v2_manifest, V2ContractError, source_contract, CONTRACT_RELATIVE,
)

ROOT_PREFIX="source=synthea/source_version=v3.3.0/"
RELEASE_POLICY_PATH=Path("/opt/synthea-new-only/ready-publication-policy-v1.json")
RELEASE_POLICY_VERSION="new-only-v2-ready-release-v1"
APPROVED_V2_CONSUMER_IMAGE="ghcr.io/johnzhang-dataforge/healthcare-landing-discovery@sha256:059d94e4d1348c194956203fea6b19be23ec39595127eea397419e66fa4e5924"
APPROVED_DAGRUN="https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38496119114"
APPROVED_CONTRACT_SHA256="d7118f4bc3306d74911e609b4f0a41b9340ba9a60acaa69174063d5025ad1249"


class V2PublishBlocked(ValueError):
    pass


def block(code):
    raise V2PublishBlocked("BLOCKED:NEW_ONLY_V2_"+code)


def require_live_consumer_release(contract_path:Path,policy_path:Path=RELEASE_POLICY_PATH)->str:
    """Explicit reviewed release authorization; preserve immutable CSV contract SHA.

    The original v2 contract includes a historical predeployment state; editing
    it would invalidate the deployed Reader's pinned contract SHA. A separate,
    versioned policy records successful *actual* Airflow v2 deployment. Neither
    AWS/S3 audit flags nor a caller-supplied environment variable can replace
    this pinned code-and-file validation.
    """
    schema,actual_sha=source_contract(contract_path)
    if actual_sha!=APPROVED_CONTRACT_SHA256:
        block("READER_CONTRACT_SHA_CHANGED")
    if schema.get("consumer_compatibility")!="NOT_YET_DEPLOYED_DO_NOT_PUBLISH_READY":
        block("READER_CONTRACT_BYTES_MODIFIED")
    if not policy_path.is_file():
        block("VERSIONED_RELEASE_POLICY_MISSING")
    policy=json.loads(policy_path.read_text(encoding="utf-8"))
    scope=policy.get("scope") if isinstance(policy,dict) else None
    consumer=policy.get("consumer") if isinstance(policy,dict) else None
    pinned=policy.get("immutable_contract") if isinstance(policy,dict) else None
    if (policy.get("policy_version")!=RELEASE_POLICY_VERSION
        or policy.get("release_decision")!="V2_RUNTIME_CONSUMER_DEPLOYED_READY"
        or not isinstance(scope,dict)
        or scope.get("generation_mode")!="NEW_ONLY"
        or scope.get("manifest_version")!="2.0"
        or scope.get("publication")!="S3_LANDING_IMMUTABLE_MANIFEST_LAST"
        or scope.get("airflow_claim")!="NO"
        or scope.get("postgresql_mutation")!="NO"
        or not isinstance(consumer,dict)
        or consumer.get("image")!=APPROVED_V2_CONSUMER_IMAGE
        or consumer.get("dag")!="landing_batch_discovery"
        or consumer.get("evidence_workflow")!=APPROVED_DAGRUN
        or consumer.get("evidence_result")!="success"
        or consumer.get("reference_commit")!="a6b87497497fb1b1367c0646e3410a24ed4f7ec3"
        or not isinstance(pinned,dict)
        or pinned.get("path")!=CONTRACT_RELATIVE
        or pinned.get("sha256")!=actual_sha):
        block("VERSIONED_CONSUMER_RELEASE_POLICY_INVALID")
    return actual_sha


def build_draft(state:Path, request_id:str, contract_path:Path)->tuple[dict,Path]:
    """Inspect complete frozen genuine Synthea CSV; never invent rows."""
    params, marker, directory=frozen_request(state,request_id)
    contract, contract_sha=source_contract(contract_path)
    measured=audit_local(directory, contract_path)
    if measured["person_rows"]!=marker["actual_persons"] or measured["visit_rows"]!=marker["actual_encounters"]:
        block("FROZEN_REQUIRED_ROW_COUNT_DRIFT")
    frozen_files=marker.get("files")
    if not isinstance(frozen_files,dict) or set(frozen_files)!={x["filename"] for x in contract["files"]}:
        block("FROZEN_CSV_INVENTORY_DRIFT")
    files=[]
    total=0
    for item in contract["files"]:
        name=item["filename"]
        current=measured["files"][name]
        original=frozen_files[name]
        if (original.get("rows")!=current["row_count"] or
            original.get("sha256")!=current["sha256"]):
            block("FROZEN_CSV_SHA_OR_ROWS_DRIFT_"+name)
        if current["size_bytes"]>512*1024*1024:
            block("MAX_OBJECT_BYTES_"+name)
        total+=current["size_bytes"]
        files.append({
            "path":"payload/csv/"+name,
            "dataset":item["dataset"],"header":item["header"],
            "row_count":current["row_count"],
            "size_bytes":current["size_bytes"],
            "sha256":current["sha256"]
        })
    if total>2*1024*1024*1024:
        block("TOTAL_OBJECT_BYTES")
    fingerprint=hashlib.sha256()
    for obj in sorted(files,key=lambda x:x["path"]):
        filename=obj["path"].rsplit("/",1)[-1]
        fingerprint.update((filename+"|"+obj["sha256"]+"\n").encode())
    batch=params["batch_id"]
    draft={
        "manifest_version":"2.0","status":"LOCAL_VALIDATED_NOT_UPLOADED",
        "source":"synthea","source_version":"v3.3.0",
        "batch_id":batch,"payload_format":"csv","expected_file_count":18,
        "files":files,
        "contract":{"path":CONTRACT_RELATIVE,"sha256":contract_sha},
        "source_parameters":{
            "generation_mode":"NEW_ONLY",
            "generation_request_id":request_id,
            "population_size":params["target_population"],
            "seed":params["seed"],"clinician_seed":params["clinician_seed"],
            "reference_date":params["reference_date"],
            "state":params["state"],"city":params.get("city"),
        },
        "source_provenance":{
            "synthea_version":params["synthea_version"],
            "synthea_commit":params["synthea_commit"],
            "generator_params_sha256":sha256_file(state/"new-only"/"requests"/request_id/"params.json"),
            "generator_local_validation_sha256":sha256_file(state/"new-only"/"requests"/request_id/"validated.json"),
        },
        "payload_fingerprint":fingerprint.hexdigest(),
    }
    print("NEW_ONLY_V2_DRAFT=PASS")
    print("PERSON_ROWS="+str(measured["person_rows"]))
    print("ENCOUNTER_ROWS="+str(measured["visit_rows"]))
    print("AUXILIARY_ZERO_ROWS="+str(len(measured["zero_row_optional_files"])))
    print("V2_REAL_CSV_COUNT=18")
    return draft,directory


def validate_final(draft,final,ingest_date,landing_uri,contract_path):
    if not isinstance(final,dict):
        block("MANIFEST_TYPE")
    manifest_uri=landing_uri+"manifest.json"
    validate_v2_manifest(final,draft["batch_id"],manifest_uri,contract_path)
    for field in ("manifest_version","source","source_version","batch_id",
                  "expected_file_count","payload_format","source_parameters",
                  "source_provenance","contract","files","payload_fingerprint"):
        if final.get(field)!=draft.get(field):
            block("IMMUTABLE_MANIFEST_DRIFT_"+field)
    if final.get("landing_uri")!=landing_uri or final.get("ingest_date")!=ingest_date:
        block("MANIFEST_PREFIX_DRIFT")


def publish(client:S3Client,draft:dict,directory:Path,contract_path:Path,
            *,replay:bool=False,ingest_date:str|None=None)->dict:
    # No API call may alter other batches; never synthesize a v2 manifest
    # without prior frozen source, S3 history, PG source identity audit.
    if not replay:
        if os.environ.get("NEW_ONLY_READONLY_SOURCE_AUDIT")!="PASS":
            block("HISTORIC_S3_AUDIT_MISSING")
        if os.environ.get("NEW_ONLY_PG_SOURCE_AUDIT")!="PASS":
            block("PG_SOURCE_AUDIT_MISSING")
    default_date=ingest_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    client.head_bucket()
    prefix,date,_=resolve_batch_prefix(client.list_keys(ROOT_PREFIX),ROOT_PREFIX,
                                       draft["batch_id"],default_date)
    uri="s3://health-landing/"+prefix
    before=client.list_keys(prefix)
    current,manifest_present=inspect_batch_keys(draft,prefix,before)
    expected=expected_payload_keys(draft,prefix)
    manifest_key=prefix+"manifest.json"
    if replay and not manifest_present:
        block("REPLAY_REQUIRES_EXISTING_MANIFEST")

    # Inspect all previously written bytes (including crash-restored payloads).
    for key in sorted(current):
        obj=client.get_object(key)
        if len(obj)!=expected[key]["size_bytes"] or sha256_bytes(obj)!=expected[key]["sha256"]:
            block("PREEXISTING_PAYLOAD_CONFLICT")

    if manifest_present:
        if len(current)!=18:
            block("MANIFEST_HAS_MISSING_PAYLOADS")
        raw=client.get_object(manifest_key)
        try:
            final=json.loads(raw)
        except (ValueError,UnicodeError) as exc:
            raise V2PublishBlocked("BLOCKED:INVALID_EXISTING_V2_MANIFEST") from exc
        validate_final(draft,final,date,uri,contract_path)
        # Independent readback even when replaying existing Manifest.
        for key,item in expected.items():
            obj=client.get_object(key)
            if len(obj)!=item["size_bytes"] or sha256_bytes(obj)!=item["sha256"]:
                block("REPLAY_PAYLOAD_DRIFT")
        return {"publish_mode":"REUSE_EXISTING","manifest_sha256":sha256_bytes(raw),
                "manifest_uri":uri+"manifest.json","file_count":18,
                "manifest_version":"2.0","ingest_date":date}

    # New manifest may only be published after an exact 18-object readback.
    if replay:
        block("REPLAY_NOT_PUBLISHED")
    for key in sorted(set(expected)-current):
        item=expected[key]
        if client.head_object(key):
            remote=client.get_object(key)
            if len(remote)!=item["size_bytes"] or sha256_bytes(remote)!=item["sha256"]:
                block("CONCURRENT_PAYLOAD_CONFLICT")
        else:
            local=directory/key.rsplit("/",1)[-1]
            client.put_object(key,local.read_bytes())
    after,concurrent_manifest=inspect_batch_keys(draft,prefix,client.list_keys(prefix))
    if len(after)!=18:
        block("REMOTE_INCOMPLETE_PAYLOAD")
    for key,item in expected.items():
        remote=client.get_object(key)
        if len(remote)!=item["size_bytes"] or sha256_bytes(remote)!=item["sha256"]:
            block("REMOTE_SHA256_READBACK")
    if concurrent_manifest or client.head_object(manifest_key):
        raw=client.get_object(manifest_key)
        validate_final(draft,json.loads(raw),date,uri,contract_path)
        mode="REUSE_CONCURRENT_MANIFEST"
    else:
        final=build_final_manifest(draft,date,uri,
               datetime.now(timezone.utc).isoformat(),draft["payload_fingerprint"])
        validate_final(draft,final,date,uri,contract_path)
        raw=canonical_json_bytes(final)
        # This PUT must be the last new object created for this batch.
        client.put_object(manifest_key,raw)
        mode="PUBLISHED_NEW"
    got=client.get_object(manifest_key)
    validate_final(draft,json.loads(got),date,uri,contract_path)
    if mode=="PUBLISHED_NEW" and got!=raw:
        block("MANIFEST_READBACK_MISMATCH")
    return {"publish_mode":mode,"manifest_sha256":sha256_bytes(got),
            "manifest_uri":uri+"manifest.json","file_count":18,
            "manifest_version":"2.0","ingest_date":date}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--request-id",required=True)
    ap.add_argument("--phase",choices=("validate","publish","replay"),required=True)
    ap.add_argument("--state-root",default="/synthea-state")
    ap.add_argument("--contract",default="/opt/synthea-new-only/csv-contract-v2.json")
    ap.add_argument("--ingest-date")
    args=ap.parse_args()
    try:
        contract=Path(args.contract)
        draft,directory=build_draft(Path(args.state_root),args.request_id,contract)
        if args.phase=="validate":
            print("S3_MUTATION=NO")
            return 0
        if args.phase=="publish":
            # Approved policy is pinned to actual Airflow DagRun + its immutable
            # Reader image and the exact original contract bytes. S3/PG source
            # collision audits remain separate mandatory pre-PUT gates.
            matched_sha=require_live_consumer_release(contract)
            print("V2_CONSUMER_RELEASE_POLICY=PASS")
            print("V2_CONSUMER_CONTRACT_SHA256="+matched_sha)
        result=publish(s3_from_env(),draft,directory,contract,
                       replay=args.phase=="replay",ingest_date=args.ingest_date)
        print("NEW_ONLY_V2_S3_PUBLISH=PASS")
        for field in ("publish_mode","manifest_uri","manifest_sha256","manifest_version","file_count"):
            print(field.upper()+"="+str(result[field]))
        print("S3_PAYLOAD_READBACK_SHA256=18/18")
        print("POSTGRESQL_MUTATION=NO")
        return 0
    except (V2PublishBlocked,PublishError,V2ContractError,KeyError,ValueError,OSError) as exc:
        print("NEW_ONLY_V2_PUBLISH_BLOCKED="+str(exc).split("\n",1)[0],file=sys.stderr)
        return 1


if __name__=="__main__":
    sys.exit(main())
