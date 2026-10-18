"""TASK004 STEP04D fixed-batch Visit contract. Pure code; SQL is one atomic transaction."""
from datetime import datetime,timezone
import hashlib,json
BATCH="task004-airflow-task004-step03e-38324111846"
MANIFEST="ecc7cf3b75240e530f2cc96635b25e4eaf0794403e1b04d50d2248cd3aaa5cb1"
PERSON_URI="s3a://health-processing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-12/batch_id="+BATCH+"/entity=patient/run_id=task004-person-20261012T235028Z-8/work/normalized/data/"
VISIT_URI="s3a://health-processing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-12/batch_id="+BATCH+"/entity=encounter/run_id=task004-encounter-20261012T235028Z-8/work/normalized/data/"
CLASS={"ambulatory":9202,"emergency":9203,"home":581476,"hospice":581476,"inpatient":9201,"outpatient":9202,"snf":9201,"urgentcare":9202,"virtual":722455,"wellness":9202}
VISIT_TYPE=32827
COLS=("person_id visit_concept_id visit_start_date visit_start_datetime visit_end_date visit_end_datetime visit_type_concept_id provider_id care_site_id visit_source_value visit_source_concept_id admitted_from_concept_id admitted_from_source_value discharged_to_concept_id discharged_to_source_value preceding_visit_occurrence_id").split()
def require(ok,msg):
    if not ok:raise RuntimeError("BLOCKED="+msg)
def q(v):return "'"+str(v).replace("'","''")+"'"
def dt(value):
    require(value is not None,"visit_timestamp_missing")
    try:
        x=datetime.fromisoformat(str(value).replace("Z","+00:00"))
        # Accepted canonical Parquet has timestamp-NTZ; Synthea source timestamps are UTC.
        # Treat NTZ as UTC, never as worker-node local timezone.
        if x.tzinfo is None: x=x.replace(tzinfo=timezone.utc)
        return x.astimezone(timezone.utc).replace(tzinfo=None).isoformat(sep=" ",timespec="microseconds")
    except (ValueError,TypeError):raise RuntimeError("BLOCKED=visit_invalid_datetime") from None
def prepare(rows):
    out=[];seen=set()
    for row in rows:
        key=row["source_encounter_id"];parent=row["source_person_id"]
        require(isinstance(key,str) and key and key not in seen,"visit_key_duplicate_or_blank")
        seen.add(key)
        require(isinstance(parent,str) and parent,"visit_parent_missing")
        require(row["source_batch_id"]==BATCH and row["source_system"]=="synthea" and row["source_version"]=="v3.3.0","visit_lineage")
        require(str(row["source_ingest_date"]).startswith("2026-10-12"),"visit_ingest")
        klass=row["encounter_class"]
        require(klass in CLASS,"visit_class_unknown")
        start=dt(row["start_datetime"]);end=dt(row["end_datetime"])
        require(start<=end,"visit_end_before_start")
        p=dict.fromkeys(COLS)
        p.update(visit_concept_id=CLASS[klass],visit_start_date=start[:10],visit_start_datetime=start,
                 visit_end_date=end[:10],visit_end_datetime=end,visit_type_concept_id=VISIT_TYPE,visit_source_value=klass)
        raw=json.dumps({"parent":parent,"fields":p},sort_keys=True,separators=(",",":"))
        out.append({"source_key":key,"source_person_key":parent,"row_fingerprint":hashlib.sha256(raw.encode()).hexdigest(),"canonical_payload":p})
    require(len(out)==3592,"visit_count")
    return sorted(out,key=lambda z:z["source_key"])
def generate(rows,rollback=True):
    require(len(rows)==3592,"visit_input_count")
    data=json.dumps(rows,sort_keys=True,separators=(",",":"))
    require("$visit_data$" not in data,"sql_delimiter")
    digest=hashlib.sha256(data.encode()).hexdigest()
    sql="""\\set ON_ERROR_STOP on
BEGIN;
SET LOCAL statement_timeout='120s';
SET LOCAL lock_timeout='5s';
SELECT pg_advisory_xact_lock(hashtext('task004:visit:exclusive'));
CREATE TEMP TABLE _visits ON COMMIT DROP AS
SELECT x->>'source_key' AS source_key,x->>'source_person_key' AS parent_key,
       x->>'row_fingerprint' AS fp,x->'canonical_payload' AS payload
FROM jsonb_array_elements($visit_data$"""+data+"""$visit_data$::jsonb) x;
DO $$
BEGIN
 IF (SELECT count(*) FROM _visits)<>3592 OR (SELECT count(DISTINCT source_key) FROM _visits)<>3592
 THEN RAISE EXCEPTION 'BLOCKED:VISIT_SOURCE_COUNT';END IF;
 IF (SELECT count(*) FROM cdm.person)<>136 OR (SELECT count(*) FROM etl.person_id_map WHERE source_system='synthea')<>136
 THEN RAISE EXCEPTION 'BLOCKED:PERSON_BASELINE';END IF;
 IF (SELECT count(*) FROM cdm.visit_occurrence) NOT IN (5799,9391)
 OR (SELECT count(*) FROM etl.visit_occurrence_id_map WHERE source_system='synthea') NOT IN (5799,9391)
 THEN RAISE EXCEPTION 'BLOCKED:VISIT_BASELINE';END IF;
 IF NOT EXISTS(SELECT 1 FROM etl.task004_batch_commit WHERE batch_id="""+q(BATCH)+""" AND entity='person' AND commit_state='VERIFIED' AND stage_rows=23)
 THEN RAISE EXCEPTION 'BLOCKED:PERSON_CHECKPOINT';END IF;
 IF NOT EXISTS(SELECT 1 FROM etl.task004_batch_ledger WHERE batch_id="""+q(BATCH)+""" AND manifest_sha256="""+q(MANIFEST)+""" AND person_processing_uri="""+q(PERSON_URI)+""" AND visit_processing_uri="""+q(VISIT_URI)+""")
 THEN RAISE EXCEPTION 'BLOCKED:BATCH_IDENTITY';END IF;
 IF EXISTS(SELECT 1 FROM _visits v LEFT JOIN etl.person_id_map m ON m.source_system='synthea' AND m.source_person_id=v.parent_key LEFT JOIN cdm.person p ON p.person_id=m.person_id WHERE p.person_id IS NULL)
 THEN RAISE EXCEPTION 'BLOCKED:PERSON_FK';END IF;
 IF (SELECT count(*) FROM cdm.concept WHERE concept_id IN (9201,9202,9203,581476,722455,32827)
 AND standard_concept='S' AND invalid_reason IS NULL)<>6
 THEN RAISE EXCEPTION 'BLOCKED:VISIT_CONCEPTS';END IF;
END $$;
INSERT INTO etl.task004_batch_stage
 (batch_id,entity,source_system,source_key,source_person_key,row_fingerprint,canonical_payload,contract_version)
SELECT """+q(BATCH)+""",'visit','synthea',source_key,parent_key,fp,payload,'task004-visit-v1' FROM _visits
ON CONFLICT DO NOTHING;
DO $$
BEGIN
 IF (SELECT count(*) FROM etl.task004_batch_stage WHERE batch_id="""+q(BATCH)+""" AND entity='visit')<>3592
 OR EXISTS(SELECT 1 FROM _visits v LEFT JOIN etl.task004_batch_stage s
 ON s.batch_id="""+q(BATCH)+""" AND s.entity='visit' AND s.source_system='synthea' AND s.source_key=v.source_key
 WHERE s.source_key IS NULL OR s.row_fingerprint<>v.fp OR s.canonical_payload<>v.payload OR s.source_person_key<>v.parent_key)
 THEN RAISE EXCEPTION 'BLOCKED:VISIT_STAGE_REPLAY';END IF;
END $$;
INSERT INTO etl.visit_occurrence_id_map(source_system,source_encounter_id)
SELECT 'synthea',v.source_key FROM _visits v WHERE NOT EXISTS(
SELECT 1 FROM etl.visit_occurrence_id_map m WHERE m.source_system='synthea' AND m.source_encounter_id=v.source_key)
ORDER BY v.source_key;
CREATE TEMP TABLE _expected ON COMMIT DROP AS
SELECT (jsonb_populate_record(NULL::cdm.visit_occurrence,v.payload||
 jsonb_build_object('visit_occurrence_id',m.visit_occurrence_id,'person_id',pm.person_id))).*
FROM _visits v
JOIN etl.visit_occurrence_id_map m ON m.source_system='synthea' AND m.source_encounter_id=v.source_key
JOIN etl.person_id_map pm ON pm.source_system='synthea' AND pm.source_person_id=v.parent_key;
DO $$
BEGIN
 IF (SELECT count(*) FROM _expected)<>3592 THEN RAISE EXCEPTION 'BLOCKED:VISIT_MAPPING';END IF;
 IF EXISTS(SELECT 1 FROM _expected e JOIN cdm.visit_occurrence v USING (visit_occurrence_id)
 WHERE to_jsonb(e) IS DISTINCT FROM to_jsonb(v))
 THEN RAISE EXCEPTION 'BLOCKED:EXISTING_VISIT_CONTENT';END IF;
END $$;
INSERT INTO cdm.visit_occurrence
SELECT e.* FROM _expected e
WHERE NOT EXISTS(SELECT 1 FROM cdm.visit_occurrence v WHERE v.visit_occurrence_id=e.visit_occurrence_id);
DO $$
BEGIN
 IF (SELECT count(*) FROM _expected e JOIN cdm.visit_occurrence v ON v.visit_occurrence_id=e.visit_occurrence_id
 WHERE to_jsonb(e) IS NOT DISTINCT FROM to_jsonb(v))<>3592
 THEN RAISE EXCEPTION 'BLOCKED:VISIT_DB_READBACK';END IF;
 IF (SELECT count(*) FROM cdm.visit_occurrence)<>9391
 OR (SELECT count(*) FROM etl.visit_occurrence_id_map WHERE source_system='synthea')<>9391
 THEN RAISE EXCEPTION 'BLOCKED:VISIT_TOTAL';END IF;
END $$;
INSERT INTO etl.task004_batch_commit
(batch_id,entity,stage_digest,stage_rows,mapped_rows,inserted_rows,updated_rows,readback_digest,commit_state,verified_at)
VALUES ("""+",".join(map(q,(BATCH,"visit",digest)))+""",3592,3592,3592,0,"""+q(digest)+""",'VERIFIED',now())
ON CONFLICT DO NOTHING;
DO $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM etl.task004_batch_commit
 WHERE batch_id="""+q(BATCH)+""" AND entity='visit'
 AND stage_digest="""+q(digest)+""" AND commit_state='VERIFIED' AND stage_rows=3592 AND mapped_rows=3592 AND updated_rows=0)
 THEN RAISE EXCEPTION 'BLOCKED:VISIT_CHECKPOINT_CONFLICT';END IF;
END $$;
UPDATE etl.task004_batch_ledger SET status='VISIT_COMMITTED',updated_at=now()
WHERE batch_id="""+q(BATCH)+""" AND status IN ('PERSON_COMMITTED','VISIT_COMMITTED');
"""
    return sql+("ROLLBACK;\n" if rollback else "COMMIT;\n")
