-- Local OMOP v5.4 Observation Period v1 — synthetic EHR encounter-bounded.
-- OpenSpec-Change: derive-local-omop-observation-period
-- OpenSpec-Task: 1.1
--
-- Source: real materialized cdm.visit_occurrence, not synthetic guessed dates.
-- One OP per existing Person, type 44814724 (Period covering healthcare encounters).
-- This heuristic DOES NOT prove uninterrupted enrollment or complete EHR coverage.
-- Run only after separately verified PRIVATE immutable Blob target-table snapshot
-- and physical ROLLBACK rehearsal. Never re-run on a nonempty OP table.
-- Only INSERT INTO cdm.observation_period is allowed; no other CDM writes.
BEGIN;
SET LOCAL statement_timeout = '45s';
SET LOCAL lock_timeout = '2s';
DO $observation_period_v1$
DECLARE
    inserted_count integer;
BEGIN
    IF NOT pg_try_advisory_xact_lock(443600, 54401) THEN
        RAISE EXCEPTION 'OP_V1_CONCURRENT_WRITER_HOLD';
    END IF;
    LOCK TABLE cdm.observation_period IN SHARE ROW EXCLUSIVE MODE NOWAIT;

    IF (SELECT COUNT(*) FROM cdm.observation_period) <> 0 THEN
        RAISE EXCEPTION 'OP_V1_TARGET_NOT_EMPTY';
    END IF;
    IF (SELECT COUNT(*) FROM cdm.person) <> 1394
       OR (SELECT COUNT(*) FROM cdm.visit_occurrence) <> 200556 THEN
        RAISE EXCEPTION 'OP_V1_CDM_SNAPSHOT_DRIFT';
    END IF;
    IF (SELECT COUNT(*) FROM etl.person_id_map
        WHERE source_system='synthea') <> 1394
       OR (SELECT COUNT(*) FROM etl.visit_occurrence_id_map
        WHERE source_system='synthea') <> 200556 THEN
        RAISE EXCEPTION 'OP_V1_SOURCE_MAP_COUNT_DRIFT';
    END IF;
    IF (SELECT COUNT(*) FROM etl.task004_batch_ledger
        WHERE source_system='synthea') <> 19
       OR (SELECT COUNT(*) FROM etl.landing_batch_ledger
        WHERE source_system='synthea' AND status='COMPLETED') <> 18 THEN
        RAISE EXCEPTION 'OP_V1_BATCH_COUNTS_DRIFT';
    END IF;
    IF (SELECT COUNT(*) FROM cdm.concept
        WHERE concept_id=44814724
          AND concept_class_id='Obs Period Type'
          AND concept_name='Period covering healthcare encounters'
          AND invalid_reason IS NULL) <> 1 THEN
        RAISE EXCEPTION 'OP_V1_VOCAB_TYPE_INVALID';
    END IF;
    IF EXISTS (
       SELECT 1 FROM cdm.visit_occurrence v
       WHERE v.visit_start_date IS NULL
          OR v.visit_end_date IS NULL
          OR v.visit_end_date < v.visit_start_date
          OR v.visit_end_date > CURRENT_DATE
    ) THEN
       RAISE EXCEPTION 'OP_V1_VISIT_INVALID_DATE';
    END IF;
    IF EXISTS (
       SELECT 1 FROM cdm.visit_occurrence v
       LEFT JOIN cdm.person p ON p.person_id=v.person_id
       WHERE p.person_id IS NULL
          OR (p.birth_datetime IS NOT NULL
              AND v.visit_start_date < p.birth_datetime::date)
    ) THEN
       RAISE EXCEPTION 'OP_V1_ORPHAN_OR_PREBIRTH_VISIT';
    END IF;
    IF EXISTS (
       SELECT 1 FROM cdm.person p
       LEFT JOIN cdm.visit_occurrence v ON v.person_id=p.person_id
       WHERE v.visit_occurrence_id IS NULL
    ) THEN
       RAISE EXCEPTION 'OP_V1_PERSON_WITHOUT_VISIT';
    END IF;
    IF EXISTS (
       SELECT 1 FROM cdm.person p
       LEFT JOIN etl.person_id_map m
         ON m.person_id=p.person_id AND m.source_system='synthea'
       WHERE m.person_id IS NULL
    ) OR EXISTS (
       SELECT 1 FROM cdm.visit_occurrence v
       LEFT JOIN etl.visit_occurrence_id_map m
         ON m.visit_occurrence_id=v.visit_occurrence_id
        AND m.source_system='synthea'
       WHERE m.visit_occurrence_id IS NULL
    ) THEN
       RAISE EXCEPTION 'OP_V1_INCOMPLETE_IDENTITY_MAP';
    END IF;
    IF EXISTS (
       SELECT 1 FROM cdm.person
       WHERE person_id IS NULL OR person_id <= 0
    ) THEN
       RAISE EXCEPTION 'OP_V1_INVALID_DETERMINISTIC_ID';
    END IF;

    INSERT INTO cdm.observation_period (
        observation_period_id,
        person_id,
        observation_period_start_date,
        observation_period_end_date,
        period_type_concept_id
    )
    SELECT person_id, person_id,
           MIN(visit_start_date), MAX(visit_end_date), 44814724
    FROM cdm.visit_occurrence
    GROUP BY person_id;
    GET DIAGNOSTICS inserted_count = ROW_COUNT;
    IF inserted_count <> 1394 THEN
        RAISE EXCEPTION 'OP_V1_NOT_ALL_PERSONS_INSERTED';
    END IF;

    IF EXISTS (
       SELECT 1 FROM cdm.observation_period op
       LEFT JOIN (
         SELECT person_id, MIN(visit_start_date) AS start_day,
                MAX(visit_end_date) AS end_day
         FROM cdm.visit_occurrence
         GROUP BY person_id
       ) b ON b.person_id=op.person_id
       WHERE b.person_id IS NULL OR op.observation_period_id<>op.person_id
          OR op.observation_period_start_date<>b.start_day
          OR op.observation_period_end_date<>b.end_day
          OR op.period_type_concept_id<>44814724
    ) OR (SELECT COUNT(*) FROM cdm.observation_period)<>1394 THEN
       RAISE EXCEPTION 'OP_V1_IN_TRANSACTION_READBACK_DRIFT';
    END IF;
END
$observation_period_v1$;
COMMIT;
