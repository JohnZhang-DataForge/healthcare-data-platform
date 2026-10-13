# TASK004 STEP04F — PostgreSQL Readonly Boundary Inventory (2026-10-13)

**Status: REAL DATABASE READ-ONLY QUERY PASS; DEDICATED CDM READ-ONLY LOGIN MISSING; CDM RUNTIME NETWORK LOGIN NOT YET VERIFIED.**

## Evidence
- [Self-Runner Run 38412213438](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38412213438): SUCCESS. The ARC Runner used `kubectl exec` against the existing PostgreSQL Pod `dw-postgre/dw-postgre-database-0` and executed the inventory inside a `BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY` transaction, with statement timeout and ON_ERROR_STOP.
- `TRANSACTION_READ_ONLY=on`, Person total=136, Visit total=9391, Person/Visit synthetic Mapping totals=136/9391, existing batch ledger checkpoint present (1).
- PostgreSQL login roles observed: `omop_admin` (superuser), `airflow_user` (not superuser).
- Existing `airflow_user` has **no SELECT privilege** on `cdm.person`, `cdm.visit_occurrence`, or `etl.task004_batch_ledger`. It also lacks INSERT on `cdm.person`. It is **not usable as CDM read/write principal**, and should not be repurposed.
- `omop_admin` was used only inside the PostgreSQL Pod for this read-only inventory. It is privileged and **must not be wired into the CDM Runtime/Airflow** for production-style operations.
- No roles were created, no GRANT/REVOKE or Kubernetes Secret changes performed. This run does **not** demonstrate TCP/PG authentication from the separate CDM Runtime image and does not claim to do so.

## Gate for next step
1. Define a dedicated least-privilege PostgreSQL login for CDM readback, granting only CONNECT, USAGE and needed SELECT on the necessary tables/schemas. This is a **database mutation** and should be performed only after scoped authorization.
2. Store credentials securely in Kubernetes Secret with namespace/Pod access restrictions; CDM image currently contains boto3/pyarrow but no PostgreSQL connection client or privileged CLI command. Build a separate read-only connection subcommand and re-publish a versioned digest.
3. Execute a real in-cluster CDM Runtime Pod → PostgreSQL Service TCP login + `READ ONLY` SELECT test using the new read-only principal.
4. Only after that, separately design a dedicated **writer** with additive privileges and explicit authorization; do not reuse `omop_admin` or Airflow metadata `airflow_user`.
5. STEP04F Airflow dynamic load tasks and STEP04G DAG replay remain pending; TASK005 ON HOLD.

**Boundary validated and blocking prerequisite identified; the end-to-end CDM Runtime database connection is not yet complete.**
