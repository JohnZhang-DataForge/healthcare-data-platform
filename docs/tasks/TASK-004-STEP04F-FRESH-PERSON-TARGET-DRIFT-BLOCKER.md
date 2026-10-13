# TASK004 STEP04F — Fresh Synthea / Person S3→PostgreSQL ROLLBACK Test: Target Drift Blocker

> **2026-10-13 只读后续结论（优先级高于本文下面的原始排查建议）：** [Person Source ID Reconciliation Closeout](TASK-004-STEP04F-PERSON-SOURCE-ID-READONLY-RECONCILIATION-CLOSEOUT.md) 已记录实际 [Self-Runner Run 38435544614](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38435544614) **SUCCESS**：23 Source ID 已有映射，其中 0 identical、23 different、0 new、0 dangling；失败批次 Ledger/Stage/Commit=0/0/0、CDM Person/Visit=136/9391。**Source ID 重合及 OMOP payload drift 已证实**；相同 seed 与变更 reference date 是否为根因仍需独立确认。Person Writer 继续 BLOCKED；不得自动重跑或 COMMIT。


**Fresh Airflow source / Processing = PASS; live dynamic Person writer ROLLBACK success = NOT YET.**

## Fresh Source Verified
- [Self-Runner 38431103586](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38431103586): SUCCESS. New `task004-airflow-task004-step03e-38431103586` batch, ingest date `2026-10-13`, full Airflow DAG: generate_publish → Person/Visit Spark Processing → reconciliation.
- Fresh Processing: **23 Person, 3,588 Visit**; separate from historical batch `task004-airflow-task004-step03e-38324111846` (23 Person / 3592 Visit).
- No Airflow database COMMIT tasks were executed. The pipeline uses the existing deterministic Synthea default seeds `20261012` for both seed and clinician_seed despite the new ingest date.

## Writer Acceptance Attempt
- The writer CI uses the newly published CDM Runtime `ghcr.io/johnzhang-dataforge/healthcare-data-platform-task004-cdm-runtime@sha256:94979587aeee2f2ea13e2c27ffc5a8850b97381f3f126c72201fe2b2b3086f5e`, existing `cdm_writer` Secret, fresh S3 Manifest, and uniquely discovered Person/Visit Processing Parquet paths. No `rows.json` was injected.
- First run [38431577013](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38431577013): its initial attempt started before source DAG success (fail-closed); after source success its rerun could not find a Processing URI in the successful Airflow task log (the URI exists in the deleted KPO's state/XCom, but is not one of the terminal log markers).
- [38432410844](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38432410844): real in-cluster S3 prefix discovery succeeded; runner parsing was blocked by a non-JSON preamble in Kubernetes/Airflow output.
- [38432556422](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38432556422): independent Airflow lineage extraction and real S3 Processing discovery succeeded; actual CDM Runtime passed S3 adapter/OMOP mapping and reached the PostgreSQL writer. Its Job terminated with **`psycopg.errors.RaiseException: BLOCKED:EXISTING_TARGET_DRIFT`**, the PostgreSQL guard verifying that an existing mapped Person target is identical to the proposed Person payload. CI run was marked failure, correctly. No `CDM_S3_WRITER_ROLLBACK=PASS` result was emitted; independent post-run baseline SELECT step was skipped due to CI fail-fast.
- This is **not** the earlier historical Ledger version incompatibility. A new batch ledger was created only inside the transaction, but the writer did not reach its final ROLLBACK SQL because the guard raised. PostgreSQL aborts failed transactions and the connection closes; no COMMIT execution path was exposed. However, an independent DB readback was not completed by that failed workflow, so do not claim independent zero-persistence verification for this run.
- Several development attempts failed for distinct reasons; additional reruns are intentionally stopped per the existing no-more-than-three-failed-loops workflow rule.

## Root-Cause Hypothesis and Safe Next Step
The Airflow pipeline retained fixed Synthea seeds `20261012` while the reference/ingest date changed to 2026-10-13. Repeated deterministic source Person identifiers may overlap historic `etl.person_id_map` keys while the new transformed records differ. This is a **plausible hypothesis**, not yet proven per-key by a reconciliation report; do not bypass `EXISTING_TARGET_DRIFT`, rewrite historical mappings, or disable the guard.

Next bounded task: run an **independent SELECT-only reconciliation** comparing the new Person source IDs + fingerprints against existing `etl.person_id_map` and `cdm.person` (report aggregate counts/digests only; no patient identifiers); verify fresh-batch ledger/stage/commit zero after the failed transaction. Then decide explicit semantics: new independent Synthea seeds if the intent is genuinely new Persons, or an audited correction/versioning policy for repeated source IDs. Only after this can the S3→PostgreSQL real Person ROLLBACK acceptance be rerun; permanent COMMIT/Airflow CDM writing remains disabled. TASK005 ON HOLD.
