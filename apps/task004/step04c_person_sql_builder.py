"""STEP04C fixed-batch Person loader. Pure SQL builder, no runtime mutation on import."""
import hashlib,json
from datetime import date
BATCH="task004-airflow-task004-step03e-38324111846"
SHA="ecc7cf3b75240e530f2cc96635b25e4eaf0794403e1b04d50d2248cd3aaa5cb1"
PERSON_URI="s3a://health-processing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-12/batch_id="+BATCH+"/entity=patient/run_id=task004-person-20261012T235028Z-8/work/normalized/data/"
VISIT_URI="s3a://health-processing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-12/batch_id="+BATCH+"/entity=encounter/run_id=task004-encounter-20261012T235028Z-8/work/normalized/data/"
GENDER={"M":8507,"F":8532}
RACE={"asian":8515,"black":8516,"hawaiian":8557,"white":8527,"other":0} # OMOP CDM 0 means no matching race concept; source value retained
ETH={"hispanic":38003563,"nonhispanic":38003564}
COLS=("gender_concept_id year_of_birth month_of_birth day_of_birth birth_datetime race_concept_id ethnicity_concept_id location_id provider_id care_site_id person_source_value gender_source_value gender_source_concept_id race_source_value race_source_concept_id ethnicity_source_value ethnicity_source_concept_id").split()
def check(ok,code):
    if not ok:raise RuntimeError("BLOCKED="+code)
def q(v):return "'"+str(v).replace("'","''")+"'"
def prepare(rows):
    seen=set(); output=[]
    for row in rows:
        key=row["source_record_id"]
        check(isinstance(key,str) and key and key not in seen,"person_key")
        seen.add(key)
        check(row["source_batch_id"]==BATCH and row["source_system"]=="synthea" and row["source_version"]=="v3.3.0","lineage")
        check(str(row["source_ingest_date"]).startswith("2026-10-12"),"ingest_date")
        g,r,e=row["gender_code"],row["race_code"],row["ethnicity_code"]
        check(g in GENDER and r in RACE and e in ETH,"unknown_concept")
        birth=date.fromisoformat(str(row["birth_date"])[:10])
        p=dict.fromkeys(COLS)
        p.update(gender_concept_id=GENDER[g],year_of_birth=birth.year,month_of_birth=birth.month,day_of_birth=birth.day,birth_datetime=birth.isoformat()+"T00:00:00",race_concept_id=RACE[r],ethnicity_concept_id=ETH[e],person_source_value=key,gender_source_value=g,race_source_value=r,ethnicity_source_value=e)
        raw=json.dumps(p,sort_keys=True,separators=(",",":"))
        output.append({"source_key":key,"row_fingerprint":hashlib.sha256(raw.encode()).hexdigest(),"canonical_payload":p})
    check(len(output)==23,"row_count")
    return sorted(output,key=lambda z:z["source_key"])
def generate(rows,rollback=True):
    check(len(rows)==23,"expected_23")
    data=json.dumps(rows,sort_keys=True,separators=(",",":"))
    check("$payload$" not in data,"delimiter")
    digest=hashlib.sha256(data.encode()).hexdigest()
    sql="""\\set ON_ERROR_STOP on
BEGIN;
SET LOCAL statement_timeout='60s';
SET LOCAL lock_timeout='5s';
SELECT pg_advisory_xact_lock(hashtext('task004:person:exclusive'));
CREATE TEMP TABLE input_rows ON COMMIT DROP AS
SELECT x->>'source_key' key,x->>'row_fingerprint' fp,x->'canonical_payload' payload
FROM jsonb_array_elements($payload$""" + data + """$payload$::jsonb) x;
DO $$
BEGIN
 IF (SELECT count(*) FROM input_rows) <> 23 OR (SELECT count(DISTINCT key) FROM input_rows) <> 23
 THEN RAISE EXCEPTION 'SOURCE_KEY_GATE'; END IF;
 IF (SELECT count(*) FROM cdm.person) NOT IN (113,136) OR (SELECT count(*) FROM cdm.visit_occurrence) <> 5799
 THEN RAISE EXCEPTION 'HISTORIC_CDM_GATE'; END IF;
 IF (SELECT count(*) FROM etl.person_id_map WHERE source_system='synthea') NOT IN (113,136)
 THEN RAISE EXCEPTION 'HISTORIC_MAP_GATE'; END IF;
 IF (SELECT count(*) FROM cdm.concept WHERE concept_id IN (8507,8532,8515,8516,8557,8527,38003563,38003564)
 AND standard_concept='S' AND invalid_reason IS NULL)<>8
 THEN RAISE EXCEPTION 'CONCEPT_GATE'; END IF;
END $$;
INSERT INTO etl.task004_batch_ledger(batch_id,manifest_sha256,source_system,source_version,ingest_date,person_processing_uri,visit_processing_uri,contract_version,status)
VALUES (""" + ",".join(map(q,(BATCH,SHA,"synthea","v3.3.0","2026-10-12",PERSON_URI,VISIT_URI,"task004-person-v1","REGISTERED"))) + """)
ON CONFLICT DO NOTHING;
DO $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM etl.task004_batch_ledger WHERE batch_id=""" +q(BATCH)+""" AND manifest_sha256="""+q(SHA)+""" AND person_processing_uri="""+q(PERSON_URI)+""")
 THEN RAISE EXCEPTION 'LEDGER_CONFLICT';END IF;
END $$;
INSERT INTO etl.task004_batch_stage(batch_id,entity,source_system,source_key,row_fingerprint,canonical_payload,contract_version)
SELECT """+q(BATCH)+""",'person','synthea',key,fp,payload,'task004-person-v1' FROM input_rows
ON CONFLICT DO NOTHING;
DO $$
BEGIN
 IF (SELECT count(*) FROM etl.task004_batch_stage WHERE batch_id="""+q(BATCH)+""" AND entity='person') <>23
 OR EXISTS(SELECT 1 FROM input_rows i LEFT JOIN etl.task004_batch_stage s ON s.batch_id="""+q(BATCH)+""" AND s.entity='person' AND s.source_key=i.key AND s.source_system='synthea'
 WHERE s.source_key IS NULL OR s.row_fingerprint<>i.fp OR s.canonical_payload<>i.payload)
 THEN RAISE EXCEPTION 'STAGE_CONFLICT';END IF;
END $$;
INSERT INTO etl.person_id_map(source_system,source_person_id)
SELECT 'synthea',i.key FROM input_rows i WHERE NOT EXISTS
(SELECT 1 FROM etl.person_id_map m WHERE m.source_system='synthea' AND m.source_person_id=i.key)
ORDER BY i.key;
DO $$
BEGIN
 IF (SELECT count(*) FROM input_rows i JOIN etl.person_id_map m ON m.source_system='synthea' AND m.source_person_id=i.key)<>23
 THEN RAISE EXCEPTION 'MAP_MISSING';END IF;
 IF EXISTS(SELECT 1 FROM input_rows i JOIN etl.person_id_map m ON m.source_system='synthea' AND m.source_person_id=i.key
 JOIN cdm.person p ON p.person_id=m.person_id WHERE to_jsonb(p) IS DISTINCT FROM
 to_jsonb(jsonb_populate_record(NULL::cdm.person,i.payload||jsonb_build_object('person_id',m.person_id))))
 THEN RAISE EXCEPTION 'EXISTING_PERSON_CONFLICT'; END IF;
END $$;
INSERT INTO cdm.person SELECT person_value.* FROM input_rows i
JOIN etl.person_id_map m ON m.source_system='synthea' AND m.source_person_id=i.key
CROSS JOIN LATERAL jsonb_populate_record(NULL::cdm.person,i.payload||jsonb_build_object('person_id',m.person_id)) person_value
WHERE NOT EXISTS(SELECT 1 FROM cdm.person p WHERE p.person_id=m.person_id);
DO $$
BEGIN
 IF (SELECT count(*) FROM input_rows i JOIN etl.person_id_map m ON m.source_system='synthea' AND m.source_person_id=i.key
 JOIN cdm.person p ON p.person_id=m.person_id WHERE to_jsonb(p) IS NOT DISTINCT FROM
 to_jsonb(jsonb_populate_record(NULL::cdm.person,i.payload||jsonb_build_object('person_id',m.person_id))))<>23
 THEN RAISE EXCEPTION 'PERSON_READBACK';END IF;
 IF (SELECT count(*) FROM cdm.person)<>136 THEN RAISE EXCEPTION 'PERSON_TOTAL';END IF;
END $$;
INSERT INTO etl.task004_batch_commit(batch_id,entity,stage_digest,stage_rows,mapped_rows,inserted_rows,updated_rows,readback_digest,commit_state,verified_at)
VALUES ("""+",".join(map(q,(BATCH,"person",digest)))+""",23,23,23,0,"""+q(digest)+""",'VERIFIED',now())
ON CONFLICT DO NOTHING;
UPDATE etl.task004_batch_ledger SET status='PERSON_COMMITTED',updated_at=now()
WHERE batch_id="""+q(BATCH)+""" AND status IN ('REGISTERED','PERSON_STAGED','PERSON_COMMITTED');
"""
    return sql+("ROLLBACK;\n" if rollback else "COMMIT;\n")
