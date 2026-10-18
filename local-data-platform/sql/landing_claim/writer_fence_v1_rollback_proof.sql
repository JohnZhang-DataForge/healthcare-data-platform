-- TASK004 minimum-privilege SECURITY DEFINER / writer same-transaction gate.
-- LIVE PROOF ONLY: entire DDL, synthetic Claim state, privilege grants and
-- all role transitions are inside one transaction and ALWAYS ROLLBACK.
-- No production deployment, business COMMIT, S3 mutation, Spark or Airflow.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL lock_timeout = '2500ms';
SET LOCAL statement_timeout = '30000ms';

DO $preflight$
BEGIN
 IF current_user <> 'omop_admin' THEN
   RAISE EXCEPTION 'BLOCKED:ADMIN_PROBE_PRINCIPAL';
 END IF;
 IF EXISTS(SELECT 1 FROM pg_catalog.pg_roles WHERE rolname='task004_writer_fence_owner')
 OR to_regnamespace('task004_writer_fence') IS NOT NULL THEN
   RAISE EXCEPTION 'BLOCKED:FENCE_PROBE_NAMESPACE_ALREADY_PRESENT';
 END IF;
 IF EXISTS (SELECT 1 FROM etl.landing_batch_ledger
            WHERE source_system='synthea'
              AND batch_id='synthea-new-only-writer-fence-rollback') THEN
   RAISE EXCEPTION 'BLOCKED:FENCE_SYNTHETIC_ROW_ALREADY_PRESENT';
 END IF;
 IF has_table_privilege('cdm_writer','etl.landing_batch_ledger','SELECT')
 OR has_table_privilege('cdm_writer','etl.landing_batch_ledger','UPDATE') THEN
   RAISE EXCEPTION 'BLOCKED:WRITER_ALREADY_HAS_LEDGER_DIRECT_ACCESS';
 END IF;
END $preflight$;

CREATE ROLE task004_writer_fence_owner NOLOGIN NOINHERIT;
CREATE SCHEMA task004_writer_fence AUTHORIZATION task004_writer_fence_owner;
REVOKE ALL ON SCHEMA task004_writer_fence FROM PUBLIC;
GRANT USAGE ON SCHEMA etl TO task004_writer_fence_owner;
-- UPDATE on one harmless column is the minimum PostgreSQL row-lock privilege.
-- This role has NO LOGIN and no DML permission on cdm.person or visit.
GRANT SELECT, UPDATE (updated_at) ON etl.landing_batch_ledger
  TO task004_writer_fence_owner;

SET LOCAL ROLE task004_writer_fence_owner;
CREATE FUNCTION task004_writer_fence.assert_active_claim(
    p_source text, p_batch text, p_sha text, p_uri text,
    p_owner text, p_attempt integer
) RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $func$
DECLARE
 v_sha text;
 v_uri text;
 v_status text;
 v_attempt integer;
 v_owner text;
 v_expiry timestamptz;
BEGIN
 -- Never trust the caller: no generic source, no legacy identity.
 IF p_source IS DISTINCT FROM 'synthea'
 OR p_batch IS NULL
 OR p_batch !~ '^synthea-new-only-[A-Za-z0-9][A-Za-z0-9._-]{1,127}$'
 OR p_sha IS NULL OR p_sha !~ '^[a-f0-9]{64}$'
 OR p_owner IS NULL OR p_owner !~ '^[a-f0-9]{48}$'
 OR p_attempt IS NULL OR p_attempt < 1
 OR p_uri IS NULL
 OR length(p_uri) > 2048
 OR p_uri NOT LIKE 's3://%/source=synthea/%'
 OR right(p_uri, length('/batch_id=' || p_batch || '/manifest.json'))
         <> '/batch_id=' || p_batch || '/manifest.json'
 THEN
    RAISE EXCEPTION 'BLOCKED:WRITER_FENCE_BAD_TICKET';
 END IF;
 -- Critical: THIS ROW LOCK MUST BE ACQUIRED WITHIN THE WRITER TRANSACTION.
 -- The lock survives function return, through both OMOP entity writes, until
 -- explicit ROLLBACK or (in a future separately approved version) COMMIT.
 SELECT manifest_sha256, manifest_uri, status, attempt_count,
        lease_owner, lease_expires_at
   INTO v_sha, v_uri, v_status, v_attempt, v_owner, v_expiry
 FROM etl.landing_batch_ledger
 WHERE source_system=p_source AND batch_id=p_batch
 FOR UPDATE NOWAIT;
 IF NOT FOUND THEN
   RAISE EXCEPTION 'BLOCKED:WRITER_FENCE_CLAIM_ABSENT';
 END IF;
 IF v_sha IS DISTINCT FROM p_sha OR v_uri IS DISTINCT FROM p_uri THEN
   RAISE EXCEPTION 'BLOCKED:WRITER_FENCE_MANIFEST_DRIFT';
 END IF;
 IF v_status IS DISTINCT FROM 'PROCESSING' THEN
   RAISE EXCEPTION 'BLOCKED:WRITER_FENCE_STATUS';
 END IF;
 IF v_attempt IS DISTINCT FROM p_attempt
 OR v_owner IS DISTINCT FROM p_owner THEN
   RAISE EXCEPTION 'BLOCKED:WRITER_FENCE_OWNER_OR_ATTEMPT';
 END IF;
 -- Use real DB clock after lock acquisition; transaction now() is stale.
 IF v_expiry IS NULL OR v_expiry <= pg_catalog.clock_timestamp() THEN
   RAISE EXCEPTION 'BLOCKED:WRITER_FENCE_LEASE_EXPIRED';
 END IF;
END
$func$;
RESET ROLE;
REVOKE ALL ON FUNCTION task004_writer_fence.assert_active_claim(
 text,text,text,text,text,integer) FROM PUBLIC;
GRANT USAGE ON SCHEMA task004_writer_fence TO cdm_writer;
GRANT EXECUTE ON FUNCTION task004_writer_fence.assert_active_claim(
 text,text,text,text,text,integer) TO cdm_writer;

DO $grants$
BEGIN
 IF NOT has_function_privilege('cdm_writer',
  'task004_writer_fence.assert_active_claim(text,text,text,text,text,integer)','EXECUTE')
 OR has_function_privilege('landing_claim_worker',
  'task004_writer_fence.assert_active_claim(text,text,text,text,text,integer)','EXECUTE')
 OR has_table_privilege('cdm_writer','etl.landing_batch_ledger','SELECT')
 OR has_table_privilege('cdm_writer','etl.landing_batch_ledger','UPDATE')
 OR has_schema_privilege('task004_writer_fence_owner','cdm','USAGE')
 OR has_table_privilege('task004_writer_fence_owner','cdm.person','INSERT') THEN
   RAISE EXCEPTION 'BLOCKED:WRITER_FENCE_LEAST_PRIVILEGE';
 END IF;
 RAISE NOTICE 'PG_WRITER_FENCE_PRIVILEGES=PASS';
END $grants$;

-- Fabricated fixture has NO S3 READY, never references a real batch.
INSERT INTO etl.landing_batch_ledger(
 source_system,batch_id,manifest_sha256,manifest_uri,
 status,attempt_count,lease_owner,lease_expires_at
) VALUES (
 'synthea','synthea-new-only-writer-fence-rollback',
 repeat('d',64),
 's3://health-landing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-14/batch_id=synthea-new-only-writer-fence-rollback/manifest.json',
 'PROCESSING',2,repeat('c',48),clock_timestamp()+interval '15 minutes'
);

SET LOCAL ROLE cdm_writer;
DO $writer$
DECLARE
 b text := 'synthea-new-only-writer-fence-rollback';
 u text := 's3://health-landing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-14/batch_id=synthea-new-only-writer-fence-rollback/manifest.json';
BEGIN
 -- Prove the writer role really has no direct Ledger read permission.
 BEGIN
   PERFORM count(*) FROM etl.landing_batch_ledger;
   RAISE EXCEPTION 'BLOCKED:WRITER_DIRECT_LEDGER_READ_ALLOWED';
 EXCEPTION WHEN insufficient_privilege THEN
   RAISE NOTICE 'PG_WRITER_FENCE_DIRECT_LEDGER_ACCESS_DENIED=PASS';
 END;
 -- Same transaction: must succeed through the definer, twice, surrounding
 -- a writer-local DML marker. No CDM business table rows are written.
 PERFORM task004_writer_fence.assert_active_claim('synthea',b,repeat('d',64),u,repeat('c',48),2);
 CREATE TEMP TABLE task004_writer_fence_tx_marker (phase text) ON COMMIT DROP;
 INSERT INTO task004_writer_fence_tx_marker VALUES ('person'),('visit');
 IF (SELECT count(*) FROM task004_writer_fence_tx_marker)<>2 THEN
   RAISE EXCEPTION 'BLOCKED:FENCE_TX_MARKER';
 END IF;
 PERFORM task004_writer_fence.assert_active_claim('synthea',b,repeat('d',64),u,repeat('c',48),2);
 RAISE NOTICE 'PG_WRITER_FENCE_BEFORE_AFTER_WRITES_SAME_TX=PASS';
 -- Negative tests: each SECURITY DEFINER exception is handled by a PL/pgSQL
 -- subtransaction, preserving the outer transaction and fixture.
 BEGIN
   PERFORM task004_writer_fence.assert_active_claim('synthea',b,repeat('d',64),u,repeat('a',48),2);
   RAISE EXCEPTION 'BLOCKED:WRONG_OWNER_ACCEPTED';
 EXCEPTION WHEN SQLSTATE 'P0001' THEN
   IF SQLERRM <> 'BLOCKED:WRITER_FENCE_OWNER_OR_ATTEMPT' THEN RAISE; END IF;
 END;
 BEGIN
   PERFORM task004_writer_fence.assert_active_claim('synthea',b,repeat('d',64),u,repeat('c',48),1);
   RAISE EXCEPTION 'BLOCKED:OLD_ATTEMPT_ACCEPTED';
 EXCEPTION WHEN SQLSTATE 'P0001' THEN
   IF SQLERRM <> 'BLOCKED:WRITER_FENCE_OWNER_OR_ATTEMPT' THEN RAISE; END IF;
 END;
 BEGIN
   PERFORM task004_writer_fence.assert_active_claim('synthea',b,repeat('a',64),u,repeat('c',48),2);
   RAISE EXCEPTION 'BLOCKED:MANIFEST_DRIFT_ACCEPTED';
 EXCEPTION WHEN SQLSTATE 'P0001' THEN
   IF SQLERRM <> 'BLOCKED:WRITER_FENCE_MANIFEST_DRIFT' THEN RAISE; END IF;
 END;
 BEGIN
   PERFORM task004_writer_fence.assert_active_claim('synthea',b||'-absent',repeat('d',64),
       replace(u,'/batch_id='||b||'/','/batch_id='||b||'-absent/'),repeat('c',48),2);
   RAISE EXCEPTION 'BLOCKED:MISSING_CLAIM_ACCEPTED';
 EXCEPTION WHEN SQLSTATE 'P0001' THEN
   IF SQLERRM <> 'BLOCKED:WRITER_FENCE_CLAIM_ABSENT' THEN RAISE; END IF;
 END;
 RAISE NOTICE 'PG_WRITER_FENCE_OWNER_ATTEMPT_MANIFEST_ABSENT=PASS';
END $writer$;
RESET ROLE;

UPDATE etl.landing_batch_ledger
  SET lease_expires_at=clock_timestamp()-interval '1 second'
 WHERE batch_id='synthea-new-only-writer-fence-rollback';
SET LOCAL ROLE cdm_writer;
DO $expired$
BEGIN
 BEGIN
  PERFORM task004_writer_fence.assert_active_claim(
   'synthea','synthea-new-only-writer-fence-rollback',repeat('d',64),
   's3://health-landing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-14/batch_id=synthea-new-only-writer-fence-rollback/manifest.json',
   repeat('c',48),2);
  RAISE EXCEPTION 'BLOCKED:EXPIRED_LEASE_ACCEPTED';
 EXCEPTION WHEN SQLSTATE 'P0001' THEN
  IF SQLERRM <> 'BLOCKED:WRITER_FENCE_LEASE_EXPIRED' THEN RAISE; END IF;
 END;
 RAISE NOTICE 'PG_WRITER_FENCE_EXPIRED=PASS';
END $expired$;
RESET ROLE;

UPDATE etl.landing_batch_ledger
  SET status='FAILED',lease_owner=NULL,lease_expires_at=NULL
 WHERE batch_id='synthea-new-only-writer-fence-rollback';
SET LOCAL ROLE cdm_writer;
DO $failed$
BEGIN
 BEGIN
  PERFORM task004_writer_fence.assert_active_claim(
   'synthea','synthea-new-only-writer-fence-rollback',repeat('d',64),
   's3://health-landing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-14/batch_id=synthea-new-only-writer-fence-rollback/manifest.json',
   repeat('c',48),2);
  RAISE EXCEPTION 'BLOCKED:FAILED_LEASE_ACCEPTED';
 EXCEPTION WHEN SQLSTATE 'P0001' THEN
  IF SQLERRM <> 'BLOCKED:WRITER_FENCE_STATUS' THEN RAISE; END IF;
 END;
 RAISE NOTICE 'PG_WRITER_FENCE_FAILED_HOLD=PASS';
END $failed$;
RESET ROLE;

-- Transactional DDL, grants, synthetic row and marker all disappear.
ROLLBACK;
SELECT CASE WHEN to_regnamespace('task004_writer_fence') IS NULL
 AND NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='task004_writer_fence_owner')
 AND NOT EXISTS(SELECT 1 FROM etl.landing_batch_ledger
                 WHERE batch_id='synthea-new-only-writer-fence-rollback')
 THEN 'PG_WRITER_FENCE_PROBE_NO_PERSISTENCE=PASS'
 ELSE 'PG_WRITER_FENCE_PROBE_NO_PERSISTENCE=FAIL' END AS rollback_proof;
