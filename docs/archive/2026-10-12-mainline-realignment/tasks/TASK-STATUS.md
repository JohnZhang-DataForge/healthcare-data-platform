# Healthcare Data Platform — 当前 TASK 状态与下一步（2026-10-12）

> **CURRENT STATUS / Agent 权威入口**。状态依据已合并的 TASK Closeout 和 Self-Runner V8/V9 真实运行证据；本文件不代表所有 Kubernetes 资源、数据库状态已经在今天重新探测。**不得将未来计划当成 PASS。**

## 已验证 / 下一步

| 范围 | 已验证结果 | 当前动作 |
|---|---|---|
| TASK001 | 历史冻结的 Landing / batch 基线 | 不重跑、不改冻结文件 |
| TASK002 | Person V2 历史回归与冻结基线 | 不擅自修改 |
| TASK003 | **COMPLETE / CLOSED**：Canonical Encounter → Raw → Processed Visit → ID mapping → OMOP CDM | 只读参考实现；正式结果见 `TASK-003-FINAL-CLOSEOUT.md` |
| TASK004 — Synthea | PASS：Kubernetes Generator + Landing + manifest | 已验收，按 Contract 复用 |
| TASK004 — Resolver/Control | PASS：Lineage resolver、control runtime image | 已验收 |
| TASK004 — Person | PASS：Standalone Spark Patient Processing | 已验收 |
| TASK004 — Visit | PASS：Standalone Spark Encounter Processing；2459 行 | 已验收；V8 真实 Actions Run `38250467965` |
| TASK004 — Batch Reconciliation | **PASS**：20 Patient / 2459 Encounter / 0 orphan | 已验收；`TASK-004-BATCH-RECONCILIATION-CLOSEOUT.md` |
| **TASK004 — Airflow orchestration** | **NOT YET VERIFIED** | **NEXT：编排已验收的 Person/Visit/Recon，实际 DAG Run + 状态/数据核验** |
| Azure/Fabric/dbt/MLflow 等 | 后续分阶段设计，未因本表自动验收 | 不阻塞当前 Batch MVP |

### TASK004 最新权威证据

- Synthea：`v3.3.0`；Batch `task004-p20-first-landing-20261011`；Ingest Date `2026-10-11`。
- V8 Visit：Self-Runner Actions Run `38250467965`，Processing Encounter `2459`，不写 PostgreSQL。
- V9 Batch Reconciliation：Healthcare PR **#16**，合并前准确 HEAD `d1f97ecdf864048ff142fd878b6cd5eb72cf5cd6`，Run `38251984921` PASS。
- V9 合并后：Healthcare main 绑定 `32a72b2941979fcb20b6d6fd0953b7a87760cdc7`，Run `38252497171` PASS；20 Patient / 2459 Encounter / 0 orphan，Processing/PostgreSQL Mutation=NO。
- 负测：Run `38251924029` 预期 Policy FAIL，ARC 业务执行 SKIPPED。
- 本文引用的 SHA 是**对应验收时的版本**，不是当前 main HEAD；开发前必须重新读取 GitHub 最新状态。

## 下一位 Agent 如何开始（最短路径）

1. 阅读 `../README.md`、`../development/PLATFORM-DEVELOPMENT-OPERATIONS-v1.0.zh-CN.md`、`../skill/SKILL-cn.md`、`../runbooks/development-lessons-cn.md`。
2. 阅读 `TASK-004-BATCH-RECONCILIATION-CLOSEOUT.md`、`TASK-004-PHASE9-CLOSEOUT.md`，以及 TASK004 当前源码、Contracts、Shell、Airflow DAG 和镜像定义；读取 Self-Runner V9 的 Workflow/Request/Checkpoint。
3. **只读核对** Healthcare 和 Self-Runner 当前 main、分支、未合并 PR、Kubernetes/Airflow 实际状态；本表不替代运行态检查。
4. 为 TASK004 Airflow orchestration 定义**一个有界 STEP**：DAG 调度/参数、依赖、ServiceAccount、Spark 状态与数据验证；保留已冻结 Person/Visit/Recon 的权威业务逻辑，不重新开发已 PASS 的阶段。
5. 按正式双仓库流程：Healthcare feature PR → Self-Runner 手工绑定准确 PR/SHA → 固定 Workflow / 必要最小适配 → PASS/FAIL 证据 → Merge → Checkpoint。
6. **不要**因为旧 `docs/archive/` 中的 `NOT_DEPLOYED`、`Visit NEXT` 或旧 Runner Pilot 重新开启已经完成的工作。

## 冻结与安全

- 不修改已冻结的 TASK001–TASK003 源码、Contract、Generator、已批准数据或 ID mapping；TASK004 已验收步骤亦不得无依据重写。
- 不盲目重试不确定的数据库 COMMIT；严格区分 Run ID 与 Batch ID；所有持久数据写入需定义幂等、Reconciliation 和边界。
- 文档状态更新走 PR；历史 Checkpoint/Closeout 的“当时状态”不被追溯性重写。

## 相关文档

- `TASK-003-FINAL-CLOSEOUT.md`：TASK003 最终闭环。
- `TASK-004-PHASE9-CLOSEOUT.md`：Control runtime image。
- `TASK-004-BATCH-RECONCILIATION-CLOSEOUT.md`：当前 TASK004 最新验收。
- `../architecture/Healthcare-Data-Platform-Architecture-and-Implementation.v4.zh-CN.md`：总架构设计（设计状态以本状态索引和真实运行证据为准）。
- `../architecture/Healthcare-ETL-Hybrid-Fabric-ML-Design.zh-CN.v2.1.md`：未来 Azure/Fabric/ML 详细设计参考，非已完成证明。
