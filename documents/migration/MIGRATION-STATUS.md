# Documentation Rebuild — 迁移进度和源资料登记

> **阶段：Pre-OpenSpec · 迁移开始日期：2026-10-16**
>
> 文档不是在本文件创建时就算完成迁移。**每个领域独立核对、合并并切换权威**，完成状态以合并后的 Main 和对应验收结果为准。

## 0. 迁移源和保护边界

- **本轮规则构建的原始 Main 基线**：`30f717f2302a2a2fc1a4aff5c8ef0a482ca33816`（创建新规则前读取）。
- **先前 OpenSpec 迁移前备份 Merge Commit**：`2ae11607aa44df3bc4524dead2a9792dd64cbb9a`。这份 Git 历史基线仍可追溯；目前 Main 的 `docs/archive/` 已被移走/删除，**不将 Git 历史混同于当前目录内容**。
- 旧历史 Archive 位置：[Healthcare-Specs/archive](https://github.com/JohnZhang-DataForge/Healthcare-Specs/tree/main/archive)（Private，引用自旧文档；如需读取必须先确认权限和实际内容）。
- 现有 `docs/` 剩余文档仅作迁移输入；不在本项目重建旧 Archive 目录。
- 文档重建不会自动触发数据生成、Airflow、Spark、OMOP Writer、K8s 变更、Terraform Apply，也不自动获得运行授权。

## 最终旧目录清理（STEP08 后）

- 原有 `docs/` **111 个文件**曾作为终审历史材料；此后从 Main 删除，但所有历史记录仍保存在删除前的 [固定 Commit `49936b51d4beadc69383e931efc3e72d2f0db47e`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/tree/49936b51d4beadc69383e931efc3e72d2f0db47e/docs)。
- [Legacy Docs Snapshot](LEGACY-DOCS-SNAPSHOT.md) 记录访问入口及永久链接规则。文档中的旧 `docs/...` 路径是**历史树路径**，不是现行 Main 工作目录；应通过固定快照链接读取。
- 清理仅涉及文档/README 链接和一个已无效的 Portal 静态 CI 路径触发器；`documents/`、业务代码、Contract、Workflow 执行逻辑均不应受删除影响。

## 1. 分阶段计划

| 顺序 | 交付物 | 迁移状态 | 完成标准 |
| --- | --- | --- | --- |
| **STEP01** | `documents/` 入口、Agent 规则、治理规则、迁移表，根 `AGENTS.md` | **COMPLETE（PR #167）** | 新 Agent 能发现并遵守规则；没有业务文件改动 |
| **STEP02** | `documents/development/` 完整工作流与测试规范 | **COMPLETE（PR #168）** | 已静态核对 Healthcare / Self-Runner 实际 Workflow、触发器、SHA 绑定与测试分级；并列明执行风险 |
| **STEP03** | `documents/architecture/` 当前总体架构 | **COMPLETE（PR #169）** | 区分本地 NEW_ONLY 验收、Portal A3/A4 局限和 Azure OneLake-first 目标/PLAN-only 边界 |
| **STEP04** | `documents/status/` 当前唯一项目状态 | **COMPLETE（PR #170）** | [唯一项目状态入口](../status/PROJECT-STATUS.md) 区分 TASK004/Condition、Portal 已验收与待商定 Spark、Azure 方案已定与 Plan-only |
| **STEP05** | `documents/components/` Local Pipeline | **COMPLETE（PR #171：文档/命名治理）** | 五组件文档、Legacy 依赖清单、禁止新增 Task/Step 代码命名的 Agent 规则和 PR Gate；旧源码物理迁移尚未进行 |
| **STEP06** | Portal / Azure-Fabric 专项模块 | **COMPLETE（PR #172）** | [Portal](../components/platform-portal/README.md)、[Azure/Fabric](../components/azure-fabric/README.md)：明确已验收、已批准设计和待实现/待定范围 |
| **STEP07** | `documents/operations/`、`decisions/`、精简 Session 协调与 OpenSpec Readiness | **COMPLETE（PR #173）** | 安全/排障长期入口、已确定决策；不新建重复 Handoff 体系；准备 STEP08/09 |
| **STEP08** | 切换项目入口、检查引用、验收文档体系 | **COMPLETE（PR #174 合并后）** | [终审报告](FINAL-DOCUMENTATION-AUDIT.md)：历史入口降级、单一状态权威、25 篇新文档链接核验 |
| **STEP09** | 下一阶段：正式初始化同仓库 OpenSpec | **READY TO START / NOT INITIALIZED** | 重新核对旧 PR #164，运行真实 CLI Init/Validate，Spec 从已核实行为建立；不得宣称已安装 |

**当前整理范围：STEP08（PR #174 合并后完成）。** 文档权威终审完成；后续新增功能按已生效的组件命名、安全协作规则开展，OpenSpec STEP09 是尚未开始的单独实施事项。

## 2. 候选来源（未迁移、不自动成为新权威）

| 领域 | 当前有用的 Legacy 来源 | 目标目录 | 领域权威状态 |
| --- | --- | --- | --- |
| Agent / 开发流程 | [旧 Operations](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/development/PLATFORM-DEVELOPMENT-OPERATIONS-v1.0.zh-CN.md)、[旧 Skill](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/skill/SKILL-cn.md)、[经验](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/runbooks/development-lessons-cn.md)；Self-Runner Main `8f8cb877887540cbed697260c3e8154e218a49c7` 下的执行 Workflow | [开发工作流](../development/DEVELOPMENT-WORKFLOW.md)、[测试规范](../development/TESTING-AND-EVIDENCE.md) | **ACTIVE（PR #168）**：已切换开发流程领域；旧 Skill 中未迁移的技术安全细节继续有效 |
| 系统总体架构 | [V4 中文](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/architecture/Healthcare-Data-Platform-Architecture-and-Implementation.v4.zh-CN.md)、[独立 Generator 设计](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/architecture/TASK-004-INDEPENDENT-SYNTHEA-GENERATORS-AND-AIRFLOW-CONSUMER-v1.0.zh-CN.md)、[Portal 证据](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/validation.md)、[OneLake-first 方案](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/azure-fabric/AZURE-ONELAKE-INFRA-PLAN-ONLY-2026-10-15.md) | [System Overview](../architecture/SYSTEM-OVERVIEW.md)、[Data Flow](../architecture/DATA-FLOW.md)、[Infrastructure](../architecture/INFRASTRUCTURE.md) | **ACTIVE（PR #169）**：仅总体架构切换；详细组件与当前状态分别待 STEP04–06 |
| 主线状态与证据 | [旧 TASK 状态](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-STATUS.md)、[最终 TASK004 证据](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md) 及 Portal/Azure 分项证据 | [PROJECT-STATUS](../status/PROJECT-STATUS.md) | **ACTIVE（PR #170）**：已切换全项目 CURRENT / NEXT；旧 TASK 文档继续作为历史证据 |
| 本地数据模块 | `apps/`、`airflow/`、`spark/`、`sql/`、`contracts/`、历史 TASK 文档 | [组件目录](../components/README.md)、[重构计划](../components/LEGACY-CODE-REFACTOR-PLAN.md) | **ACTIVE（PR #171）**：组件知识已迁移；现有 Task 命名 Runtime 兼容迁移另行开发 |
| Azure Fabric | [旧 Azure 入口](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/azure-fabric/README.md)、[OneLake-first 方案](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/azure-fabric/AZURE-ONELAKE-INFRA-PLAN-ONLY-2026-10-15.md)、`azure/` | [Azure/Fabric 组件](../components/azure-fabric/README.md) | **ACTIVE（PR #172）**：OneLake-first + IaC/Plan-only 事实；尚未定稿的 ETL 实现不提前批准 |
| Platform Portal | [旧 Portal 入口](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/README.md)、`platform-portal/` | [Platform Portal 组件](../components/platform-portal/README.md) | **ACTIVE（PR #172）**：Marquez/A3/A4 证据与局限，后续实际 Spark 方案仍未批准 |
| 运维和经验 | `docs/runbooks/`、`kubernetes/`、旧 Portal/Azure Operations、真实代码/验收 | [Operations](../operations/README.md)、[Safe Operations](../operations/SAFE-OPERATIONS.md)、[Session Coordination](../development/SESSION-COORDINATION.md)、[Decisions](../decisions/README.md) | **ACTIVE（PR #173）**：通用操作/决策规则已迁移；旧技术细节仍按实际源码/历史证据查阅 |

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
- **未合并工作说明**：OpenSpec bootstrap PR #164 仍 open，不能代表 Main 已初始化 OpenSpec。

## 6. STEP05 — 组件和代码命名规范重建

- **Healthcare 基线**：`2c85b485381a72425506829fd321d93b164a231d`；清点已有 apps/airflow/spark/sql/scripts/images/kubernetes/tests 中带 Task ID 的文件路径及关键 `task004_cdm` ↔ Writer 镜像/PG API 依赖。
- **强制新增代码命名**：Domain + Component + Capability；Task/Step 只用于 PR/计划/运行记录/Legacy 证据。已新增 [规范](../development/CODE-ORGANIZATION-AND-NAMING.md)、[新增路径检查](../../scripts/quality/check_new_code_names.py)、[CI Workflow](../../.github/workflows/code-component-naming-check.yml)。
- **交付**：[组件目录](../components/README.md) 和五个独立 README、[Legacy 重构计划](../components/LEGACY-CODE-REFACTOR-PLAN.md)。文档审核并不意味着旧 Runtime 源码已经 Rename。
- **安全范围**：不得借重命名自动修改旧 `etl.task004_*`、Batch/Manifest、镜像固定 Digest 或重新触发已经验收的 COMMIT。

## 7. STEP06 — Portal / Azure 专项整理

- **审核基线**：Healthcare `241944d0a6e0c222f2e862d4b79c4279bf7fd35b`；Self-Runner `8f8cb877887540cbed697260c3e8154e218a49c7`。静态检查现有 Portal Helm/PG14/Airflow/Spark Probe 代码、历史 A3/A4/Marquez 真实运行记录，Azure Terraform root/modules/IAM、Notebook/Pipeline fail-closed 定义和 3 次 2026-10-15 Plan 记录。
- **Portal 冲突处理**：A4 真实 Spark Application 与 Marquez facets 存在，但 Live Workflow 初次 FAIL、应用 Job→Run 及 Dataset I/O 未证实；下一步接入实际业务 Spark 的方案仍在讨论，未提前通过。
- **Azure 冲突处理**：2026-10-14 Warehouse-first 被 2026-10-15 OneLake-first 目标取代；Data Factory 为 Fabric Data Pipeline，三个新 Item Plan PASS / APPLY NO；Exporter、Notebook ETL、Pipeline 绑定和实际云端数据链路仍未落地。
- **权限范围**：只更新新组件权威文档和导航/迁移表，不编辑 Legacy、业务代码、Workflow 或实际云端/集群资源。

## 8. STEP07 — 简化 Operations 与 OpenSpec 准备

- **静态核验基线**：Healthcare `d1962f79e1c7337c372de1aebfaaec87dfc7d1c8`、Self-Runner `8f8cb877887540cbed697260c3e8154e218a49c7`。只读查 K8s/Portal/PG/Azure 技术资料、旧 Runbook、当前组件规范及未合并 OpenSpec PR #164。
- **新权威**：[Operations](../operations/README.md)、[Safe Operations](../operations/SAFE-OPERATIONS.md)、[Decision Index](../decisions/README.md)、[Session Coordination](../development/SESSION-COORDINATION.md)。不创建独立 `AGENT-HANDOFF.md`，OpenSpec Change/Tasks（未来）+ PR/Run（当前）承接接力状态。
- **过时冲突**：旧 Runbook 把 TASK004 Airflow 写成 NEXT，旧 Portal Policy 把 A4 写成未执行，旧 OpenSpec PR #164 配置还指向 `docs/tasks/TASK-STATUS.md`；必须以本轮新权威为准，历史正文保留。
- **只做准备**：[OPENSPEC-READINESS](OPENSPEC-READINESS.md) 说明 STEP08/09 Gate，当前不合并 PR #164、不执行 CLI、不写 `openspec/`。
- **运行安全**：不更改任何业务、Terraform、Self-Runner、Kubernetes、PG/S3 或 Azure；无 Live 验收。

## 9. STEP08 — 文档终审与入口权威切换

- **只读核验 SHA**：Healthcare Main `f5ee37697bed08fc35e288d84420bafd4b2d8e22`。截至核验，该树有 **671 个 tracked blob、157 个 Markdown、25 份 `documents/` Markdown**。
- **完整新文档链接审计**：25 篇新文档的 **249 条相对 Markdown 链接**目标存在；无缺失。此为基线审计数字，最终 PR 变更后还需做增量及 Main 回读检查。
- **7 个旧 Agent/状态/技术入口纠偏**：`docs/README.md`、`docs/tasks/TASK-STATUS.md`、`docs/runbooks/README.md`、`docs/skill/SKILL-cn.md`、旧 Developer Ops、Portal、Azure README；保留各自的原始历史证据及时间快照，不再将其作为新的 CURRENT/NEXT。
- **唯一项目 CURRENT/NEXT**：[PROJECT-STATUS](../status/PROJECT-STATUS.md)。长期决策、安全与组件知识保留在 `documents/`，业务代码/Contract 和 GitHub Run 仍各自有权威。
- **未解决且正确阻断的非文档事项**：OpenSpec CLI 未验证、旧 PR #164 未合并需修订；Portal Spark 正式集成方案未定；Azure Plan-only 没有 Apply。详见 [终审报告](FINAL-DOCUMENTATION-AUDIT.md)。
- **无 Runtime 变更**：本轮不修改 Airflow/Spark/SQL/Images/K8s/Workflow/Terraform，未运行 Self-Runner、PG/S3/Azure、没有重放冻结批次。

## 10. 每一步完成时登记

下一 STEP 的 PR 在本文件追加或更新：**领域、旧文件/代码来源、Source SHA、核实的证据及运行时间、冲突决议、新文件路径、ACTIVE/未完成范围、PR 号、合并 SHA**。不要提前猜测 PR 和合并 SHA。

在某领域 ACTIVE 前，新 Agent 仍必须从代码/Contract/当前证据与未迁移的有效旧操作规则获取事实。旧文档中的历史 CURRENT/NEXT 不应作为新一轮自动执行命令。
