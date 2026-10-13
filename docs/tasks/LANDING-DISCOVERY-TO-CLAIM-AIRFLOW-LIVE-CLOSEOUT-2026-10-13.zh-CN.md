# Landing Discovery → PostgreSQL Claim Guard — Airflow 真正两任务连接验收（2026-10-13）

> **验收：SUCCESS（安全接线模式）。** Airflow 原有定时 DAG `landing_batch_discovery` 现在有**两个连续 KPO 任务**：`scan_ready_manifests` → `evaluate_batch_claims`。真正 Airflow 3 GitSync、DagBag、DagRun / 两个 TaskInstance 均 PASS。下游 Claim 组件已用专用 DB 权限读取真实 PostgreSQL Ledger、校验历史记录排除策略；**本阶段实际 Claim 写入开关保持关闭**，只评估批次而不持久领取或调用 Spark。已验证 PostgreSQL Ledger 0 行、OMOP Person=136、Visit=9391 不变。**不能将本阶段描述成“自动 Spark 消费已开启 / 动态 DB Writer COMMIT 已完成”。**

## 1. 本轮新增业务组件 / 安全边界

- `airflow/dags/landing_batch_discovery.py`：原 DAG ID 与 `*/15` 周期保持不变，追加 `evaluate_batch_claims` **KubernetesPodOperator**；上下游用 **Airflow XCom** 传 `status=READ_ONLY_DISCOVERED`、固定 `batch_id`、`manifest_uri`、`manifest_sha256`，**不调用 Synthea**。两个 Task 均成功后，DAG Run SUCCESS。
- `apps/landing_claim/claim_discovered_inventory.py`：接入既有 `apps/landing_claim/batch_ledger.py` 原子领取接口；解析 XCom/检查 READY、禁止 truncated 25-item inventory、重复身份与伪造状态；对每个 Candidate 检查**历史旧 ledger** `etl.task004_batch_ledger` 以及新 `etl.landing_batch_ledger`，历史已有记录 = `SKIP_LEGACY_BATCH`，已 COMPELETED = `SKIP_COMPLETED`，FAILED/PROCESSING 有保守状态、Manifest SHA/URI 不一致拒绝。真正允许领取之前，必须重新 GET S3 Manifest bytes 并复核 SHA256。
- 独立非 root 镜像：`ghcr.io/johnzhang-dataforge/healthcare-landing-claim@sha256:cdc9666b0834d0af88cc60ce4b5da4f5b5161b09c12886e95f80342a1fcd5eea`；真正 [Build Run 38470295463](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/38470295463) SUCCESS。
- `dw-spark/landing-claim-db`（已有 Secret）供 claim KPO 连接 `omop` 的 `landing_claim_worker` 专属受限账号；本轮**只新增了旧表 `etl.task004_batch_ledger` 的 SELECT 授权**，没有新增该表写入、CDM Schema 或 CDM Person/Visit 写入权限。
- **当前部署门槛：** `CLAIM_ENABLE=NO`、`CLAIM_ALLOWLIST=""`，所以真实 Airflow Task 只做 SQL SELECT、历史/重复状态判定，不对任何实际 6 个 S3 READY Batch 进行持久 Claim。**这是必须的**：因为下游 Spark/PG COMMIT 尚未连接，提前 Claim 会让 Ledger 留下过期 `PROCESSING` 租约；并且当前 6 个历史 Batch 不能自动假定为全新未入库数据。
- 已完成的较早 `apps/landing_claim/batch_ledger.py` 原子 `claim()` 在 [前阶段真实 PG ROLLBACK](LANDING-BATCH-CLAIM-ROLLBACK-CLOSEOUT-2026-10-13.zh-CN.md) 验证；本阶段的 *active claim* 代码路径可受控开启，但**没有放行生产 Claim**。
- Airflow XCom 当前只传**最多 25 个候选**，超过时 `preview_truncated=true`，下游将 FAIL CLOSED；不能静默忽略后续 Batch。解除此容量限制前，需要分页/持久队列设计，而不是粗暴打开 Claim。
- 旧 `task004_processing_pipeline` 保留且未修改；不可把它重新用作正式 Generator 入口。

## 2. GitHub PR 与 Run 实证

| 阶段 | Run / PR | 结果 |
|---|---|---|
| 构建独立 Claim Runtime | [Healthcare Run 38470295463](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/38470295463) | SUCCESS，20 个 claim-suite 测试 PASS、GHCR 推送与不可变 digest |
| 接线完整代码 | [Healthcare PR #77](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/77) | **MERGED**，Main `fe1a21762d7dc41c9b6505166da045b56f610fe2` |
| Premerge 工具首轮 | [Self-Runner 38470705470](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38470705470) | FAIL：Airflow 3 KPO 将 `env_vars` dict 转成 `V1EnvVar` 对象列表；测试器改为解析列表 |
| Premerge 工具第二轮 | [Self-Runner 38470785061](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38470785061) | FAIL：Shell heredoc 在 runner 本机提前展开 `$(cat /input/preview.json)`；改成转义后由容器解析 |
| **真实受限 PG / K8s 分类** | **[Self-Runner 38470907298](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38470907298)** | **SUCCESS**：Airflow 3 DagBag 双 Task 依赖 PASS；授予最小 Legacy SELECT；worker02 限权 Pod 检查 1 个真正历史 Batch + 1 个未授权模拟 Candidate，分类为历史排除/未授权观察、`CLAIMED_BATCHES=0`；独立 readback Ledger=0、Person=136、Visit=9391 |
| 真实 Main GitSync + 真实两 Task | **[Self-Runner 38471287896](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38471287896)** | **SUCCESS**：Main GitSync exact SHA PASS、Scheduler DagBag Parse PASS、真正 Airflow DAG Run=`success`、`scan_ready_manifests=success`、`evaluate_batch_claims=success`、最后新 Ledger=0、Person=136、Visit=9391，`CLAIM_ENABLE=NO` |
| Runner 生产证据 | [Self-Runner PR #74](https://github.com/JohnZhang-DataForge/Self-Runner/pull/74)、[#75](https://github.com/JohnZhang-DataForge/Self-Runner/pull/75) | **MERGED**；Premerge 和 Postmerge 两阶段工作流均保留 GitHub 历史 |

Postmerge 首轮 [Run 38471247826](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38471247826) 也 SUCCESS，但验证脚本漏了 `kubectl exec -i`，导致一段 stdin DagBag 断言实际未运行；第二轮 Run 38471287896 修复并输出 `AIRFLOW_CLAIM_CHAIN_PARSE=PASS`，以第二轮作为**最终权威实证**。

最终关键输出：

```text
AIRFLOW_CLAIM_GITSYNC_EXACT_MAIN=PASS
AIRFLOW_CLAIM_CHAIN_PARSE=PASS
AIRFLOW_DISCOVERY_CLAIM_DAGRUN=success
TASK_SCAN_READY_MANIFESTS=success
TASK_EVALUATE_BATCH_CLAIMS=success
AIRFLOW_DISCOVERY_TO_CLAIM_REAL_DAGRUN=PASS
DISCOVERY_TO_CLAIM_REAL_POSTGRES_ZERO_WRITES=PASS
LEDGER_ROWS=0
PERSON_ROWS=136
VISIT_ROWS=9391
```

## 3. 下一开发闭环 / 禁止误判

**下一步是受控 `Landing Batch Consumer → Spark Person/Visit`，不是重复写 S3 Discovery/Claim 基础组件。**

1. 在自动 CLAIM 启用前，扩展完整 Manifest 不受 25 XCom Preview 限制的、具幂等持久化的队列/分页方案（或暂时清晰地对超限 Fail Closed）；增加已入库历史 Source IDs 的检查和 S3 CSV 完整字节读取/校验，防止把旧批当作新 Person。
2. 先构建消费侧 **单个授权的全新 Manifest** → 独占 Claim → Spark Person/Visit → Processing Reconciliation → 动态 PostgreSQL Writer 的安全事务方案。**不能无差别放开所有 READY Batch 的 Claim**。
3. 加入 Lease heartbeat / 未知数据库 COMMIT 的对账、失败/租约超时恢复、完整 DB Reconciliation 验收，再在安全路径明确之后启用真实 Claim。前面 `mark_completed` 只有形状校验 digest，**不是独立的 CDM readback 证明**。
4. 需要实际新患者、不会和已经入库 Source ID 发生冲突的 S3 Batch 才能真正执行初次 PostgreSQL Dynamic COMMIT。Generator NEW_ONLY 与消费者仍按完全解耦模式单独推进。

**状态：S3 DISCOVERY=PASS；AIRFLOW 2-KPO DISCOVERY→PG CLAIM GUARD=LIVE PASS；ACTUAL READY CLAIM=DISABLED / NOT YET VERIFIED；SPARK AUTOMATIC CONSUMPTION=NOT IMPLEMENTED；DYNAMIC PG COMMIT=NOT IMPLEMENTED；TASK004 IN PROGRESS；TASK005 ON HOLD。**
