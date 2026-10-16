# TASK004 STEP04F — Dynamic Person/Visit Source + Row Adapters

**Acceptance: pure dynamic batch source/row adapters PASS. Database materialization not yet enabled.**

## Purpose and changes
This implements reusable dynamic-batch input preparation for the next true Airflow-to-PostgreSQL loader. The frozen STEP04C/D one-batch PostgreSQL writers remain unchanged and are not called.

- `airflow/dags/task004_cdm_dynamic_adapters.py`: validates the immutable `cdm_materialization_plan` context against original DAG planning rules; maps variable-length canonical Person/Visit rows to OMOP payloads; requires source/batch/date/version consistency; rejects duplicate keys, invalid Visit timestamps, unsupported codes and missing parent IDs; deterministic fingerprints; emits payloads without mutating the database. Race `other` retains source value and concept 0. Canonical timestamp-NTZ is UTC. Mapping policy mirrors accepted STEP04C/D.
- `airflow/dags/task004_cdm_dynamic_source.py`: injectable S3 source reader verifies immutable manifest SHA, refuses zero or multiple parquet data files, and passes decoded record arrays through the dynamic adapters. Requires a future runtime image to provide boto3/pyarrow and environment credentials; no network access during tests.
- `tests/task004/test_step04f_dynamic_row_adapters.py`: ten tests covering row transform, FK linkage, replay consistency, batch drift, counts, unknown concepts, timestamps and write authorization boundary.
- `tests/task004/test_step04f_dynamic_source.py`: four mock-S3 tests covering the approved manifest, tampering, missing/multiple parquet.

## Tests and proof
[Self-Runner 38402376742](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38402376742) **SUCCESS**, pinned code `43f7582667b3b8780da3b0e1732a60154a0f5541`: 10 dynamic row tests + 4 manifest/source tests, syntax validation. No database access or Kubernetes mutation in this run. The prior row-only [38402212439](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38402212439) also PASS.

## Remaining before marking STEP04F complete
1. Implement **dynamic transactional PostgreSQL loaders**, using `batch_id` + manifest/plan digest and dynamic source counts; safe Person→Visit sequencing, distributed locking, batch ledger/stage/commit and missing/changed source conflict behavior. Do **not** use frozen historical `113/5799` baselines and `23/3592` assumptions in new runs.
2. Verify runtime image dependencies (boto3, pyarrow, PostgreSQL client or connection library), least-privilege database identity, immutable image digest, and network access from `dw-spark`.
3. Add CDM person/visit database tasks and joint readback after `cdm_materialization_plan`, validate on actual Airflow scheduler, and run source-pinned real DAG trials.
4. New-batch database writes are **not authorized** by the STEP04C/D fixed-batch approvals. Obtain explicit scoped authorization before any new batch COMMIT.
5. STEP04G full-DAG replay, recoverability and concurrency acceptance remains pending. TASK005 on hold.

**This is one verified dynamic-source implementation loop, not a completed end-to-end dynamic loader.**
