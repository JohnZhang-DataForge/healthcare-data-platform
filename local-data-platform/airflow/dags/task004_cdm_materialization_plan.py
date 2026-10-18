"""Dynamic batch materialization plan contract (no database writes).

Consumes validated Airflow handoff, rejects stale/foreign batch paths,
and creates a stable serialization for downstream Person→Visit transactions.
"""
import hashlib
import json
import re
from datetime import date
from urllib.parse import urlsplit

_SHA=re.compile(r"^[0-9a-f]{64}$")
_BATCH=re.compile(r"^task004-airflow-[A-Za-z0-9._-]+$")  # Legacy default stays frozen.
_NEW_ONLY_BATCH=re.compile(r"^synthea-new-only-[A-Za-z0-9][A-Za-z0-9._-]{1,127}$")
_NEW_ONLY_WRITER_VERSION="synthea-new-only-v1"
_ALLOWED_BUCKETS={"manifest_uri":"health-landing",
                  "person_processing_uri":"health-processing",
                  "visit_processing_uri":"health-processing"}

def fail(msg):
    raise ValueError("BLOCKED="+msg)

def parse_location(uri,scheme,bucket,part):
    if not isinstance(uri,str):
        fail("missing_"+part+"_uri")
    u=urlsplit(uri)
    if u.scheme!=scheme or u.netloc!=bucket or u.query or u.fragment or not u.path.startswith("/"):
        fail("untrusted_"+part+"_uri")
    parts=u.path.split("/")
    if any(k in ("..",".","") for k in parts[1:-1]) or "%2f" in uri.lower():
        fail("unsafe_"+part+"_path")
    return u.path

def plan(handoff):
    if not isinstance(handoff,dict) or handoff.get("state")!="HANDOFF_VERIFIED_NOT_LOADED" or handoff.get("cdm_write_permitted") is not False:
        fail("handoff_not_verified")
    batch=handoff.get("batch_id")
    sha=handoff.get("manifest_sha256")
    identity_version=handoff.get("writer_identity_version")
    if not isinstance(batch,str):
        fail("batch_id")
    if identity_version is None:
        # Absence of a version selects *only* the original legacy identity.
        if not _BATCH.fullmatch(batch):
            fail("batch_id")
    elif identity_version==_NEW_ONLY_WRITER_VERSION:
        if not _NEW_ONLY_BATCH.fullmatch(batch):
            fail("new_only_batch_id")
    else:
        fail("writer_identity_version")
    if not isinstance(sha,str) or not _SHA.fullmatch(sha):
        fail("manifest_sha256")
    if handoff.get("source_version")!="v3.3.0":
        fail("version")
    for part,bucket in _ALLOWED_BUCKETS.items():
        uri=handoff.get(part)
        path=parse_location(uri,"s3" if part=="manifest_uri" else "s3a",bucket,part)
        if "/batch_id="+batch+"/" not in path:
            fail("mixed_batch_"+part)
        if identity_version==_NEW_ONLY_WRITER_VERSION and not path.startswith(
            "/source=synthea/source_version=v3.3.0/ingest_date="
        ):
            fail("new_only_source_path")
        if part=="manifest_uri" and not path.endswith("/manifest.json"):
            fail("manifest_name")
        if part!="manifest_uri" and not path.endswith("/"):
            fail("processing_prefix")
        if part=="person_processing_uri" and "/entity=patient/" not in path:
            fail("person_entity")
        if part=="visit_processing_uri" and "/entity=encounter/" not in path:
            fail("visit_entity")
    for kind in ("person","visit"):
        count=handoff.get(kind+"_rows")
        if isinstance(count,bool) or not isinstance(count,int) or count<=0 or count>1000000:
            fail(kind+"_count")
        if identity_version==_NEW_ONLY_WRITER_VERSION and (
            (kind=="person" and count>100) or (kind=="visit" and count>100000)
        ):
            fail("new_only_"+kind+"_count")
    marker="/ingest_date="
    dates=set()
    for k in _ALLOWED_BUCKETS:
        parts=handoff[k].split(marker)
        if len(parts)!=2:
            fail("ingest_date_"+k)
        part=parts[1].split("/",1)[0]
        try: date.fromisoformat(part)
        except ValueError: fail("bad_ingest_date")
        dates.add(part)
    if len(dates)!=1:
        fail("inconsistent_ingest_date")
    immutable={k:handoff[k] for k in ("batch_id","manifest_sha256","manifest_uri","person_processing_uri","visit_processing_uri","person_rows","visit_rows","source_version")}
    immutable["ingest_date"]=dates.pop()
    if identity_version is not None:
        # Explicit v2 compatibility is bound into the immutable plan digest.
        # Legacy plans have the exact same fields and digest as before.
        immutable["writer_identity_version"]=identity_version
    canonical=json.dumps(immutable,sort_keys=True,separators=(",",":"),ensure_ascii=True)
    immutable["plan_sha256"]=hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    immutable["load_order"]=["person","visit","db_reconcile"]
    immutable["database_mutation_authorized"]=False
    immutable["state"]="PLANNED_AWAITING_LOADER_VALIDATION"
    return immutable

def same_plan(before,after):
    old=plan(before);new=plan(after)
    if old["plan_sha256"]!=new["plan_sha256"]:
        fail("immutable_batch_context_changed")
    return True
