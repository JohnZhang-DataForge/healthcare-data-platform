# TASK004 STEP04C — Person DB readiness: READ ONLY, not authorized to mutate

Evidence: [Self-Runner Run 38385679758](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38385679758), read-only SQL from pinned feature SHA `986996575b3a406b77cb6b07a8c1ebbf448cace6`.

| Gate | Observed |
|---|---|
| `transaction_read_only` | on |
| Historical `cdm.person` | 113 |
| Historical `etl.person_id_map` synthea | 113 |
| Historical `etl.person_stage` | 113 |
| Existing map target gaps / target unmapped | 0 / 0 |
| Mapping business-key duplicates / person_id duplicates | 0 / 0 |
| Person map business key unique index | true |
| Person target INSERT and map INSERT privileges for inspection role | true / true |
| Proposed `task004_batch_ledger`, `task004_batch_stage`, `task004_batch_commit` | all **absent** |
| Historical shared Person Stage has `batch_id` | **false** |
| Vocabulary concept table (`cdm.concept` or `vocab.concept`) | true |

Source scope from STEP04A: pinned batch `task004-airflow-task004-step03e-38324111846`; 23 Person rows with 0 existing stable mapping keys. These are *candidate* insert counts, not approval or a completed OMOP materialization.

**BLOCKED FOR LIVE WRITES:** necessary batch-scoped ledger/staging/commit schema has not been deployed; STEP04B is offline simulation only; the actual OMOP Person concept mapping, transaction and end-to-end independently verified loader are not yet approved or implemented.

This report gives a baseline to prepare a reviewed migration and a controlled Person loader. Never execute the historic full-table `sql/task002/person-upsert.sql` on the 04A input, and never reset any IDENTITY sequence. Actual DDL/Person INSERT requires separate explicit authorization including database `omop`, target tables, the pinned batch, and expected scope.

**Current result: STEP04C READINESS INVESTIGATION PASS / STEP04C PERSON LOAD NOT STARTED.**
