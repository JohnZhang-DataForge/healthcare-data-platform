# TASK004 — NEW_ONLY Airflow→Spark→OMOP 最终真实验收 Closeout（2026-10-14 EDT / 2026-10-15 UTC）

> **权威当前结论：TASK004 = COMPLETED / CLOSED（用户扩展后的 Person + Visit 同批次 PostgreSQL OMOP 入库与 Airflow 幂等消费范围）。TASK005 = READY FOR STEP00 READ-ONLY ONLY，Condition 业务写入尚未开始。** 早期 TASK004 STEP03E MVP、第三批 READY/PENDING、2026-10-13 Agent Handoff 均为各自时间点的历史记录；若与本文冲突，以本 Closeout + 实际 GitHub Runner 证据 + 实时集群为准。本 Closeout 不意味着 Healthcare Data Platform 所有后续模块都已完成。

## 1. 最终验收范围与真实结果

第三个独立 Synthea NEW_ONLY v2 批次从 immutable S3 Landing READY，经 Airflow `new_only_omop_consumer` 的 S3 Discovery→只读 Claim→Spark Patient/Encounter→Spark Reconcile→immutable Writer Handoff→带物理 Secret 双闸门的 Atomic Writer→PostgreSQL Person/Visit/ID Map/Claim/Stage/Checkpoint 原子 COMMIT，在真正的 v4 DagRun 全流程成功。随后以**同一个已提交批次**、相同 manifest identity、同样的 `spark_processing=true` + `writer_commit=true` 启动新的手动 DagRun，真实路由到 `already_completed_no_replay`，Spark、Writer 跳过，独立 PostgreSQL 前后快照完全一致；DAG 已重新暂停。

**三条真实 NEW_ONLY Batch：**

| Batch ID | 本次新增 Person | 本次新增 Visit | 业务状态 |
| --- | ---: | ---: | --- |
| `synthea-new-only-gh-38497355290` | 1 | 812 | COMPLETED（旧历史，不得重复首次 COMMIT） |
| `synthea-new-only-gh-38489944582` | 70 | 11,487 | COMPLETED（旧历史，不得重复首次 COMMIT） |
| `synthea-new-only-gh-38588671004` | **1** | **244** | **COMPLETED，首次由 Airflow Writer KPO 真正写入** |

前三批累加到现有库的新增量不等于 OMOP 总行数；数据库原有其他基线数据依旧存在。

## 2. 第三批不可变身份与执行版本

- **Batch ID:** `synthea-new-only-gh-38588671004`
- **Manifest URI:** `s3://health-landing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-14/batch_id=synthea-new-only-gh-38588671004/manifest.json`
- **Manifest SHA256:** `22b6c386b5c165e0c9cff3d3ce5fbae2115aee87b4761fc4c11fb43a2c4720b1`
- **Source:** Synthea v3.3.0，独立新源 1 Person / 244 Encounter，18 个 immutable S3 Landing 对象；此前 [S3 READY/原样 replay Run 38588933989](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38588933989) PASS。
- **业务 DAG:** `new_only_omop_consumer`，`schedule=None`，`max_active_runs=1`，14 tasks，手动双 flag 与物理 Secret 双重授权（非定时自动 COMMIT）。
- **Airflow 真正成功的业务 DagRun:** `task004-third-real-20261014-v4`，2026-10-14 23:49:29–23:54:10 UTC，`DagRun.state=success`，`spark_patient`、`spark_encounter`、`spark_reconcile`、`prepare_writer_handoff`、`execute_new_only_writer`、`writer_committed_verified` 均为 `success`。
- **成功的 Writer 镜像:** `ghcr.io/johnzhang-dataforge/healthcare-data-platform-new-only-omop-writer@sha256:1565a4481669520916a336e7ce5de52f3856333c43632078d03854b22bc28ae4`
- **镜像人工构建:** [Healthcare GitHub Actions Run 38655747233](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/38655747233) SUCCESS，DAG 镜像更新 [PR #146](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/146) merged。
- **业务独立只读核验:** [Self-Runner Run 38657060822](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38657060822) **SUCCESS**。从 Airflow metadata 查询真实 v4 成功，不用 UI 颜色代替数据库证据。

## 3. PostgreSQL 真实 COMMIT 与独立持久化核验

表中数据均来自独立只读数据库会话，不是模拟 SQL 或 DAG XCom 推测：

| PostgreSQL 对象 / 核验项 | v4 前 | v4 后 / 重复 SKIP 后 |
| --- | ---: | ---: |
| `cdm.person` | 207 | **208** |
| `cdm.visit_occurrence` | 21,690 | **21,934** |
| `etl.person_id_map` | 207 | **208** |
| `etl.visit_occurrence_id_map` | 21,690 | **21,934** |
| `etl.landing_batch_ledger` Claim 总数 | 2 | **3** |
| 第三批 Claim | ABSENT | **1，COMPLETED** |
| 第三批 `etl.task004_batch_ledger` | 0 | **1** |
| 第三批 `etl.task004_batch_stage` Person / Visit | 0 / 0 | **1 / 244**（合计 245） |
| 第三批 `etl.task004_batch_commit` | 0 | **2 VERIFIED checkpoints** |
| 第一、第二批历史 Claim | 2 COMPLETED | **仍为 2 COMPLETED** |

第三批的 Claim 在独立 readback 中为 `COMPLETED`，Stage/Checkpoint/映射数匹配，符合本次用户定义的原子入库验收；**不把 Writer Task 成功视为唯一证据**。

## 4. 同批次 Airflow 幂等重放 — 最终关闭门槛

- **最终证据 Run:** [Self-Runner 38657630069](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38657630069) — **SUCCESS**。
- **重复 DagRun:** `task004-third-completed-skip-38657630069`，使用第三批原样 Batch/Manifest/SHA，显式 `consumer_readonly=true`、`spark_processing=true`、`writer_commit=true`。
- **真实 Airflow 结果:** DagRun `success`；`scan_ready_manifests`、`select_verified_new_only_batch`、`inspect_claim_readonly`、`route_new_only_status`、`already_completed_no_replay` 为 `success`；`spark_patient`、`spark_encounter`、`spark_reconcile`、`prepare_writer_handoff`、`route_writer_authorization`、`execute_new_only_writer`、`writer_committed_verified` 为 `skipped`。
- **持久化不变性:** 重放前后两次独立 PostgreSQL READ ONLY 查询文件 `diff -u` 完全相同：Person=208、Visit=21,934、双 Map=208/21,934、Claim=3、第三批 Claim COMPLETED1、Writer Ledger1、Stage Person1/Visit244、VERIFIED2，旧完成批次仍各 1。
- **无副作用:** `TASK004_THIRD_COMPLETED_SKIP_NO_SPARK_OR_WRITER=PASS`、`TASK004_THIRD_IDEMPOTENCY_PG_ZERO_CHANGE=PASS`、`SPARK_RERUN=NO`、`BUSINESS_COMMIT=NO`、`AUTO_CLAIM=NO`；`AIRFLOW_WRITER_DAG_REPAUSED=PASS`。
- 已完成批次的自动 SKIP 是 DAG Branch 路由保证，并不代表可无闸门重置失败 Writer 或对所有未知并发/断网情况进行任意重试。**不要清除旧 Writer Task 并直接执行 COMMIT。**

## 5. 真实排障经验（需在以后 Writer 镜像开发中复用）

最初 v1 / v2 / v3 均到达 `execute_new_only_writer`，但都在真正 COMMIT 之前被 `ValueError: BLOCKED=batch_id` 拒绝；每轮都先通过 PostgreSQL READ ONLY 检查第三批 Claim/Stage/Checkpoint **0**，避免不明状态下盲目重试。错误不是第三批 batch_id 缺失，而是多处 runtime 文件继承了**旧版本 CDM 基础镜像**，构造中间 Plan 时遗漏 `writer_identity_version="synthea-new-only-v1"`：

1. v1：`task004_cdm_materialization_plan.py` 是旧版，首次 `verified_plan` 检查失败；[PR #142](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/142) 通过 Dockerfile 显式 COPY 修复。
2. v2：`task004_cdm_dynamic_adapters.py`、`task004_cdm_dynamic_source.py` 是旧版，S3 decode→transform 时旧 adapter 的二次 `validate_plan` 失败；[PR #143](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/143) 显式 COPY 修复。后续 [真实第三批 S3 只读 1/244 Run 38647450779](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38647450779) PASS。
3. v3：`task004_cdm_dynamic_pg_writer.py` 是继承的旧版；用户在失败 Pod 同镜像临时 inspect 证实 `render()` 构造 `original` 未传 `writer_identity_version`，SQL 渲染阶段二次 `validate_plan` 拦截。[PR #144](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/144) 将 GitHub Main 已支持新版标识的 renderer 显式 COPY。
4. 人工构建第一次 Workflow 失败不是 Writer：Python `-c '...'` 中错误 Bash 单引号转义，改用 `python - <<'PY'` 原样 heredoc；[PR #145](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/145) 后构建 [38655747233](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/38655747233) SUCCESS，固定新 digest [PR #146](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/146)。
5. **经验：** 对基于旧 CDM runtime 的复合 Writer 镜像，必须核实所有涉及 Plan 的 runtime 模块版本，不仅验证第一个 Plan 函数；现场日志 `Traceback` 指向的真正调用文件/行优先于推断。失败可能是旧 overlay，而不是上游 Handoff 源数据错误。对不明 COMMIT 结果，**先独立 PostgreSQL 持久化查询，再决定是否恢复**；不要为测试循环重生 Synthea、反复重写旧批、或无边界增加单测与安全机制。

## 6. 状态关闭、交接和保留风险

**TASK004: COMPLETED / CLOSED**（本项目所约定 NEW_ONLY Synthea → Landing → Spark Person/Visit → Airflow 编排 → Atomic PostgreSQL OMOP 入库 → 正常同批次幂等 SKIP）；三批 NEW_ONLY 已实测 COMMIT；其他历史 STEP03E、只读实验和回滚实验不应与第三批真实 Airflow COMMIT 混淆。

**TASK005: READY FOR STEP00 READ-ONLY（Condition）**。新 Session 首先读 `docs/README.md`、`docs/tasks/TASK-STATUS.md`、本 Closeout、`docs/tasks/TASK-005-CONDITION-DEVELOPMENT-PLAN-v1.0.zh-CN.md`。按已有 Condition 设计，STEP00 首先验证真实 `conditions.csv` 契约、Person/Visit FK、OMOP schema/vocabulary、稳定 occurrence key；**不因 TASK004 DONE 自动授权 Condition INSERT/COMMIT**。

**不包括在 TASK004 完成声明中：** UPDATE_ONLY、MIX_DATA、Condition、跨 Writer 并发双写压测、生产级密码与权限隔离、灾备/未知事务结果自动恢复、Marquez/OpenLineage Portal 完整 Job/Run/Dataset bloodline。它们属于后续独立迭代。为防演示 Secret 长期保留，**需由运维确认 `dw-spark/task004-new-only-writer-commit` 临时高权限 Secret 的当前状态，并在不再需要 COMMIT 时予以撤销/轮换**；本轮验证只证明业务/幂等性，没有声称已撤销该 Secret。若另一 Portal Session 修改 Airflow/Spark，共享资源仍按人工协调规则处理。

## 7. 一眼可复核的最终证据

- 第三批 S3 immutable READY：[38588933989](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38588933989)
- 真 v4 Airflow 全流程 + 独立 PG 持久回读：[38657060822](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38657060822)
- 第三批真实已完成重复 SKIP + PG Before/After 零变化：[38657630069](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38657630069)
- 最终镜像手动构建：[38655747233](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/38655747233)
- 当前 DAG Writer image pin：[Healthcare PR #146](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/146)

保留历史失败记录 v1/v2/v3 和修复 PR，用于审计；不覆盖失败结论，也不把以前的 `TASK004 IN PROGRESS` 时点快照冒充当前状态。
