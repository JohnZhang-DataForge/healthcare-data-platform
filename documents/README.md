# Healthcare Data Platform — 文档新入口

> **2026-10-31 正式开发设计依据**：[Fabric Notebook + Pipeline + Environment + Shared Engine ADR](architecture/design/FABRIC-NATIVE-NOTEBOOK-PIPELINE-ENVIRONMENT-ADR-20261031.md)、[目录归属规范](engineering/development/SHARED-DATA-ENGINE-STRUCTURE-AND-OWNERSHIP.md)。本次是规范定版，不代表 Fabric 云资源已部署。

> **状态：ACTIVE（经终审的项目文档权威入口）** · 2026-10-16 · **STEP01–STEP08 COMPLETE（PR #174 合并后）**；OpenSpec G0–G4 Bootstrap 已完成，后续工作由 Active Changes 管理（2026-10-18 核对）。
>
> 本目录已经完成本轮 STEP01–08 对本地 Pipeline、Portal、Azure/Fabric、项目状态、开发规则、运维与决策的终审核对。**历史证据和未实施的新能力仍由对应源码/验收与今后创建的 OpenSpec Change 管理**；文档目录中没有某项能力，不意味着它已经验收或不存在。

> **Fabric 新权威架构（2026-10-20）**：[Module-first Terraform Environment](architecture/design/FABRIC-TERRAFORM-ENVIRONMENT-ARCHITECTURE.md) · [实施 OpenSpec](../openspec/changes/simplify-fabric-environment-iac/tasks.md)。以已授权部署身份、可用 Capacity、现成 Landing 和 Terraform State 为外部前置，继续复用旧 Azure-Infra 的 Module 架构；历史 A=B/Bootstrap 不再是当前开发主线。**仅是架构更新，非真实 Apply**。

## 当前文档目录（Data Platform / Engineering 已切换）

- [Architecture](architecture/SYSTEM-OVERVIEW.md)：全局系统架构、数据流、基础设施和 Architecture Decisions。
- [Infra — Healthcare On-Demand Live Demo](infra/README.md)：面向 Emory 的按需公网演示、双运行时 PySpark/OpenLineage、Azure Blob 中转、Cloudflare 只读站点（目标架构，尚未实施）。
- [架构设计讨论稿](architecture/design/README.md)：[V2 多来源 Fabric 与双 Portal 展示路线](architecture/design/HEALTHCARE-V2-MULTISOURCE-FABRIC-ROADMAP-DESIGN.md)、Data Platform V2 源码迁移与 [OpenSpec 接入设计](architecture/design/OPENSPEC-ADOPTION-DESIGN.md)（为编制时点的 Draft；OpenSpec 已投入变更管理，本地物理目录已迁移但运行路径/E2E 未验收；Fabric 新业务 ETL 尚未实施）。
- [Systems](systems/README.md)：Data Platform 本地五组件、Azure/Fabric 与 Platform Portal 已统一进入 `systems/`，均提供 README/CODE 组件导航。
- [Engineering](engineering/README.md)：开发规范、Agent 规则、测试、运维、迁移与项目状态。

**迁移结果**：本地 Data Platform 与 Engineering 已采用新的 `systems/`、`engineering/` 目录，CODE.md 源码地图和 Markdown 链接均有独立 CI。旧的本地组件及工程文档副本已按可追溯 Git 历史方式清理；**Azure/Fabric 与 Portal 的唯一当前系统说明分别位于 `systems/azure-fabric/`、`systems/platform-portal/`；旧 `components/` 相应重复说明均已退役**。

## Agent 开工入口

**先读 [AGENTS.md](../AGENTS.md)、[Agent 规则](engineering/development/AGENT-RULES.md) 和 [当前项目状态](engineering/status/PROJECT-STATUS.md)。** 根目录 `AGENTS.md` 是唯一按任务分流入口：它会根据代码开发、测试、文档或共享环境操作指向必要的详细规范。不要每次通读全部工程文档，也不在本目录维护第二套任务分类表。

当前采用 **直接维护 Git 正式源码 + Self-Runner / GitHub Actions 受控验证** 的开发模式。**正式功能、治理与重构变更以 [OpenSpec 开发生命周期](engineering/development/OPENSPEC-DEVELOPMENT-LIFECYCLE.md) 和 [Active Changes](../openspec/changes/relocate-local-data-platform/tasks.md) 为具体设计/Tasks 入口，遵守 Main Required CI；历史 [G0–G7 计划](engineering/migration/OPENSPEC-IMPLEMENTATION-PLAN.md) 仅供 Bootstrap 审计，不再指挥当前 G5/G6。** 原 `documents/` 保留架构、组件、人类可读开发/运维规范的权威，不被 OpenSpec 替代。具体实施参见 [Development Workflow](engineering/development/DEVELOPMENT-WORKFLOW.md)；需要真实 Runtime 操作时必须遵守 [Safe Operations](engineering/operations/SAFE-OPERATIONS.md)。旧 Skill 和零散排障经验只保留在 [历史 Git 快照](engineering/migration/LEGACY-DOCS-SNAPSHOT.md)，不作为现行开发流程。

## 文档终审历史与当前 OpenSpec 入口

- **[Final Authority Audit](engineering/migration/FINAL-DOCUMENTATION-AUDIT.md)** — STEP08 当时的 25 份文档链接审计（历史统计，并非现行 `documents/` 文档总数）、旧入口权威纠偏及后续边界。
- [OpenSpec G0–G7 正式实施计划](engineering/migration/OPENSPEC-IMPLEMENTATION-PLAN.md) — STEP09 当时的历史实施阶段和 PR/Run 证据，**不再维护当前变更 Tasks**；[G0 基线审计](engineering/migration/OPENSPEC-BASELINE-AUDIT.md) 已完成只读检查，[Readiness](engineering/migration/OPENSPEC-READINESS.md) 为开工检查。G0–G4 历史阶段已完成，G5/G6 的实际推进在 [源码迁移 Change](../openspec/changes/relocate-local-data-platform/tasks.md)，参见 [生命周期](engineering/development/OPENSPEC-DEVELOPMENT-LIFECYCLE.md)。

## 长期运维与架构决策（STEP07 已审核）

- [Operations Index](engineering/operations/README.md) — 有效运维知识入口和仍需按需查阅的旧技术经验。
- [Safe Operations](engineering/operations/SAFE-OPERATIONS.md) — 共享 K8s/Spark/Airflow/PG/S3/Azure 操作的安全门槛。
- [Architecture Decisions](architecture/decisions/README.md) — 已批准的重要架构路线和代替旧方案的原因。
- [OpenSpec 迁移准备与 STEP08/09 Gate](engineering/migration/OPENSPEC-READINESS.md) — 旧 PR #164 已于 2026-10-17 关闭、未合并；[接入设计稿](architecture/design/OPENSPEC-ADOPTION-DESIGN.md) 与 [G0–G7 执行计划](engineering/migration/OPENSPEC-IMPLEMENTATION-PLAN.md) 已对齐，G1 已初始化、G2 已配置中文。

**2026-10-18 已落实的源码根目录**：本地业务源码已通过 [PR #225](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/225) 移至 `local-data-platform/`，文档源码链接与代码地图在 #226 修复、仓库质量工具在 #227 归入 `.github/quality/`。`documents/systems/data-platform/` 仍是组件**文档**命名空间；**物理目录完成不等于 Import/Docker/Airflow/Spark/E2E 已验收**，后续由 [Active Change](../openspec/changes/relocate-local-data-platform/tasks.md) 跟踪。

已完成名称决定的独立 OpenSpec 文档试点：[命名 PR #223](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/223) 已合并，验证 [OpenSpec Run #39155840396](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39155840396) 成功；[归档 PR #224](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/224) 合并后归档路径为 `openspec/changes/archive/2026-10-18-adopt-local-data-platform-naming/`。此次仅命名治理，不代表 G5 迁移 Change 或 G6 完成。

## Azure/Fabric 与 Platform Portal（当前有效导航）

- [Platform Portal：Marquez / OpenLineage](systems/platform-portal/README.md) — 部署与 A3/A4 历史验收、Spark Job↔Run/Dataset 未完成和待讨论接入方案。
- [Azure/Fabric：OMOP → Azure Blob → Fabric Pipeline/Notebook → OneLake](systems/azure-fabric/README.md) — OneLake-first 方案、Terraform Plan-only 证据、未完成的导出/业务装载边界。

## Systems — Data Platform（STEP05 已审核，目录已切换）

- [Data Platform 组件目录与职责](systems/data-platform/README.md) — Synthea、Landing、Airflow、Spark、OMOP 五个可长期维护的业务模块。
- [Legacy Task-named 代码重构计划](engineering/development/LEGACY-CODE-REFACTOR-PLAN.md) — 旧 `task004` 依赖、兼容门槛、逐阶段源码迁移计划（尚未实际 Rename）。

## 当前项目状态（由 PROJECT-STATUS 维护）

- **[PROJECT-STATUS.md](engineering/status/PROJECT-STATUS.md)** — 跨项目唯一 CURRENT/NEXT 总览：TASK004 历史验收冻结、TASK005 暂缓、目录源码迁移运行兼容仍待办、OpenSpec 门禁已真实通过 Ruleset 正反验证、Portal/Azure 分别保留待办；各变更具体进度链接到对应 OpenSpec Change。

## 当前整体架构（STEP03 审核基线）

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
| [`contracts/`](../local-data-platform/contracts) · [Synthea CODE](systems/data-platform/synthea/CODE.md) · [OMOP CODE](systems/data-platform/omop/CODE.md) | 具体行为合同和数据 Schema 等以当前 Git 源码与有效 Contract 为准，不因文档搬迁而改写 |
| [`openspec/`](../openspec/config.yaml) | `changes/` 是具体变更的唯一 Proposal/Design/Tasks/验收记录；`specs/` 仅放经核实并采用的行为要求；不代替 `documents/` 的架构/运维、GitHub PR 或 Runtime 锁 |

历史 `docs/` 快照存在互相矛盾的日期记录；不得仅按文件名中的 CURRENT 或文件创建日期认定事实。对代码/运行状态的陈述必须标明 **Source SHA 与对应验收证据**。有不一致时先记录，停止未经核实的权威切换。

## 已知项目基线（历史验收，不是新一轮实时探针）

- [仓库根 README](../README.md) 描述已验收的本地 Synthea → S3 Landing → Airflow → Spark Person/Visit → PostgreSQL OMOP 路径。
- TASK004 NEW_ONLY Person/Visit 实际 E2E 和同批次 SKIP 有[最终验收证据](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md)；该结论不代表其他数据域或所有并发/恢复场景已验收。
- [Condition TASK005](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-005-CONDITION-DEVELOPMENT-PLAN-v1.0.zh-CN.md) 处于可做 STEP00 只读预检、尚未完成业务入库的状态；开发前再次核对最新 Main 和授权。
- Portal 已使用原生 Marquez Web + OpenLineage，**Airflow 事件已证实**、Spark 独立 Smoke 部分成功，但 Dataset 全链路尚未验收；Azure/Fabric 则采用 **PG → Azure Blob → Fabric Pipeline → Notebook → OneLake Lakehouse** 的简化目标，目前仅三组件 Terraform Plan 验证成功，不得误报部署与业务 E2E。

## 为什么不直接重写全部文档？

我们采取 **逐领域分析 → 核对源码/运行证据 → 消除矛盾 → 新建简洁文档 → 审核切换权威** 的方式。现有历史证据不批量覆盖，不修改 `docs/` 正文来伪造一致性。

**当前权威分工**：`AGENTS.md` 是 Agent 开工入口；`documents/` 管长期架构、系统、开发规范、运维和跨系统状态；`openspec/changes/` 是具体变更及任务进度的唯一记录，`openspec/specs/` 只管理已核实采用的行为；代码/Contract 与 GitHub PR/Run 是实际实现及验收依据。不要在 Engineering 维护平行 Tasks。
