# TASK004 STEP04C — Batch Schema Deployment (authorized, verified)

**Database schema deployment: COMPLETE / PASS. Person data loading: NOT STARTED.**

## Authorization & execution
- User expressly authorized three TASK004 support tables in PostgreSQL `omop`, followed by at most 23 Person mappings/rows for fixed source batch. No Visit loading or historic changes authorized.
- SQL source: `sql/task004/step04c-batch-schema-v1-authorized.sql`, fixed feature SHA `b4cecbfa46a335af5484a75267ce2944cf47909a`.
- Actual ARC workflow: [Self-Runner 38388739874](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38388739874) **SUCCESS**, including independent post-commit read-only check.
- Earlier full DDL executed in ROLLBACK [38387006783](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38387006783) **SUCCESS**.

## Post-COMMIT independent PostgreSQL readback
| Database `omop` | Verified result |
|---|---|
| `etl.task004_batch_ledger` | PRESENT |
| `etl.task004_batch_stage` | PRESENT |
| `etl.task004_batch_commit` | PRESENT |
| Historical `cdm.person` | **113**, unchanged |
| Historical `cdm.visit_occurrence` | **5799**, unchanged |
| Existing Synthea Person map | **113**, unchanged |
| Existing Synthea Visit map | **5799**, unchanged |

Migration is additive. No Person/Visit CDM records or ID mappings were inserted by this deployment.

## Next authorized bounded work
1. Build and independently validate canonical 18-column Patient -> actual OMOP 18-column Person mapper; verify demographic OMOP vocabulary IDs and NULL/required fields. Explicitly exclude runtime metadata from stable fingerprints.
2. Implement batch-scoped staging + stable Person ID allocation + transactionally commit to `cdm.person` with conflict/no-update/historical guards. Do **not** use old full-table `sql/task002/person-upsert.sql`.
3. Fixed batch `task004-airflow-task004-step03e-38324111846`, up to 23 Person rows; dry-run precommit plan, apply within authorized bounds, independent target readback; then same-batch replay NO-OP. If preflight fails, stop without partial writes.
4. No Visit DB writes. Do not claim TASK004 complete until actual Visit, orchestration and database replay/recovery acceptance.

**STEP04C SCHEMA=PASS; STEP04C PERSON MATERIALIZATION=PENDING.**
