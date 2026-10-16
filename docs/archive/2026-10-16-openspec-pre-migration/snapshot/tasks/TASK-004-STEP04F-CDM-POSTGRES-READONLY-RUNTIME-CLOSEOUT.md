# TASK004 STEP04F — CDM Runtime PostgreSQL Read-Only Client Verification

**Result: PASS. Real digest-pinned CDM Runtime → PostgreSQL Service login verified in Kubernetes. No OMOP data mutation, no Airflow DAG trigger.**

## Implementation
- Added `airflow/dags/task004_cdm_postgres_readonly.py` using pinned `psycopg[binary]==3.2.10`.
- CLI `apps/task004/cdm_runtime_cli.py` now supports `--validate-postgres` alongside existing `--validate-source`; original immutable plan digest is checked before any network operation.
- PG identity is restricted to `PGUSER=cdm_reader`, credentials from a Kubernetes Secret; connection forces `default_transaction_read_only=on`, explicit `read_only=True`, query timeout and parameterized ledger lookup. No DML methods or COMMIT executor exposed.
- No change to existing dynamic SQL writer's default ROLLBACK behavior. Separate writer authorization remains pending.

## Verified workflows
- Healthcare [Publish 38425423103](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/38425423103): Python reader+packaging tests, image build, GHCR push SUCCESS.
- **Immutable image:** `ghcr.io/johnzhang-dataforge/healthcare-data-platform-task004-cdm-runtime@sha256:75e52c1d0460a5eebb03149383f1c2771959dd31ff2a226fc4475943945a88d4`.
- Self-Runner [Kubernetes live Job 38425638192](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38425638192): SUCCESS, `dw-spark` on worker02, published CDM image, existing `task004-cdm-reader-db` Secret, PostgreSQL Service `dw-postgre.dw-postgre.svc.cluster.local:5432`.
- Read-only checks succeeded: Person=136, Visit=9391, pinned historical batch ledger=1, identity `cdm_reader`, no `cdm.person INSERT` privilege. `CDM_RUNTIME_PG_READER_K8S=PASS`, `POSTGRESQL_MUTATION=NO`.
- Ephemeral Job and ConfigMap cleanup requested by CI; no Airflow trigger, no new Synthea generation, no new database role or grant, and no OMOP insert/update/delete.

## Next bounded milestone
Design **separate least-privilege `cdm_writer` execution path and strict Airflow-run-scoped authorization**; dynamic Person→Visit COMMIT and full DAG replay are still not implemented or verified. STEP04G and TASK005 remain pending.
