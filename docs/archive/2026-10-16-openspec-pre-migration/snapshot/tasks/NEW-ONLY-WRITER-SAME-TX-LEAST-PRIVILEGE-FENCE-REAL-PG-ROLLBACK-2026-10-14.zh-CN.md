# TASK004 — Writer 最小权限同事务 SECURITY DEFINER Fencing：真实 PostgreSQL ROLLBACK 候选验收

> **2026-10-14 EDT — 一轮真实数据库安全候选实验 PASS，不是生产部署或 OMOP 业务 COMMIT。**
> Self-Runner [Push Run 38551210536](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38551210536) SUCCESS，Claim **26/26**、Writer **30/30** regressions，PostgreSQL 真实角色切换/临时安装/校验/最终 ROLLBACK 验证。第一次 Run [38551134818](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38551134818) 因新测试误将既有 `ClaimError` 当作 `ValueError` 而失败；修复后一次验证成功。本阶段 **TASK004 IN PROGRESS / TASK005 ON HOLD**。

## 1. 当前基线与本轮代码

- Healthcare `main` 原先已经有 `apps/landing_claim/lease_fence.py`：Claim Worker 在自己的事务可 `SELECT ... FOR UPDATE NOWAIT`，但 `cdm_writer` 无 Claim Ledger SELECT/UPDATE 权限。此前真正 v2 1 Person + 812 Visit 共同 ROLLBACK 已通过，**本轮没有重复运行 Spark 或真正 S3→CDM Writer**。
- 新 `sql/landing_claim/writer_fence_v1_rollback_proof.sql` 在一个 **BEGIN → ROLLBACK** 中，暂建 `task004_writer_fence_owner` **NOLOGIN NOINHERIT**、隔离 `task004_writer_fence` Schema 和 `SECURITY DEFINER` 函数 `assert_active_claim`。函数持有显式 `pg_catalog, pg_temp` 安全 search_path、无动态 SQL、固定 `etl.landing_batch_ledger`、`FOR UPDATE NOWAIT`，行锁在**调用者相同的 PostgreSQL 事务**中一直保持到结束。仅授予函数所有者 Claim Ledger 的 `SELECT` 和对单个非业务列 `updated_at` 的 `UPDATE`（用于 row-lock 资格）；不授予任何 CDM Schema Usage/Person INSERT。
- `cdm_writer` 仅获得受限 Schema USAGE / 函数 EXECUTE；`PUBLIC` 执行权回收；`landing_claim_worker` 无此函数的 EXECUTE。**不会**给 `cdm_writer` 直接 Claim Ledger SELECT/INSERT/UPDATE 权限。
- 函数严格校验 `synthea-new-only-*`、Source、Manifest SHA/URI、48hex Owner、正 Attempt、`PROCESSING` 和 PostgreSQL 实时时钟 `clock_timestamp()`。锁拿到以后检查身份与租约；错误 Owner、旧 Attempt、Manifest Drift、缺失 Claim、过期/FAILED 均 fail closed。
- 新 `apps/omop_writer/fenced_joint_rollback.py` 是**尚未启用的候选 Writer 适配器**，用单个传入的 `cdm_writer` connection/cursor 做 `BEGIN → 受限 DB Fencing → Person+Visit 原有 SQL（含 Existing Target Drift/Checkpoint）→ 同事务紧前再校验 → ROLLBACK`。拒绝自动开启的事务连接、跨 Plan/Claim Ticket 身份、无显式身份版本。无 COMMIT path、无独立 Claim 检查连接、未接入 Airflow。

## 2. 实际 PostgreSQL 执行证据

测试 Runner 只签出固定 Healthcare candidate SHA；不启动 Spark/Airflow/Claim Job。真实 `dw-postgre/dw-postgre-database-0` 的 `omop_admin` 执行 SQL **合成 Claim**（`synthea-new-only-writer-fence-rollback`，不是 S3 READY），再使用 `SET LOCAL ROLE cdm_writer` 验证实际**权限与事务**，临时事务内两条普通临时表 marker DML 仅代表 Writer 阶段；**不是**真实 Person/Visit 表写入。

```text
WRITER_FENCE_PYTHON_REGRESSION=PASS        # Claim 26/26, Writer 30/30
REAL_PG_WRITER_FENCE_BASELINE=PASS
PG_WRITER_FENCE_PRIVILEGES=PASS
PG_WRITER_FENCE_DIRECT_LEDGER_ACCESS_DENIED=PASS
PG_WRITER_FENCE_BEFORE_AFTER_WRITES_SAME_TX=PASS
PG_WRITER_FENCE_OWNER_ATTEMPT_MANIFEST_ABSENT=PASS
PG_WRITER_FENCE_EXPIRED=PASS
PG_WRITER_FENCE_FAILED_HOLD=PASS
PG_WRITER_FENCE_PROBE_NO_PERSISTENCE=PASS
TASK004_WRITER_FENCE_REAL_PG_ROLLBACK=PASS
WRITER_FENCE_REAL_PG_TABLES_UNCHANGED=PASS
OMOP_BUSINESS_COMMIT=NO
S3_READY_MUTATION=NO
SPARK_RERUN=NO
```

独立只读 PostgreSQL Before/After（来自同一 Run 的单独连接）：

| 指标 | Before | After |
|---|---:|---:|
| `cdm.person` | 136 | 136 |
| `cdm.visit_occurrence` | 9391 | 9391 |
| `etl.person_id_map` | 136 | 136 |
| `etl.visit_occurrence_id_map` | 9391 | 9391 |
| `etl.landing_batch_ledger` | 0 | 0 |
| 真 NEW_ONLY v2 Batch Claim / Legacy Ledger / Stage / Commit | 0/0/0/0 | 0/0/0/0 |

**关键：SQL 在同一个 BEGIN 内创建的角色、Schema、Function、GRANT、合成 Claim 和 marker 全部 ROLLBACK。** Probe 后 Catalog 中不存在该角色/Schema，Claim Ledger 没有新增。**目前运行数据库还没有正式安装该 Definer Function！** 新 Python 适配器也尚未部署到真实 Writer Runtime。此阶段证明的是「数据库权限隔离机制可行、失败条件可拒绝、同事务原型正确」，而不是已完成真实 fenced Person+Visit ROLLBACK，更不是已获得 COMMIT 授权。

## 3. 已验证与未验证边界

- ✅ 真实 Postgres 最小角色权限、SECURITY DEFINER、`FOR UPDATE NOWAIT` 行锁调用、DB clock/Manifest/Owner/Attempt 检查及过期/FAILED 负例；同事务临时 DML marker 前后两次函数调用；完全 ROLLBACK。
- ✅ 保留旧 Writer Legacy/Existing Target Drift 代码和原真正 S3 1/812 ROLLBACK 证据。没有 S3 READY、Spark 或 Airflow 变更。
- ⛔ **未**把 Function/Schema/Role 持久部署；**未**验证 `cdm_writer` 真正 1 Person/812 Visit 在新代理保护下的完整 PostgreSQL ROLLBACK。
- ⛔ **未**完成两个真正同时运行的 PG Writer 会话在一行 Claim 上的 NOWAIT 互斥实测。当前 Claim Ledger 总行数为 0，且本轮禁止合成业务状态 COMMIT；另一个会话无法读到未提交的合成 Claim 行。不能把本轮单会话 NOWAIT 调用宣称为并发验收。
- ⛔ 未实现 unknown-COMMIT reconciliation、同批幂等正式 COMMIT、自动 Claim。实际新的 READY 仍 UNCLAIMED。

## 4. NEXT（仍是 TASK004 的安全阶段）

1. 对 `sql/landing_claim/writer_fence_v1_rollback_proof.sql` 进行独立 DB 安全审查：确认正式 DDL/Owner/Grant 原子部署、回退策略和函数 EXECUTE 边界，再决定是否单独授权持久化**纯 DDL**（不得隐含业务 COMMIT）。
2. 在合法的、明确协调的两会话测试窗口安排**真正的行锁竞争**，并验证 Winner/HOLD/NOWAIT、租约过期、错误 Owner/旧 Attempt。若需要持久化可见的合成 Ledger fixture，须另行授权并明确清理；不能用未提交的单会话 fixture 冒充竞争验证。
3. 在不重跑 Spark 的前提下，基于现有不可变 Person1/Visit812 Parquet 和经授权的真实 Claim 票据，走 `cdm_writer` 同连接 SQL Person→Visit **ROLLBACK** + 独立 PG readback；前置拒绝跨连接只读 Claim。
4. 真实安全 Fencing、并发及 Reconciliation 验收后才准备另行批准 COMMIT；`CLAIM_ENABLE=NO`、`CLAIM_ALLOWLIST=""`、Portal A4 HOLD、TASK005 ON HOLD 全部继续生效。Portal/TASK004 共用 Spark/Airflow 的操作必须人工协调。

**验收术语：DB Definer/RBAC 实验 PASS ≠ 函数已生产部署 ≠ 真实新批 fenced Writer ROLLBACK ≠ 真 COMMIT。**
