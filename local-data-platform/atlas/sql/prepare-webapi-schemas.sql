-- Controlled P3 application-only migration. REVIEW BEFORE EXECUTING.
-- Preconditions: atlas_webapi LOGIN and atlas_migrator LOGIN roles have been
-- created with separate randomly generated passwords; their credentials
-- are held in the dw-atlas Kubernetes Secret, not in Git or SQL text.
-- The existing omop/cdm data and all current non-ATLAS schemas remain unchanged.
-- DDL is transactional; fail closed if any Atlas schemas already exist.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '45s';

DO $guard$
BEGIN
  IF to_regnamespace('webapi') IS NOT NULL
     OR to_regnamespace('atlas_results') IS NOT NULL
     OR to_regnamespace('atlas_temp') IS NOT NULL THEN
    RAISE EXCEPTION 'ATLAS_SCHEMA_COLLISION: stop and independently inspect existing content';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'atlas_webapi')
     OR NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'atlas_migrator') THEN
    RAISE EXCEPTION 'ATLAS_ROLE_MISSING: provision dedicated roles first';
  END IF;
  IF to_regnamespace('cdm') IS NULL THEN
    RAISE EXCEPTION 'LOCAL_CDM_NOT_FOUND';
  END IF;
END
$guard$;

CREATE SCHEMA webapi AUTHORIZATION atlas_migrator;
CREATE SCHEMA atlas_results AUTHORIZATION atlas_migrator;
CREATE SCHEMA atlas_temp AUTHORIZATION atlas_migrator;

GRANT USAGE ON SCHEMA webapi TO atlas_webapi;
GRANT USAGE, CREATE ON SCHEMA atlas_results, atlas_temp TO atlas_webapi;

ALTER DEFAULT PRIVILEGES FOR ROLE atlas_migrator IN SCHEMA webapi
  GRANT SELECT, INSERT, UPDATE, DELETE, REFERENCES ON TABLES TO atlas_webapi;
ALTER DEFAULT PRIVILEGES FOR ROLE atlas_migrator IN SCHEMA webapi
  GRANT USAGE, SELECT ON SEQUENCES TO atlas_webapi;

GRANT USAGE ON SCHEMA cdm TO atlas_webapi;
GRANT SELECT ON ALL TABLES IN SCHEMA cdm TO atlas_webapi;

COMMIT;
