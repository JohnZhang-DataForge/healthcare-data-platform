"""Pure Airflow-to-OMOP handoff validation. No database or network I/O.

A valid handoff is NOT permission to write CDM data. This checks upstream
provenance before the future per-batch loaders are attached.
"""
import re

SHA256=re.compile(r"^[0-9a-f]{64}$")
EXPECTED_SOURCE_VERSION="v3.3.0"

def validate_handoff(generate,person,visit):
    if not all(isinstance(x,dict) for x in (generate,person,visit)):
        raise ValueError("BLOCKED=missing_upstream_xcom")
    batch=generate.get("batch_id")
    manifest=generate.get("manifest_uri")
    digest=generate.get("manifest_sha256")
    if not isinstance(batch,str) or not batch.startswith("task004-airflow-") or not re.fullmatch(r"[A-Za-z0-9._-]+",batch):
        raise ValueError("BLOCKED=invalid_batch")
    if not isinstance(digest,str) or not SHA256.fullmatch(digest):
        raise ValueError("BLOCKED=invalid_manifest_sha")
    if generate.get("source_version")!=EXPECTED_SOURCE_VERSION or generate.get("status")!="INTAKE_VERIFIED":
        raise ValueError("BLOCKED=source_not_verified")
    if not isinstance(manifest,str) or not manifest.startswith("s3://health-landing/") or "/batch_id="+batch+"/" not in manifest or not manifest.endswith("/manifest.json"):
        raise ValueError("BLOCKED=untrusted_manifest")
    result={"batch_id":batch,"manifest_sha256":digest,"source_version":EXPECTED_SOURCE_VERSION,
            "manifest_uri":manifest,"person_processing_uri":None,"visit_processing_uri":None}
    for name,obj,entity in (("person",person,"patient"),("visit",visit,"encounter")):
        uri=obj.get("processing_data_uri")
        count=obj.get("canonical_rows")
        if not isinstance(uri,str) or not uri.startswith("s3a://health-processing/") or "/batch_id="+batch+"/" not in uri or "/entity="+entity+"/" not in uri or not uri.endswith("/"):
            raise ValueError("BLOCKED="+name+"_processing_lineage")
        if isinstance(count,bool) or not isinstance(count,int) or count<=0:
            raise ValueError("BLOCKED="+name+"_row_count")
        result[name+"_processing_uri"]=uri
        result[name+"_rows"]=count
    result["cdm_write_permitted"]=False
    result["state"]="HANDOFF_VERIFIED_NOT_LOADED"
    return result
