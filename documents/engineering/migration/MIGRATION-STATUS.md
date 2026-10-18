# Documentation Rebuild — 迁移进度和源资料登记

> **历史迁移基线：Pre-OpenSpec · 开始日期：2026-10-16；当前状态：STEP01–08 COMPLETE / OpenSpec G0–G4 COMPLETE。** 最新 CURRENT/NEXT 以 [PROJECT-STATUS](../status/PROJECT-STATUS.md) 和 [OpenSpec G0–G7 计划](OPENSPEC-IMPLEMENTATION-PLAN.md) 为准，下面保留的历史阶段记录不得当作当前开工命令。
>
> 文档不是在本文件创建时就算完成迁移。**每个领域独立核对、合并并切换权威**，完成状态以合并后的 Main 和对应验收结果为准。

## 0. 迁移源和保护边界

- **本轮规则构建的原始 Main 基线**：`30f717f2302a2a2fc1a4aff5c8ef0a482ca33816`（创建新规则前读取）。
- **先前 OpenSpec 迁移前备份 Merge Commit**：`2ae11607aa44df3bc4524dead2a9792dd64cbb9a`。这份 Git 历史基线仍可追溯；目前 Main 的 `docs/archive/` 已被移走/删除，**不将 Git 历史混同于当前目录内容**。
- 旧历史 Archive 位置：[Healthcare-Specs/archive](https://github.com/JohnZhang-DataForge/Healthcare-Specs/tree/main/archive)（Private，引用自旧文档；如需读取必须先确认权限和实际内容）。
- 原 `docs/` 已从当前 Main 全部清理；其固定 Git 历史快照仅作迁移输入和验收证据，不在本项目重建旧 Archive 目录。
- 文档重建不会自动触发数据生成、Airflow、Spark、OMOP Writer、K8s 变更、Terraform Apply，也不自动获得运行授权。

## 最终旧目录清理（STEP08 后）

- 原有 `docs/` **111 个文件**曾作为终审历史材料；此后从 Main 删除，但所有历史记录仍保存在删除前的 [固定 Commit `49936b51d4beadc69383e931efc3e72d2f0db47e`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/tree/49936b51d4beadc69383e931efc3e72d2f0db47e/docs)。
- [Legacy Docs Snapshot](LEGACY-DOCS-SNAPSHOT.md) 记录访问入口及永久链接规则。文档中的旧 `docs/...` 路径是**历史树路径**，不是现行 Main 工作目录；应通过固定快照链接读取。
- 清理仅涉及文档/README 链接和一个已无效的 Portal 静态 CI 路径触发器；`documents/`、业务代码、Contract、Workflow 执行逻辑均不应受删除影响。

## 2026-10-16 文档层级重组（后续阶段）

- 新层级：`documents/architecture/`、`documents/systems/data-platform/` 和 `documents/engineering/`。Architecture Decisions 通过 PR #187 迁入 Architecture。
- PR #188：先复制本地五组件与 Engineering 文档，旧目录不删；PR #189：更新 documents 根入口；PR #190：更新 Architecture 引用；PR #191：更新 CODE Map CI/Agent 规则；PR #192：修复 Azure/Portal 原 README 指向 Engineering 的四个依赖链接；PR #193：新增 Markdown 链接 CI。旧的 Data Platform/Engineering 文档副本随后已从 Main 清理，历史版本仍可追溯。
- **历史范围说明**：下表 STEP02–STEP07 中出现的 `documents/development/`、`documents/components/` 等，是当时相关 PR 的**历史位置**，不是当前 Main 的权威目录；当前导航请使用 [Systems](../../systems/README.md) 和 [Engineering](../README.md)。该段记录 2026-10-16 的过渡情况；Azure/Fabric 后续已迁至 `documents/systems/azure-fabric/` 并退役原组件文档，Portal 后续已迁移至 `documents/systems/platform-portal/`。

## 1. 分阶段计划

| 顺序 | 交付物 | 迁移状态 | 完成标准 |
| --- | --- | --- | --- |
| **STEP01** | `documents/` 入口、Agent 规则、治理规则、迁移表，根 `AGENTS.md` | **COMPLETE（PR #167）** | 新 Agent 能发现并遵守规则；没有业务文件改动 |
| **STEP02** | `documents/development/` 完整工作流与测试规范 | **COMPLETE（PR #168）** | 已静态核对 Healthcare / Self-Runner 实际 Workflow、触发器、SHA 绑定与测试分级；并列明执行风险 |
| **STEP03** | `documents/architecture/` 当前总体架构 | **COMPLETE（PR #169）** | 区分本地 NEW_ONLY 验收、Portal A3/A4 局限和 Azure OneLake-first 目标/PLAN-only 边界 |
| **STEP04** | `documents/status/` 当前唯一项目状态 | **COMPLETE（PR #170）** | [唯一项目状态入口](../status/PROJECT-STATUS.md) 区分 TASK004/Condition、Portal 已验收与待商定 Spark、Azure 方案已定与 Plan-only |
| **STEP05** | `documents/components/` Local Pipeline | **COMPLETE（PR #171：文档/命名治理）** | 五组件文档、Legacy 依赖清单、禁止新增 Task/Step 代码命名的 Agent 规则和 PR Gate；旧源码物理迁移尚未进行 |
| **STEP06** | Portal / Azure-Fabric 专项模块 | **COMPLETE（PR #172）** | [Portal（STEP06 当时的文档）](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/ad39ed608c699ea3f30b74bd4bc331733d462e99/documents/components/platform-portal/README.md)、[Azure/Fabric（当时文档）](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/41be1aba4d8b730b2a9e17fadfc0450e6aec5095/documents/components/azure-fabric/README.md)：明确已验收、已批准设计和待实现/待定范围 |
| **STEP07** | `documents/operations/`、决策索引（现位于 `documents/architecture/decisions/`）、精简 Session 协调与 OpenSpec Readiness | **COMPLETE（PR #173）** | 安全/排障长期入口、已确定决策；不新建重复 Handoff 体系；准备 STEP08/09 |
| **STEP08** | 切换项目入口、检查引用、验收文档体系 | **COMPLETE（PR #174 合并后）** | [终审报告](FINAL-DOCUMENTATION-AUDIT.md)：历史入口降级、单一状态权威、25 篇新文档链接核验 |
| **STEP09** | 同仓库 OpenSpec 接入与后续实施 | **G0–G4 COMPLETE；G5–G7 NOT STARTED** | [唯一 G0–G7 计划](OPENSPEC-IMPLEMENTATION-PLAN.md) 记录真实 CLI/CI/PR/Run 证据；G5 仅首个业务 Change 的设计审核，未迁移代码 |

**2026-10-16 历史整理状态（非当前 Main）**：STEP01–08 的权威终审已完成；后续 PR #187–193 推进了 `architecture/decisions/`、`systems/data-platform/` 和 `engineering/` 层级切换，并已清理原 `docs/` 和旧本地组件/工程文档副本。该段为 2026-10-16 历史状态：当时 Azure/Fabric 与 Platform Portal 文档均在 `documents/components/`。此后 Azure/Fabric 已切换为 `documents/systems/azure-fabric/`；该段为 2026-10-16 历史状态，Portal 后续已迁至 `documents/systems/platform-portal/`。OpenSpec 状态以当前专门计划与基线审计为准。以上 STEP01–08 表格保留原阶段的交付路径和验收结论。

## 2. 候选来源（未迁移、不自动成为新权威）

| 领域 | 当前有用的 Legacy 来源 | 目标目录 | 领域权威状态 |
| --- | --- | --- | --- |
| Agent / 开发流程 | [旧 Operations](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/development/PLATFORM-DEVELOPMENT-OPERATIONS-v1.0.zh-CN.md)、[旧 Skill](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/skill/SKILL-cn.md)、[经验](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/runbooks/development-lessons-cn.md)；Self-Runner Main `8f8cb877887540cbed697260c3e8154e218a49c7` 下的执行 Workflow | [开发工作流](../development/DEVELOPMENT-WORKFLOW.md)、[测试规范](../development/TESTING-AND-EVIDENCE.md) | **ACTIVE（PR #168）**：已切换开发流程领域；旧 Skill 中未迁移的技术安全细节继续有效 |
| 系统总体架构 | [V4 中文](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/architecture/Healthcare-Data-Platform-Architecture-and-Implementation.v4.zh-CN.md)、[独立 Generator 设计](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/architecture/TASK-004-INDEPENDENT-SYNTHEA-GENERATORS-AND-AIRFLOW-CONSUMER-v1.0.zh-CN.md)、[Portal 证据](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/validation.md)、[OneLake-first 方案](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/azure-fabric/AZURE-ONELAKE-INFRA-PLAN-ONLY-2026-10-15.md) | [System Overview](../../architecture/SYSTEM-OVERVIEW.md)、[Data Flow](../../architecture/DATA-FLOW.md)、[Infrastructure](../../architecture/INFRASTRUCTURE.md) | **ACTIVE（PR #169）**：仅总体架构切换；详细组件与当前状态分别待 STEP04–06 |
| 主线状态与证据 | [旧 TASK 状态](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-STATUS.md)、[最终 TASK004 证据](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md) 及 Portal/Azure 分项证据 | [PROJECT-STATUS](../status/PROJECT-STATUS.md) | **ACTIVE（PR #170）**：已切换全项目 CURRENT / NEXT；旧 TASK 文档继续作为历史证据 |
| 本地数据模块 | `apps/`、`airflow/`、`spark/`、`sql/`、`contracts/`、历史 TASK 文档 | [组件目录](../../systems/data-platform/README.md)、[重构计划](../development/LEGACY-CODE-REFACTOR-PLAN.md) | **ACTIVE（PR #171）**：组件知识已迁移；现有 Task 命名 Runtime 兼容迁移另行开发 |
| Azure Fabric（STEP06 历史审计，当前入口已更新） | [旧 Azure 入口](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/azure-fabric/README.md)、[OneLake-first 方案](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/azure-fabric/AZURE-ONELAKE-INFRA-PLAN-ONLY-2026-10-15.md)、`azure/` | [Azure/Fabric 当前系统文档](../../systems/azure-fabric/README.md) | **ACTIVE（PR #172）**：OneLake-first + IaC/Plan-only 事实；尚未定稿的 ETL 实现不提前批准 |
| Platform Portal | [旧 Portal 入口](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/README.md)、`platform-portal/` | [Platform Portal 当前系统文档](../../systems/platform-portal/README.md) | **ACTIVE（PR #172）**：Marquez/A3/A4 证据与局限，后续实际 Spark 方案仍未批准 |
| 运维和经验 | `docs/runbooks/`、`kubernetes/`、旧 Portal/Azure Operations、真实代码/验收 | [Operations](../operations/README.md)、[Safe Operations](../operations/SAFE-OPERATIONS.md)、[Session Coordination](../development/SESSION-COORDINATION.md)、[Decisions](../../architecture/decisions/README.md) | **ACTIVE（PR #173）**：通用操作/决策规则已迁移；旧技术细节仍按实际源码/历史证据查阅 |

## 3. STEP02 事实核验摘要（静态）

- Healthcare Source SHA：`63524cc244b64f784ff0e7887caa8e63fed5049f`；Self-Runner Source SHA：`8f8cb877887540cbed697260c3e8154e218a49c7`。
- 已核对 `generic-task-executor.yml`、`generic-task-executor-v2.yml`、`cross-repo-generic-pr-v4.yml`、`azure-infra.yaml`、`synthea-new-only-run-new-request.yml`、`landing-batch-discovery-readonly.yml` 及部分 Healthcare Actions 与原操作规范。
- 核心冲突已纠正：通用执行器并非任意 Healthcare 跨仓执行；某些 readonly 工作流仍创建临时 K8s 资源；Azure 工作流可手动选择 Apply 但当前文档工作不授权 Apply；旧 Skill 中 TASK004 未完成的 CURRENT 属于历史记录。
- 这轮**未实际触发** GitHub Actions、Runner、Terraform、Airflow、Spark、PG 或 S3 操作。

## 4. STEP03 — 当前架构重建依据与冲突处理

- **Healthcare Main 核对基线**：`8d276dc7a121c15396a9ce328fcfea4688a795ae`，只读查看 `airflow/dags/new_only_omop_consumer.py`、`landing_batch_discovery.py`、`platform-portal/`、`azure/infra-terraform/` 及旧设计/验收文件；不执行任何 Runtime 操作。
- **Synthea 旧 V4 冲突**：旧版“Airflow 生成 Synthea”不再有效，现为独立 Producer 发布 immutable READY，手工 Airflow Consumer 消费。Discovery 周期扫描不等于全部业务自动 COMMIT。
- **Portal 角色更新**：新增 Marquez 原生 Web/独立 PG14 子系统；A3 Airflow 与 A4 隔离 Spark Smoke 已有证据，完整 Job/Run/Dataset 业务血缘仍未验收。
- **Azure 目标更改**：旧 Warehouse-first/多层云端转换不是第一阶段；最新为 local PG → read-only exporter (未实现) → existing Azure Blob → Fabric Data Pipeline 编排 Notebook → OneLake Lakehouse。已完成 3 项 Plan、**0 Apply/0 业务 ETL**；不把 Fabric Pipeline 说成独立 Azure Data Factory Account。
- **范围**：只改 `documents/` 新架构页、文档导航/迁移状态和根 `README.md` 的过时云端说明；不修订 `docs/` 原文，不修改业务或 Azure Terraform。
- **验收边界**：已核验历史 Run/Source SHA；本文没有当前资源在线状态的全量重新检查。

## 5. STEP04 — 项目状态确认与边界

- **本轮 Main 核对基线**：Healthcare `c4991d8fe1d4b6b9e65e024c2217f6c140eb17ed`；Self-Runner `8f8cb877887540cbed697260c3e8154e218a49c7`。
- **用户确认**：TASK004 已关闭；Portal 前期实施完成、下一步 Spark 实际接入方案尚在讨论；Azure OMOP→Blob→Fabric Pipeline/Notebook→OneLake 方案已敲定，IaC/Workflow/Plan 完成但未 Apply，业务实施细节仍待讨论。
- **交叉核验**：TASK004 Final Closeout + Run 38657060822/38657630069；Portal A3 实测与 A4 独立 Spark Smoke；Azure 三个 Fabric Item Plan Run 38799966270、38832798550、38832801221，全部 Plan-only。
- **关键状态边界**：Portal 下阶段没有批准的新方案；Azure 只有资源定义与 Plan、Notebook/Pipeline 仍 fail-closed，Export/ETL/E2E 未实施；未执行任何共享资源或云端操作。
- **STEP06 当时的未合并工作说明（历史）**：OpenSpec bootstrap PR #164 当时仍 open，不能代表当时 Main 已初始化 OpenSpec。此后 PR #164 已关闭未合并，新 OpenSpec G0–G4 已完成。

## 6. STEP05 — 组件和代码命名规范重建

- **Healthcare 基线**：`2c85b485381a72425506829fd321d93b164a231d`；清点已有 apps/airflow/spark/sql/scripts/images/kubernetes/tests 中带 Task ID 的文件路径及关键 `task004_cdm` ↔ Writer 镜像/PG API 依赖。
- **强制新增代码命名**：Domain + Component + Capability；Task/Step 只用于 PR/计划/运行记录/Legacy 证据。已新增 [规范](../development/CODE-ORGANIZATION-AND-NAMING.md)、[新增路径检查](../../../.github/quality/scripts/check_new_code_names.py)、[CI Workflow](../../../.github/workflows/code-component-naming-check.yml)。
- **交付**：[组件目录](../../systems/data-platform/README.md) 和五个独立 README、[Legacy 重构计划](../development/LEGACY-CODE-REFACTOR-PLAN.md)。文档审核并不意味着旧 Runtime 源码已经 Rename。
- **安全范围**：不得借重命名自动修改旧 `etl.task004_*`、Batch/Manifest、镜像固定 Digest 或重新触发已经验收的 COMMIT。

## 7. STEP06 — Portal / Azure 专项整理

- **审核基线**：Healthcare `241944d0a6e0c222f2e862d4b79c4279bf7fd35b`；Self-Runner `8f8cb877887540cbed697260c3e8154e218a49c7`。静态检查现有 Portal Helm/PG14/Airflow/Spark Probe 代码、历史 A3/A4/Marquez 真实运行记录，Azure Terraform root/modules/IAM、Notebook/Pipeline fail-closed 定义和 3 次 2026-10-15 Plan 记录。
- **Portal 冲突处理**：A4 真实 Spark Application 与 Marquez facets 存在，但 Live Workflow 初次 FAIL、应用 Job→Run 及 Dataset I/O 未证实；下一步接入实际业务 Spark 的方案仍在讨论，未提前通过。
- **Azure 冲突处理**：2026-10-14 Warehouse-first 被 2026-10-15 OneLake-first 目标取代；Data Factory 为 Fabric Data Pipeline，三个新 Item Plan PASS / APPLY NO；Exporter、Notebook ETL、Pipeline 绑定和实际云端数据链路仍未落地。
- **权限范围**：只更新新组件权威文档和导航/迁移表，不编辑 Legacy、业务代码、Workflow 或实际云端/集群资源。

## 8. STEP07 — 简化 Operations 与 OpenSpec 准备

- **静态核验基线**：Healthcare `d1962f79e1c7337c372de1aebfaaec87dfc7d1c8`、Self-Runner `8f8cb877887540cbed697260c3e8154e218a49c7`。只读查 K8s/Portal/PG/Azure 技术资料、旧 Runbook、当前组件规范及未合并 OpenSpec PR #164。
- **新权威**：[Operations](../operations/README.md)、[Safe Operations](../operations/SAFE-OPERATIONS.md)、[Decision Index](../../architecture/decisions/README.md)、[Session Coordination](../development/SESSION-COORDINATION.md)。不创建独立 `AGENT-HANDOFF.md`，OpenSpec Change/Tasks（未来）+ PR/Run（当前）承接接力状态。
- **过时冲突**：旧 Runbook 把 TASK004 Airflow 写成 NEXT，旧 Portal Policy 把 A4 写成未执行，旧 OpenSpec PR #164 配置还指向 `docs/tasks/TASK-STATUS.md`；必须以本轮新权威为准，历史正文保留。
- **STEP07 当时只做准备（历史）**：[OPENSPEC-READINESS](OPENSPEC-READINESS.md) 记录 STEP08/09 Gate，当时不合并 PR #164、不执行 CLI、不写 `openspec/`。此后的 G0–G4 已另行完成，当前以 [正式计划](OPENSPEC-IMPLEMENTATION-PLAN.md) 为准。
- **运行安全**：不更改任何业务、Terraform、Self-Runner、Kubernetes、PG/S3 或 Azure；无 Live 验收。

## 9. STEP08 — 文档终审与入口权威切换

- **只读核验 SHA**：Healthcare Main `f5ee37697bed08fc35e288d84420bafd4b2d8e22`。截至核验，该树有 **671 个 tracked blob、157 个 Markdown、25 份 `documents/` Markdown**。
- **完整新文档链接审计**：25 篇新文档的 **249 条相对 Markdown 链接**目标存在；无缺失。此为 STEP08 当时的基线审计数字，不代表当前 Main 的文档和链接总数。
- **7 个旧 Agent/状态/技术入口纠偏**：`docs/README.md`、`docs/tasks/TASK-STATUS.md`、`docs/runbooks/README.md`、`docs/skill/SKILL-cn.md`、旧 Developer Ops、Portal、Azure README；保留各自的原始历史证据及时间快照，不再将其作为新的 CURRENT/NEXT。
- **唯一项目 CURRENT/NEXT**：[PROJECT-STATUS](../status/PROJECT-STATUS.md)。长期决策、安全与组件知识保留在 `documents/`，业务代码/Contract 和 GitHub Run 仍各自有权威。
- **STEP08 当时尚未解决的非文档事项（历史）**：OpenSpec CLI 未验证、旧 PR #164 未合并需修订。**2026-10-18 后续结果**：旧 PR #164 已关闭未合并；G0–G4 官方初始化、配置和 CI 已按 [实施计划](OPENSPEC-IMPLEMENTATION-PLAN.md) 验证并合并。Portal Spark 正式集成方案仍未确定；Azure Terraform 仍为 Plan-only，未授权 Apply。详见 [终审报告](FINAL-DOCUMENTATION-AUDIT.md)。
- **无 Runtime 变更**：本轮不修改 Airflow/Spark/SQL/Images/K8s/Workflow/Terraform，未运行 Self-Runner、PG/S3/Azure、没有重放冻结批次。

## 10. 每一步完成时登记

**Azure/Fabric 后续迁移结果（2026-10-18，仅 Git 源码与文档）**：源基线 Healthcare `41be1aba4d8b730b2a9e17fadfc0450e6aec5095`；旧 `azure/infra-terraform/` 与新 `azure-fabric/infra-terraform/` 的 107 个 tree 条目一一对应，除两个说明文件外代码 Blob SHA 相同；Self-Runner `azure-infra.yaml` 已采用新目录，七组件历史 Plan-only 证据保持不变。当前权威文档是 [Azure/Fabric Systems README](../../systems/azure-fabric/README.md) 与 [CODE map](../../systems/azure-fabric/CODE.md)。旧组件文档及旧 Terraform 副本从 Main 退役，可通过上述固定历史 Commit 读取。没有执行 Terraform Plan/Apply/Destroy 或 Azure 数据操作。


**Azure/Fabric 文档职责收口（PR #214，2026-10-18）**：参照 Data Platform 现行组件 README/CODE 方式，`documents/systems/azure-fabric/README.md` 是唯一系统总入口，`CODE.md` 为跨组件索引，Terraform 的职责、逐文件源码导航及 IAM/OIDC/State/历史 Plan 证据分别位于 `infra-terraform/README.md`、`CODE.md` 和 `ARCHITECTURE.md`。源码区旧 `azure-fabric/README.md`、`azure-fabric/infra-terraform/README.md`、`azure-fabric/infra-terraform/docs/ARCHITECTURE.md` 已退役，历史原文仍可通过 PR 前固定 Git Commit 追溯。本次仅 Git 文档移动、链接修复及 CI 检查，Terraform 定义、State、云端资源均未触及，无 Plan/Apply/Destroy。

**Portal 文档统一迁移（2026-10-18）**：参考本地 Data Platform 和 Azure/Fabric 的 README/CODE 规范，原 `documents/components/platform-portal/README.md`、`platform-portal/README.md` 及 Airflow/Spark/PG14 子目录说明并入 `documents/systems/platform-portal/` 的系统 README/CODE、四组件 README/CODE。现行文档由新系统目录唯一维护，原版仍可通过 [迁移前 Git Commit](https://github.com/JohnZhang-DataForge/healthcare-data-platform/tree/ad39ed608c699ea3f30b74bd4bc331733d462e99/documents/components/platform-portal) 查阅。A3 真实通过、A4 原 Workflow 失败与后续只读局部成功并列保留；没有部署 Marquez、修改 PG14/PG17、共享 Scheduler、Spark Operator、SparkApplication 或业务数据。

下一 STEP 的 PR 在本文件追加或更新：**领域、旧文件/代码来源、Source SHA、核实的证据及运行时间、冲突决议、新文件路径、ACTIVE/未完成范围、PR 号、合并 SHA**。不要提前猜测 PR 和合并 SHA。

在某领域 ACTIVE 前，新 Agent 仍必须从代码/Contract/当前证据与未迁移的有效旧操作规则获取事实。旧文档中的历史 CURRENT/NEXT 不应作为新一轮自动执行命令。
