# TASK004 STEP04F — Dedicated CDM Writer / Real PostgreSQL ROLLBACK

**Acceptance: PASS. This step creates a persistent scoped writer identity but does not commit any OMOP Person/Visit business rows.**

## Successful evidence
- [Self-Runner Run 38427294423](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38427294423) **SUCCESS**. This complete loop used pinned healthcare code SHA `57e7d5322968429e57b7e6e283bba9ba9ba16a52` and the current independent Kubernetes runtime.
- PostgreSQL `cdm_writer` was provisioned/rotated without superuser/database creation/role creation rights. Its generated credential is stored as a Kubernetes Secret `dw-spark/task004-cdm-writer-db`; it is not in Git.
- Granted CONNECT to `omop`, USAGE to `cdm`/`etl` schemas, and SELECT/INSERT only to `cdm.person`, `cdm.visit_occurrence`, `etl.person_id_map`, `etl.visit_occurrence_id_map`, `etl.task004_batch_ledger`, `etl.task004_batch_stage`, `etl.task004_batch_commit`. SELECT-only `cdm.concept`. Scoped USAGE to exactly `etl.person_id_map_person_id_seq` and `etl.visit_occurrence_id_map_visit_occurrence_id_seq`.
- Verified no superuser, UPDATE on `cdm.person` or DELETE on `cdm.visit_occurrence` privileges. No broad schema-level default grants.
- Generated synthetic dynamic Person SQL with the existing validated PostgreSQL builder; rendered SQL explicitly ends `ROLLBACK;` and contains no `COMMIT;`. Executed it in a standalone ephemeral Kubernetes `postgres:16-alpine` Job using **cdm_writer** Secret over the Postgres Service, exercising ledger, stage, ID mapping, OMOP insert, checkpoint and ROLLBACK in the same transaction.
- Independent new session readback: Person=136, Visit=9391, zero synthetic Ledger/Stage/Commit/Person Map rows. Markers `CDM_WRITER_REAL_POSTGRES_ROLLBACK=PASS`, `CDM_WRITER_ROLLBACK_NO_PERSISTENCE=PASS`.
- Initial run 38427170949 completed the database ROLLBACK but did not emit the expected log marker because `psql -q` suppressed confirmations; a one-line fix and full rerun passed in 38427294423.

## Boundaries
- Persistent role/GRANT/Secret changes **were made** as the requested provisioning operation. No persistent OMOP business rows were inserted/updated/deleted; sequence advancement under ROLLBACK is possible in PostgreSQL and sequence values were not compared.
- Standalone PostgreSQL client Job **not yet our CDM Runtime image**. The current CDM Runtime still exposes read-only PostgreSQL operations and does not expose a writer/COMMIT executor.
- Live new-batch COMMIT and Airflow Person→Visit writer orchestration have **not** been authorized or verified; design a separate explicit per-batch authorization gate, transactional identity and replay semantics first.
- STEP04G full Airflow replay and TASK005 remain blocked.
