BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
SET LOCAL search_path = pg_catalog, public;

CREATE TEMP TABLE expected_visit_id_map (
    visit_occurrence_id integer GENERATED ALWAYS AS IDENTITY
        (MINVALUE 1 MAXVALUE 2147483647 NO CYCLE),
    source_system varchar(50) NOT NULL,
    source_encounter_id varchar(255) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (visit_occurrence_id),
    UNIQUE (source_system, source_encounter_id),
    CHECK (visit_occurrence_id > 0),
    CHECK (btrim(source_system) <> ''),
    CHECK (btrim(source_encounter_id) <> '')
) ON COMMIT DROP;

DO $body$
DECLARE
    target regclass;
    expected regclass := 'pg_temp.expected_visit_id_map'::regclass;
    item regclass;
    seq_id regclass;
    expected_seq regclass;
    actual_columns jsonb;
    expected_columns jsonb;
    actual_constraints jsonb;
    expected_constraints jsonb;
    signature jsonb;
    seq_state jsonb;
    action text := 'REUSED';
    map_rows bigint;
    visit_rows bigint;
BEGIN
    -- Shared transaction lock name must also be used by the future allocator.
    PERFORM pg_advisory_xact_lock(3003, 5001);

    IF current_database() <> 'omop' THEN
        RAISE EXCEPTION 'Wrong database';
    END IF;

    LOCK TABLE cdm.visit_occurrence IN SHARE ROW EXCLUSIVE MODE;
    SELECT count(*) INTO visit_rows FROM cdm.visit_occurrence;
    target := to_regclass('etl.visit_occurrence_id_map');

    IF target IS NULL THEN
        IF visit_rows <> 0 THEN
            RAISE EXCEPTION
                'Visit data exists without ID map; stop for reconciliation';
        END IF;

        CREATE TABLE etl.visit_occurrence_id_map (
            visit_occurrence_id integer GENERATED ALWAYS AS IDENTITY
                (MINVALUE 1 MAXVALUE 2147483647 NO CYCLE),
            source_system varchar(50) NOT NULL,
            source_encounter_id varchar(255) NOT NULL,
            created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (visit_occurrence_id),
            UNIQUE (source_system, source_encounter_id),
            CHECK (visit_occurrence_id > 0),
            CHECK (btrim(source_system) <> ''),
            CHECK (btrim(source_encounter_id) <> '')
        );

        action := 'CREATED';
        target := 'etl.visit_occurrence_id_map'::regclass;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE oid = target
          AND relkind = 'r'
          AND relpersistence = 'p'
          AND NOT relispartition
          AND NOT relrowsecurity
    ) OR EXISTS (
        SELECT 1 FROM pg_inherits
        WHERE inhrelid = target OR inhparent = target
    ) THEN
        RAISE EXCEPTION 'Unexpected Visit ID map relation type';
    END IF;

    LOCK TABLE etl.visit_occurrence_id_map
        IN SHARE ROW EXCLUSIVE MODE;

    FOREACH item IN ARRAY ARRAY[expected, target] LOOP
        SELECT jsonb_agg(jsonb_build_array(
            a.attname,
            format_type(a.atttypid, a.atttypmod),
            a.attnotnull,
            a.attidentity,
            a.attgenerated,
            pg_get_expr(d.adbin, d.adrelid)
        ) ORDER BY a.attnum)
        INTO actual_columns
        FROM pg_attribute a
        LEFT JOIN pg_attrdef d
          ON d.adrelid = a.attrelid AND d.adnum = a.attnum
        WHERE a.attrelid = item
          AND a.attnum > 0
          AND NOT a.attisdropped;

        SELECT jsonb_agg(jsonb_build_array(
            contype,
            pg_get_constraintdef(oid),
            convalidated,
            condeferrable,
            condeferred
        ) ORDER BY contype, pg_get_constraintdef(oid))
        INTO actual_constraints
        FROM pg_constraint
        WHERE conrelid = item;

        IF item = expected THEN
            expected_columns := actual_columns;
            expected_constraints := actual_constraints;
        ELSIF actual_columns IS DISTINCT FROM expected_columns
           OR actual_constraints IS DISTINCT FROM expected_constraints
        THEN
            RAISE EXCEPTION
                'Existing Visit ID map schema differs; no automatic migration';
        END IF;
    END LOOP;

    IF EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgrelid = target AND NOT tgisinternal
    ) THEN
        RAISE EXCEPTION 'Unexpected custom trigger on Visit ID map';
    END IF;

    seq_id := pg_get_serial_sequence(
        'etl.visit_occurrence_id_map',
        'visit_occurrence_id'
    )::regclass;

    expected_seq := pg_get_serial_sequence(
        'pg_temp.expected_visit_id_map',
        'visit_occurrence_id'
    )::regclass;

    IF seq_id IS NULL OR NOT EXISTS (
        SELECT 1 FROM pg_sequence a, pg_sequence e
        WHERE a.seqrelid = seq_id
          AND e.seqrelid = expected_seq
          AND ROW(
              a.seqtypid, a.seqstart, a.seqincrement, a.seqmax,
              a.seqmin, a.seqcache, a.seqcycle
          ) = ROW(
              e.seqtypid, e.seqstart, e.seqincrement, e.seqmax,
              e.seqmin, e.seqcache, e.seqcycle
          )
    ) THEN
        RAISE EXCEPTION 'Unexpected Visit identity sequence definition';
    END IF;

    -- Reading these fields does not call nextval or advance the sequence.
    EXECUTE format(
        'SELECT jsonb_build_object(''last_value'',last_value,''is_called'',is_called) FROM %s',
        seq_id
    ) INTO seq_state;

    SELECT count(*) INTO map_rows
    FROM etl.visit_occurrence_id_map;

    signature := jsonb_build_object(
        'columns', actual_columns,
        'constraints', actual_constraints
    );

    PERFORM set_config(
        'healthcare.foundation_result',
        jsonb_build_object(
            'status', 'PASS',
            'action', action,
            'map_rows', map_rows,
            'cdm_visit_rows', visit_rows,
            'sequence', seq_id::text,
            'sequence_state', seq_state,
            'schema', signature,
            'ids_allocated', 0
        )::text,
        true
    );
END
$body$;

SELECT current_setting('healthcare.foundation_result');
COMMIT;
