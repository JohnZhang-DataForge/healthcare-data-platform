BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL statement_timeout = '30s';
SET LOCAL lock_timeout = '5s';

WITH wanted(name) AS (
    VALUES ('cdm.visit_occurrence'), ('etl.person_id_map'),
           ('etl.visit_occurrence_id_map')
), relations AS (
    SELECT name, to_regclass(name) AS oid FROM wanted
)
SELECT jsonb_build_object(
    'report', 'database_baseline',
    'database', current_database(),
    'captured_at', transaction_timestamp(),
    'read_only', current_setting('transaction_read_only'),
    'isolation', current_setting('transaction_isolation'),
    'person_rows', (SELECT count(*) FROM cdm.person),
    'synthea_person_map_rows',
        (SELECT count(*) FROM etl.person_id_map WHERE source_system = 'synthea'),
    'visit_rows', (SELECT count(*) FROM cdm.visit_occurrence),
    'max_visit_id', (SELECT max(visit_occurrence_id) FROM cdm.visit_occurrence),
    'tables', (
        SELECT jsonb_agg(jsonb_build_object(
            'name', r.name, 'exists', r.oid IS NOT NULL,
            'columns', COALESCE((
                SELECT jsonb_agg(jsonb_build_object(
                    'position', a.attnum, 'name', a.attname,
                    'type', format_type(a.atttypid, a.atttypmod),
                    'nullable', NOT a.attnotnull, 'identity', a.attidentity,
                    'default', pg_get_expr(d.adbin, d.adrelid)
                ) ORDER BY a.attnum)
                FROM pg_attribute a
                LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
                WHERE a.attrelid = r.oid AND a.attnum > 0 AND NOT a.attisdropped
            ), '[]'::jsonb),
            'constraints', COALESCE((
                SELECT jsonb_agg(jsonb_build_object(
                    'name', c.conname, 'definition', pg_get_constraintdef(c.oid)
                ) ORDER BY c.conname)
                FROM pg_constraint c WHERE c.conrelid = r.oid
            ), '[]'::jsonb),
            'indexes', COALESCE((
                SELECT jsonb_agg(pg_get_indexdef(i.indexrelid) ORDER BY i.indexrelid)
                FROM pg_index i WHERE i.indrelid = r.oid
            ), '[]'::jsonb)
        ) ORDER BY r.name) FROM relations r
    ),
    'concepts', (
        SELECT jsonb_agg(jsonb_build_object(
            'requested_id', requested.id, 'found', c.concept_id IS NOT NULL,
            'name', c.concept_name, 'domain', c.domain_id,
            'standard', c.standard_concept, 'invalid_reason', c.invalid_reason,
            'valid_start_date', c.valid_start_date, 'valid_end_date', c.valid_end_date
        ) ORDER BY requested.id)
        FROM unnest(ARRAY[:concept_ids]::integer[]) AS requested(id)
        LEFT JOIN cdm.concept c ON c.concept_id = requested.id
    ),
    'visit_sequences', COALESCE((
        SELECT jsonb_agg(jsonb_build_object(
            'schema', schemaname, 'name', sequencename,
            'type', data_type::text, 'start', start_value,
            'increment', increment_by, 'max', max_value,
            'last_value', last_value, 'cycle', cycle
        ) ORDER BY schemaname, sequencename)
        FROM pg_sequences
        WHERE schemaname IN ('etl', 'cdm')
          AND (sequencename ILIKE '%visit%' OR sequencename ILIKE '%encounter%')
    ), '[]'::jsonb)
);

-- Only generate a SELECT for an existing optional map; never create it here.
SELECT CASE WHEN to_regclass('etl.visit_occurrence_id_map') IS NULL THEN
    $$SELECT jsonb_build_object('report','visit_map_count','exists',false,'rows',NULL);$$
ELSE
    $$SELECT jsonb_build_object('report','visit_map_count','exists',true,'rows',count(*)) FROM etl.visit_occurrence_id_map;$$
END
\gexec

COMMIT;
