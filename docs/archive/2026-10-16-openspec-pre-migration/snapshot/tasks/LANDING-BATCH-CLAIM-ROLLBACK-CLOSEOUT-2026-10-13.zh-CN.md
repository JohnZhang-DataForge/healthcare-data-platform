# Landing Batch Claim / Processing Ledger — PostgreSQL 真实 ROLLBACK 验收（2026-10-13）

> **当前状态：独立 Claim 组件 + 专用 Ledger、专用受限 DB 账号/PVC 无关的 Secret 已完成；真实 PostgreSQL 的状态机与 ROLLBACK PASS。** 本轮**没有**把 Claim 接到定时 Airflow DAG，也没有领取真实 S3 已发布批次、没有 Spark/OMOP 入库。本阶段将安全、可复用的“数据库原子领取”作为独立组件验收；下一步才是 Consumer 接线/单批安全闭环。TASK004 仍 IN PROGRESS，TASK005 ON HOLD。

## 1. 功能命名及实现

- `sql/landing_claim/create_landing_batch_ledger.sql`：**实际已执行 COMMIT** 的新增表 `etl.landing_batch_ledger`，与旧 `etl.task004_batch_ledger` 完全独立，未修改旧表、`cdm.person`、`cdm.visit_occurrence` 或 Source ID Mapping。
- `apps/landing_claim/batch_ledger.py`：通用 `Candidate.from_discovery` / `claim` / `mark_failed` / `mark_completed`。每个候选按 `(source_system,batch_id)` 唯一键，绑定不可变 `manifest_sha256` 与完整 `manifest_uri`，使用 `INSERT ON CONFLICT DO NOTHING` + `SELECT FOR UPDATE` 的同一数据库事务来完成原子领取。
- `apps/landing_claim/verify_rollback.py`：在真实 PG 中以模拟 Batch ID 执行整个状态机，**外层事务 ROLLBACK**；不向正式队列领取历史 READY Batch。
- `tests/landing_claim/test_batch_ledger.py`：12 个无需真实 DB 的安全契约测试。
- Kubernetes `dw-spark` Secret `landing-claim-db`，独立 PostgreSQL `landing_claim_worker`。它**只有**新 Ledger 的 `SELECT/INSERT/UPDATE`、etl schema USAGE、DB CONNECT；没有 `cdm.person`/Visit INSERT，也没有旧 task004 Ledger INSERT、superuser、CREATE ROLE 等权限。

## 2. 状态迁移合同

| 输入情况 | 结果 | 安全理由 |
|---|---|---|
| 原子首次插入成功 | `CLAIMED`、attempt=1、随机 lease_owner | 唯一键 + PG 事务保证一次领取有单一获胜者 |
| 相同 Manifest 且 PROCESSING/未过期 | `BUSY` | 不重复启动工作 |
| 同 source/batch，SHA 或 URI 不同 | `BLOCKED:IMMUTABLE_MANIFEST_DRIFT` | 拒绝 ID 对应输入变化 |
| 已 COMPLETED | `SKIP_COMPLETED` | 已核实批次不重复处理 |
| 已 FAILED | `FAILED_NEEDS_RECONCILIATION` | 不自动重试可能已部分写库的未知状态 |
| FAILED 且显式 `retry_failed=True` | `CLAIMED`、attempt+1、新 token | **调用方必须先独立对账**；本轮只提供安全显式分支 |
| 已 PROCESSING 但租约过期 | `BLOCKED_EXPIRED_LEASE` | 不自动抢占；真实业务 Worker 提交需要进一步围栏 |
| 错误/过期 lease_owner 尝试 FAIL/COMPLETE | `BLOCKED:STALE_OR_WRONG_OWNER` | 归属检查 |
| 运行中 token 对应 `mark_completed` | DB 状态 `COMPLETED`，需要 64 位 reconciliation SHA | **仅提供存储接口**，真正 OMOP Reconciliation 证明来源还没接上，绝不允许 Airflow 现在自动调用 |

> **重要边界**：过期 Lease 不代表旧 Worker 已停止；**自动超时抢占、Heartbeat 更新、真实 PG 并行竞态执行、未知 COMMIT 恢复仍需后续开发**。本阶段的并发保证来自 PostgreSQL 原子 UPSERT + 行锁结构及单元合同，*并未*做双 Pod 并发的真实压测，因此不能声称完整恢复闭环。

## 3. GitHub Actions 三轮真实执行（遵守最多三次验证）

| Run | 结论 | 事实 |
|---|---|---|
| [38468700627](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38468700627) | FAIL | 离线 fake cursor 漏了 `insert_rowcount`；没有任何数据库修改。 |
| [38468796733](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38468796733) | 部分成功后 FAIL | 12 个测试 PASS、**新增 `etl.landing_batch_ledger` DDL 已 COMMIT**、`landing_claim_worker` 专用账号及 Secret 已建立、最低权限 readback PASS；真实 Pod 第一步检查对无权限的 `cdm` schema 做 `has_table_privilege` 时被 PG 拒绝（恰说明新用户缺乏 CDM USAGE）。修正为核查 `has_schema_privilege`，没有放宽数据库授权。该轮外部 Probe 未插入业务数据。 |
| **[38468961485](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38468961485)** | **SUCCESS** | 12 Tests PASS；复核新 Ledger 12 个必需列、role/secret 权限；worker02 真实 K8s Pod 用独立账号连接 `omop`，执行首次领取/忙碌/身份漂移/失败/显式重试/旧 token 防护/完成跳过/过期租约阻止，**整体 ROLLBACK**；独立 PG readback 0 探针行，历史 Person=136、Visit=9391 保持不变。 |

最终 PASS 标志：

```text
LANDING_CLAIM_UNIT_TESTS=PASS
LANDING_LEDGER_SCHEMA_REUSE_AFTER_INITIAL_COMMIT=PASS
CLAIM_SCOPED_PRIVILEGES=PASS
REAL_PG_ATOMIC_CLAIM_TRANSITIONS=PASS
REAL_PG_IMMUTABLE_IDENTITY=PASS
REAL_PG_OWNER_FENCING=PASS
REAL_PG_FAILED_EXPLICIT_RETRY=PASS
REAL_PG_EXPIRED_LEASE_BLOCK=PASS
REAL_PG_LEAST_PRIVILEGE=PASS
REAL_PG_ROLLBACK_NO_PROBES=PASS
LANDING_CLAIM_REAL_POSTGRES_ROLLBACK=PASS
LANDING_CLAIM_INDEPENDENT_READBACK=PASS
OMOP_BUSINESS_MUTATION=NO
```

成功运行测试的 Healthcare 精确源码 SHA `cd5f19b8f59c352cb3956ede47b62e23c088b3db`，Self-Runner 精确工作流 SHA `651401cf8584528c81db9b0b915326cdd7d499a9`。两边需合并 Main 后再核对新 Main SHA；源码只增加 docs 则不改变已运行的 Python/SQL。

## 4. 数据库变更明细与未完成部分

- **持久修改**：仅新表 `etl.landing_batch_ledger`、受限账号 `landing_claim_worker` 和对应 `dw-spark/landing-claim-db` Secret。Secret 不存入 Git，不在日志显示。
- **所有模拟 Claim DML 都 ROLLBACK**；新 Ledger 里探针行数=0。实际 S3 数据、历史 `etl.task004_*` 表和 `cdm.*` 未变。
- **Airflow**：`landing_batch_discovery` 仍然是单任务、每 15 分钟只读扫描，**没有**领取真实数据。因此定时发现可继续运行，不会意外把那 6 个历史批次作为新写库任务。
- **未做**：把 XCom Preview 变为可领用的全量批次队列、API/CLI 生产运行接口、Heartbeat 和租约回收 / 真实并发故障模拟、Claim 后 Spark/DB 对账、受验证的 `COMPLETED` 证明接入。特别是 `mark_completed` 当前只检查 digest 形状，**不是对数据库的独立验证**，不能当成真实 CDM 事务完整确认。

## 5. 当前下一步（下一独立有界闭环）

**Landing Consumer Integration**：在保留旧 `landing_batch_discovery` 只读 DAG 的前提下，将 Discovery 的完整候选结果按固定 Manifest 身份交给**受控、可暂停**的 Consumer Claim 任务；先测试与真实数据库 `etl.landing_batch_ledger` 的 state readback，并且不要自动 CLAIM/处理历史已经入库的 6 个 Batch。需要实现历史 Ledger 兼容性 / 旧批次排除安全门槛，之后再按明确授权接 Spark Person/Visit；再后是 Dynamic Writer COMMIT、DB Reconciliation 与 Replay。

**当前状态：DISCOVERY=PASS；POSTGRES_CLAIM_SCHEMA+SCOPED_ROLE+STATE_MACHINE_ROLLBACK=PASS；AUTOMATED_CLAIM_CONSUMER=NOT_IMPLEMENTED；REAL_READY_BATCH_COMMIT=NOT_IMPLEMENTED；TASK004 IN PROGRESS；TASK005 ON HOLD。**
