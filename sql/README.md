# SQL — PostgreSQL, OMOP schema and integrity checks

[← Repository overview](../README.md) · [OMOP CODE](../documents/components/omop/CODE.md) · [Database acceptance](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md)

This directory contains the versioned SQL used for **landing batch claim/fencing**, the historical Person/Visit materialization foundation, batch ledger schemas, and independent read-only checks.

| Folder | Contents |
| --- | --- |
| [`landing_claim/`](landing_claim/) | Batch ledger DDL, Writer fence deployment and rollback proof |
| [`task002/`](task002/) | Person upsert foundation |
| [`task003/`](task003/) | Visit ID mapping foundation and baseline |
| [`task004/`](task004/) | Batch ledger/stage/checkpoint schema and Person/Visit validation/mapping checks |

## Operational distinction

- **Read-only inventory:** `task004/step04a-readonly-*.sql` and schema/readiness queries inspect actual structure and data.
- **Mutating DDL/DML:** `landing_claim/create_landing_batch_ledger.sql`, `landing_claim/writer_fence_v1_deploy.sql` and `task004/step04c-batch-schema-v1-authorized.sql` require explicit authorization and careful schema/version review.
- **Business Writer SQL:** the accepted atomic Person+Visit commit is dynamically rendered by Python in [`apps/omop_writer/`](../apps/omop_writer/) together with [`airflow/dags/task004_cdm_dynamic_pg_writer.py`](../airflow/dags/task004_cdm_dynamic_pg_writer.py); it is not simply a static `.sql` file to execute directly.

Existing database objects include `cdm.person`, `cdm.visit_occurrence`, `etl.task004_batch_ledger`, `etl.task004_batch_stage`, `etl.task004_batch_commit`, the Claim ledger and `task004_writer_fence`. **Those historical identifiers are live compatibility contracts**; do not rename tables, lock keys, functions or contract versions as a cosmetic cleanup.

Read-only verification should be done in an explicitly read-only PostgreSQL transaction, with no credentials embedded in scripts, and with independent state checks before any attempted recovery. See [final acceptance](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md) for actual persisted counts and successful idempotent replay.
