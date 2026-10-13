# TASK004 STEP04C — Person CDM Commit + Replay Acceptance (2026-10-13)

**PERSON: LIVE DATABASE VERIFIED / COMPLETE for the pinned batch. VISIT: NOT LOADED.**

## Scope and authorization

User explicitly authorized permanent TASK004 batch schema and **up to 23 Person ID mappings + 23 CDM Person rows** for batch `task004-airflow-task004-step03e-38324111846`, same-batch replay, historical preservation, and **no Visit inserts or updates**. The three batch-schema tables were already deployed in [38388739874](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38388739874).

This acceptance is for the **fixed 2026-10-12 source batch only**. It does not establish a general multi-batch loader or complete DAG idempotency.

## Verified source and policy

- Immutable Manifest SHA: `ecc7cf3b75240e530f2cc96635b25e4eaf0794403e1b04d50d2248cd3aaa5cb1`, verified by actual S3 readback.
- Real Airflow XCom Processing Person input at `s3a://health-processing/.../entity=patient/run_id=task004-person-20261012T235028Z-8/work/normalized/data/`; 23 unique records.
- Demographics (aggregates only): gender F=14/M=9; race asian=2, black=10, white=10, **other=1**; ethnicity hispanic=2/nonhispanic=21.
- OMOP demographic concept mapping derives from existing `spark/common/omop.py`. Explicit `other` race mapping uses **OMOP concept ID 0 = no matching concept**, preserving source value `other` instead of guessing an arbitrary standard concept ID.
- The loader blocks invalid, missing or unknown demographic source codes, an unexpected batch/manifest, missing vocabulary concepts, batch stage-content conflicts, or a conflicting mapped existing CDM row.

## Real Runner evidence

[Self-Runner Run 38390404434](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38390404434): **SUCCESS**; exact Healthcare SHA `ba1810c5b68d5147c8afd7d8a32caa909ea645ba`, unit tests and real ARC Kubernetes cluster. Execution in order:

1. Source/SQL validation with actual immutable Manifest + Person Parquet.
2. Full PostgreSQL Person transaction in mandatory **ROLLBACK** (precommit rehearsal; no persistent changes).
3. Same bounded transaction in **COMMIT** mode; zero SQL changes outside user-authorized entities.
4. Independent read-only PostgreSQL session for map/CDM/ledger/stage/Visit counts.
5. Same source batch **COMMIT replay**, independently verifying unchanged totals.

Earlier failures were fail-closed *before any database mutation*, diagnosed [38389930492](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38389930492) and [38390091375](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38390091375): source `race_code=other` had no approved mapping. Correct mapping and negative tests added before write.

## Independent post-COMMIT readback

| Metric | Baseline | Actual after commit | Actual after same-batch replay |
|---|---:|---:|---:|
| `cdm.person` | 113 | **136** | **136** |
| Synthea `etl.person_id_map` | 113 | **136** | **136** |
| `cdm.visit_occurrence` | 5799 | **5799** | **5799** |
| Synthea Visit Mapping | 5799 | **5799** | Not modified |
| Task004 Person stage scoped to this batch | 0 | **23** | **23** |
| Task004 Person commit checkpoint `VERIFIED` | 0 | **1** | Unchanged |
| Batch Person map→target join count | 0 | **23** | Verified by repeated transactional row-value equality checks |

**Inference with narrow support:** 23 new Person mappings and 23 CDM Person rows were committed (113→136). Replay added zero additional map and CDM rows, and the transactional comparison checks required exact row-value equality for all 23 mapped people. Existing historic rows were never selected for update in generated SQL. The independent readback does not include a pre/post cryptographic snapshot of all original historical rows; future regression hardening may add one.

## Key artifacts and boundaries

- `apps/task004/step04c_person_sql_builder.py`: deterministic fixed-source 23-row OMOP mapper with batch-scoped stage, stable ID map, conflict/no-overwrite checks, transactional Person insert.
- `apps/task004/step04c_person_runner.py`: S3 readback + Kubernetes PostgreSQL runner, no source IDs/secrets logged.
- `tests/task004/test_step04c_person_loader.py`: source lineage/demographic policy/SQL safety tests.
- Self-Runner `.github/workflows/task004-step04c-person-load.yml`: complete read-only/dryrun/COMMIT/readback/replay evidence.

## Remaining TASK004 work

- STEP04D Visit **3,592** source encounters → OMOP `cdm.visit_occurrence`, stable Visit IDs and person FK, with independent readback/replay.
- STEP04E–H: final batch DB reconciliation, DAG integration, retry/unknown-commit and full end-to-end replay/recovery verification. The existing frozen STEP03E DAG does not yet automatically orchestrate the new Person database commit.
- STEP04C Person baseline is verified for this one fixed batch, not generalized/concurrent-production acceptance. **TASK005 remains ON HOLD.**
