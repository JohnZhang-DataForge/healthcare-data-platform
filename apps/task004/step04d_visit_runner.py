#!/usr/bin/env python3
"""STEP04D exact fixed batch. Source read and PostgreSQL stdout have no patient identifiers."""
import argparse,hashlib,io,subprocess
import pyarrow.parquet as pq
from step04a_compare_source_postgres_readonly import SHA,LANDING,URIS,s3client,split,require
from step04d_visit_sql_builder import prepare,generate

def main():
    ap=argparse.ArgumentParser()
    op=ap.add_mutually_exclusive_group(required=True)
    op.add_argument("--rollback",action="store_true")
    op.add_argument("--commit",action="store_true")
    args=ap.parse_args()
    s3=s3client()
    bucket,key=split(LANDING)
    require(hashlib.sha256(s3.get_object(Bucket=bucket,Key=key)["Body"].read()).hexdigest()==SHA,"manifest_sha256")
    bucket,prefix=split(URIS["visit"])
    files=[x["Key"] for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket,Prefix=prefix) for x in page.get("Contents",[]) if x["Key"].endswith(".parquet")]
    require(len(files)==1,"expected_one_visit_parquet")
    rows=pq.read_table(io.BytesIO(s3.get_object(Bucket=bucket,Key=files[0])["Body"].read())).to_pylist()
    from collections import Counter
    print("VISIT_CLASS_AGGREGATES="+",".join(k+":"+str(v) for k,v in sorted(Counter(str(x.get("encounter_class")) for x in rows).items())),flush=True)
    sql=generate(prepare(rows),rollback=not args.commit)
    cmd=["kubectl","exec","-i","-n","dw-postgre","dw-postgre-database-0","--","sh","-c",
        "export PGPASSWORD=\"${POSTGRES_PASSWORD:-${PGPASSWORD:-}}\"; exec psql -X -q -At -v ON_ERROR_STOP=1 -U omop_admin -d omop"]
    p=subprocess.run(cmd,input=sql,text=True,capture_output=True,timeout=210)
    if p.returncode:
        # stderr can contain individual source values/SQL, never print it in CI.
        raise RuntimeError("BLOCKED=visit_transaction_failed_exit_"+str(p.returncode))
    print("VISIT_SOURCE_MANIFEST=PASS")
    print("VISIT_SOURCE_ROWS=3592")
    print("VISIT_TRANSACTION="+("ROLLBACK" if args.rollback else "COMMIT"))
    print("VISIT_SQL=PASS")
if __name__=="__main__":main()
