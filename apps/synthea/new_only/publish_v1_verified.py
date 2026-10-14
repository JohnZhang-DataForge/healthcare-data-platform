#!/usr/bin/env python3
"""NEW_ONLY v1-compatible immutable S3 publisher.

The source is an already frozen NEW_ONLY request on worker01 PVC.
This module CANNOT create new Synthea people, touch PostgreSQL, or
change historical Airflow/Writer code. Existing v1 contracts stay frozen.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

# A dedicated NEW_ONLY entrypoint, reusing battle-tested v1 internals.
from publish_synthea_landing import (
    S3Client, PublishError, publish_batch, validate_local_draft,
    sha256_bytes, validate_final_manifest,
)

REQUEST_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{7,65}$")
SOURCE_VERSION = "v3.3.0"
COMMIT = "995cf2fd33e67918d4e33110d9f68ad248002221"
BASE = "source=synthea/source_version=v3.3.0/"


class NewOnlyBlocked(RuntimeError):
    pass


def block(reason: str) -> None:
    raise NewOnlyBlocked("BLOCKED:" + reason)


def file_sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for data in iter(lambda:f.read(1024*1024),b""):
            h.update(data)
    return h.hexdigest()


def frozen_request(state: Path, request: str) -> tuple[dict, dict, Path]:
    if not REQUEST_RE.fullmatch(request):
        block("REQUEST_ID_INVALID")
    root=state/"new-only"/"requests"/request
    if not root.is_dir():
        block("REQUEST_NOT_ON_PVC")
    params_path=root/"params.json"
    marker_path=root/"validated.json"
    if not params_path.is_file() or not marker_path.is_file():
        block("GENERATOR_NOT_LOCALLY_VALIDATED")
    params=json.loads(params_path.read_text())
    marker=json.loads(marker_path.read_text())
    batch="synthea-new-only-"+request
    if (params.get("generation_request_id")!=request
        or params.get("batch_id")!=batch
        or params.get("synthea_commit")!=COMMIT
        or params.get("synthea_version")!=SOURCE_VERSION
        or marker.get("generation_request_id")!=request
        or marker.get("batch_id")!=batch
        or marker.get("state")!="LOCAL_CSV_VALIDATED_NOT_PUBLISHED"
        or marker.get("params_sha256")!=file_sha(params_path)
        or marker.get("publication_eligible") is not False
        or marker.get("legacy_18_csv_nonempty_contract_applied") is not False):
        block("FROZEN_REQUEST_IDENTITY_DRIFT")
    population=params.get("target_population")
    if type(population) is not int or not 1<=population<=100:
        block("FROZEN_POPULATION_INVALID")
    csv_dir=root/"csv"
    if not csv_dir.is_dir():
        block("LOCAL_SOURCE_CSV_MISSING")
    if len(marker.get("person_id_hashes",[]))!=marker.get("actual_persons"):
        block("FROZEN_PERSON_REGISTRY_DRIFT")
    # Check the current CSV's Person identity against validated state.
    patient_file=csv_dir/"patients.csv"
    if not patient_file.is_file():
        block("MISSING_PATIENTS")
    person_ids=[]
    with patient_file.open("r",encoding="utf-8-sig",newline="") as f:
        rd=csv.DictReader(f)
        for row in rd:
            person_ids.append(row.get("Id",""))
    actual=sorted(hashlib.sha256(("synthea-source:"+p).encode()).hexdigest()
                  for p in person_ids if p)
    if (not person_ids or len(person_ids)!=len(set(person_ids))
        or actual!=marker["person_id_hashes"]
        or len(actual)!=marker["actual_persons"]):
        block("PERSON_SOURCE_REGISTRY_DRIFT")
    return params,marker,csv_dir


def enforce_v1_metadata(draft: dict, params: dict, marker: dict,
                        params_path: Path, marker_path: Path, request: str) -> dict:
    """Add only v1-compatible OPTIONAL provenance fields, never weaken v1."""
    batch="synthea-new-only-"+request
    if (draft.get("manifest_version")!="1.0"
        or draft.get("status")!="LOCAL_VALIDATED_NOT_UPLOADED"
        or draft.get("batch_id")!=batch
        or draft.get("expected_file_count")!=18
        or len(draft.get("files",[]))!=18):
        block("V1_DRAFT_INVALID")
    source=draft["source_parameters"]
    for key, value in {
        "population_size": params["target_population"],
        "seed": params["seed"],
        "clinician_seed": params["clinician_seed"],
        "reference_date": params["reference_date"],
        "state": params["state"],
    }.items():
        if source.get(key)!=value:
            block("SOURCE_PARAM_DRIFT_"+key)
    if marker.get("actual_persons")!=next(x["row_count"] for x in draft["files"] if x["dataset"]=="patients"):
        block("PERSON_ROWS_DRIFT")
    if marker.get("actual_encounters")!=next(x["row_count"] for x in draft["files"] if x["dataset"]=="encounters"):
        block("ENCOUNTER_ROWS_DRIFT")
    if any(x["row_count"]<=0 for x in draft["files"]):
        block("V1_REQUIRES_NONEMPTY_ALL_18")
    if source.get("generation_mode") not in (None,"NEW_ONLY"):
        block("PRODUCER_MODE_DRIFT")
    source["generation_mode"]="NEW_ONLY"
    source["generation_request_id"]=request
    provenance=draft["source_provenance"]
    provenance["generator_params_sha256"]=file_sha(params_path)
    provenance["generator_local_validation_sha256"]=file_sha(marker_path)
    return draft


def prepare(state: Path, request: str, validator: Path, contract: Path,
            scratch: Path) -> tuple[dict,dict,Path]:
    params,marker,csv_dir=frozen_request(state,request)
    if not validator.is_file() or not contract.is_file():
        block("V1_VALIDATOR_ASSET_MISSING")
    scratch.mkdir(parents=True,exist_ok=True)
    draft_path=scratch/"manifest.draft.v1.json"
    report_path=scratch/"strict-v1-validation.json"
    args=[
        "python3",str(validator),"--source-dir",str(csv_dir),
        "--contract",str(contract),
        "--batch-id",params["batch_id"],
        "--synthea-version",params["synthea_version"],
        "--synthea-commit",params["synthea_commit"],
        "--population-size",str(params["target_population"]),
        "--seed",str(params["seed"]),
        "--clinician-seed",str(params["clinician_seed"]),
        "--reference-date",params["reference_date"],
        "--state",params["state"],
        "--output",str(draft_path),
        "--report",str(report_path),
    ]
    if params.get("city"):
        args+=["--city",params["city"]]
    outcome=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                           text=True,check=False)
    if outcome.returncode!=0:
        # Fail-closed; avoid placing patient content in workflow logs.
        block("STRICT_V1_VALIDATOR_REJECTED")
    report=json.loads(report_path.read_text())
    if report.get("status")!="PASS" or report.get("validated_file_count")!=18:
        block("STRICT_V1_VALIDATION_INCOMPLETE")
    draft=enforce_v1_metadata(json.loads(draft_path.read_text()),params,marker,
                              state/"new-only"/"requests"/request/"params.json",
                              state/"new-only"/"requests"/request/"validated.json",request)
    validate_local_draft(draft,csv_dir,params["batch_id"])
    draft_path.write_text(json.dumps(draft,indent=2,sort_keys=True)+"\n")
    total=sum(x["size_bytes"] for x in draft["files"])
    # The current v1 uploader buffers one object. Do not allow unbounded Pod RAM usage.
    if max(x["size_bytes"] for x in draft["files"])>512*1024*1024:
        block("V1_PUBLISHER_PER_OBJECT_SIZE_LIMIT")
    if total>2*1024*1024*1024:
        block("V1_PUBLISHER_TOTAL_SIZE_LIMIT")
    print("SYNTHEA_NEW_ONLY_STRICT_V1_VALIDATOR=PASS")
    print("CSV_NONEMPTY_COUNT=18/18")
    print("PERSON_ROWS="+str(marker["actual_persons"]))
    print("ENCOUNTER_ROWS="+str(marker["actual_encounters"]))
    print("TOTAL_CSV_BYTES="+str(total))
    print("V1_DRAFT_SHA256="+file_sha(draft_path))
    return draft,marker,csv_dir


def s3_from_env() -> S3Client:
    return S3Client(
        endpoint=os.environ["S3_ENDPOINT"],
        bucket=os.environ.get("S3_BUCKET_LANDING","health-landing"),
        region=os.environ.get("AWS_DEFAULT_REGION","us-east-1"),
        access_key=os.environ["AWS_ACCESS_KEY_ID"],
        secret_key=os.environ["AWS_SECRET_ACCESS_KEY"],
    )


def publish(state: Path, request: str, validator: Path, contract: Path, scratch: Path,
            *, replay: bool) -> dict:
    draft,marker,csv_dir=prepare(state,request,validator,contract,scratch)
    client=s3_from_env()
    client.head_bucket()
    batch=draft["batch_id"]
    # Replay needs an existing Manifest; never bootstrap via accidental --replay.
    existing=client.list_keys(BASE)
    own=[x for x in existing if "/batch_id="+batch+"/" in x]
    if replay:
        if len([x for x in own if x.endswith("/manifest.json")])!=1:
            block("REPLAY_REQUIRES_VERIFIED_MANIFEST")
    elif own:
        block("FRESH_PUBLICATION_REQUIRES_EMPTY_BATCH_PREFIX")
    # The S3 + PostgreSQL source-ID audits run in dedicated preceding
    # Self-Runner steps. They are NOT a transactional COMMIT authorization.
    # Publisher still refuses overwrites/conflicts and reads all payloads back.
    if not replay and os.environ.get("NEW_ONLY_READONLY_SOURCE_AUDIT")!="PASS":
        block("SOURCE_ID_AUDIT_NOT_CONFIRMED")
    if not replay and os.environ.get("NEW_ONLY_PG_SOURCE_AUDIT")!="PASS":
        block("PG_SOURCE_ID_AUDIT_NOT_CONFIRMED")
    result=publish_batch(client,draft,csv_dir,batch,
                        os.environ.get("LANDING_INGEST_DATE",datetime.now(timezone.utc).strftime("%Y-%m-%d")),"health-landing")
    if result.get("status")!="INTAKE_VERIFIED" or result.get("verified_file_count")!=18:
        block("REMOTE_MANIFEST_NOT_VERIFIED")
    remote=client.get_object(result["manifest_uri"].split("health-landing/",1)[1])
    if sha256_bytes(remote)!=result["manifest_sha256"]:
        block("FINAL_REMOTE_MANIFEST_SHA_DRIFT")
    final=json.loads(remote)
    validate_final_manifest(draft,final,result["ingest_date"],result["landing_uri"],
                            result["payload_fingerprint"])
    if (final["source_parameters"].get("generation_mode")!="NEW_ONLY"
        or final["source_parameters"].get("generation_request_id")!=request):
        block("FINAL_PRODUCER_PROVENANCE_DRIFT")
    print("SYNTHEA_NEW_ONLY_S3_PUBLICATION=PASS")
    print("BATCH_ID="+batch)
    print("MANIFEST_URI="+result["manifest_uri"])
    print("MANIFEST_SHA256="+result["manifest_sha256"])
    print("LANDING_URI="+result["landing_uri"])
    print("PUBLISH_MODE="+result["publish_mode"])
    print("S3_PAYLOAD_READBACK_SHA256=18/18")
    print("MANIFEST_STATUS=INTAKE_VERIFIED")
    print("LEGACY_V1_CONSUMER_SCHEMA=PASS")
    print("POSTGRESQL_MUTATION=NO")
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--state-root",default="/synthea-state")
    p.add_argument("--request-id",required=True)
    p.add_argument("--validator",default="/audit/validate_generated_synthea_batch.py")
    p.add_argument("--contract",default="/audit/csv-contract.json")
    p.add_argument("--scratch",default="/work")
    p.add_argument("--phase",choices=["validate","publish","replay"],required=True)
    a=p.parse_args()
    args=(Path(a.state_root),a.request_id,Path(a.validator),Path(a.contract),Path(a.scratch))
    try:
        if a.phase=="validate":
            prepare(*args)
            print("S3_MUTATION=NO")
            print("POSTGRESQL_MUTATION=NO")
        else:
            publish(*args,replay=(a.phase=="replay"))
    except (NewOnlyBlocked,PublishError,ValueError,KeyError,OSError,subprocess.SubprocessError) as exc:
        print("NEW_ONLY_S3_PUBLISH_BLOCKED="+str(exc).split("\n",1)[0],file=sys.stderr)
        return 1
    return 0


if __name__=="__main__":
    raise SystemExit(main())
