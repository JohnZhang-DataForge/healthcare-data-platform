\set ON_ERROR_STOP on
-- Additive, independent consumer lease ledger. No changes to legacy task004
-- ledger, source manifests, patient/visit tables, or existing mappings.
-- Never rerun against an existing unexpected layout: refuse preexisting table.
BEGIN;
SET LOCAL lock_timeout = '3s';
SET LOCAL statement_timeout = '30s';
SELECT pg_advisory_xact_lock(hashtext('landing-batch-ledger-schema-v1'));
DO $$
BEGIN
  IF to_regclass('etl.landing_batch_ledger') IS NOT NULL THEN
    RAISE EXCEPTION 'BLOCKED:LANDING_LEDGER_ALREADY_EXISTS_REVIEW_SCHEMA';
  END IF;
END $$;

CREATE TABLE etl.landing_batch_ledger (
  source_system text NOT NULL CHECK (length(source_system) BETWEEN 1 AND 64),
  batch_id text NOT NULL CHECK (length(batch_id) BETWEEN 1 AND 256),
  manifest_sha256 text NOT NULL
    CHECK (manifest_sha256 ~ '^[a-f0-9]{64}$'),
  manifest_uri text NOT NULL
    CHECK (manifest_uri LIKE 's3://%' AND length(manifest_uri) <= 2048),
  status text NOT NULL
    CHECK (status IN ('PROCESSING', 'FAILED', 'COMPLETED')),
  attempt_count integer NOT NULL DEFAULT 1 CHECK (attempt_count >= 1),
  lease_owner text,
  lease_expires_at timestamptz,
  reconciliation_sha256 text
    CHECK (reconciliation_sha256 IS NULL OR reconciliation_sha256 ~ '^[a-f0-9]{64}$'),
  started_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  completed_at timestamptz,
  PRIMARY KEY (source_system, batch_id),
  CHECK (
    (status = 'PROCESSING' AND lease_owner IS NOT NULL
      AND length(lease_owner) > 0 AND lease_expires_at IS NOT NULL
      AND reconciliation_sha256 IS NULL AND completed_at IS NULL)
    OR
    (status = 'FAILED' AND lease_owner IS NULL
      AND lease_expires_at IS NULL AND reconciliation_sha256 IS NULL
      AND completed_at IS NULL)
    OR
    (status = 'COMPLETED' AND lease_owner IS NULL
      AND lease_expires_at IS NULL AND reconciliation_sha256 IS NOT NULL
      AND completed_at IS NOT NULL)
  )
);

-- Keep new consumer state isolated from the legacy OMOP writer bookkeeping.
COMMIT;
\echo LANDING_BATCH_LEDGER_SCHEMA=PASS
\echo OMOP_BUSINESS_MUTATION=NO
