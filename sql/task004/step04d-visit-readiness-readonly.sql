\set ON_ERROR_STOP on
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL statement_timeout='30s';
SELECT 'PERSON_ROWS='||count(*) FROM cdm.person;
SELECT 'VISIT_ROWS='||count(*) FROM cdm.visit_occurrence;
SELECT 'PERSON_MAP_ROWS='||count(*) FROM etl.person_id_map WHERE source_system='synthea';
SELECT 'VISIT_MAP_ROWS='||count(*) FROM etl.visit_occurrence_id_map WHERE source_system='synthea';
SELECT 'BATCH_PERSON_STAGE='||count(*) FROM etl.task004_batch_stage WHERE batch_id='task004-airflow-task004-step03e-38324111846' AND entity='person';
SELECT 'BATCH_VISIT_STAGE='||count(*) FROM etl.task004_batch_stage WHERE batch_id='task004-airflow-task004-step03e-38324111846' AND entity='visit';
SELECT 'PERSON_COMMIT_VERIFIED='||count(*) FROM etl.task004_batch_commit WHERE batch_id='task004-airflow-task004-step03e-38324111846' AND entity='person' AND commit_state='VERIFIED';
SELECT 'BATCH_VISIT_COMMIT='||count(*) FROM etl.task004_batch_commit WHERE batch_id='task004-airflow-task004-step03e-38324111846' AND entity='visit';
SELECT 'VISIT_MAP_DUPLICATE_KEYS='||count(*) FROM (SELECT source_system,source_encounter_id FROM etl.visit_occurrence_id_map GROUP BY 1,2 HAVING count(*)>1) t;
SELECT 'VISIT_MAP_ORPHANS='||count(*) FROM etl.visit_occurrence_id_map m LEFT JOIN cdm.visit_occurrence v ON v.visit_occurrence_id=m.visit_occurrence_id WHERE v.visit_occurrence_id IS NULL;
SELECT 'VISIT_FK_ORPHANS='||count(*) FROM cdm.visit_occurrence v LEFT JOIN cdm.person p ON p.person_id=v.person_id WHERE p.person_id IS NULL;
SELECT 'VISIT_MAP_UNIQUE='||EXISTS(SELECT 1 FROM pg_index i JOIN pg_class t ON t.oid=i.indrelid JOIN pg_namespace n ON n.oid=t.relnamespace WHERE n.nspname='etl' AND t.relname='visit_occurrence_id_map' AND i.indisunique AND i.indisvalid AND i.indpred IS NULL AND (SELECT array_agg(a.attname ORDER BY a.attname) FROM unnest(i.indkey::smallint[]) k(attnum) JOIN pg_attribute a ON a.attrelid=t.oid AND a.attnum=k.attnum)=ARRAY['source_encounter_id','source_system']::name[]);
SELECT 'VISIT_TABLE_COLUMNS='||string_agg(column_name||':'||data_type||':'||is_nullable,',' ORDER BY ordinal_position) FROM information_schema.columns WHERE table_schema='cdm' AND table_name='visit_occurrence';
COMMIT;
