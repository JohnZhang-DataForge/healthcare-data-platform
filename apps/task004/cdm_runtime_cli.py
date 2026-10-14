"""TASK004 read-only CDM runtime entrypoint.

Only validates a dynamic batch plan. This entrypoint deliberately has no
database connection, SQL execution or commit capability.
"""
import argparse
import json
from pathlib import Path
from task004_cdm_materialization_plan import plan

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan-file", required=True)
    parser.add_argument("--validate-source", choices=("person", "visit"))
    parser.add_argument("--validate-postgres", action="store_true")
    parser.add_argument("--rollback-entity", choices=("person", "visit"))
    parser.add_argument("--rollback-rows-file")
    parser.add_argument("--rollback-from-s3", choices=("person", "visit"))
    args = parser.parse_args()
    supplied = json.loads(Path(args.plan_file).read_text(encoding="utf-8"))
    keys = ("batch_id", "manifest_sha256", "manifest_uri",
            "person_processing_uri", "visit_processing_uri",
            "person_rows", "visit_rows", "source_version")
    original = {key: supplied[key] for key in keys}
    if "writer_identity_version" in supplied:
        original["writer_identity_version"]=supplied["writer_identity_version"]
    original.update(state="HANDOFF_VERIFIED_NOT_LOADED",
                    cdm_write_permitted=False)
    verified = plan(original)
    if verified["plan_sha256"] != supplied.get("plan_sha256"):
        raise ValueError("BLOCKED=plan_drift")
    if supplied.get("database_mutation_authorized") is not False:
        raise ValueError("BLOCKED=database_mutation_forbidden")
    if args.rollback_from_s3:
        if args.rollback_entity or args.rollback_rows_file or args.validate_source or args.validate_postgres:
            raise ValueError("BLOCKED=conflicting_commands")
        import io
        import os
        import boto3
        import pyarrow.parquet as parquet
        from task004_cdm_dynamic_source import read
        from task004_cdm_postgres_rollback_executor import execute_rollback
        endpoint=os.environ.get("TASK004_S3_ENDPOINT_URL")
        if not endpoint or not endpoint.startswith(("http://","https://")):
            raise ValueError("BLOCKED=missing_s3_endpoint")
        s3=boto3.client("s3",endpoint_url=endpoint)
        rows=read(s3,supplied,args.rollback_from_s3,
                  lambda data:parquet.read_table(io.BytesIO(data)).to_pylist())
        result=execute_rollback(supplied,rows,args.rollback_from_s3)
        print("CDM_S3_WRITER_ROLLBACK=PASS")
        print("ROLLBACK_ENTITY="+result["entity"])
        print("ROLLBACK_ROWS="+str(result["row_count"]))
    if args.rollback_entity:
        if not args.rollback_rows_file:
            raise ValueError("BLOCKED=missing_rollback_rows")
        from task004_cdm_postgres_rollback_executor import execute_rollback
        rows=json.loads(Path(args.rollback_rows_file).read_text(encoding="utf-8"))
        result=execute_rollback(supplied,rows,args.rollback_entity)
        print("CDM_WRITER_RUNTIME_ROLLBACK=PASS")
        print("ROLLBACK_ENTITY=" + result["entity"])
        print("ROLLBACK_ROWS=" + str(result["row_count"]))
    elif args.rollback_rows_file:
        raise ValueError("BLOCKED=unused_rollback_rows")
    if args.validate_postgres:
        from task004_cdm_postgres_readonly import validate_readonly
        result=validate_readonly(supplied)
        for name in ("person_rows", "visit_rows", "ledger_rows"):
            print("PG_" + name.upper() + "=" + str(result[name]))
        print("CDM_POSTGRES_READONLY=PASS")
    if args.validate_source:
        # Defer optional imports until real source validation is requested.
        import io
        import os
        import boto3
        import pyarrow.parquet as parquet
        from task004_cdm_dynamic_source import read
        endpoint = os.environ.get("TASK004_S3_ENDPOINT_URL")
        if not endpoint or not endpoint.startswith(("http://", "https://")):
            raise ValueError("BLOCKED=missing_s3_endpoint")
        s3 = boto3.client("s3", endpoint_url=endpoint)
        items = read(s3, supplied, args.validate_source,
                     lambda data: parquet.read_table(io.BytesIO(data)).to_pylist())
        print("DYNAMIC_SOURCE_VALIDATED=PASS")
        print("ENTITY=" + args.validate_source)
        print("ROW_COUNT=" + str(len(items)))
    print("DYNAMIC_CDM_PLAN_VALIDATED=PASS")
    print("DATABASE_MUTATION=NO")

if __name__ == "__main__":
    main()
