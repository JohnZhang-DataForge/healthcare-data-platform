---
status: active
scope: documentation-final-authority-audit
last_verified: 2026-10-16
source_sha: f5ee37697bed08fc35e288d84420bafd4b2d8e22
---

# STEP08 — 最终文档权威终审

> **终审对象**：Healthcare Main `f5ee37697bed08fc35e288d84420bafd4b2d8e22`，与 STEP08 PR [#174](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/174) 的导航/历史入口最小变更。范围仅是**文件和历史证据静态审查**；不是实时 Kubernetes/PG/S3/Azure 或 OpenSpec CLI 健康验证。此报告在 PR #174 合并后成为完成记录。

**终审后整理（已完成）**：按用户指示，原 `docs/` 已在后续独立 PR 中从 Main 清理；历史源固定在 [Git Commit `49936b51d4beadc69383e931efc3e72d2f0db47e`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/tree/49936b51d4beadc69383e931efc3e72d2f0db47e/docs)，原有验收/失败记录可追溯。详见 [快照清单](LEGACY-DOCS-SNAPSHOT.md)。这属于 STEP08 的后续 housekeeping，不改变终审时的证据结论。

## 核验范围与检查结果

| 审查项 | 结果（含边界） |
| --- | --- |
| Main 文件清点 | **671 个 blob、157 个 `.md`、其中 25 个 `documents/` Markdown**（变更前基线） |
| 新 `documents/` 相对链接 | **25/25 文件、249 条相对链接、0 个缺失路径**（变更前基线；另做 PR diff 与合并后检查） |
| Markdown/源码身份 | [当前项目状态](../status/PROJECT-STATUS.md) 明确只按指定验收范围计 PASS，不把旧日期快照当实时 Running |
| 独立状态权威 | Agent 入口为 [AGENTS.md](../../../AGENTS.md) → [documents](../../README.md) → [PROJECT-STATUS](../status/PROJECT-STATUS.md)；所有 Legacy CURRENT/NEXT 已降为历史 |
| 组件与开发边界 | [组件地图](../../systems/data-platform/README.md)、[新代码命名](../development/CODE-ORGANIZATION-AND-NAMING.md)、[Session Coordination](../development/SESSION-COORDINATION.md) 已生效；历史 Task 命名代码未迁移 |
| 过时入口清理 | 仅添加安全醒目的**历史提示和优先级链接**，不删除旧 Closeout/失败记录，也不把旧仓库归档复制回来 |
| OpenSpec / Archive | 本轮基线 Main 无 `openspec/`、无 `docs/archive/`；旧独立 Private Healthcare-Specs/archive 不被迁回 |
| Runtime | 未修改应用代码、业务 DAG/Writer、Azure Terraform、Self-Runner Workflow、K8s/PG/S3/Blob；没有重新执行 E2E 或 Apply |

**终审分支增量复核**：更新后的 `documents/` 已有 **26 份 Markdown、277 条仓库内相对链接，0 个断链，0 个未闭合代码 Fence**；根 `README.md` 加上七个明确降级的 Legacy 门户文件共 **8 个入口、229 条相对链接、0 个断链，0 个未闭合 Fence**。两组检查合计 **506 条相对链接**。全部为 STEP08 PR [#174](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/174) 当时的 Git Tree 静态核对，不代表当前 Main 的文档和链接总数。

**审计注意**：249 条是新 `documents/` 内的**仓库相对链接路径存在性检查**，不是外部网址访问验证、Markdown 标题 Fragment 校验、网站链接可用性测试或全部 111 份 Legacy 文档的完整链接修复。Legacy 历史原样保留，个别旧链接可能随历史演进失效，使用前按当前树与源代码核实。

## 唯一权威表（新 Agent 必须遵循）

| 领域 | 唯一现行入口 | 历史资料的处理 |
| --- | --- | --- |
| AI 开发/安全/命名 | [AGENTS.md](../../../AGENTS.md)、[Agent Rules](../development/AGENT-RULES.md)、[Code Naming](../development/CODE-ORGANIZATION-AND-NAMING.md) | `docs/skill/SKILL-cn.md`、旧开发 Operations 不再决定 CURRENT |
| CURRENT/NEXT | [PROJECT-STATUS](../status/PROJECT-STATUS.md) | `docs/tasks/TASK-STATUS.md` 是日期化事件和里程碑审计记录 |
| 架构/数据流 | [System Overview](../../architecture/SYSTEM-OVERVIEW.md)、[Data Flow](../../architecture/DATA-FLOW.md) | 旧 V4 和 Warehouse-first 为历史设计 |
| 本地/Portal/Azure 组件 | [Components](../../systems/data-platform/README.md) | 旧 `docs/platform-portal/`、`docs/azure-fabric/` 继续作为具体实测和历史 |
| 安全操作与并行 Session | [Operations](../operations/README.md)、[Session Coordination](../development/SESSION-COORDINATION.md) | 旧 Runbook/协调规则仅历史技术参考，不能从 2026-10-13 HOLD 推断今天的运行状态 |
| 重要技术决策 | [Architecture Decisions](../../architecture/decisions/README.md) | 不建立按 Session 膨胀的 ADR/Handoff |
| 需求变更和接力（即将采用） | [OpenSpec Readiness](OPENSPEC-READINESS.md)；正式初始化后才有 `openspec/` | 旧未合并 [PR #164](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/164) 不是当前规范 |

## 开发可恢复性确认

- **已验收**：TASK004 NEW_ONLY Person/Visit + Writer + PG 独立读回 + 完成 Batch SKIP，以 [最终 E2E Closeout](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md) 为事实依据。
- **下一业务任务**：Condition STEP00 只读预检已具备启动条件；业务实现/数据库写入尚未授权。
- **Portal**：Marquez/Airflow A3 已有验收，A4 隔离 Spark Smoke 部分通过；真实业务 Spark Job/Run/Dataset 接入方案仍在讨论。
- **Azure**：PG→Azure Blob→Fabric Pipeline/Notebook→OneLake 方案已经确定，Terraform/Runner 与三个 Item Plan PASS，但尚未 Apply，也没有真实数据 E2E。
- **旧 Task-named 运行代码**：不是本次重构范围；所有新正式代码按组件/能力命名，不批量改 Writer Image、DAG ID 或旧 `etl.task004_*` 数据库对象。

## 从这里怎样开始 STEP09

- 读 [OpenSpec Readiness](OPENSPEC-READINESS.md)，从**当时最新 Main** 处理旧 PR #164 过时的 `docs/` 配置入口。
- 验证实际 OpenSpec CLI 版本/配置 Schema；创建最少量 `openspec/specs/` 和 `changes/`；不从历史报告中推断已有新功能。
- 首批 Baseline 以**已验收本地 NEW_ONLY 行为**为主；Portal 和 Azure 未实现部分使用后续 Proposed Change，不能假装已部署。
- 选择一个小型已批准功能 Change，利用 PR/SHA/Run 验证从新 Session 接力的完整流程；运行资源授权依旧受独立安全规则约束。

**验收结论（PR #174 合并生效）：STEP01–08 的文档权威与迁移整理可以关闭。STEP09 OpenSpec 仍是下一项真实实施工作，不是已完成步骤。**
