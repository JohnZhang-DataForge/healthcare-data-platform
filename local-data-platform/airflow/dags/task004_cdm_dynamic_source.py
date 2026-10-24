"""Bound dynamic batch Parquet source reads; pure injectable S3 and decoder clients.

This is a source adapter, not a DB writer. The caller supplies boto3 S3 and
pyarrow decode in the future runtime image. Refuses manifest drift, empty
datasets, and unexpected objects under the immutable Processing prefix.
"""
from urllib.parse import urlsplit
from task004_cdm_dynamic_adapters import transform, manifest_matches, gate

def locate(uri):
    x=urlsplit(uri)
    return x.netloc,x.path.lstrip("/")

def read(s3,context,entity,decode):
    gate(entity in ("person","visit"),"invalid_entity")
    gate(context.get("database_mutation_authorized") is False,"database_write_forbidden")
    manifest_bucket,manifest_key=locate(context["manifest_uri"])
    manifest=s3.get_object(Bucket=manifest_bucket,Key=manifest_key)["Body"].read()
    manifest_matches(manifest,context)
    bucket,prefix=locate(context[entity+"_processing_uri"])
    keys=[]
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket,Prefix=prefix):
        keys.extend(z["Key"] for z in page.get("Contents",[]) if z["Key"].endswith(".parquet"))
    # Spark writes one Parquet part per output partition.  All parts belong
    # to the single immutable Processing dataset bound by the validated plan.
    gate(bool(keys) and len(keys)==len(set(keys)),"parquet_cardinality")
    rows=[]
    for key in sorted(keys):
        gate(key.startswith(prefix),"parquet_prefix")
        raw=s3.get_object(Bucket=bucket,Key=key)["Body"].read()
        gate(isinstance(raw,bytes) and len(raw)>0,"empty_parquet")
        part=decode(raw)
        gate(isinstance(part,list),"parquet_decode")
        rows.extend(part)
    # Validate the complete dataset once (batch, exact total count, unique IDs).
    return transform(rows,context,entity)
