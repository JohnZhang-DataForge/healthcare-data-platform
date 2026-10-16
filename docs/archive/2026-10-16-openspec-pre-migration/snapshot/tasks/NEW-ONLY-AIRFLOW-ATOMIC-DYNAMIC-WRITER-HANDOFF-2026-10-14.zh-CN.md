# TASK004 — NEW_ONLY Airflow Spark→Writer 动态批次合同与原子事务 Renderer

> **2026-10-14 EDT — 代码合同/真实 PG 只读验收成功，尚非新批次 COMMIT。** [Self-Runner Run 38562133245](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38562133245) **SUCCESS**，Claim **26/26**、Writer **42/42**（包括新增动态 5 个）、Landing Discovery **46/46**，总 **114/114**。真实 PostgreSQL 只读独立验证 Person=137、Visit=10203、已提交 NEW_ONLY Claim=1 COMPLETED、Stage=813、2 VERIFIED checkpoints 不变。未运行 Spark/未触发 Airflow DagRun/未 Claim/未做新业务 COMMIT；TASK004 IN PROGRESS、TASK005 ON HOLD。

## 本轮关键设计：Spark 完成后再由一个 Writer 事务进行 Claim + COMMIT

之前消费者 Claim API 的 `claim()` 会**单独持久化** `PROCESSING` Lease，然后通过跨 Pod / XCom 把 Owner+Attempt 传给后继 Spark/Writer。Demo 中这会引入 **Spark 失败遗留 Lease、跨任务续租、Lease 超时恢复** 等不必要复杂度。

本轮选用已经在 [38555481037](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38555481037) 验证过的单批次原子路径：

```text
new_only_omop_consumer: S3 verified READY
       |
       +-- Claim=COMPLETED --> already_completed_no_replay (已真实 live PASS)
       |
       +-- Claim=ABSENT --> unclaimed_batch_hold (仍 HOLD/未触发 Spark)
                              |
                        [future] Spark Person + Visit complete + Parquet readback
                              |
                  pure prepare_new_only_writer_handoff()
                  (immutable Plan, no DB Claim/COMMIT)
                              |
                  [future] cdm_reader read-only actual S3/PG Source-ID audit
                              |
                  [future] *one* PostgreSQL BEGIN
                         landing_claim_worker creates Claim PROCESSING,
                         cdm_writer same-TX fenced Person/Visit Writer,
                         real DB full-row reconciliation,
                         final fencing,
                         landing_claim_worker marks Claim COMPLETED
                         one COMMIT
                              |
                  [future] independently query persisted PG state
```

这一选择 **不需要事先跨 Airflow Task 传递真实 Lease Owner token**：Owner48hex/Attempt1在 Writer 的同一个事务内部绑定和校验。Claim Ledger 只有与 Person/Visit 同时成功提交才变成 COMPLETED。**它不是多会话、生产级独立 Claim→Writer 设计**；`omop_admin` Session 使用 `SET LOCAL ROLE landing_claim_worker/cdm_writer` 的现有 Demo 模式，不应误称各独立 Pod 都已有真正最小权限登录/COMMIT。

## 版本化改动

- `airflow/dags/new_only_omop_writer_handoff.py`：新纯函数 `prepare_new_only_writer_handoff(selected,claim_readback,person_xcom,visit_xcom)`。要求源批实际 S3 Discovery 精确匹配、PG `ABSENT`、真实 Spark 两实体 `processing_readback=PASS`、各自 run_id/Parquet URI、同一 manifest/ingest_date、rows 上限；调用既有 `task004_cdm_preflight_contract.validate_handoff` 和 `task004_cdm_materialization_plan.plan` 创建 SHA256 锁定 Plan。返回 `NEW_ONLY_WRITER_HANDOFF_VERIFIED_NOT_AUTHORIZED`、`business_commit_authorized=false`。
- `apps/omop_writer/commit_new_only_batch_once.py`：原 `generate_commit_sql()` **冻结**真实已完成 `synthea-new-only-gh-38497355290`/Manifest SHA/1+812 身份不变；内部 SQL Writer 主体抽取为私有 `_render_atomic_new_only_sql(expected_identity)`，Stage/Checkpoint/Person+Visit full-row reconciliation 行数随 context 动态化。保留原事务的 3 次 Definer Fencing、角色隔离、双实体 Checkpoints、Existing Target Drift、完整 DB 对账、单个 COMMIT。
- `apps/omop_writer/dynamic_new_only_commit.py`：`generate_dynamic_commit_sql(plan,people,visits,lease_owner,handoff)` 冻结历史已提交批次，强校验动态 Plan 与 Handoff、source fingerprint、Person 父关系及 1..100 Person/1..100000 Visit，调用共享私有 Renderer。**仅返回 SQL 文本**，无 CLI 执行/无 Airflow KPO/无提交权限；不允许绕过运行时真实 S3/PG Reader preflight。
- `tests/omop_writer/test_dynamic_airflow_new_only_commit.py`：动态 Visit 1/812 对账 SQL；拒绝历史批次、脏 Claim、DRIFT、伪造 XCom、无效 token、错误源身份；确认原 one-shot `generate_commit_sql` 不被泛化为可重新 COMMIT 的 API。
- Self-Runner 专用 `.github/workflows/task004-newonly-dynamic-writer-handoff.yml` 锁定 Healthcare candidate **SHA `6456a70c5449c26b7c4eb2f9d2aeec989202fc6c`**，完成 114 单测及真 PG 只读核验。**无 Spark Live、无 S3 mutation、无 PG business mutation。**

## 已验收与尚未接线的精确边界

**DONE（真正完成代码+CI）：** NEW_ONLY Spark Person/Visit→Writer 数据合同；复用首次 COMMIT 的事务核验代码，并支持动态真正 Batch/行数；已完成的历史真实批次保持不能重新使用动态 Writer；全部 unit/contract regressions PASS，真 PG 完成状态安全保留。

**NOT DONE（下一轮主线）：**
1. 实际 `new_only_omop_consumer` DAG 尚没有 Spark Person/Visit 任务，`unclaimed_batch_hold` 仍是安全终点；需要把已有 `landing_spark_processing` 复用到此 DAG，并在 Spark 之后调用纯 Handoff。
2. 封装通用动态 Writer 的 `cdm_reader` 真实 S3 GET/Parquet readback + PG collision check 和原子 SQL 执行，必须先在独立真实新 batch 做 ROLLBACK-only 实测，之后受控真实 COMMIT；不能拿旧已完成批次再写入。
3. 运行时确实需要在 worker02 获取固定 digest Writer 代码/依赖，且需严格控制敏感数据和凭据；本轮只提供代码合同，不应将 `generate_dynamic_commit_sql()` 作为直接暴露给 Airflow 配置的任意 SQL 执行工具。
4. 与 Portal/其它 TASK004 开发 Session **人工协调 Spark/共享 Airflow** 后才进行 SparkApplication / live Spark；若其它 session 正在修改 Spark 则不要并行触发实际 Spark。
5. 新批次不直接启用早期 `claim_discovered_inventory.py` 的 `CLAIM_ENABLE=YES`；先确保完整 Writer 恰好一个事务可以处理新的 READY Batch。双 Writer 并发、复杂 Lease Recovery 是 FUTURE ENHANCEMENT，不阻塞 Demo，但 DB Data Integrity 仍严格。

**结论：** 代码上已打通可复用的 *Handoff→原子 Claim/Writer SQL Renderer* 合同，尚未把它作为 live Airflow 写入任务运行。旧批次 OMOP Person137/Visit10203 保持不变，`TASK004=IN PROGRESS`，`TASK005=ON HOLD`，Portal A4 HOLD。
