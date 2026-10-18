#!/usr/bin/env python3
"""Strict NEW_ONLY-only v2 Landing manifest validation.

This is a reader contract, never a PUT/Claim/Writer permission. The existing
v1 validation code path remains untouched. V2 allows ONLY auxiliary header-only
CSV datasets; Person and Encounter are mandatory and nonempty.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

CONTRACT_RELATIVE="contracts/synthea/new-only/csv-contract-v2.json"
BATCH_RE=re.compile(r"^synthea-new-only-([A-Za-z0-9][A-Za-z0-9-]{7,65})$")
SHA_RE=re.compile(r"^[0-9a-f]{64}$")
S3_RE=re.compile(
    r"^s3://health-landing/source=synthea/source_version=v3\.3\.0/"
    r"ingest_date=(\d{4}-\d{2}-\d{2})/batch_id=([^/]+)/manifest\.json$"
)
PINNED_COMMIT="995cf2fd33e67918d4e33110d9f68ad248002221"


class V2ContractError(ValueError):
    pass


def reject(reason):
    raise V2ContractError("V2_CONTRACT_BLOCKED:"+reason)


def source_contract(path:Path|None=None)->tuple[dict,str]:
    if path is None:
        repo=Path(__file__).resolve().parents[2]/CONTRACT_RELATIVE
        packaged=Path(__file__).with_name("csv-contract-v2.json")
        path=repo if repo.is_file() else packaged
    if not path.is_file():
        reject("PINNED_V2_CONTRACT_FILE_MISSING")
    raw=path.read_bytes()
    contract=json.loads(raw)
    if (contract.get("contract_version")!="new-only-v2"
        or contract.get("source")!="synthea"
        or contract.get("source_version")!="v3.3.0"
        or contract.get("generation_mode")!="NEW_ONLY"
        or contract.get("manifest_version")!="2.0"
        or contract.get("required_nonempty_datasets")!=["patients","encounters"]
        or contract.get("expected_file_count")!=18
        or contract.get("require_nonempty_data_rows") is not False):
        reject("CONTRACT_IDENTITY")
    files=contract.get("files")
    if not isinstance(files,list) or len(files)!=18:
        reject("CONTRACT_INVENTORY")
    if len({a["filename"] for a in files})!=18 or len({a["dataset"] for a in files})!=18:
        reject("CONTRACT_DUPLICATE_DATASETS")
    return contract,hashlib.sha256(raw).hexdigest()


def require_sha(value,reason):
    if not isinstance(value,str) or not SHA_RE.fullmatch(value):
        reject(reason)
    return value


def validate_v2_manifest(manifest:Any, expected_batch_id:str, manifest_uri:str,
                         contract_path:Path|None=None)->list[dict]:
    if not isinstance(manifest,dict):
        reject("ROOT_NOT_OBJECT")
    if manifest.get("manifest_version")!="2.0":
        reject("VERSION")
    if manifest.get("status")!="INTAKE_VERIFIED":
        reject("NOT_READY")
    match=BATCH_RE.fullmatch(expected_batch_id) if isinstance(expected_batch_id,str) else None
    if match is None or manifest.get("batch_id")!=expected_batch_id:
        reject("NEW_ONLY_BATCH_ID")
    requested_id=match.group(1)
    uri=S3_RE.fullmatch(manifest_uri) if isinstance(manifest_uri,str) else None
    if uri is None or uri.group(2)!=expected_batch_id:
        reject("MANIFEST_URI_LINEAGE")
    expected_date=uri.group(1)
    landing=manifest_uri[:-len("manifest.json")]
    if (manifest.get("source")!="synthea"
        or manifest.get("source_version")!="v3.3.0"
        or manifest.get("ingest_date")!=expected_date
        or manifest.get("landing_uri")!=landing
        or manifest.get("payload_format")!="csv"
        or type(manifest.get("expected_file_count")) is not int
        or manifest.get("expected_file_count")!=18):
        reject("LINEAGE_OR_INVENTORY")
    params=manifest.get("source_parameters")
    if (not isinstance(params,dict)
        or params.get("generation_mode")!="NEW_ONLY"
        or params.get("generation_request_id")!=requested_id
        or type(params.get("population_size")) is not int
        or not 1<=params["population_size"]<=100):
        reject("PRODUCER_PROVENANCE")
    prov=manifest.get("source_provenance")
    if (not isinstance(prov,dict)
        or prov.get("synthea_commit")!=PINNED_COMMIT
        or prov.get("synthea_version")!="v3.3.0"):
        reject("SYNTHEA_SOURCE_PIN")
    contract,sha=source_contract(contract_path)
    declared=manifest.get("contract")
    if (not isinstance(declared,dict)
        or declared.get("path")!=CONTRACT_RELATIVE
        or require_sha(declared.get("sha256"),"CONTRACT_SHA")!=sha):
        reject("V2_CONTRACT_SHA_MISMATCH")
    objects=manifest.get("files")
    if not isinstance(objects,list) or len(objects)!=18:
        reject("EXPECTED_EXACTLY_18_FILES")
    expected={item["filename"]:item for item in contract["files"]}
    seen={}
    output=[]
    for item in objects:
        if not isinstance(item,dict):
            reject("FILE_NOT_OBJECT")
        name=item.get("path","")
        if not isinstance(name,str) or not name.startswith("payload/csv/"):
            reject("FILE_PATH")
        filename=name[len("payload/csv/"):]
        if filename not in expected or filename in seen or "/" in filename:
            reject("FILE_INVENTORY_OR_DUPLICATE")
        spec=expected[filename]
        if item.get("dataset")!=spec["dataset"] or item.get("header")!=spec["header"]:
            reject("FILE_DATASET_OR_HEADER_"+filename)
        count=item.get("row_count")
        size=item.get("size_bytes")
        if type(count) is not int or count<0:
            reject("NEGATIVE_OR_INVALID_ROWS_"+filename)
        if spec["dataset"] in ("patients","encounters") and count<1:
            reject("REQUIRED_SOURCE_EMPTY_"+filename)
        if type(size) is not int or size<=0:
            reject("EMPTY_CSV_OBJECT_"+filename)
        file_sha=require_sha(item.get("sha256"),"FILE_SHA_"+filename)
        seen[filename]=True
        output.append({"path":name,"dataset":spec["dataset"],"header":spec["header"],
                       "row_count":count,"size_bytes":size,"sha256":file_sha})
    if set(seen)!=set(expected):
        reject("MISSING_EXPECTED_CSV")
    patient_count=next(x["row_count"] for x in output if x["dataset"]=="patients")
    if patient_count<params["population_size"]:
        reject("PERSON_ROWS_BELOW_POPULATION")
    verification=manifest.get("verification")
    if (not isinstance(verification,dict)
        or verification.get("s3_readback")!="PASS"
        or type(verification.get("verified_file_count")) is not int
        or verification.get("verified_file_count")!=18
        or verification.get("checksum_algorithm")!="SHA256"):
        reject("REMOTE_READBACK_NOT_ATTESTED")
    fingerprint=hashlib.sha256()
    for item in sorted(output,key=lambda x:x["path"]):
        fingerprint.update(
            (item["path"].rsplit("/",1)[-1]+"|"+item["sha256"]+"\n").encode())
    if require_sha(manifest.get("payload_fingerprint"),"PAYLOAD_FINGERPRINT")!=fingerprint.hexdigest():
        reject("PAYLOAD_FINGERPRINT_MISMATCH")
    return output
