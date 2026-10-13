"""Dynamic TASK004 Person/Visit canonical -> OMOP row adapters.

No network/database calls. Requires validated dynamic plan; never authorizes writes.
The original STEP04C/D fixed-batch loaders remain unchanged for auditability.
"""
import hashlib
import json
from datetime import date, datetime, timezone

from task004_cdm_materialization_plan import plan as validate_plan

GENDER={"M":8507,"F":8532}
RACE={"asian":8515,"black":8516,"hawaiian":8557,"white":8527,"other":0}
ETHNICITY={"hispanic":38003563,"nonhispanic":38003564}
VISIT_CLASS={"ambulatory":9202,"emergency":9203,"home":581476,
             "hospice":581476,"inpatient":9201,"outpatient":9202,
             "snf":9201,"urgentcare":9202,"virtual":722455,"wellness":9202}
PERSON_COLUMNS=("gender_concept_id year_of_birth month_of_birth day_of_birth birth_datetime race_concept_id ethnicity_concept_id location_id provider_id care_site_id person_source_value gender_source_value gender_source_concept_id race_source_value race_source_concept_id ethnicity_source_value ethnicity_source_concept_id").split()
VISIT_COLUMNS=("visit_concept_id visit_start_date visit_start_datetime visit_end_date visit_end_datetime visit_type_concept_id provider_id care_site_id visit_source_value visit_source_concept_id admitted_from_concept_id admitted_from_source_value discharged_to_concept_id discharged_to_source_value preceding_visit_occurrence_id").split()

def gate(ok,reason):
    if not ok:
        raise ValueError("BLOCKED="+reason)

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()

def check_row(row,context,entity):
    gate(isinstance(row,dict),"row_not_object")
    gate(row.get("source_system")=="synthea" and row.get("source_version")==context["source_version"],"source_identity")
    gate(row.get("source_batch_id")==context["batch_id"],"mixed_batch")
    gate(str(row.get("source_ingest_date"))==context["ingest_date"],"source_date")

def stamp(v):
    gate(v is not None,"datetime_missing")
    try:
        t=datetime.fromisoformat(str(v).replace("Z","+00:00"))
        if t.tzinfo is None:t=t.replace(tzinfo=timezone.utc)
        return t.astimezone(timezone.utc).replace(tzinfo=None).isoformat(sep=" ",timespec="microseconds")
    except (TypeError,ValueError) as e:
        raise ValueError("BLOCKED=invalid_datetime") from None

def transform(rows,context,entity):
    gate(entity in ("person","visit"),"invalid_entity")
    gate(isinstance(context,dict) and context.get("database_mutation_authorized") is False,"authorization_boundary")
    # Revalidate the immutable part against the same constraints as the DAG plan.
    raw={k:context[k] for k in ("batch_id","manifest_sha256","manifest_uri","person_processing_uri","visit_processing_uri","person_rows","visit_rows","source_version")}
    raw.update(state="HANDOFF_VERIFIED_NOT_LOADED",cdm_write_permitted=False)
    verified=validate_plan(raw)
    gate(context.get("plan_sha256")==verified["plan_sha256"],"plan_drift")
    gate(isinstance(rows,list) and len(rows)==context[entity+"_rows"],"row_count")
    out=[];seen=set()
    for row in rows:
        check_row(row,context,entity)
        key_name="source_record_id" if entity=="person" else "source_encounter_id"
        key=row.get(key_name)
        gate(isinstance(key,str) and bool(key.strip()) and key not in seen,"duplicate_or_missing_key")
        gate(len(key)<=255,"source_key_too_long")
        seen.add(key)
        if entity=="person":
            gender,race,eth=row.get("gender_code"),row.get("race_code"),row.get("ethnicity_code")
            gate(gender in GENDER and race in RACE and eth in ETHNICITY,"unknown_demographic")
            try:bd=date.fromisoformat(str(row.get("birth_date"))[:10])
            except ValueError:raise ValueError("BLOCKED=invalid_birth_date") from None
            p=dict.fromkeys(PERSON_COLUMNS)
            p.update(gender_concept_id=GENDER[gender],year_of_birth=bd.year,
                     month_of_birth=bd.month,day_of_birth=bd.day,
                     birth_datetime=bd.isoformat()+"T00:00:00",
                     race_concept_id=RACE[race],ethnicity_concept_id=ETHNICITY[eth],
                     person_source_value=key,gender_source_value=gender,
                     race_source_value=race,ethnicity_source_value=eth)
            parent=None
        else:
            parent=row.get("source_person_id")
            gate(isinstance(parent,str) and bool(parent.strip()) and len(parent)<=255,"missing_parent_key")
            klass=row.get("encounter_class")
            gate(klass in VISIT_CLASS,"unknown_visit_class")
            start,end=stamp(row.get("start_datetime")),stamp(row.get("end_datetime"))
            gate(start<=end,"reversed_visit")
            p=dict.fromkeys(VISIT_COLUMNS)
            p.update(visit_concept_id=VISIT_CLASS[klass],
                     visit_type_concept_id=32827,visit_start_date=start[:10],
                     visit_start_datetime=start,visit_end_date=end[:10],
                     visit_end_datetime=end,visit_source_value=klass)
        item={"source_key":key,"canonical_payload":p}
        if parent is not None:item["source_person_key"]=parent
        item["row_fingerprint"]=digest({"source_person_key":parent,"payload":p})
        out.append(item)
    return sorted(out,key=lambda x:x["source_key"])

def manifest_matches(actual_bytes,context):
    gate(isinstance(actual_bytes,bytes),"manifest_bytes")
    gate(hashlib.sha256(actual_bytes).hexdigest()==context["manifest_sha256"],"manifest_sha_mismatch")
    return True

def source_keys_match(people,visits):
    ids={p["source_key"] for p in people}
    gate(all(v["source_person_key"] in ids for v in visits),"visit_person_reference_missing")
    return True
