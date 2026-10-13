\set ON_ERROR_STOP on
-- TASK004 STEP04C controlled additive DDL, explicitly authorized 2026-10-13.
-- No INSERT/UPDATE/DELETE in cdm, historic etl tables or existing maps.
BEGIN;
SET LOCAL lock_timeout = '3s';
SET LOCAL statement_timeout = '45s';
SELECT pg_advisory_xact_lock(hashtext('TASK004:SCHEMA:MIGRATION:V1'));

DO $$
BEGIN
  IF (SELECT count(*) FROM cdm.person) <> 113
     OR (SELECT count(*) FROM cdm.visit_occurrence) <> 5799
     OR (SELECT count(*) FROM etl.person_id_map WHERE source_system='synthea') <> 113
     OR (SELECT count(*) FROM etl.visit_occurrence_id_map WHERE source_system='synthea') <> 5799
  THEN RAISE EXCEPTION 'HISTORICAL_BASELINE_CHANGED: migration gated'; END IF;
  IF to_regclass('etl.task004_batch_ledger') IS NOT NULL
     OR to_regclass('etl.task004_batch_stage') IS NOT NULL
     OR to_regclass('etl.task004_batch_commit') IS NOT NULL
  THEN RAISE EXCEPTION 'MIGRATION_TABLES_ALREADY_PRESENT: review schema manually'; END IF;
END $$;

CREATE TABLE etl.task004_batch_ledger (
  batch_id text PRIMARY KEY,
  manifest_sha256 char(64) NOT NULL CHECK (manifest_sha256 ~ '^[0-9a-f]{64}$'),
  source_system varchar(50) NOT NULL,
  source_version text NOT NULL,
  ingest_date date NOT NULL,
  person_processing_uri text NOT NULL,
  visit_processing_uri text NOT NULL,
  contract_version text NOT NULL,
  status text NOT NULL DEFAULT 'REGISTERED'
    CHECK(status IN ('REGISTERED','PERSON_STAGED','PERSON_COMMITTED',
                     'VISIT_STAGED','VISIT_COMMITTED','RECONCILED','READBACK_REQUIRED','BLOCKED')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (length(batch_id) > 0)
);

CREATE TABLE etl.task004_batch_stage (
  batch_id text NOT NULL REFERENCES etl.task004_batch_ledger(batch_id) ON DELETE RESTRICT,
  entity text NOT NULL CHECK (entity IN ('person','visit')),
  source_system varchar(50) NOT NULL,
  source_key text NOT NULL CHECK (length(source_key)>0),
  source_person_key text,
  row_fingerprint char(64) NOT NULL CHECK(row_fingerprint ~ '^[0-9a-f]{64}$'),
  canonical_payload jsonb NOT NULL CHECK (jsonb_typeof(canonical_payload)='object'),
  contract_version text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (batch_id,entity,source_system,source_key),
  CHECK (entity <> 'visit' OR (source_person_key IS NOT NULL AND length(source_person_key)>0))
);

CREATE TABLE etl.task004_batch_commit (
  batch_id text NOT NULL REFERENCES etl.task004_batch_ledger(batch_id) ON DELETE RESTRICT,
  entity text NOT NULL CHECK (entity IN ('person','visit')),
  stage_digest char(64) NOT NULL CHECK(stage_digest ~ '^[0-9a-f]{64}$'),
  stage_rows integer NOT NULL CHECK(stage_rows >= 0),
  mapped_rows integer NOT NULL CHECK(mapped_rows >= 0),
  inserted_rows integer NOT NULL CHECK(inserted_rows >= 0),
  updated_rows integer NOT NULL DEFAULT 0 CHECK(updated_rows >= 0),
  readback_digest char(64),
  commit_state text NOT NULL CHECK (commit_state IN ('PREPARED','COMMITTED','READBACK_REQUIRED','VERIFIED')),
  created_at timestamptz NOT NULL DEFAULT now(),
  verified_at timestamptz,
  PRIMARY KEY (batch_id,entity)
);

DO $$
BEGIN
 IF (SELECT count(*) FROM cdm.person) <> 113
 OR (SELECT count(*) FROM cdm.visit_occurrence) <> 5799
 THEN RAISE EXCEPTION 'HISTORICAL_BASELINE_CHANGED_AFTER_DDL'; END IF;
END $$;
COMMIT;
\echo TASK004_BATCH_SCHEMA_MIGRATION=PASS
\echo HISTORICAL_CDM_MUTATION=NO
