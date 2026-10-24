# Portal P2/P4 — NEW_ONLY Real Business Run and OpenLineage / Dataset Evidence (2026-10-24)

> **Independent result**: real NEW_ONLY Airflow DagRun **SUCCESS**, Person/Visit/Reconcile **SUCCESS**, 3 new KPO Pods pinned to expected GHCR Digest; the Writer gate explicitly HOLD/SKIP. Marquez actually received 10 completed Airflow DAG/Task Jobs; Person and Visit each have an actual **COMPLETED Spark child Run with 1 S3 Landing Input + 1 S3 Processing Output DatasetVersion**. Reconcile reads BOTH real Processing Parquet inputs, but its **two child Runs remain RUNNING despite Spark application COMPLETED**. Parent/child cross-Airflow/Spark facets and Writer COMMIT remain open, and the first omnibus workflow conclusion was **FAILURE due to its over-strict top-level Job Dataset check**. Preserve this nuance.

## 1. Exact immutable inputs and operations

- Approved exact synthetic READY batch: `synthea-new-only-gh-39625216978`.
- Immutable Manifest: `s3://health-landing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-21/batch_id=synthea-new-only-gh-39625216978/manifest.json`.
- Manifest SHA256: `84562e5d0054b374f1c4d390f5c6604fc97a9aa5bd263b1df143651fb3e51fee`.
- Independent pre-run read-only inventory [Self-Runner #40124907392](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40124907392) SUCCESS: SeaweedFS READY=35, quarantined invalid=1, this selected READY batch had **0 Claim rows + 0 Writer ledger rows**, queried with `landing_claim_worker` and PostgreSQL `transaction_read_only=on`.
- P4 one child image [GHCR Release #40123946926](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/40123946926) new `:latest` Digest: `sha256:f735f6088efad7f0f0b6f2a4d2540ecfa5195925cda719cfc0c17c5e78a21f37`. Previous `:latest` backup: `pre-latest-run40123946926-a1` Digest `sha256:93adcaeefc5c29f87e3fca212e20faaebbaad99b23c7a8fe0fb5ebe5636331ba`.
- Real business DagRun `new_only_omop_consumer`, Run ID `portal-p4-spark-only-40125211881`, manual `consumer_readonly=true`, `spark_processing=true`, exact Batch/Manifest, deliberately **no `writer_commit`**.
- [Real execution #40125211881](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40125211881) final GitHub Workflow **FAILURE** at its own *Marquez acceptance query*, but underlying `P4_REAL_NEWONLY_DAGRUN_STATE=success` and `P4_BUSINESS_SPARK_ONLY_DAGRUN=PASS`. Never replace recorded Workflow FAILURE with fake SUCCESS.

## 2. Actual business Task/Container/App outcome

- `scan_ready_manifests`, `select_verified_new_only_batch`, `inspect_claim_readonly`, `route_new_only_status`, `spark_patient`, `spark_encounter`, `spark_reconcile`, `prepare_writer_handoff`, `route_writer_authorization`, `writer_awaits_live_preflight`: **all Airflow TaskInstance `success`**.
- `execute_new_only_writer` and `writer_committed_verified`: **`skipped`**, not executed. `already_completed_no_replay` and `unclaimed_batch_hold` skipped as expected. Do **not** claim OMOP COMMIT or PG17 new rows from Spark-only run.
- [Independent in-flight readback #40125494267](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40125494267) saw real `spark_patient` and `spark_encounter` Control Pods running, both Driver SparkApplications `RUNNING`; [second readback #40125675091](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40125675091) observed `spark_patient`, `spark_encounter`, `spark_reconcile` `success`, with Writer authorization still routing.
- Actual three NEW_ONLY KPO control Pods `spark-patient-ct7zbx5u`, `spark-encounter-zx1wkv68`, `spark-reconcile-ps5hanbr` all had **`imageID=ghcr.io/johnzhang-dataforge/healthcare-data-platform-local-dp-landing-processing-v2@sha256:f735f6088efad7f0f0b6f2a4d2540ecfa5195925cda719cfc0c17c5e78a21f37`**. Proves actual new Pods used new `:latest`.

## 3. Airflow Provider emitted true business Runs

- [GET-only Marquez Airflow readback #40126168286](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40126168286) **SUCCESS**: `healthcare-platform-airflow` contained **10 NEW_ONLY business DAG/Task Jobs with a new COMPLETED Run** after the 2026-10-24 19:25 UTC cutoff. Among them DAG Job `new_only_omop_consumer`, `scan_ready_manifests`, `select_verified_new_only_batch`, `inspect_claim_readonly`, `route_new_only_status`, `spark_patient`, `spark_encounter`, `spark_reconcile`, `prepare_writer_handoff` and `route_writer_authorization`.
- Thus P2's actual business opt-in is **proven as a real DAG+Task Job/Run event path**, not merely A3 two-task Probe. Airflow TaskInstance skip/branch gates remain authoritative; OpenLineage does not authorize writer and does not imply Airflow parent facets for Spark.

## 4. Spark application vs Spark child Job hierarchy and real S3A edges

The initial [real execution #40125211881](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40125211881) checked dataset versions on the **top-level Spark application Jobs**, finding 0, and failed. Follow-up independent exact Run audits [#40125843864](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40125843864), [#40125924152](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40125924152) **SUCCESS** show actual dataset edges live on **action-level child Jobs**. App-level `COMPLETED` with 0 versions is not evidence of missing physical Dataset lineage.

| Real job (namespace `healthcare-platform-spark-business`) | Real Run ID | Run state | Input DatasetVersions | Output DatasetVersions |
| --- | --- | --- | --- | --- |
| `task004_person_20261024t192638z_9.adaptive_spark_plan.normalized_data` | `01a16f63-7aa4-7a60-9ad9-46d8c4064617` | COMPLETED | 1 | 1 |
| `task004_encounter_20261024t192638z_9.adaptive_spark_plan.normalized_data` | `01a16f63-69a5-7c78-85f5-9a3613d02693` | COMPLETED | 1 | 1 |
| `task004_reconcile_20261024t192952z_7` | `01a16f64-e2d2-7af3-9294-8141bb7e45d4` | COMPLETED | 0 | 0 |
| `task004_reconcile_20261024t192952z_7.map_partitions_parallel_collection` | `01a16f65-3707-7518-8c59-795243902654` | RUNNING | 1 (Encounter) | 0 |
| Same Reconcile child Job | `01a16f65-174d-71f2-920e-bcb6245fda64` | RUNNING | 1 (Patient) | 0 |

- Person read true `s3://health-landing/.../payload/csv/patients.csv`, wrote `s3://health-processing/.../entity=patient/run_id=task004-person-20261024T192638Z-9/work/normalized/data`.
- Visit read true `s3://health-landing/.../payload/csv/encounters.csv`, wrote `s3://health-processing/.../entity=encounter/run_id=task004-encounter-20261024T192638Z-9/work/normalized/data`.
- Reconcile child inputs point to **exactly those same two real Processing Dataset versions**: Patient `a911dd93-79d9-30ee-a0ac-c7d3c39e39b1`, Encounter `5a791afe-a142-3977-9dcb-8febdcdd32d2`. [GET-only detailed audit #40125995864](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40125995864) confirms each input edge; no Reconcile output is expected, because actual reconcile.py only reads.
- **Pending anomaly**: Reconcile's two action-level child Runs remain `RUNNING` despite Kubernetes SparkApplication and Airflow Task `success` and application-level `COMPLETED`; do not silently convert RUNNING to COMPLETED. Their `parent` and `spark_jobDetails` facets were present. This may require independent listener/provider lifecycle investigation, not guessed root-cause nor synthetic COMPLETE posts.

## 5. Verified boundaries / follow-up

**P2 3.3**: TRUE business Airflow Job/Run SUCCESS after live execution. **P4 5.3**: Person & Visit true read/write S3A datasets SUCCESS; Reconcile two real reads observed with anomalous child Run terminal state ⇒ remain **partially verified / NOT FULL PASS**. **P4 5.4 and P5 6.1–6.4**: no Writer COMMIT/PG17 independent readback or same-batch SKIP yet. No fake OpenLineage events, no automatic DB reset.

Follow-up: (1) Reconcile `RUNNING` child Run lifecycle anomaly, with exact Job/Run IDs above; (2) Airflow-to-Spark cross-system parent mapping (not proven by presence of a `parent` facet alone); (3) fresh authorized Writer COMMIT + PG17 Readback + same-batch SKIP, maintaining full original Fencing checks; (4) a correct verifier must inspect **all child Spark Jobs** and distinguish application COMMITTED from action-level Dataset facets, rather than prematurely validating DatasetVersion on top-level App Job.

**验收器修正规则（下一次执行前）**：必须按实际 Spark 应用名前缀逐个枚举 Marquez child Jobs、读取各 Job 的真实 Run 与 DatasetVersion，不能仅检查应用顶层 Job 的 Input/Output=0；Reconcile 必须分别检查 Patient/Encounter 两个实际 DatasetVersion 以及 child Run 的终态。仅完成三项作业不等于经过 Writer COMMIT。该规则需要先做离线回归与受控只读读回，不能修改 Marquez 元数据凑齐结果。
