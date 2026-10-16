# Healthcare Data Platform — 文档新入口

> **状态：ACTIVE（新文档治理入口）** · 2026-10-16 · **阶段：Pre-OpenSpec Documentation Rebuild**
>
> 本目录逐步建立经代码、Contract、真实验收核实的项目知识。**目前并非所有模块都已迁入**，不能把这里暂缺的文档理解为功能不存在或已经通过验收。

## Agent 必读入口

1. [AI/Agent 开发与安全规则](development/AGENT-RULES.md) — 当前通用 AI 操作约束。
2. [开发工作流](development/DEVELOPMENT-WORKFLOW.md) — 当前 Healthcare / Self-Runner、STEP/PR/SHA/执行/交接流程。
3. **[组件与代码命名规范](development/CODE-ORGANIZATION-AND-NAMING.md)** — 新代码不能用 Task/Step 命名；Legacy 按功能逐步迁移。
4. [测试与验收](development/TESTING-AND-EVIDENCE.md) — 分级验证、独立读回与证据格式。
5. [文档治理与渐进迁移规则](development/DOCUMENTATION-GOVERNANCE.md) — 当前文档的唯一权威、证据、冲突、迁移门槛。
6. [多 Session 协调规则](development/SESSION-COORDINATION.md) — 并行 PR、共享资源、人为授权、接力验证；不另建 Handoff 日志。
7. [迁移进度与顺序](migration/MIGRATION-STATUS.md) — 明确哪些模块迁移完毕、哪些仍依赖旧资料。

## 长期运维与架构决策（STEP07 已审核）

- [Operations Index](operations/README.md) — 有效运维知识入口和仍需按需查阅的旧技术经验。
- [Safe Operations](operations/SAFE-OPERATIONS.md) — 共享 K8s/Spark/Airflow/PG/S3/Azure 操作的安全门槛。
- [Architecture Decisions](decisions/README.md) — 已批准的重要架构路线和代替旧方案的原因。
- [OpenSpec 迁移准备与 STEP08/09 Gate](migration/OPENSPEC-READINESS.md) — 只准备，不初始化；旧未合并 PR #164 需先纠正权威来源。

## Portal 与 Azure/Fabric 专项组件（STEP06 已审核）

- [Platform Portal：Marquez / OpenLineage](components/platform-portal/README.md) — 部署与 A3/A4 历史验收、Spark Job↔Run/Dataset 未完成和待讨论接入方案。
- [Azure/Fabric：OMOP → Azure Blob → Fabric Pipeline/Notebook → OneLake](components/azure-fabric/README.md) — OneLake-first 方案、Terraform Plan-only 证据、未完成的导出/业务装载边界。

## Local Pipeline 组件（STEP05 已审核）

- [组件目录与职责](components/README.md) — Synthea、Landing、Airflow、Spark、OMOP 五个可长期维护的业务模块。
- [Legacy Task-named 代码重构计划](components/LEGACY-CODE-REFACTOR-PLAN.md) — 旧 `task004` 依赖、兼容门槛、逐阶段源码迁移计划（尚未实际 Rename）。

## 当前项目状态（STEP04 已审核）

- **[PROJECT-STATUS.md](status/PROJECT-STATUS.md)** — 项目唯一 CURRENT/NEXT：TASK004 Closed、TASK005 只读预检、Portal Spark 方案讨论中、Azure OneLake-first 的 Terraform PLAN-ONLY 与未落地范围。

## 当前整体架构（STEP03 已审核）

- [总体系统架构](architecture/SYSTEM-OVERVIEW.md) — 本地 Synthea/OMOP、Portal OpenLineage/Marquez、Azure OneLake-first 目标和验收边界。
- [数据流架构](architecture/DATA-FLOW.md) — 本地真实 E2E、Portal 观测事件、PG → Azure Blob → Fabric Pipeline → Notebook → OneLake 的目标流。
- [基础设施架构](architecture/INFRASTRUCTURE.md) — K8s Nodes/Namespaces/PG14 与 PG17、Marquez、Fabric Terraform 模块及已验证 Plan。

**最小读取策略**：先读本页和必要规则，再按任务读取有关代码、Contract、测试、部署配置及证据；避免一次性加载旧 `docs/` 全量 Markdown。

## 两套目录的过渡边界

| 位置 | 当前职责 |
| --- | --- |
| `documents/` | 新治理规范及**已完成审核并在迁移表标记为 ACTIVE 的**架构、模块和运维知识 |
| [`docs/`](../docs/README.md) | Legacy：旧架构、状态、Runbook、Task 计划、已验收证据的迁移来源；未迁移领域仍须按需查阅 |
| [`contracts/`](../contracts/README.md) | 具体行为合同和数据 Schema 等以当前 Git 源码与有效 Contract 为准，不因文档搬迁而改写 |
| `openspec/`（未来） | **当前 Main 尚未初始化**；未来用 Specs / Changes 管可验证行为与开发接力，不代替 `documents/` 的架构/运维、GitHub PR 或 Runtime 锁 |

旧 `docs/` 存在互相矛盾的日期快照；不得仅按文件名中的 CURRENT 或文件创建日期认定事实。对代码/运行状态的陈述必须标明 **Source SHA 与对应验收证据**。有不一致时先记录，停止未经核实的权威切换。

## 已知项目基线（迁移上下文，不是新一轮实时探针）

- [仓库根 README](../README.md) 描述已验收的本地 Synthea → S3 Landing → Airflow → Spark Person/Visit → PostgreSQL OMOP 路径。
- TASK004 NEW_ONLY Person/Visit 实际 E2E 和同批次 SKIP 有[最终验收证据](../docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md)；该结论不代表其他数据域或所有并发/恢复场景已验收。
- [Condition TASK005](../docs/tasks/TASK-005-CONDITION-DEVELOPMENT-PLAN-v1.0.zh-CN.md) 处于可做 STEP00 只读预检、尚未完成业务入库的状态；开发前再次核对最新 Main 和授权。
- Portal 已使用原生 Marquez Web + OpenLineage，**Airflow 事件已证实**、Spark 独立 Smoke 部分成功，但 Dataset 全链路尚未验收；Azure/Fabric 则采用 **PG → Azure Blob → Fabric Pipeline → Notebook → OneLake Lakehouse** 的简化目标，目前仅三组件 Terraform Plan 验证成功，不得误报部署与业务 E2E。

## 为什么不直接重写全部文档？

我们采取 **逐领域分析 → 核对源码/运行证据 → 消除矛盾 → 新建简洁文档 → 审核切换权威** 的方式。现有历史证据不批量覆盖，不修改 `docs/` 正文来伪造一致性。

迁移完成后：`documents/` 管理实际架构、开发方法、运维知识及证据索引；引入 OpenSpec 后，由 `openspec/specs/` 管理可验证行为要求，`openspec/changes/` 管理后续设计/功能变更；避免两套内容重复成为权威。
