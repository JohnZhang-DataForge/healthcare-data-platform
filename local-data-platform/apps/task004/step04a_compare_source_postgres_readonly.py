#!/usr/bin/env python3
"""TASK004 STEP04A. Read-only pinned S3 parquet / PG business-key comparison.

No source identifiers or credentials are emitted. This runs in an ephemeral
Self-Runner process, uses a local kubectl S3 service port-forward, and reads
PostgreSQL through an explicitly read-only transaction.
"""
import base64
import hashlib
import io
import json
import os
import re
import subprocess
from urllib.parse import urlparse

import boto3
import pyarrow.parquet as pq

BATCH="task004-airflow-task004-step03e-38324111846"
SHA="ecc7cf3b75240e530f2cc96635b25e4eaf0794403e1b04d50d2248cd3aaa5cb1"
BASE="source=synthea/source_version=v3.3.0/ingest_date=2026-10-12/batch_id="+BATCH+"/"
URIS={
    "person":"s3a://health-processing/"+BASE+"entity=patient/run_id=task004-person-20261012T235028Z-8/work/normalized/data/",
    "visit":"s3a://health-processing/"+BASE+"entity=encounter/run_id=task004-encounter-20261012T235028Z-8/work/normalized/data/",
}
LANDING="s3://health-landing/"+BASE+"manifest.json"
FIELDS={
    "person":("source_record_id","source_system","source_batch_id","source_version","source_ingest_date"),
    "visit":("source_encounter_id","source_person_id","source_system","source_batch_id","source_version","source_ingest_date"),
}

def require(ok,message):
    if not ok: raise RuntimeError("BLOCKED="+message)

def kubectl(*args, input=None):
    return subprocess.run(["kubectl",*args],input=input,text=True,
                          capture_output=True,timeout=55,check=True).stdout

def s3client():
    response=json.loads(kubectl("get","secret","dw-spark-s3-secret","-n","dw-spark","-o","json"))
    secret=response["data"]
    def decode(k): return base64.b64decode(secret[k]).decode()
    return boto3.client("s3",endpoint_url="http://127.0.0.1:18333",
                        aws_access_key_id=decode("AWS_ACCESS_KEY_ID"),
                        aws_secret_access_key=decode("AWS_SECRET_ACCESS_KEY"),
                        region_name="us-east-1",
                        config=__import__("botocore.config",fromlist=["Config"]).Config(
                            s3={"addressing_style":"path"},retries={"max_attempts":2}))

def split(uri):
    p=urlparse(uri)
    require(p.scheme in ("s3","s3a"),"uri_scheme")
    return p.netloc,p.path.lstrip("/")

def parquet_keys(s3,entity):
    bucket,prefix=split(URIS[entity])
    paginator=s3.get_paginator("list_objects_v2")
    objects=[]
    for page in paginator.paginate(Bucket=bucket,Prefix=prefix,
                                  PaginationConfig={"MaxItems":200}):
        objects.extend(o["Key"] for o in page.get("Contents",[])
                       if o["Key"].endswith(".parquet"))
    require(0<len(objects)<=100,"parquet_object_count_"+entity)
    key_field=FIELDS[entity][0]
    keys=[];person_refs=[];columns=None
    rows=0
    for obj in objects:
        raw=s3.get_object(Bucket=bucket,Key=obj)["Body"].read()
        file=pq.ParquetFile(io.BytesIO(raw))
        schema=set(file.schema_arrow.names)
        require(set(FIELDS[entity]).issubset(schema),"schema_missing_"+entity)
        if columns is None: columns=sorted(schema)
        else: require(columns==sorted(schema),"schema_inconsistent_"+entity)
        cols=list(FIELDS[entity])
        table=file.read(columns=cols)
        n=table.num_rows
        rows+=n
        source=table.column("source_system").to_pylist()
        batches=table.column("source_batch_id").to_pylist()
        versions=table.column("source_version").to_pylist()
        dates=table.column("source_ingest_date").to_pylist()
        require(all(str(x).strip().lower()=="synthea" for x in source),"source_system_"+entity)
        require(all(x==BATCH for x in batches),"batch_"+entity)
        require(all(x=="v3.3.0" for x in versions),"version_"+entity)
        require(all(str(x).startswith("2026-10-12") for x in dates),"date_"+entity)
        keys.extend(table.column(key_field).to_pylist())
        if entity=="visit":person_refs.extend(table.column("source_person_id").to_pylist())
    require(all(isinstance(x,str) and bool(x.strip()) for x in keys),"blank_key_"+entity)
    require(len(keys)==len(set(keys)),"duplicate_key_"+entity)
    require(rows=={"person":23,"visit":3592}[entity],"expected_rows_"+entity)
    return set(keys),set(person_refs),rows,len(objects),columns

SQL="""BEGIN TRANSACTION READ ONLY;
SET LOCAL statement_timeout = '30s';
SELECT json_build_object(
 'person',COALESCE((SELECT json_agg(source_person_id) FROM etl.person_id_map
  WHERE source_system='synthea'),'[]'::json),
 'visit',COALESCE((SELECT json_agg(source_encounter_id) FROM etl.visit_occurrence_id_map
  WHERE source_system='synthea'),'[]'::json)
)::text;
COMMIT;
"""
def existing_keys():
    stdout=kubectl("exec","-i","-n","dw-postgre","dw-postgre-database-0",
                   "--","psql","-X","-v","ON_ERROR_STOP=1","-At","-U","omop_admin","-d","omop",input=SQL)
    matches=[x for x in stdout.splitlines() if x.startswith("{")]
    require(len(matches)==1,"pg_json_contract")
    data=json.loads(matches[0])
    return {k:set(data[k]) for k in ("person","visit")}

def main():
    s3=s3client()
    lb,lk=split(LANDING)
    manifest=s3.get_object(Bucket=lb,Key=lk)["Body"].read()
    require(hashlib.sha256(manifest).hexdigest()==SHA,"manifest_sha256")
    people,_,nrp,npf,pschema=parquet_keys(s3,"person")
    visits,refs,nrv,nvf,vschema=parquet_keys(s3,"visit")
    require(all(isinstance(x,str) and x.strip() for x in refs),"visit_reference_blank")
    require(refs.issubset(people),"visit_same_batch_fk")
    db=existing_keys()
    print("TASK=TASK004")
    print("STEP=04A")
    print("MODE=READ_ONLY")
    print("SOURCE_BATCH_ID="+BATCH)
    print("MANIFEST_SHA256="+SHA)
    print("MANIFEST_READBACK_GATE=PASS")
    print("PERSON_PROCESSING_SCHEMA_GATE=PASS")
    print("VISIT_PROCESSING_SCHEMA_GATE=PASS")
    print("PERSON_PARQUET_FILES="+str(npf))
    print("VISIT_PARQUET_FILES="+str(nvf))
    print("PERSON_SOURCE_ROWS="+str(nrp))
    print("VISIT_SOURCE_ROWS="+str(nrv))
    print("PERSON_SOURCE_KEYS_UNIQUE=PASS")
    print("VISIT_SOURCE_KEYS_UNIQUE=PASS")
    print("VISIT_SOURCE_PERSON_FK_GATE=PASS")
    for entity,keys in (("person",people),("visit",visits)):
        old=keys&db[entity]
        print(entity.upper()+"_EXISTING_MAPPING="+str(len(old)))
        print(entity.upper()+"_NEW_MAPPING_NEEDED="+str(len(keys-old)))
    print("PERSON_PROCESSING_COLUMNS="+",".join(pschema))
    print("VISIT_PROCESSING_COLUMNS="+",".join(vschema))
    print("EXISTING_CONTENT_CONFLICT_GATE=UNASSESSED")
    print("BATCH_ISOLATION_GATE=BLOCKED")
    print("POSTGRESQL_MUTATION=NO")
    print("LANDING_MUTATION=NO")
    print("AIRFLOW_TRIGGER=NO")
    print("RESULT=PASS")

if __name__=="__main__": main()
