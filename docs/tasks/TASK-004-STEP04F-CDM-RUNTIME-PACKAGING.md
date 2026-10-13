# TASK004 STEP04F — CDM Runtime packaging: safe first image

**Status: BUILD AND UNIT TEST PASS; LIVE DATABASE WRITER NOT YET PACKAGED OR ENABLED.**

Earlier GitHub write-tool safety block cleared on retry. Implemented an independent nonroot CDM image at `images/task004-cdm-runtime/Dockerfile` and CLI `apps/task004/cdm_runtime_cli.py`. The CLI takes a JSON `--plan-file` from the already verified Airflow dynamic plan, reconstructs the immutable context, checks the plan fingerprint and explicitly refuses `database_mutation_authorized=true`. No S3 read or PostgreSQL connection is exposed yet.

**Proof:** Self-Runner [38405587478](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38405587478) SUCCESS, pinned Healthcare SHA `2c4e05b91b331c4f499c53745ce43afecba2ba5f`: 4 CLI/package tests, Python compilation and real `docker build` of the isolated image. No image pushed or deployed. No DAG execution, no PostgreSQL mutation, no secret exposure.

**Next bounded work:**
- Add immutable S3 manifest/Parquet source reader and dynamic OMOP mapping to CDM image, with pinned boto3/pyarrow and explicit endpoint/secret source configuration.
- Package the dynamic PostgreSQL writer with an isolated, least-privilege database client; enforce default `ROLLBACK` and explicit bounded authorization for COMMIT.
- Build/publish an immutable digest image; add isolated in-cluster runtime smoke tests.
- Wire `cdm_load_person → cdm_load_visit → cdm_db_reconcile` to the DAG with strictly verified upstream XCom, then acceptance/replay/recovery. New-batch COMMIT is not authorized at present.

This validated image is a packaging scaffold, NOT a complete dynamic database loading runtime. TASK005 remains ON HOLD.
