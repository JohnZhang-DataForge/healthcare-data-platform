# TASK004 — NEW_ONLY v2 真 S3 → OMOP Writer Person + Visit 同一 PostgreSQL 事务 ROLLBACK 成功验收

> **2026-10-13 EDT / 2026-10-14 UTC：REAL POSITIVE JOINT ROLLBACK PASS。** [真实 Self-Hosted Runner 38508357752](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38508357752) 整体 **SUCCESS**（包含严格 25/25 Writer 合同测试、真 SeaweedFS 两份 Parquet、PG Reader 预审、PG Writer 联合事务、最终独立 PostgreSQL 表级只读核验）。[Healthcare PR #119](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/119) 与 [Self-Runner PR #97](https://github.com/JohnZhang-DataForge/Self-Runner/pull/97) 已合并 Main。原旧身份合同 [Healthcare PR #109](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/109) 已因 Main 文档冲突由 #119 完全取代并明确关闭、不合并；历史代码/验证证据保留。

## 一、真实输入（冻结，不得改写 READY）

- 批次：`synthea-new-only-gh-38497355290`，源 Synthea v3.3.0 NEW_ONLY，S3 READY 为 `manifest_version=2.0`；18 CSV，其中一个辅助 CSV 合法 0 行，Person=1、Encounter=812。
- Immutable Manifest：`s3://health-landing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-14/batch_id=synthea-new-only-gh-38497355290/manifest.json`
- Manifest SHA：`dfb5d30e83c6a9b35b3a723137a5f3ab67649ad94ef1801e2bae3ef42fe5fa80`
- **真正 Person Processing Parquet（上轮 Airflow/Spark XCom）**：
  `s3a://health-processing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-14/batch_id=synthea-new-only-gh-38497355290/entity=patient/run_id=task004-person-20261014T032923Z-9/work/normalized/data/`
- **真正 Encounter Processing Parquet（上轮 Airflow/Spark XCom）**：
  `s3a://health-processing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-14/batch_id=synthea-new-only-gh-38497355290/entity=encounter/run_id=task004-encounter-20261014T032923Z-8/work/normalized/data/`

真 v2 完整 Airflow→Spark 的证据：[Run 38505927396](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38505927396) / [Spark Closeout](NEW-ONLY-V2-AIRFLOW-SPARK-PERSON-VISIT-REAL-LIVE-CLOSEOUT-2026-10-13.zh-CN.md)。

## 二、实现与真正执行

1. 从曾成功验收的 Writer 身份合同 #109 将七项代码/合同/测试按最新 Main **重新应用**到 #119，保持旧无版本 `task004-airflow-*` 的 Plan 和 Digest 不变；只在显式 `writer_identity_version=synthea-new-only-v1` 时接受 `synthea-new-only-*`。旧 `BLOCKED:EXISTING_TARGET_DRIFT` 保留；新版本直接 `allow_commit=True` 被拒绝。
2. 添加 `apps/omop_writer/joint_s3_rollback.py`：严格重建 Plan SHA，重读真实 S3 Manifest 做 SHA 核验，独立解码两个 Parquet、验证 metadata/batch/ingest_date、1/812 行数、Source Key 唯一、Visit→Person Parent Key 和 row_fingerprint。
3. **audit** 容器在 `worker02/dw-spark` 使用 `cdm_reader` 和 `BEGIN TRANSACTION READ ONLY` 实际检查 OMOP 的历史 batch/Person Source Key/Visit Source Key、当前 Claim/Lease；`READY_TO_CLAIM` 只代表无冲突，**绝不等于 COMMIT 授权**。输出：`NEW_ONLY_REAL_S3_PERSON_ROWS=1`、`NEW_ONLY_REAL_S3_VISIT_ROWS=812`、`NEW_ONLY_PRECOMMIT_READER_REAL_PG=PASS`、`CLAIM_ENABLE=NO`。
4. **rollback** 容器使用 `cdm_writer`，以同一 S3 immutable Plan 再读取双方真实 Parquet，调用原 Person/Visit SQL Renderer 的完整校验逻辑，安全地拼接为**单个 BEGIN / Person Stage+ID Map+CDM+Verified Checkpoint / DROP 本事务局部 TEMP TABLE / Visit Stage+ID Map+CDM+Verified Checkpoint+Person FK / 联合 Ledger/Stage/Checkpoint 校验 / 单个显式 ROLLBACK**。跨实体运行阶段 Person checkpoint 在同一个尚未提交的事务内对 Visit 可见；保留 Existing Target Drift 和 Concept 校验；禁止 COMMIT。
5. 第二次真实执行 [Run 38508357752](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38508357752) 返回：
   ```text
   NEW_ONLY_REAL_S3_PERSON_ROWS=1
   NEW_ONLY_REAL_S3_VISIT_ROWS=812
   NEW_ONLY_PRECOMMIT_READER_REAL_PG=PASS
   JOINT_PHASE=audit:SUCCESS
   NEW_ONLY_JOINT_PERSON_ROWS=1
   NEW_ONLY_JOINT_VISIT_ROWS=812
   NEW_ONLY_JOINT_PERSON_VISIT_SQL_ROLLBACK=PASS
   JOINT_PHASE=rollback:SUCCESS
   REAL_S3_JOINT_PG_ROLLBACK=PASS
   OMOP_COMMIT=NO
   ```

## 三、独立数据库读回（证实无表记录持久化）

| PostgreSQL 表级核验 | Before | After |
|---|---:|---:|
| `cdm.person` | 136 | 136 |
| `cdm.visit_occurrence` | 9391 | 9391 |
| `etl.person_id_map` | 136 | 136 |
| `etl.visit_occurrence_id_map` | 9391 | 9391 |
| `etl.landing_batch_ledger` | 0 | 0 |
| 新 v2 Batch Claim | 0 | 0 |
| 新 v2 Batch Writer Ledger | 0 | 0 |
| 新 v2 Batch Stage | 0 | 0 |
| 新 v2 Batch Commit | 0 | 0 |

Run 实际日志 `JOINT_WRITER_TABLE_ROWS_UNCHANGED=PASS`、`CLAIM_ENABLE=NO`、`S3_READY_MUTATION=NO`；真实 Writer **最终执行 ROLLBACK 而非 COMMIT**，新批次**未真正入库**。

**重要精度限制：PostgreSQL Sequence / `nextval()` 不受事务 ROLLBACK 回退。** 本轮曾执行实际 ID 分配再回滚，序列计数器**可能**前进。我们已验收的是**表数据、映射行、Claim/Batch Ledger/Stage/Commit 无持久化变化**，**不能称整个数据库内部状态逐比特不变**。后续 COMMIT 不应假设 ID 连续，也不应为了“复原序列”随意 `setval`（会影响并发及历史 ID）。

## 四、修复与重试闭环（符合最多三轮失败停止）

- 最初只读 Writer 身份/联合 SQL 单元回归 [Run 38507947974](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38507947974) 发现相邻第二个 `BEGIN;` 的边界计数漏检；立即修为逐行严格计数。
- 修复后 [Run 38508035737](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38508035737) 验证全部 Writer 测试 + 真 PG READ ONLY 成功。
- 首次真实 [Run 38508208065](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38508208065) 的 S3/PG Reader 审核 PASS；Writer 失败原因是 `psql` 专用 `\\set ON_ERROR_STOP` 被传给 `psycopg`，发生 SQL SyntaxError；独立 PostgreSQL 表记录回读仍完全不变。
- 修复执行边界为显式移除经过验证的 `psql` 元命令（保留全部 SQL 安全逻辑），最终 [Run 38508357752](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38508357752) 单次真实重测 SUCCESS。

## 五、NEXT（还没完成的是正式幂等 COMMIT）

- **当前 TASK004 仍 IN PROGRESS、TASK005 ON HOLD**。本次联合正向 ROLLBACK **已完成，不要重复跑同一批**。后续要给真正自动 Claim/lease 引入 DB 事务级 Owner/Token/Fencing、租约到期/并发抢占/unknown commit Recovery 的严格拒绝门槛；不能因本轮 `READY_TO_CLAIM` 便让未 Claimed 的 Writer COMMIT。
- 之后分批验证一次真实受控 COMMIT → Person/Visit ID Map/Stage/Commit & Reconciliation → 同 SHA 幂等重放、Different SHA Drift 拒绝；才考虑 Airflow 自动 Claim→Spark→Writer。
- 原历史 Writer 的 `BLOCKED:EXISTING_TARGET_DRIFT`、Legacy Batch 兼容仍需继续回归。Writer 身份版本与实际 Commit 授权是两个完全不同的开关。
- 与 Portal Session 并行期间继续遵守 `docs/platform-portal/SESSION-COORDINATION-POLICY.zh-CN.md`：Portal A4 在本 TASK004 Spark/Airflow 使用窗口 HOLD，不允许同时启动共享 Spark/Operator。不要因为本轮 Writer PASS 自行给 Portal 生成伪造的已成功入库 OpenLineage 事件。
