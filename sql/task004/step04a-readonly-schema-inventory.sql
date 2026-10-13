-- TASK004 STEP04A / inventory only. Run with psql -X -v ON_ERROR_STOP=1 -f ...
-- No DDL, DML, locks, Airflow trigger, S3 access or Kubernetes mutation.
\set ON_ERROR_STOP on
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL statement_timeout = '30s';
SET LOCAL lock_timeout = '3s';
SELECT current_database() AS database_name, current_user AS executing_role,
       current_setting('transaction_read_only') AS transaction_read_only;
SELECT s.nspname AS schema_name, c.relname AS table_name, c.relkind,
       pg_total_relation_size(c.oid) AS size_bytes
FROM pg_class c JOIN pg_namespace s ON s.oid = c.relnamespace
WHERE (s.nspname, c.relname) IN (
 ('cdm','person'),('cdm','visit_occurrence'),
 ('etl','person_stage'),('etl','person_id_map'),
 ('etl','visit_occurrence_id_map'))
ORDER BY 1,2;
SELECT n.nspname AS schema_name, c.relname AS table_name,
       a.attnum AS column_position, a.attname AS column_name,
       format_type(a.atttypid,a.atttypmod) AS pg_type,
       a.attnotnull AS not_null, a.attidentity AS identity_kind,
       pg_get_expr(d.adbin,d.adrelid) AS default_expression
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
JOIN pg_attribute a ON a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped
LEFT JOIN pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum
WHERE (n.nspname,c.relname) IN (
 ('cdm','person'),('cdm','visit_occurrence'),
 ('etl','person_stage'),('etl','person_id_map'),
 ('etl','visit_occurrence_id_map'))
ORDER BY 1,2,3;
SELECT n.nspname AS schema_name,c.relname AS table_name,
       con.conname AS constraint_name,con.contype AS constraint_type,
       pg_get_constraintdef(con.oid,true) AS definition
FROM pg_constraint con JOIN pg_class c ON c.oid=con.conrelid
JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE (n.nspname,c.relname) IN (
 ('cdm','person'),('cdm','visit_occurrence'),
 ('etl','person_stage'),('etl','person_id_map'),
 ('etl','visit_occurrence_id_map'))
ORDER BY 1,2,3;
SELECT n.nspname AS schema_name, t.relname AS table_name,
       i.relname AS index_name,pg_get_indexdef(i.oid) AS index_definition
FROM pg_index ix JOIN pg_class t ON t.oid=ix.indrelid
JOIN pg_class i ON i.oid=ix.indexrelid
JOIN pg_namespace n ON n.oid=t.relnamespace
WHERE (n.nspname,t.relname) IN (
 ('cdm','person'),('cdm','visit_occurrence'),
 ('etl','person_stage'),('etl','person_id_map'),
 ('etl','visit_occurrence_id_map'))
ORDER BY 1,2,3;
SELECT n.nspname AS schema_name,c.relname AS table_name,
       has_table_privilege(c.oid,'SELECT') AS can_select,
       has_table_privilege(c.oid,'INSERT') AS can_insert,
       has_table_privilege(c.oid,'UPDATE') AS can_update
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE (n.nspname,c.relname) IN (
 ('cdm','person'),('cdm','visit_occurrence'),
 ('etl','person_stage'),('etl','person_id_map'),
 ('etl','visit_occurrence_id_map'))
ORDER BY 1,2;
COMMIT;
