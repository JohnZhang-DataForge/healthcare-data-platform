# TASK004 STEP04F — CDM Runtime PostgreSQL Writer ROLLBACK Acceptance

**Result: PASS. Actual published CDM runtime executed a synthetic dynamic Person transaction through the scoped writer and rolled it back. No OMOP business data committed.**

## Implementation

- Added `airflow/dags/task004_cdm_postgres_rollback_executor.py`, running the previously verified dynamic PostgreSQL SQL renderer with `allow_commit=False` only, refusing any SQL that does not end in `ROLLBACK`, and explicitly requiring the `cdm_writer` identity and DB connection variables. Runs through `psycopg` without exposing a COMMIT subcommand.
- Added CLI `--rollback-entity person|visit --rollback-rows-file /path/to/rows.json`, while preserving existing immutable plan fingerprint validation. Added packaged executor to the nonroot CDM Docker image and fail-closed unit tests.
- **New GHCR image digest:** `ghcr.io/johnzhang-dataforge/healthcare-data-platform-task004-cdm-runtime@sha256:4cc976d07d4a1ac58ab604436acc12602368b500b01c9d2b2f734eb2c1b9d978`.
- [Image build/publish 38428967714](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/38428967714) SUCCESS.
- [Self-Runner live Kubernetes 38429423958](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38429423958) SUCCESS, created a synthetic Person plan and OMOP rows, mounted read-only ConfigMap into digest-pinned CDM Runtime on worker02, and connected using the existing `dw-spark/task004-cdm-writer-db` Secret.
- Real PostgreSQL ROLLBACK path executed through our **own** CDM runtime (not a standalone `psql` image). Evidence: `CDM_WRITER_RUNTIME_K8S_ROLLBACK=PASS` and `CDM_WRITER_RUNTIME_NO_PERSISTENCE=PASS`.
- Independent PostgreSQL readback after the Job verified Person=136, Visit=9391 and zero synthetic ledger/stage/commit/map records.
- No Airflow DAG changes, no new batch COMMIT, no real patient/visit records inserted.
- Initial Self-Runner run 38429262275 failed because the fixture's module path pointed to the wrong checkout directory; fixed the path and reran to success. One GitHub write attempt was rejected by an intermittent tool safety check; subsequent valid workflow update succeeded.

## Limitations and next step
The rollback CLI currently accepts prepared OMOP rows from a mounted JSON file and thus has not yet been wired to the source adapter for an Airflow dynamic batch. A separate strict writer authorization boundary, verified idempotent new-batch COMMIT path, independent readback and Airflow sequencing are still needed. PostgreSQL sequences can advance despite rollback. **Do not enable COMMIT from the current CLI.** TASK005 remains on hold.
