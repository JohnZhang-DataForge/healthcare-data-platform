# OMOP Writer — 真实 S3 Parquet → PostgreSQL ROLLBACK Gate（2026-10-13）

> **事实分级：REAL S3 SOURCE=PASS / REAL PG WRITER TARGET-DRIFT REJECTION=PASS / DB ZERO-PERSISTENCE=PASS；REAL NEW-BATCH SUCCESSFUL ROLLBACK=NOT YET。** 本次真正使用 SeaweedFS 上不可变 S3 Manifest 和 Spark 输出的 Person/Visit Parquet，并将真实 Person 变换数据提交到既有 **ROLLBACK-only** `cdm_writer` PostgreSQL Executor；数据库正确拒绝了重复 Patient ID 且 Birth Date 内容变更的批次，Writer Job 以预期的 **`BLOCKED:EXISTING_TARGET_DRIFT`** 结束，独立回读无持久业务变更。**Self-Runner Workflow SUCCESS 是“预期负例拦截”通过，不是 Writer Job 成功完成 ROLLBACK SQL，也绝不能声称动态 COMMIT 已完成。**

## 1. 输入是实际已经发布的 S3 数据，不是测试行

使用已冻结的 2026-10-13 批次 `task004-airflow-task004-step03e-38431103586`：

- Manifest: `s3://health-landing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-13/batch_id=task004-airflow-task004-step03e-38431103586/manifest.json`
- Verified raw Manifest SHA256：`e6dc34dd45357a43561f5e970185c5e44da4368647440a78363f43b1a762bc8a`
- Person Processing: `s3a://health-processing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-13/batch_id=task004-airflow-task004-step03e-38431103586/entity=patient/run_id=task004-person-20261013T163151Z-7/work/normalized/data/`
- Visit Processing: `s3a://health-processing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-13/batch_id=task004-airflow-task004-step03e-38431103586/entity=encounter/run_id=task004-encounter-20261013T163151Z-8/work/normalized/data/`
- 本次真正读到的 **Person=23，Visit=3588**，两个 Parquet 都由固定 CDM Runtime 的严格 `task004_cdm_dynamic_source.read()` + row adapters 验证。
- 仅用于对照的历史已入库批次 `task004-airflow-task004-step03e-38324111846` 仍有 Person/Visit 两轮 Processing 输出。真实 inventory 里这些前缀都有各自明确的 run_id，禁止用模糊的“latest” 随意绑定 Writer。

真实 S3 Processing URI 只读定位的独立证据：[Self-Runner Run 38479261229](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38479261229) **SUCCESS**，`OMOP_S3_PROCESSING_READONLY_INVENTORY=PASS`，`DATABASE_MUTATION=NO`。只打印批次、对象位置、Manifest SHA 和 Parquet 对象/前缀数量，不打印患者身份或明细。

## 2. 代码与已有组件的真实复用

- `apps/omop_writer/build_s3_rollback_plan.py`：新、可复用的**功能命名**工具，显式指定一个 `batch_id` + Manifest SHA/URI + Person/Visit 具体 S3 Processing URI + 行数，复用经过验证的 `task004_cdm_materialization_plan.plan()` 生成不可变 `plan_sha256`、严格 Person→Visit→db_reconcile 顺序、**`database_mutation_authorized=False`**。工具不连 S3/数据库，也不会制造 COMMIT 许可。
- `tests/omop_writer/test_s3_rollback_plan.py`：4 个新增测试，另外既有 9 个 OMOP Precommit 单元测试、8 个历史 dynamic writer 单元测试一起通过。当前 legacy `plan()` 要求 `batch_id` 以 `task004-airflow-` 开头；真正 NEW_ONLY Generator 将来如改用独立业务命名，必须先做**新 versioned Plan Contract 兼容扩展**，不能用字符串替换绕过合同。
- 复用独立受限 `cdm_writer` 角色、`dw-spark/task004-cdm-writer-db` Secret、固定 Runtime `ghcr.io/johnzhang-dataforge/healthcare-data-platform-task004-cdm-runtime@sha256:94979587aeee2f2ea13e2c27ffc5a8850b97381f3f126c72201fe2b2b3086f5e`。**没有部署新的 Runtime Image、没有改 Airflow DAG、没有创建新的 Claim、没有调用 Generator 或 Spark Job。**
- Writer 执行 `--rollback-from-s3 person`：先下载、SHA 校验 Manifest 和匹配的单一 Person Parquet，再进行 Python OMOP Adapter，调用已有 `task004_cdm_postgres_rollback_executor.execute_rollback()`，该函数强制 `allow_commit=False`，生成器只能输出结尾 `ROLLBACK;`，不会开放 COMMIT。
- 真实 PostgreSQL 数据已存在同 Source Person ID 且 payload 不相同，内层 PostgreSQL `BLOCKED:EXISTING_TARGET_DRIFT` 在事务完成前抛错；PG 事务随错误中止、连接关闭，**没有输出成功的 `CDM_S3_WRITER_ROLLBACK=PASS`**。这符合先前 [Seed/Reference Date 根因证明](TASK-004-STEP04F-SYNTHEA-SEED-REFERENCE-DATE-ROOTCAUSE-READONLY-CLOSEOUT.md)：23/23 个源患者 ID 复用、出生日期变化。这次没有忽略或降低任何拦截等级。

## 3. 一轮真实 Self-Runner 接受测试

- **[Run 38479591382](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38479591382)**：**SUCCESS（预期负例）**。源码精确 SHA `251bf47c0f41e8939da07be7aacabc0c0c5bd792`、Self-Runner 工作流 SHA `68dd450b6cb221105dd719145a36b56eaaa28d91`。
- 真实闭环：

```text
OMOP_S3_WRITER_ROLLBACK_SOURCE_TESTS=PASS
OMOP_IMMUTABLE_S3_ROLLBACK_PLAN=PASS
REAL_S3_IMMUTABLE_PLAN=PASS
OMOP_S3_WRITER_BASELINE=PASS
OMOP_REAL_S3_PERSON_VISIT_PARQUET_VALIDATED=PASS
OMOP_REAL_S3_PG_WRITER_TARGET_DRIFT_BLOCKED=PASS
OMOP_REAL_S3_WRITER_FULL_ROLLBACK_SUCCESS=NO
OMOP_COMMIT=NO
OMOP_REAL_S3_WRITER_ZERO_PERSISTENCE=PASS
DATABASE_BUSINESS_MUTATION=NO
```

- 21 个测试：OMOP Writer 13 个 + Existing Dynamic PG Writer 8 个，都 SUCCESS。
- 真正两次独立 PostgreSQL `READ ONLY` 查询（before/after 完全 `diff -u` 一致）：

| 项目 | 前 | 后 |
|---|---:|---:|
| `cdm.person` | 136 | 136 |
| `cdm.visit_occurrence` | 9391 | 9391 |
| `etl.landing_batch_ledger` | 0 | 0 |
| 该冲突批次 `etl.task004_batch_ledger` | 0 | 0 |
| 该冲突批次 `etl.task004_batch_stage` | 0 | 0 |
| 该冲突批次 `etl.task004_batch_commit` | 0 | 0 |

本次未持久修改数据库数据或权限。测试程序创建过 worker02 临时 K8s Jobs/ConfigMap，执行后清理；真正 S3 数据不变。**不要把 Job 因预期冲突 FAIL 的步骤，误记为真正的 ROLLBACK 完成正例。**

## 4. 真正完成第三层所必需的下一步

1. **先得到无 Source ID 冲突的真正新批次**，它应由独立 NEW_ONLY Synthea Generator 冻结 Seed/Reference Date 并发布 READY Manifest，不能复用此次已证实 23/23 患者身份冲突的数据，也不能直接将已经 COMMIT 的 2026-10-12 历史批次重标成新批次。
2. 为新批次版本化升级动态 Plan（当前固定 `task004-airflow-` 批次 ID 前缀和旧 `task004-dynamic-v1` Ledger 合同），保持旧已入库对象不受影响。接着通过新独立 Writer Runtime 执行**完整 Person→Visit S3-to-PG ROLLBACK 正例**，独立验证 Map、Ledger、Stage、OMOP 零持久化；真实历史 drift 负例继续拒绝。
3. **最后才**设计 claim-owner/token 的事务内核查、有效 Lease、未知 COMMIT 恢复、真实 SQL checkpoint/row counts、逐行/外键/源键 DB reconciliation；明确 per-batch 启用实际 COMMIT，先 Person 再 Visit，再进行同批 replay/idempotency。
4. 不要为了完成第三层而直接启用旧 renderer 的 `allow_commit=True` 或在 Airflow 定时 DAG 的安全配置中改 `CLAIM_ENABLE=NO`；两者目前均不安全。

**结论：真实 S3→OMOP Adapter→真实 PG Writer 的接线与 fail-closed 防护已验收；没有可用于正向真实 ROLLBACK 的全新非冲突批次，因此第三层第2步的 ROLLBACK 成功正例继续 BLOCKED。Task004 IN PROGRESS，Task005 ON HOLD。**
