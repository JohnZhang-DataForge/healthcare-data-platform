\set ON_ERROR_STOP on
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT 'LEDGER_PRESENT=' || (to_regclass('etl.task004_batch_ledger') IS NOT NULL);
SELECT 'STAGE_PRESENT=' || (to_regclass('etl.task004_batch_stage') IS NOT NULL);
SELECT 'COMMIT_PRESENT=' || (to_regclass('etl.task004_batch_commit') IS NOT NULL);
SELECT 'HISTORIC_PERSON_ROWS=' || count(*) FROM cdm.person;
SELECT 'HISTORIC_VISIT_ROWS=' || count(*) FROM cdm.visit_occurrence;
SELECT 'HISTORIC_PERSON_MAP_ROWS=' || count(*) FROM etl.person_id_map WHERE source_system='synthea';
SELECT 'HISTORIC_VISIT_MAP_ROWS=' || count(*) FROM etl.visit_occurrence_id_map WHERE source_system='synthea';
COMMIT;
