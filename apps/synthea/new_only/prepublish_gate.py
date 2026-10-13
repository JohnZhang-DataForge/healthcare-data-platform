#!/usr/bin/env python3
"""NEW_ONLY prepublication gates. READ ONLY; no S3 PUT or database connection.

The PostgreSQL side is performed separately by Self-Runner in a READ ONLY SQL
transaction and joined with this report in ephemeral runner storage.
No result in this module grants authority to publish or COMMIT.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path

class PublishGateBlocked(ValueError):
    pass

def refuse(reason):
    raise PublishGateBlocked("BLOCKED:" + reason)

def source_hash(value):
    # A keyed source-id registry is compared to the live SQL md5() result;
    # this is an audit filter, NEVER a substitute for the transactional
    # exact-key Writer drift gate.
    return hashlib.md5(value.encode("utf-8")).hexdigest()

def load_contract(path):
    d=json.loads(Path(path).read_text(encoding="utf-8"))
    if (d.get("contract_version")!="new-only-v2" or
        d.get("manifest_version")!="2.0" or
        d.get("generation_mode")!="NEW_ONLY" or
        d.get("consumer_compatibility")!="NOT_YET_DEPLOYED_DO_NOT_PUBLISH_READY" or
        d.get("expected_file_count")!=18 or
        d.get("required_nonempty_datasets")!=["patients","encounters"]):
        refuse("NEW_ONLY_VERSIONED_CONTRACT")
    files=d.get("files",[])
    if len(files)!=18 or len({f["filename"] for f in files})!=18:
        refuse("NEW_ONLY_18_FILES")
    return d

def read_ids(raw, *, filename, column, expected_header, allow_zero=False):
    if len(raw)>64*1024*1024:
        refuse("CSV_TOO_LARGE")
    try:
        stream=io.StringIO(raw.decode("utf-8-sig"),newline="")
        reader=csv.reader(stream,strict=True)
        header=next(reader)
        if header!=expected_header or column not in header:
            refuse("CSV_HEADER_DRIFT_" + filename)
        ids=[]
        position=header.index(column)
        for row in reader:
            if len(row)!=len(header):
                refuse("CSV_ROW_SHAPE_" + filename)
            if not row[position]:
                refuse("EMPTY_SOURCE_ID_" + filename)
            ids.append(row[position])
        if not ids and not allow_zero:
            refuse("EMPTY_SOURCE_ENTITY_" + filename)
        if len(ids)!=len(set(ids)):
            refuse("DUPLICATE_SOURCE_ID_" + filename)
        return ids
    except (UnicodeError, csv.Error, StopIteration) as exc:
        raise PublishGateBlocked("BLOCKED:UNREADABLE_CSV_"+filename) from exc

def audit_local(csv_dir,contract_path):
    spec=load_contract(contract_path)
    folder=Path(csv_dir)
    expected={f["filename"] for f in spec["files"]}
    if not folder.is_dir() or {p.name for p in folder.glob("*.csv") if p.is_file()}!=expected:
        refuse("LOCAL_CSV_INVENTORY")
    summary={}; headers={}; identities={}
    for item in spec["files"]:
        name=item["filename"]
        path=folder/name
        data=path.read_bytes()
        if not data or len(data)>64*1024*1024:
            refuse("LOCAL_CSV_SIZE_" + name)
        try:
            rows=list(csv.reader(io.StringIO(data.decode("utf-8-sig"),newline=""),strict=True))
        except (UnicodeError,csv.Error) as exc:
            raise PublishGateBlocked("BLOCKED:CSV_DECODE_"+name) from exc
        if not rows or rows[0]!=item["header"]:
            refuse("LOCAL_HEADER_"+name)
        if any(len(row)!=len(item["header"]) for row in rows[1:]):
            refuse("LOCAL_CSV_ROW_SHAPE_"+name)
        count=len(rows)-1
        if item["dataset"] in ("patients","encounters") and count<1:
            refuse("EMPTY_REQUIRED_"+name)
        headers[name]=item["header"]
        summary[name]={"row_count":count,"sha256":hashlib.sha256(data).hexdigest(),"size_bytes":len(data)}
        if name=="patients.csv":
            identities["person"]=read_ids(data,filename=name,column="Id",expected_header=item["header"])
        elif name=="encounters.csv":
            identities["visit"]=read_ids(data,filename=name,column="Id",expected_header=item["header"])
            parent_index=item["header"].index("PATIENT")
            for row in rows[1:]:
                if row[parent_index] not in identities["person"]:
                    refuse("ENCOUNTER_ORPHAN")
    if not 1<=len(identities["person"])<=100:
        refuse("PERSON_COUNT_NOT_1_TO_100")
    return {
        "batch_not_published":True,
        "csv_contract_version":"new-only-v2",
        "manifest_version":"2.0",
        "csv_file_count":18,
        "person_rows":len(identities["person"]),
        "visit_rows":len(identities["visit"]),
        "zero_row_optional_files":sorted(n for n,v in summary.items() if v["row_count"]==0),
        "files":summary,
        "person_source_hashes":sorted(source_hash(x) for x in identities["person"]),
        "visit_source_hashes":sorted(source_hash(x) for x in identities["visit"]),
        "database_mutation":False,"landing_mutation":False,
    }

def audit_historical_landing(s3,base_prefix,local,candidate_batch):
    """Conservatively include every historical Patient/Encounter CSV in S3,
    even in not-yet-READY prefixes; immutable READY SHA is checked if present.
    No S3 mutation or fallback that ignores malformed historical CSV.
    """
    keys=s3.list_keys(base_prefix)
    if len(keys)>20000:
        refuse("UNBOUNDED_LANDING_SCAN")
    remote=[k for k in keys if k.endswith("/payload/csv/patients.csv") or k.endswith("/payload/csv/encounters.csv")]
    remote_manifests={k for k in keys if k.endswith("/manifest.json")}
    current_person=set(local["person_source_hashes"])
    current_visit=set(local["visit_source_hashes"])
    matches_person=set();matches_visit=set();read_count=0
    for key in remote:
        # Never reuse source identities from an already present batch_id,
        # including a half-published attempt with no verified manifest.
        parts=key.split("/")
        if any(x=="batch_id="+candidate_batch for x in parts):
            refuse("CANDIDATE_BATCH_PREFIX_ALREADY_EXISTS")
        raw=s3.get_object(key)
        manifest_key=key.split("/payload/csv/",1)[0]+"/manifest.json"
        if manifest_key in remote_manifests:
            doc=json.loads(s3.get_object(manifest_key))
            if doc.get("status")=="INTAKE_VERIFIED":
                expected=next((x for x in doc.get("files",[]) if x.get("path")=="payload/csv/"+key.rsplit("/",1)[-1]),None)
                if expected is None or expected.get("sha256")!=hashlib.sha256(raw).hexdigest():
                    refuse("HISTORICAL_S3_CHECKSUM_DRIFT")
        name=key.rsplit("/",1)[-1]
        if name=="patients.csv":
            required="Id";entity="person"
        else:
            required="Id";entity="visit"
        # Source columns for historical v1 are defined in the retained v2
        # 18-file header baseline and match Synthea v3.3.0 exports.
        hdr=local["headers"][name]
        ids=read_ids(raw,filename=name,column=required,expected_header=hdr)
        hits={source_hash(x) for x in ids}&(current_person if entity=="person" else current_visit)
        if entity=="person": matches_person|=hits
        else: matches_visit|=hits
        read_count+=1
    return {
        "historical_source_csvs_scanned":read_count,
        "s3_person_source_collisions":len(matches_person),
        "s3_visit_source_collisions":len(matches_visit),
        "s3_collision_free":not (matches_person or matches_visit),
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--csv-dir",required=True)
    ap.add_argument("--contract",required=True)
    ap.add_argument("--batch-id",required=True)
    ap.add_argument("--output",required=True)
    ap.add_argument("--scan-s3",action="store_true")
    args=ap.parse_args()
    local=audit_local(args.csv_dir,args.contract)
    if args.scan_s3:
        import sys
        sys.path.insert(0,os.environ.get("SYNTHEA_S3_CLIENT_DIR","/opt/task004"))
        from publish_synthea_landing import S3Client
        s3=S3Client(
            endpoint=os.environ["S3_ENDPOINT"],
            bucket=os.environ.get("S3_BUCKET_LANDING","health-landing"),
            region=os.environ.get("AWS_DEFAULT_REGION","us-east-1"),
            access_key=os.environ["AWS_ACCESS_KEY_ID"],
            secret_key=os.environ["AWS_SECRET_ACCESS_KEY"])
        s3.head_bucket()
        scan=audit_historical_landing(s3,"source=synthea/source_version=v3.3.0/",
            dict(local,headers={f["filename"]:f["header"] for f in load_contract(args.contract)["files"]}),
            args.batch_id)
        local["landing"]=scan
        if not scan["s3_collision_free"]:
            refuse("EXISTING_LANDING_SOURCE_IDS")
    # Raw synthetic identifiers never leave this Pod; only MD5 hashes go into
    # ephemeral Runner memory. The runner must independently check live PG.
    Path(args.output).write_text(json.dumps(local,sort_keys=True))
    print("NEW_ONLY_V2_LOCAL_CONTRACT=PASS")
    print("PERSON_ROWS="+str(local["person_rows"]))
    print("VISIT_ROWS="+str(local["visit_rows"]))
    print("ZERO_ROW_OPTIONAL_CSVS="+str(len(local["zero_row_optional_files"])))
    if args.scan_s3:
        print("LANDING_HISTORICAL_CSVS_SCANNED="+str(local["landing"]["historical_source_csvs_scanned"]))
        print("LANDING_GLOBAL_SOURCE_IDS=PASS")
    print("MANIFEST_READY=NO")
    print("POSTGRESQL_MUTATION=NO")
    print("S3_MUTATION=NO")

if __name__=="__main__":
    main()
