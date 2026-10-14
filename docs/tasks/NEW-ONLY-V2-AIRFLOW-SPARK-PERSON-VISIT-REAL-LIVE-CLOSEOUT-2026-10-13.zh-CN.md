# TASK004 — NEW_ONLY v2 Airflow → Spark Person/Encounter → Parquet → Reconciliation 真实验收

> **CLOSED / REAL LIVE PASS**（2026-10-13 EDT / 2026-10-14 UTC）。Healthcare PR [#116](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/116) merged，Main merge SHA `5e71de1c7455dda3eff6f5c47c9f2d7bb998dda8`；Self-Runner PR [#96](https://github.com/JohnZhang-DataForge/Self-Runner/pull/96) merged，Runner Workflow merge SHA `612246d596bb01f80a3572dfacfb293987df677c`。[真实 Self-Runner Run 38505927396](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38505927396) 的 `regression` + `replay` 两个 Job 均 SUCCESS。**这不是 PostgreSQL Writer ROLLBACK 或 COMMIT；TASK004 IN PROGRESS，TASK005 ON HOLD。**

## 一、选择的唯一真实新批次

- Batch ID：`synthea-new-only-gh-38497355290`
- Manifest：`s3://health-landing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-14/batch_id=synthea-new-only-gh-38497355290/manifest.json`
- Immutable Manifest SHA256：`dfb5d30e83c6a9b35b3a723137a5f3ab67649ad94ef1801e2bae3ef42fe5fa80`
- 真实源：18 CSV（一个合法 header-only 辅助表），Patient=1、Encounter=812。S3 READY 发布过的字节、v1 两批 READY 和 Synthea Request **均没有重新生成、改写或发布**。
- Airflow DagRun ID：`newonly-v2-spark-38505927396`，DAG `landing_batch_discovery`，**手工**明确 `processing_only=true` + `new_only_processing_probe=true` 两把开关；只能对 Discovery 精确匹配 SHA 的 READY、Claim Guard `OBSERVED_ONLY`、`CLAIM_ENABLE=NO` 进行 Processing-only，定时 Scan 不触发 Spark。

## 二、真实 Spark 处理与后续 Writer 输入（请使用下面实际 URI，不能使用测试虚构 URI）

```text
Airflow scan READY v2 (true S3)
  -> evaluate_batch_claims (NO, OBSERVED_ONLY)
  -> authorize_processing_replay (manual double opt-in)
  -> processing_only_gate
  -> spark_patient     SUCCESS, 1 row, readback=PASS
  -> spark_encounter   SUCCESS, 812 rows, readback=PASS
  -> spark_reconcile   SUCCESS
  -> verify_spark_processing SUCCESS, handoff cdm_write_permitted=false
```

**真实 Person Processing Parquet：**

`s3a://health-processing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-14/batch_id=synthea-new-only-gh-38497355290/entity=patient/run_id=task004-person-20261014T032923Z-9/work/normalized/data/`

**真实 Encounter Processing Parquet：**

`s3a://health-processing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-14/batch_id=synthea-new-only-gh-38497355290/entity=encounter/run_id=task004-encounter-20261014T032923Z-8/work/normalized/data/`

Self-Runner 精确取实际 Airflow TaskInstance/XCom，实际日志：

- `LANDING_SPARK_REAL_DAGRUN_STATE=success`；
- 8/8 Task 实际 `success`（`scan_ready_manifests`、`evaluate_batch_claims`、`authorize_processing_replay`、`processing_only_gate`、`spark_patient`、`spark_encounter`、`spark_reconcile`、`verify_spark_processing`）；
- `REAL_NEW_ONLY_V2_SPARK_PERSON_ROWS=1`；
- `REAL_NEW_ONLY_V2_SPARK_VISIT_ROWS=812`；
- `REAL_NEW_ONLY_V2_SPARK_PARQUET_READBACK=PASS`；
- `REAL_NEW_ONLY_V2_SPARK_RECONCILIATION_XCOM=PASS`；
- `LANDING_SPARK_NO_OMOP_OR_CLAIM_MUTATION=PASS`。

这里 Parquet URI **确实来自真实执行中的 Spark state + Airflow XCom**，不是 Workflow 人工编造的输出；读取成功的元数据也经 Reconciliation 检查。注意现有 Spark `encounter` canonical 数量为 812，但 **cdm.visit_occurrence 尚未插入任何本轮行**。

## 三、生产保护及兼容

- v1 历史 `task004-airflow-*` 仍使用冻结的旧 TASK004 镜像 digest `8d55a150...`；它的选取逻辑 `SKIP_LEGACY_BATCH` 保留。
- 只有显示标记为 NEW_ONLY 手工探针时，Spark Controller 使用已通过 worker02 S3 Readback 的新镜像 `ghcr.io/johnzhang-dataforge/healthcare-landing-processing-v2@sha256:9af63252823bae0187b2517a013c147e2df8dfbe9a7c783ac31cd5dd7dbbb937`。
- `task004_cdm_preflight_contract.py` 额外拒绝新批次与不同 Batch/Source Version/日期的 Manifest 和 Parquet 混用，且始终返回 `cdm_write_permitted=false`。
- 单元测试首次因日期跨 Manifest/Parquet 的安全负例未拦截而失败；修复明确的 ingest_date drift 后，最终 Regression Run 38505771598 PASS，随后新的真实 Run 38505927396 完整 PASS。符合最多 3 次修复限制。
- PostgreSQL worker03 `BEGIN TRANSACTION READ ONLY` **Before**：`cdm.person=136`、`cdm.visit_occurrence=9391`、`etl.landing_batch_ledger=0`、新 v2 Batch `etl.task004_batch_ledger/stage/commit=0/0/0`。
- **After** 独立只读核验：`cdm.person=136`、`cdm.visit_occurrence=9391`、Claim=0，与 Before 完全相同。源 Writer 未连接执行任何 INSERT/COMMIT；`S3_READY_MUTATION=NO`、`POSTGRESQL_MUTATION=NO`。Processing Bucket 产生新 Parquet 是本轮明确授权的唯一数据写入。

## 四、NEXT 严格按依赖

1. 核实 Healthcare Writer 身份合同 PR [#109](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/109) 的冲突与 Main 合并状态；旧 `task004-airflow-*` 逻辑和 `BLOCKED:EXISTING_TARGET_DRIFT` 必须保留，新 `synthea-new-only-*` 需显式 `writer_identity_version=synthea-new-only-v1`，不是粗暴删正则。
2. 使用本报告的**真实两条 Parquet URI**和原 Manifest SHA，构建 immutable rollback-only Writer Plan；先在受限 S3 Reader + `cdm_reader` PostgreSQL READ ONLY 下进行 Person/Visit Source ID/Checksum/Concept/Parent Key 预审。不得直接 COMMIT。
3. **Person→Visit 正向联合事务 ROLLBACK**：现有旧 Writer 把每个 Entity 作为独立事务并要求 Person VERIFIED；不能误将两个独立 ROLLBACK 视为联合正向成功。需要设计事务编排，保证 Person→Visit FK 与 staged checkpoints 在事务中可见，最后整事务 ROLLBACK，独立读回 Person/Visit/ID Map/Batch Ledger/Stage/Commit/Claim 无变化，并保留 Drift 阻断负例。
4. 再做 Claim owner/lease fencing、失效补偿/并发/unknown commit、DB reconciliation、单批真实 COMMIT 和重放幂等，最终安全启用自动 Airflow Claim→Spark→Writer。通用 NEW_ONLY 新 Request Workflow 镜像 v1/v2 选择为单独尾项；UPDATE_ONLY/MIX_DATA/TASK005 仍暂停。

**多 Session 运行协调：** Portal A4 Spark Agent 仍按 `docs/platform-portal/SESSION-COORDINATION-POLICY.zh-CN.md` HOLD；Portal 不应因本轮 TASK004 Spark PASS 自行启用 OpenLineage Agent 或运行共享 Spark。
