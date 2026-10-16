# TASK004 — NEW_ONLY Claim / Lease Token Fencing v1，真实 PostgreSQL ROLLBACK 验收

> **2026-10-14 EDT（Run 日志 UTC）— Claim 侧 Owner/Attempt/Lease Fencing: REAL LIVE PASS，Writer 侧 COMMIT Fencing: NOT YET。** [真实 Self-Hosted Runner 38529634738](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38529634738) **SUCCESS**：Claim 26/26 + OMOP Writer 25/25 Python regressions；真实 worker02 `dw-spark` 短命 Pod 使用 `landing_claim_worker` 最小权限角色，PostgreSQL 合成批次 Claim→Lease Heartbeat→超时拒绝→FAILED 隔离→Owner/Attempt 轮换→最终全部 ROLLBACK；新批次真实 READY、CDM、Claim Ledger 均未持久化写入。

## 1. 本轮变更（不执行真实 NEW_ONLY Claim 或业务 COMMIT）

Healthcare `apps/landing_claim/lease_fence.py` 新增三个显式入口：

1. `ticket_from_claim(candidate, claim_result)`：只有真正 `decision=CLAIMED` 可签发票据，严格认证 `synthea-new-only-*`、48 位 hex lease token、正整数 Attempt 和不可变 Manifest 身份。
2. `assert_live_fence(cur, ticket)`：**在调用方现有的同一个 PostgreSQL 事务内**执行 `SELECT ... FROM etl.landing_batch_ledger ... FOR UPDATE NOWAIT` 取行锁；验证 Manifest SHA/URI、`PROCESSING` 状态、`lease_owner`、`attempt_count`，并在**锁拿到之后**使用 PostgreSQL `clock_timestamp()` 再检查 `lease_expires_at`。不 `commit()`、不 `rollback()`、不新开连接。函数必须在未来 Writer Person→Visit 的同一个事务内使用，且 **COMMIT 紧前必须再验一次时钟和 token**。
3. `renew_live_fence(cur,ticket,lease_seconds)`：先通过上述行锁与资格校验，再使用有相同身份/Attempt/Owner/未过期条件的 UPDATE + RETURNING，防止过期租约被续活；合法 30–3600 秒。

合成批次 `synthea-new-only-fence-<workflow-run-id>` **不是 S3 READY，绝不能作为真实业务输入、也不能用于 COMMIT**。真实 `synthea-new-only-gh-38497355290` 仍处于未 Claimed 状态。

## 2. 真实集群验证

- 第一次 [Run 38529523481](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38529523481)：26/26 Claim + 25/25 Writer 测试都通过，但实时 Pod 检查 `cdm.person` 表权限时因 `landing_claim_worker` **没有 `cdm` Schema USAGE** 而报 `InsufficientPrivilege`。这是权限检测的实现问题，不是 Claim 原子性或业务数据问题；该 Run 的独立 PostgreSQL After 读回 PASS。
- 改为验证 `has_schema_privilege(current_user,'cdm','USAGE')=false`，且 `etl.task004_batch_ledger INSERT=false`，正确保持最小权限。
- 第二次 [Run 38529634738](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38529634738) 整体 SUCCESS，日志：
  ```text
  FENCE_AND_LEGACY_REGRESSION=PASS
  FENCE_REAL_PG_BASELINE=PASS
  PG_FENCE_REAL_OWNER_FIRST_ATTEMPT=PASS
  PG_FENCE_REAL_HEARTBEAT_AND_WRONG_OWNER=PASS
  PG_FENCE_REAL_EXPIRED_NO_REVIVAL=PASS
  PG_FENCE_REAL_FAILED_RECONCILIATION_HOLD=PASS
  PG_FENCE_REAL_ATTEMPT_ROTATION_AND_STALE_BLOCK=PASS
  PG_FENCE_SYNTHETIC_ROLLBACK_NO_LEDGER_ROW=PASS
  FENCE_REAL_JOB=SUCCESS
  TASK004_FENCE_REAL_PG_ROLLBACK=PASS
  FENCE_REAL_PG_NO_PERSISTENCE=PASS
  CLAIM_ENABLE=NO
  OMOP_COMMIT=NO
  S3_READY_MUTATION=NO
  ```

PostgreSQL 通过 `BEGIN TRANSACTION READ ONLY` 独立查 Before / After：

| 表 / 受保护批次 | Before | After |
|---|---:|---:|
| `cdm.person` | 136 | 136 |
| `cdm.visit_occurrence` | 9391 | 9391 |
| `etl.landing_batch_ledger` 全部行 | 0 | 0 |
| 真实 NEW_ONLY v2 Batch Claim | 0 | 0 |
| 真实 NEW_ONLY v2 Batch Writer Ledger | 0 | 0 |
| 真实 NEW_ONLY v2 Batch Stage | 0 | 0 |
| 真实 NEW_ONLY v2 Batch Commit | 0 | 0 |

本轮只测试了**同一数据库连接内的事务性行锁/Token/状态转换**，并未通过多个真实并发 Writer 会话进行锁竞争实测；不要误称已经证明两 Writer 并发执行互斥。

## 3. 极重要：还不能做生产安全 COMMIT

**已经具备 Claim 侧 Fencing 规则，但未接入 Writer 同事务：**

- Claim 登录角色 `landing_claim_worker` 只有新 `etl.landing_batch_ledger` 的 SELECT/INSERT/UPDATE 等，**没有 CDM Schema USAGE，也不能写 `cdm.person/visit`**；
- OMOP `cdm_writer` 原本用于真正 Person/Visit 事务，不能简单用 `cdm_reader` 或 Claim Worker 事先查状态，再放 cdm_writer 在**另一个**连接 COMMIT。那样是典型 **TOCTOU race**（检查结束后 Owner 可能变更/过期）。**不能给 cdm_writer 为了方便而直接宽泛授予 Claim Ledger 的 INSERT/UPDATE 权限**；
- 下一安全步骤是设计数据库内的、`cdm_writer` 可调用的**最小权限同事务锁校验**（例如经安全审计的 `SECURITY DEFINER` Function，指定固定 search_path、撤销 PUBLIC 执行、仅授予 Writer EXECUTE），在同一 `BEGIN` 的 Person/Visit DML 前和 COMMIT 紧前检查 Owner+Attempt+Manifest+租约，保留行锁直到事务结束；需要测试 Token 错误、过期、Attempt 轮换、后台 Claim 修改竞态、超时等负例。**本轮没有部署任何 Definer Function、没有变更 PostgreSQL Grant/Schema，也没有实现此 Writer 同事务锁。**
- 原 `batch_ledger.claim(..., retry_failed=True)` 是早期供受控合成测试使用的显式重试接口，**尚未拥有“未知业务 COMMIT 已否发生”数据库协调证据**；新真正 READY 若 FAILED 必须 HOLD 待 reconciliation，不可直接把人工 `retry_failed=True` 视为安全恢复授权。原 `mark_completed` 的外部 digest 同样不是充分的真实 CDM Reconciliation 证明，严禁暴露给 Airflow。
- 强制 `CLAIM_ENABLE=NO`、`CLAIM_ALLOWLIST=""` 不变。真实 NEW_ONLY 批次、旧 v1 READY、PG Writer 1 Person/812 Visit 的正向 ROLLBACK 证据不重跑、不改写。

## 4. NEXT

优先完成 **cdm_writer 角色的同事务数据库锁代理（Definer 最小权限）、真实并发竞争/失效测试、受控的 Owner+Attempt 后继 Writer ROLLBACK + 独立 PG Table Readback**。这之后另立一个版本化候选阶段做 **Claim + Writer + Reconciliation 同事务安全 COMMIT**、unknown commit recovery 和同批重放幂等。**TASK004 IN PROGRESS；UPDATE_ONLY/MIX_DATA/TASK005 ON HOLD；Portal A4 共享 Spark 运行仍 HOLD，跨 Session 按人工协调规则执行。**
