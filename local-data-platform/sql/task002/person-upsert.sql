\set ON_ERROR_STOP on

BEGIN;


-- ============================================================
-- TASK-002
-- OMOP Person transactional UPSERT
--
-- Source:
--   etl.person_stage
--
-- Target:
--   cdm.person
--
-- Behavior:
--   INSERT missing person_id
--   UPDATE only when at least one OMOP Person field changed
--   NO-OP when target row already equals stage row
-- ============================================================


-- Serialize Person CDM commits in this lab implementation.
SELECT pg_advisory_xact_lock(
    hashtext('TASK-002:cdm.person')
);


-- ============================================================
-- 1. Pre-commit plan
-- ============================================================

SELECT
    'UPSERT_PLAN_INSERT_ROWS='
    || COUNT(*)

FROM etl.person_stage s

LEFT JOIN cdm.person p
  ON p.person_id = s.person_id

WHERE p.person_id IS NULL;


SELECT
    'UPSERT_PLAN_UPDATE_ROWS='
    || COUNT(*)

FROM etl.person_stage s

JOIN cdm.person p
  ON p.person_id = s.person_id

WHERE ROW(
    p.gender_concept_id,
    p.year_of_birth,
    p.month_of_birth,
    p.day_of_birth,
    p.birth_datetime,
    p.race_concept_id,
    p.ethnicity_concept_id,
    p.location_id,
    p.provider_id,
    p.care_site_id,
    p.person_source_value,
    p.gender_source_value,
    p.gender_source_concept_id,
    p.race_source_value,
    p.race_source_concept_id,
    p.ethnicity_source_value,
    p.ethnicity_source_concept_id
)
IS DISTINCT FROM
ROW(
    s.gender_concept_id,
    s.year_of_birth,
    s.month_of_birth,
    s.day_of_birth,
    s.birth_datetime,
    s.race_concept_id,
    s.ethnicity_concept_id,
    s.location_id,
    s.provider_id,
    s.care_site_id,
    s.person_source_value,
    s.gender_source_value,
    s.gender_source_concept_id,
    s.race_source_value,
    s.race_source_concept_id,
    s.ethnicity_source_value,
    s.ethnicity_source_concept_id
);


-- ============================================================
-- 2. Transactional UPSERT
-- ============================================================

INSERT INTO cdm.person
(
    person_id,
    gender_concept_id,
    year_of_birth,
    month_of_birth,
    day_of_birth,
    birth_datetime,
    race_concept_id,
    ethnicity_concept_id,
    location_id,
    provider_id,
    care_site_id,
    person_source_value,
    gender_source_value,
    gender_source_concept_id,
    race_source_value,
    race_source_concept_id,
    ethnicity_source_value,
    ethnicity_source_concept_id
)

SELECT
    person_id,
    gender_concept_id,
    year_of_birth,
    month_of_birth,
    day_of_birth,
    birth_datetime,
    race_concept_id,
    ethnicity_concept_id,
    location_id,
    provider_id,
    care_site_id,
    person_source_value,
    gender_source_value,
    gender_source_concept_id,
    race_source_value,
    race_source_concept_id,
    ethnicity_source_value,
    ethnicity_source_concept_id

FROM etl.person_stage

ON CONFLICT (person_id)
DO UPDATE SET

    gender_concept_id =
        EXCLUDED.gender_concept_id,

    year_of_birth =
        EXCLUDED.year_of_birth,

    month_of_birth =
        EXCLUDED.month_of_birth,

    day_of_birth =
        EXCLUDED.day_of_birth,

    birth_datetime =
        EXCLUDED.birth_datetime,

    race_concept_id =
        EXCLUDED.race_concept_id,

    ethnicity_concept_id =
        EXCLUDED.ethnicity_concept_id,

    location_id =
        EXCLUDED.location_id,

    provider_id =
        EXCLUDED.provider_id,

    care_site_id =
        EXCLUDED.care_site_id,

    person_source_value =
        EXCLUDED.person_source_value,

    gender_source_value =
        EXCLUDED.gender_source_value,

    gender_source_concept_id =
        EXCLUDED.gender_source_concept_id,

    race_source_value =
        EXCLUDED.race_source_value,

    race_source_concept_id =
        EXCLUDED.race_source_concept_id,

    ethnicity_source_value =
        EXCLUDED.ethnicity_source_value,

    ethnicity_source_concept_id =
        EXCLUDED.ethnicity_source_concept_id

WHERE ROW(
    cdm.person.gender_concept_id,
    cdm.person.year_of_birth,
    cdm.person.month_of_birth,
    cdm.person.day_of_birth,
    cdm.person.birth_datetime,
    cdm.person.race_concept_id,
    cdm.person.ethnicity_concept_id,
    cdm.person.location_id,
    cdm.person.provider_id,
    cdm.person.care_site_id,
    cdm.person.person_source_value,
    cdm.person.gender_source_value,
    cdm.person.gender_source_concept_id,
    cdm.person.race_source_value,
    cdm.person.race_source_concept_id,
    cdm.person.ethnicity_source_value,
    cdm.person.ethnicity_source_concept_id
)
IS DISTINCT FROM
ROW(
    EXCLUDED.gender_concept_id,
    EXCLUDED.year_of_birth,
    EXCLUDED.month_of_birth,
    EXCLUDED.day_of_birth,
    EXCLUDED.birth_datetime,
    EXCLUDED.race_concept_id,
    EXCLUDED.ethnicity_concept_id,
    EXCLUDED.location_id,
    EXCLUDED.provider_id,
    EXCLUDED.care_site_id,
    EXCLUDED.person_source_value,
    EXCLUDED.gender_source_value,
    EXCLUDED.gender_source_concept_id,
    EXCLUDED.race_source_value,
    EXCLUDED.race_source_concept_id,
    EXCLUDED.ethnicity_source_value,
    EXCLUDED.ethnicity_source_concept_id
);


-- ============================================================
-- 3. Post-commit reconciliation inside transaction
-- ============================================================

SELECT
    'POST_UPSERT_STAGE_MINUS_CDM='
    || COUNT(*)

FROM
(
    SELECT *
    FROM etl.person_stage

    EXCEPT

    SELECT p.*
    FROM cdm.person p

    JOIN etl.person_id_map m
      ON p.person_id = m.person_id

    WHERE m.source_system = 'synthea'
) d;


SELECT
    'POST_UPSERT_CDM_MINUS_STAGE='
    || COUNT(*)

FROM
(
    SELECT p.*
    FROM cdm.person p

    JOIN etl.person_id_map m
      ON p.person_id = m.person_id

    WHERE m.source_system = 'synthea'

    EXCEPT

    SELECT *
    FROM etl.person_stage
) d;


COMMIT;
