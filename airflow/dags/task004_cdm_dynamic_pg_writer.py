"""Dynamic TASK004 OMOP transaction renderer. No I/O or writes on import.

Receives validated dynamic batch plan and prepared Person/Visit rows.
Explicit allow_commit=True is required to produce COMMIT SQL. Caller must
perform independent source integrity and grant an appropriately scoped writer.
"""
import hashlib,json,re
from task004_cdm_materialization_plan import plan as validate_plan
from task004_cdm_dynamic_adapters import gate
ENTITY={"person":("person_id_map","source_person_id","cdm.person","person_id"),
        "visit":("visit_occurrence_id_map","source_encounter_id","cdm.visit_occurrence","visit_occurrence_id")}
def quote(s):
    return "'"+str(s).replace("'","''")+"'"
def render(context,rows,entity,*,allow_commit=False):
    gate(entity in ENTITY,"entity")
    gate(isinstance(context,dict) and context.get("database_mutation_authorized") is False,"authorization_boundary")
    original={k:context[k] for k in ("batch_id","manifest_sha256","manifest_uri","person_processing_uri","visit_processing_uri","person_rows","visit_rows","source_version")}
    original.update(state="HANDOFF_VERIFIED_NOT_LOADED",cdm_write_permitted=False)
    verified=validate_plan(original)
    gate(verified["plan_sha256"]==context.get("plan_sha256"),"plan_changed")
    gate(isinstance(rows,list) and len(rows)==context[entity+"_rows"] and len(rows)>0,"count")
    keys=[r.get("source_key") for r in rows]
    gate(all(isinstance(k,str) and k and len(k)<=255 for k in keys) and len(set(keys))==len(keys),"keys")
    for row in rows:
        gate(re.fullmatch("[0-9a-f]{64}",row.get("row_fingerprint","")) is not None,"fingerprint")
        gate(isinstance(row.get("canonical_payload"),dict),"payload")
        if entity=="visit":gate(isinstance(row.get("source_person_key"),str) and bool(row["source_person_key"]),"parent")
    data=json.dumps(sorted(rows,key=lambda x:x["source_key"]),sort_keys=True,separators=(",",":"),allow_nan=False)
    gate("$data_task004$" not in data,"delimiter")
    digest=hashlib.sha256(data.encode()).hexdigest()
    batch=quote(context["batch_id"]);sha=quote(context["manifest_sha256"])
    map_table,key_col,target,id_col=ENTITY[entity]
    parent_col="source_person_key"
    expected="jsonb_populate_record(NULL::"+target+", i.payload||jsonb_build_object('"+id_col+"',m."+id_col
    if entity=="visit":
        expected+=",'person_id',pmap.person_id"
    expected+="))"
    parent_join=("JOIN etl.person_id_map pmap ON pmap.source_system='synthea' AND pmap.source_person_id=i.parent_key " if entity=="visit" else "")
    row_projection="i.payload"
    sql="""\\set ON_ERROR_STOP on
BEGIN;
SET LOCAL lock_timeout='5s';
SET LOCAL statement_timeout='120s';
SELECT pg_advisory_xact_lock(hashtext('task004:dynamic:omop:global'));
CREATE TEMP TABLE task004_rows ON COMMIT DROP AS
SELECT x->>'source_key' source_key,
       x->>'source_person_key' parent_key,
       x->>'row_fingerprint' fp,
       x->'canonical_payload' payload
FROM jsonb_array_elements($data_task004$"""+data+"""$data_task004$::jsonb) x;
DO $$
BEGIN
 IF (SELECT count(*) FROM task004_rows)<>"""+str(len(rows))+"""
 OR (SELECT count(DISTINCT source_key) FROM task004_rows)<>"""+str(len(rows))+"""
 THEN RAISE EXCEPTION 'BLOCKED:INPUT_CARDINALITY';END IF;
END $$;
INSERT INTO etl.task004_batch_ledger
(batch_id,manifest_sha256,source_system,source_version,ingest_date,person_processing_uri,visit_processing_uri,contract_version,status)
VALUES ("""+",".join(quote(context[x]) for x in ("batch_id","manifest_sha256"))+""",'synthea','v3.3.0',"""+quote(context["ingest_date"])+""","""+quote(context["person_processing_uri"])+""","""+quote(context["visit_processing_uri"])+""",'task004-dynamic-v1','REGISTERED')
ON CONFLICT DO NOTHING;
DO $$
BEGIN
 IF NOT EXISTS (SELECT 1 FROM etl.task004_batch_ledger WHERE batch_id="""+batch+"""
 AND manifest_sha256="""+sha+"""
 AND person_processing_uri="""+quote(context["person_processing_uri"])+"""
 AND visit_processing_uri="""+quote(context["visit_processing_uri"])+"""
 AND contract_version='task004-dynamic-v1')
 THEN RAISE EXCEPTION 'BLOCKED:LEDGER_DRIFT';END IF;
END $$;
"""
    concepts=([8507,8532,8515,8516,8557,8527,38003563,38003564] if entity=="person"
              else [9201,9202,9203,581476,722455,32827])
    sql+="""DO $$
BEGIN
 IF (SELECT count(*) FROM cdm.concept WHERE concept_id IN ("""+",".join(map(str,concepts))+""")
 AND standard_concept='S' AND invalid_reason IS NULL)<>"""+str(len(concepts))+"""
 THEN RAISE EXCEPTION 'BLOCKED:VOCABULARY_INVALID';END IF;
END $$;
"""
    if entity=="visit":
        sql+="""DO $$
BEGIN
 IF NOT EXISTS (SELECT 1 FROM etl.task004_batch_commit WHERE batch_id="""+batch+""" AND entity='person' AND commit_state='VERIFIED')
 THEN RAISE EXCEPTION 'BLOCKED:PERSON_COMMIT_MISSING';END IF;
 IF EXISTS(SELECT 1 FROM task004_rows i LEFT JOIN etl.person_id_map pmap
 ON pmap.source_system='synthea' AND pmap.source_person_id=i.parent_key
 LEFT JOIN cdm.person p ON p.person_id=pmap.person_id WHERE p.person_id IS NULL)
 THEN RAISE EXCEPTION 'BLOCKED:PERSON_FK_MISSING';END IF;
END $$;
"""
    sql+="""INSERT INTO etl.task004_batch_stage
(batch_id,entity,source_system,source_key,source_person_key,row_fingerprint,canonical_payload,contract_version)
SELECT """+batch+","+quote(entity)+""",'synthea',source_key,parent_key,fp,payload,'task004-dynamic-v1'
FROM task004_rows ON CONFLICT DO NOTHING;
DO $$
BEGIN
 IF (SELECT count(*) FROM etl.task004_batch_stage WHERE batch_id="""+batch+""" AND entity="""+quote(entity)+""")<>"""+str(len(rows))+"""
 OR EXISTS (SELECT 1 FROM task004_rows i LEFT JOIN etl.task004_batch_stage s
 ON s.batch_id="""+batch+""" AND s.entity="""+quote(entity)+""" AND s.source_system='synthea'
 AND s.source_key=i.source_key WHERE s.source_key IS NULL OR
 s.row_fingerprint<>i.fp OR s.canonical_payload<>i.payload OR
 s.source_person_key IS DISTINCT FROM i.parent_key)
 THEN RAISE EXCEPTION 'BLOCKED:STAGE_DRIFT';END IF;
END $$;
INSERT INTO etl."""+map_table+"""(source_system,"""+key_col+""")
SELECT 'synthea',i.source_key FROM task004_rows i
WHERE NOT EXISTS (SELECT 1 FROM etl."""+map_table+""" m WHERE m.source_system='synthea' AND m."""+key_col+"""=i.source_key)
ORDER BY i.source_key;
CREATE TEMP TABLE task004_expected ON COMMIT DROP AS
SELECT ("""+expected+""").*
FROM task004_rows i
JOIN etl."""+map_table+""" m ON m.source_system='synthea' AND m."""+key_col+"""=i.source_key
"""+parent_join+""";
DO $$
BEGIN
 IF (SELECT count(*) FROM task004_expected)<>"""+str(len(rows))+"""
 THEN RAISE EXCEPTION 'BLOCKED:MAP_COUNT';END IF;
 IF EXISTS (SELECT 1 FROM task004_expected e JOIN """+target+""" t USING ("""+id_col+""")
 WHERE to_jsonb(e) IS DISTINCT FROM to_jsonb(t))
 THEN RAISE EXCEPTION 'BLOCKED:EXISTING_TARGET_DRIFT';END IF;
END $$;
INSERT INTO """+target+"""
SELECT e.* FROM task004_expected e
WHERE NOT EXISTS(SELECT 1 FROM """+target+""" t WHERE t."""+id_col+"""=e."""+id_col+""");
DO $$
BEGIN
 IF (SELECT count(*) FROM task004_expected e JOIN """+target+""" t USING ("""+id_col+""")
 WHERE to_jsonb(e) IS NOT DISTINCT FROM to_jsonb(t))<>"""+str(len(rows))+"""
 THEN RAISE EXCEPTION 'BLOCKED:TARGET_RECONCILIATION';END IF;
END $$;
INSERT INTO etl.task004_batch_commit
(batch_id,entity,stage_digest,stage_rows,mapped_rows,inserted_rows,updated_rows,readback_digest,commit_state,verified_at)
VALUES ("""+batch+","+quote(entity)+","+quote(digest)+","+str(len(rows))+","+str(len(rows))+","+str(len(rows))+""",0,"""+quote(digest)+""",'VERIFIED',now())
ON CONFLICT DO NOTHING;
DO $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM etl.task004_batch_commit WHERE batch_id="""+batch+"""
 AND entity="""+quote(entity)+""" AND stage_digest="""+quote(digest)+"""
 AND stage_rows="""+str(len(rows))+""" AND mapped_rows="""+str(len(rows))+"""
 AND updated_rows=0 AND commit_state='VERIFIED')
 THEN RAISE EXCEPTION 'BLOCKED:CHECKPOINT_DRIFT';END IF;
END $$;
"""
    # The default is fail-safe ROLLBACK. Permanent writes require explicit caller opt-in.
    return sql+("COMMIT;\n" if allow_commit else "ROLLBACK;\n")
