# TASK004 STEP04F — CDM Runtime S3/Parquet packaging acceptance

**Status: BUILD + IMAGE SMOKE TEST PASS. Not a deployed or enabled PostgreSQL writer.**

## Implemented
- Updated isolated non-root `images/task004-cdm-runtime/Dockerfile` installs pinned `boto3==1.40.40` and `pyarrow==21.0.0`, and packages four existing audited Python modules: dynamic batch planner, Person/Visit canonical-to-OMOP adapters, strict S3 source reader, and transactional PostgreSQL SQL builder.
- Extended `apps/task004/cdm_runtime_cli.py` with optional `--validate-source person|visit`, which validates current immutable plan, fetches its S3 Manifest and exactly one Processing Parquet, checks source integrity and creates canonical-to-OMOP rows **in memory**.
- `TASK004_S3_ENDPOINT_URL` is injected via environment; IAM/S3 credentials must be injected using runtime secrets, not DAG XCom. The CLI does not print clinical records or rendered SQL.
- The packaged dynamic PostgreSQL renderer stays **non-executing**; the CLI exposes no `COMMIT`, `psql`, Kubernetes command execution or DB authorization bypass. No new-batch database mutation was performed.

## Real evidence
[Self-Runner 38406288417](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38406288417) **SUCCESS**, pinned Healthcare SHA `146c3bdb4f8d1af5c8256ff05fbc979e7c0508f6`:
- 5 CLI/package tests, 10 dynamic row adapter tests, 4 mocked S3 tests, and 8 dynamic PG writer contract tests passed (27 total).
- Actual `docker build` succeeded on GitHub-hosted runner.
- Actual `docker run --entrypoint python` imported boto3, pyarrow, S3 source adapter and dynamic PostgreSQL SQL renderer: `CDM_RUNTIME_DEPENDENCIES=PASS`, `CDM_IMAGE_BUILD_AND_SMOKE=PASS`.
- No image pushed/deployed. No live S3 source read in this run, no DAG run, no PostgreSQL mutations.

## Next steps
- Publish immutable GHCR digest, deploy a strictly read-only in-cluster source validation Job with Kubernetes Secret injection and pinned endpoint; validate actual S3 canonical inputs.
- Add least-privilege PostgreSQL execution capability and a safe Airflow Operator/command to support separately authorized new-batch Person→Visit COMMIT, with default ROLLBACK, post-commit independent readback, secret control and retries.
- Integrate Airflow CDM load and final reconciliation tasks, and complete STEP04G replay and recovery verification. TASK005 remains ON HOLD.

This checkpoint establishes **complete source-adapter and SQL-renderer code packaging**, not completed CDM data loading orchestration.
