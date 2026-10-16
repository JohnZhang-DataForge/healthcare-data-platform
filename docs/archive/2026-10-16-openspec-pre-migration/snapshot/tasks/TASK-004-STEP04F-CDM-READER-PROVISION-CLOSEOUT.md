# TASK004 STEP04F — Dedicated PostgreSQL CDM Reader Provisioning

**Status: dedicated reader created and role privileges verified in PostgreSQL; standalone runtime-to-service TCP login NOT yet verified.**

## Verified execution

- [Self-Runner Run 38418708979](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38418708979) — SUCCESS, existing PostgreSQL Pod `dw-postgre-database-0`.
- Created/rotated `cdm_reader` as a PostgreSQL LOGIN role without superuser, database creation or role creation rights, and stored its generated password only as Kubernetes Secret `dw-spark/task004-cdm-reader-db`.
- Granted CONNECT on database `omop`, USAGE on schemas `cdm`/`etl`, and SELECT on `cdm.person`, `cdm.visit_occurrence`, `etl.person_id_map`, `etl.visit_occurrence_id_map`, `etl.task004_batch_ledger`, `etl.task004_batch_stage`, `etl.task004_batch_commit`.
- Independently verified `READER_SUPERUSER=false`, Person/Visit/Ledger SELECT=true, Person INSERT=false, Person UPDATE=false, Visit DELETE=false.
- Did **not** insert/update/delete any OMOP business data, connect with `omop_admin` from the CDM Runtime, trigger Airflow, or enable writer credentials.
- PostgreSQL role creation/rotation, GRANT statements, and new Kubernetes Secret are intentional **persistent administrative changes**, distinct from business data mutations.

## Remaining verification / constraints

- A proposed in-cluster independent PostgreSQL client Job was prevented by the GitHub tool's safety check. **No successful CDM Runtime/standalone-client TCP login has been demonstrated yet.** Do not mark this complete.
- The existing CDM image lacks a PostgreSQL client; next checkpoint needs a read-only client image/entrypoint, Secret-scoped Job and live PostgreSQL Service authentication, while ensuring credentials are never logged.
- This reader role is deliberately not a writer; future dynamic CDM COMMIT requires separate constrained principal and authorization. TASK005 ON HOLD.
