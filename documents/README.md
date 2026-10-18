# Healthcare Data Platform — 文档新入口

> **状态：ACTIVE（经终审的项目文档权威入口）** · 2026-10-16 · **STEP01–STEP08 COMPLETE（PR #174 合并后）**；OpenSpec STEP09 尚未开始。
>
> 本目录已经完成本轮 STEP01–08 对本地 Pipeline、Portal、Azure/Fabric、项目状态、开发规则、运维与决策的终审核对。**历史证据和未实施的新能力仍由对应源码/验收与未来 OpenSpec Change 管理**；文档目录中没有某项能力，不意味着它已经验收或不存在。

## 当前文档目录（Data Platform / Engineering 已切换）

- [Architecture](architecture/SYSTEM-OVERVIEW.md)：全局系统架构、数据流、基础设施和 Architecture Decisions。
- [架构设计讨论稿](architecture/design/README.md)：[V2 多来源 Fabric 与双 Portal 展示路线](architecture/design/HEALTHCARE-V2-MULTISOURCE-FABRIC-ROADMAP-DESIGN.md)、Data Platform V2 源码迁移与 [OpenSpec 接入设计](architecture/design/OPENSPEC-ADOPTION-DESIGN.md)（均为中文 Draft，尚未实施）。
- [Systems](systems/README.md)：Data Platform 本地五组件及源码导航；Azure/Fabric 已有 `systems/azure-fabric/` 说明，Portal 当前仍引用 `components/platform-portal/`。
- [Engineering](engineering/README.md)：开发规范、Agent 规则、测试、运维、迁移与项目状态。

**迁移结果**：本地 Data Platform 与 Engineering 已采用新的 `systems/`、`engineering/` 目录，CODE.md 源码地图和 Markdown 链接均有独立 CI。旧的本地组件及工程文档副本已按可追溯 Git 历史方式清理；**Azure/Fabric 的新系统说明已位于 `systems/azure-fabric/`，旧 `components/azure-fabric/` 文档尚保留；Portal 当前仍使用 `components/platform-portal/`。不在本次 OpenSpec 方案修改中清理这些历史页面**。

## Agent 开工入口

**先读 [AGENTS.md](../AGENTS.md)、[Agent 规则](engineering/development/AGENT-RULES.md) 和 [当前项目状态](engineering/status/PROJECT-STATUS.md)。** 根目录 `AGENTS.md` 是唯一按任务分流入口：它会根据代码开发、测试、文档或共享环境操作指向必要的详细规范。不要每次通读全部工程文档，也不在本目录维护第二套任务分类表。

当前采用 **直接维护 Git 正式源码 + Self-Runner / GitHub Actions 受控验证** 的开发模式。具体实施参见 [Development Workflow](engineering/development/DEVELOPMENT-WORKFLOW.md)；需要真实 Runtime 操作时必须遵守 [Safe Operations](engineering/operations/SAFE-OPERATIONS.md)。旧 Skill 和零散排障经验只保留在 [历史 Git 快照](engineering/migration/LEGACY-DOCS-SNAPSHOT.md)，不作为现行开发流程。

## 最终文档终审与 OpenSpec 下一步（STEP08）

- **[Final Authority Audit](engineering/migration/FINAL-DOCUMENTATION-AUDIT.md)** — STEP08 当时的 25 份文档链接审计（历史统计，并非现行 `documents/` 文档总数）、旧入口权威纠偏及后续边界。
- [OpenSpec G0–G7 正式实施计划](engineering/migration/OPENSPEC-IMPLEMENTATION-PLAN.md) — STEP09 的唯一阶段定义、命名 CI、首个 Change 及迁移验收门槛；[Readiness](engineering/migration/OPENSPEC-READINESS.md) 为开工检查。**计划已确定，`openspec/` 尚未初始化。**

## 长期运维与架构决策（STEP07 已审核）

- [Operations Index](engineering/operations/README.md) — 有效运维知识入口和仍需按需查阅的旧技术经验。
- [Safe Operations](engineering/operations/SAFE-OPERATIONS.md) — 共享 K8s/Spark/Airflow/PG/S3/Azure 操作的安全门槛。
- [Architecture Decisions](architecture/decisions/README.md) — 已批准的重要架构路线和代替旧方案的原因。
- [OpenSpec 迁移准备与 STEP08/09 Gate](engineering/migration/OPENSPEC-READINESS.md) — 旧 PR #164 已于 2026-10-17 关闭、未合并；[接入设计稿](architecture/design/OPENSPEC-ADOPTION-DESIGN.md) 与 [G0–G7 执行计划](engineering/migration/OPENSPEC-IMPLEMENTATION-PLAN.md) 已对齐，尚未初始化。

## Azure/Fabric 与 Platform Portal（当前有效导航）

- [Platform Portal：Marquez / OpenLineage](components/platform-portal/README.md) — 部署与 A3/A4 历史验收、Spark Job↔Run/Dataset 未完成和待讨论接入方案。
- [Azure/Fabric：OMOP → Azure Blob → Fabric Pipeline/Notebook → OneLake](systems/azure-fabric/README.md) — OneLake-first 方案、Terraform Plan-only 证据、未完成的导出/业务装载边界。

## Systems — Data Platform（STEP05 已审核，目录已切换）

- [Data Platform 组件目录与职责](systems/data-platform/README.md) — Synthea、Landing、Airflow、Spark、OMOP 五个可长期维护的业务模块。
- [Legacy Task-named 代码重构计划](engineering/development/LEGACY-CODE-REFACTOR-PLAN.md) — 旧 `task004` 依赖、兼容门槛、逐阶段源码迁移计划（尚未实际 Rename）。

## 当前项目状态（STEP04 已审核）

- **[PROJECT-STATUS.md](engineering/status/PROJECT-STATUS.md)** — 项目唯一 CURRENT/NEXT：TASK004 Closed、TASK005 Condition 业务暂缓但保留只读预检准备、OpenSpec G0–G7 待实施、Portal Spark 讨论中、Azure OneLake-first Terraform PLAN-ONLY。

## 当前整体架构（STEP03 已审核）

- [总体系统架构](architecture/SYSTEM-OVERVIEW.md) — 本地 Synthea/OMOP、Portal OpenLineage/Marquez、Azure OneLake-first 目标和验收边界。
- [数据流架构](architecture/DATA-FLOW.md) — 本地真实 E2E、Portal 观测事件、PG → Azure Blob → Fabric Pipeline → Notebook → OneLake 的目标流。
- [基础设施架构](architecture/INFRASTRUCTURE.md) — K8s Nodes/Namespaces/PG14 与 PG17、Marquez、Fabric Terraform 模块及已验证 Plan。

**最小读取策略**：先读本页和必要规则，再按任务读取有关代码、Contract、测试、部署配置及证据；避免一次性加载旧 `docs/` 全量 Markdown。

## 历史文档已退出 Main

- **原 `docs/` 的 111 个文件已从 Main 清理**（删除 PR 合并后生效），不等于销毁验收材料：见 [Legacy Docs 固定历史快照](engineering/migration/LEGACY-DOCS-SNAPSHOT.md)。
- 本页以及组件文档中需要的历史验收、Portal Smoke、Azure Plan 记录，全部引用 **删除前 Commit `49936b51d4beadc69383e931efc3e72d2f0db47e`** 的不可变 GitHub 链接。新的 Agent 不得在 Main 中寻找旧 `docs/`，也不得把历史 NEXT 当作当前业务状态。

## 当前目录与历史来源的边界

| 位置 | 当前职责 |
| --- | --- |
| `documents/` | Architecture 管全局与决策；Systems 管子系统组件及源码导航；Engineering 管开发、运维、迁移与项目状态。新旧文档并存期间按迁移门槛逐步切换。 |
| [`docs/`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/README.md) | **仅 Git 历史快照**：旧架构、Task、Runbook、已验收证据，不存在于最新 Main；如需查阅可点开冻结链接 |
| [`contracts/`](../contracts/) · [Synthea CODE](systems/data-platform/synthea/CODE.md) · [OMOP CODE](systems/data-platform/omop/CODE.md) | 具体行为合同和数据 Schema 等以当前 Git 源码与有效 Contract 为准，不因文档搬迁而改写 |
| `openspec/`（未来） | **当前 Main 尚未初始化**；未来用 Specs / Changes 管可验证行为与开发接力，不代替 `documents/` 的架构/运维、GitHub PR 或 Runtime 锁 |

历史 `docs/` 快照存在互相矛盾的日期记录；不得仅按文件名中的 CURRENT 或文件创建日期认定事实。对代码/运行状态的陈述必须标明 **Source SHA 与对应验收证据**。有不一致时先记录，停止未经核实的权威切换。

## 已知项目基线（迁移上下文，不是新一轮实时探针）

- [仓库根 README](../README.md) 描述已验收的本地 Synthea → S3 Landing → Airflow → Spark Person/Visit → PostgreSQL OMOP 路径。
- TASK004 NEW_ONLY Person/Visit 实际 E2E 和同批次 SKIP 有[最终验收证据](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md)；该结论不代表其他数据域或所有并发/恢复场景已验收。
- [Condition TASK005](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-005-CONDITION-DEVELOPMENT-PLAN-v1.0.zh-CN.md) 处于可做 STEP00 只读预检、尚未完成业务入库的状态；开发前再次核对最新 Main 和授权。
- Portal 已使用原生 Marquez Web + OpenLineage，**Airflow 事件已证实**、Spark 独立 Smoke 部分成功，但 Dataset 全链路尚未验收；Azure/Fabric 则采用 **PG → Azure Blob → Fabric Pipeline → Notebook → OneLake Lakehouse** 的简化目标，目前仅三组件 Terraform Plan 验证成功，不得误报部署与业务 E2E。

## 为什么不直接重写全部文档？

我们采取 **逐领域分析 → 核对源码/运行证据 → 消除矛盾 → 新建简洁文档 → 审核切换权威** 的方式。现有历史证据不批量覆盖，不修改 `docs/` 正文来伪造一致性。

迁移完成后：`documents/` 管理实际架构、开发方法、运维知识及证据索引；引入 OpenSpec 后，由 `openspec/specs/` 管理可验证行为要求，`openspec/changes/` 管理后续设计/功能变更；避免两套内容重复成为权威。
