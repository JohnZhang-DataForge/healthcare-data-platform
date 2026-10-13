-- TASK004 STEP04A part 2: bounded, privacy-safe aggregate inventory.
-- Only counts and diagnostic aggregate values are emitted, never source IDs/PHI.
\set ON_ERROR_STOP on
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL statement_timeout = '30s';
SET LOCAL lock_timeout = '3s';
SELECT current_database() AS database_name,
       current_setting('transaction_read_only') AS transaction_read_only;
SELECT 'cdm.person' AS object_name, count(*) AS rows, count(DISTINCT person_id) AS unique_ids
FROM cdm.person
UNION ALL
SELECT 'cdm.visit_occurrence',count(*),count(DISTINCT visit_occurrence_id)
FROM cdm.visit_occurrence
UNION ALL
SELECT 'etl.person_id_map',count(*),count(DISTINCT person_id)
FROM etl.person_id_map
UNION ALL
SELECT 'etl.visit_occurrence_id_map',count(*),count(DISTINCT visit_occurrence_id)
FROM etl.visit_occurrence_id_map
UNION ALL
SELECT 'etl.person_stage',count(*),count(DISTINCT person_id)
FROM etl.person_stage
ORDER BY 1;
SELECT 'person' AS entity,
       count(*) AS map_rows,
       count(*) FILTER (WHERE source_system='synthea') AS synthea_rows,
       count(DISTINCT (source_system,source_person_id)) AS unique_business_keys,
       count(DISTINCT person_id) AS unique_target_ids,
       count(*) FILTER (WHERE p.person_id IS NULL) AS mappings_without_target
FROM etl.person_id_map m
LEFT JOIN cdm.person p USING(person_id)
UNION ALL
SELECT 'visit',count(*),
       count(*) FILTER (WHERE source_system='synthea'),
       count(DISTINCT (source_system,source_encounter_id)),
       count(DISTINCT visit_occurrence_id),
       count(*) FILTER (WHERE v.visit_occurrence_id IS NULL)
FROM etl.visit_occurrence_id_map m
LEFT JOIN cdm.visit_occurrence v USING(visit_occurrence_id)
ORDER BY 1;
SELECT count(*) AS visit_rows,
       count(*) FILTER (WHERE p.person_id IS NULL) AS orphan_person_fk,
       count(*) FILTER (WHERE m.visit_occurrence_id IS NULL) AS target_without_id_map
FROM cdm.visit_occurrence v
LEFT JOIN cdm.person p ON p.person_id=v.person_id
LEFT JOIN etl.visit_occurrence_id_map m ON m.visit_occurrence_id=v.visit_occurrence_id;
SELECT count(*) AS person_rows,
       count(*) FILTER (WHERE m.person_id IS NULL) AS target_without_id_map
FROM cdm.person p LEFT JOIN etl.person_id_map m ON m.person_id=p.person_id;
SELECT 'person' AS entity, count(*) AS duplicate_business_key_groups
FROM (SELECT source_system,source_person_id FROM etl.person_id_map
      GROUP BY 1,2 HAVING count(*)>1) q
UNION ALL
SELECT 'visit',count(*)
FROM (SELECT source_system,source_encounter_id FROM etl.visit_occurrence_id_map
      GROUP BY 1,2 HAVING count(*)>1) q;
SELECT count(*) AS stage_rows,
       count(DISTINCT person_id) AS stage_unique_person_ids,
       count(*) FILTER (WHERE p.person_id IS NOT NULL) AS stage_matching_target_ids
FROM etl.person_stage s LEFT JOIN cdm.person p USING(person_id);
SELECT n.nspname AS schema_name,c.relname AS table_name,
       EXISTS (SELECT 1 FROM pg_attribute a WHERE a.attrelid=c.oid
               AND a.attname='batch_id' AND a.attnum>0 AND NOT a.attisdropped) AS has_batch_id,
       EXISTS (SELECT 1 FROM pg_attribute a WHERE a.attrelid=c.oid
               AND a.attname='manifest_sha256' AND a.attnum>0 AND NOT a.attisdropped) AS has_manifest_sha
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE (n.nspname,c.relname) IN
 (('etl','person_stage'),('etl','person_id_map'),('etl','visit_occurrence_id_map'),
  ('cdm','person'),('cdm','visit_occurrence'))
ORDER BY 1,2;
COMMIT;
