-- TASK004 STEP04C read-only authorization readiness gate. NO DDL/DML.
\set ON_ERROR_STOP on
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL statement_timeout='30s';
SET LOCAL lock_timeout='3s';
SELECT 'READ_ONLY=' || current_setting('transaction_read_only');
SELECT 'CDM_PERSON_ROWS=' || count(*) FROM cdm.person;
SELECT 'PERSON_MAP_ROWS=' || count(*) FROM etl.person_id_map WHERE source_system='synthea';
SELECT 'PERSON_STAGE_SHARED_ROWS=' || count(*) FROM etl.person_stage;
SELECT 'HISTORIC_MAP_TARGET_GAPS=' || count(*) FROM etl.person_id_map m LEFT JOIN cdm.person p ON p.person_id=m.person_id WHERE m.source_system='synthea' AND p.person_id IS NULL;
SELECT 'HISTORIC_TARGET_UNMAPPED=' || count(*) FROM cdm.person p LEFT JOIN etl.person_id_map m ON m.person_id=p.person_id WHERE m.person_id IS NULL;
SELECT 'MAP_DUPLICATE_BUSINESS_KEYS=' || count(*) FROM (
 SELECT source_system,source_person_id FROM etl.person_id_map GROUP BY source_system,source_person_id HAVING count(*)>1
) q;
SELECT 'MAP_DUPLICATE_PERSON_IDS=' || count(*) FROM (
 SELECT person_id FROM etl.person_id_map GROUP BY person_id HAVING count(*)>1
) q;
SELECT 'PROPOSED_LEDGER_PRESENT=' || (to_regclass('etl.task004_batch_ledger') IS NOT NULL);
SELECT 'PROPOSED_BATCH_STAGE_PRESENT=' || (to_regclass('etl.task004_batch_stage') IS NOT NULL);
SELECT 'PROPOSED_BATCH_COMMIT_PRESENT=' || (to_regclass('etl.task004_batch_commit') IS NOT NULL);
SELECT 'MAP_BUSINESS_KEY_UNIQUE_INDEX=' || EXISTS (
 SELECT 1 FROM pg_index i
 JOIN pg_class t ON t.oid=i.indrelid
 JOIN pg_namespace n ON n.oid=t.relnamespace
 WHERE n.nspname='etl' AND t.relname='person_id_map'
   AND i.indisunique AND i.indisvalid AND i.indpred IS NULL
   AND (SELECT array_agg(a.attname ORDER BY a.attname)
        FROM unnest(i.indkey::smallint[]) k(attnum)
        JOIN pg_attribute a ON a.attrelid=t.oid AND a.attnum=k.attnum)
       = ARRAY['source_person_id','source_system']
);
SELECT 'CDM_PERSON_INSERT_PRIVILEGE=' || has_table_privilege('cdm.person','INSERT');
SELECT 'MAP_INSERT_PRIVILEGE=' || has_table_privilege('etl.person_id_map','INSERT');
SELECT 'PERSON_STAGE_HAS_BATCH_ID=' || EXISTS (
 SELECT 1 FROM information_schema.columns WHERE table_schema='etl' AND table_name='person_stage' AND column_name='batch_id');
SELECT 'V_CONCEPT_TABLE_PRESENT=' || (to_regclass('cdm.concept') IS NOT NULL OR to_regclass('vocab.concept') IS NOT NULL);
SELECT 'POSTGRESQL_MUTATION=NO';
COMMIT;
