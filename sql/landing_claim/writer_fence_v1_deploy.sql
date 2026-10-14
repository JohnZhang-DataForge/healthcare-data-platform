-- TASK004 v1 same-TX Writer fencing: deploy *ONLY* narrow SQL function/roles.
-- Authorized administrative schema COMMIT only; ZERO business INSERT/UPDATE/COMMIT.
-- If already installed, validate the exact privilege/definer/row-lock contract.
-- Does not claim a real S3 batch or touch cdm.person / visit.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL lock_timeout='3s';
SET LOCAL statement_timeout='45s';
DO $pre$
DECLARE n boolean; s boolean; f boolean;
BEGIN
 IF current_user <> 'omop_admin' THEN RAISE EXCEPTION 'BLOCKED:FENCE_INSTALL_ADMIN'; END IF;
 n := EXISTS (SELECT 1 FROM pg_roles WHERE rolname='task004_writer_fence_owner');
 s := to_regnamespace('task004_writer_fence') IS NOT NULL;
 f := to_regprocedure('task004_writer_fence.assert_active_claim(text,text,text,text,text,integer)') IS NOT NULL;
 IF (n OR s OR f) AND NOT (n AND s AND f) THEN
   RAISE EXCEPTION 'BLOCKED:FENCE_PARTIAL_DEPLOYMENT';
 END IF;
 IF has_table_privilege('cdm_writer','etl.landing_batch_ledger','SELECT')
 OR has_table_privilege('cdm_writer','etl.landing_batch_ledger','UPDATE') THEN
   RAISE EXCEPTION 'BLOCKED:FENCE_WRITER_DIRECT_LEDGER_RIGHTS';
 END IF;
END $pre$;

-- Exclusive deployment gate for repeat workflow runs (deployment is DDL-only).
SELECT CASE WHEN to_regnamespace('task004_writer_fence') IS NULL
 THEN 'true' ELSE 'false' END AS first_install \gset
\if :first_install
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

\echo FENCE_FUNCTION_DDL_INSTALL=NEW
\else
\echo FENCE_FUNCTION_DDL_INSTALL=ALREADY_PRESENT_VERIFY_ONLY
\endif

DO $audit$
DECLARE p record;
BEGIN
 SELECT x.prosecdef AS secdef, x.proowner AS owner_oid, x.proconfig AS settings,
        pg_get_functiondef(x.oid) AS def, x.proacl AS acl
 INTO p
 FROM pg_proc x
 WHERE x.oid=to_regprocedure('task004_writer_fence.assert_active_claim(text,text,text,text,text,integer)');
 IF NOT FOUND OR NOT p.secdef
 OR p.owner_oid <> (SELECT oid FROM pg_roles WHERE rolname='task004_writer_fence_owner')
 OR NOT ('search_path=pg_catalog, pg_temp'=ANY(p.settings))
 OR position('FOR UPDATE NOWAIT' in p.def)=0
 OR position('clock_timestamp()' in p.def)=0
 OR EXISTS (SELECT 1 FROM aclexplode(p.acl) WHERE grantee=0 AND privilege_type='EXECUTE')
 OR NOT has_function_privilege('cdm_writer',
   'task004_writer_fence.assert_active_claim(text,text,text,text,text,integer)','EXECUTE')
 OR has_function_privilege('landing_claim_worker',
   'task004_writer_fence.assert_active_claim(text,text,text,text,text,integer)','EXECUTE')
 OR has_table_privilege('cdm_writer','etl.landing_batch_ledger','SELECT')
 OR has_table_privilege('cdm_writer','etl.landing_batch_ledger','UPDATE')
 OR has_schema_privilege('task004_writer_fence_owner','cdm','USAGE')
 OR has_table_privilege('task004_writer_fence_owner','cdm.person','INSERT')
 THEN
   RAISE EXCEPTION 'BLOCKED:FENCE_DEPLOY_VERIFICATION';
 END IF;
 RAISE NOTICE 'FENCE_DDL_DEPLOY_SAFETY=PASS';
END $audit$;
-- Explicit administrative DDL COMMIT. No Claim row nor cdm business DML is issued.
COMMIT;
SELECT CASE WHEN to_regprocedure('task004_writer_fence.assert_active_claim(text,text,text,text,text,integer)')
 IS NOT NULL THEN 'FENCE_DDL_PERSISTED=PASS' ELSE 'FENCE_DDL_PERSISTED=FAIL' END;
\echo OMOP_BUSINESS_COMMIT=NO
\echo AIRFLOW_CLAIM_ENABLE=NO
