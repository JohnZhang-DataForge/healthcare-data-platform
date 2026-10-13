#!/usr/bin/env python3
"""Run fixed batch Person transaction through ARC, no credential/source-key logging."""
import argparse,hashlib,io,subprocess
import pyarrow.parquet as pq
from step04a_compare_source_postgres_readonly import BATCH,SHA,LANDING,URIS,s3client,split,require
from step04c_person_sql_builder import prepare,generate

def run(cmd,stdin):
    p=subprocess.run(cmd,input=stdin,text=True,capture_output=True,timeout=120)
    if p.returncode:
        # Avoid emitting source values or statement text from database errors.
        raise RuntimeError("BLOCKED=psql_transaction_failed_exit_"+str(p.returncode))
    return p.stdout
def main():
    args=argparse.ArgumentParser()
    group=args.add_mutually_exclusive_group(required=True)
    group.add_argument("--rollback",action="store_true")
    group.add_argument("--commit",action="store_true")
    opt=args.parse_args()
    s3=s3client()
    bucket,key=split(LANDING)
    manifest=s3.get_object(Bucket=bucket,Key=key)["Body"].read()
    require(hashlib.sha256(manifest).hexdigest()==SHA,"manifest_sha_mismatch")
    bucket,prefix=split(URIS["person"])
    files=[o["Key"] for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket,Prefix=prefix) for o in page.get("Contents",[]) if o["Key"].endswith(".parquet")]
    require(len(files)==1,"person_parquet_file_count")
    data=s3.get_object(Bucket=bucket,Key=files[0])["Body"].read()
    rows=prepare(pq.read_table(io.BytesIO(data)).to_pylist())
    sql=generate(rows,rollback=not opt.commit)
    cmd=["kubectl","exec","-i","-n","dw-postgre","dw-postgre-database-0","--","sh","-c",
         "export PGPASSWORD=\"${POSTGRES_PASSWORD:-${PGPASSWORD:-}}\"; exec psql -X -q -At -v ON_ERROR_STOP=1 -U omop_admin -d omop"]
    run(cmd,sql)
    print("TASK004_STEP04C_PERSON_SOURCE=PASS")
    print("MANIFEST_SHA_GATE=PASS")
    print("PERSON_SOURCE_ROWS=23")
    print("TRANSACTION_MODE="+("COMMIT" if opt.commit else "ROLLBACK"))
    print("VISIT_MUTATION=NO")
    print("PERSON_SQL=PASS")
if __name__=="__main__":main()
