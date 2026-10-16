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

## 1. 分阶段计划

| 顺序 | 交付物 | 迁移状态 | 完成标准 |
| --- | --- | --- | --- |
| **STEP01** | `documents/` 入口、Agent 规则、治理规则、迁移表，根 `AGENTS.md` | **COMPLETE（PR #167）** | 新 Agent 能发现并遵守规则；没有业务文件改动 |
| **STEP02** | `documents/development/` 完整工作流与测试规范 | **COMPLETE（PR #168）** | 已静态核对 Healthcare / Self-Runner 实际 Workflow、触发器、SHA 绑定与测试分级；并列明执行风险 |
| **STEP03** | `documents/architecture/` 当前总体架构 | **COMPLETE（PR #169）** | 区分本地 NEW_ONLY 验收、Portal A3/A4 局限和 Azure OneLake-first 目标/PLAN-only 边界 |
| **STEP04** | `documents/status/` 当前唯一项目状态 | **COMPLETE（本次状态 PR 合并后）** | [唯一项目状态入口](../status/PROJECT-STATUS.md) 区分 TASK004/Condition、Portal 已验收与待商定 Spark、Azure 方案已定与 Plan-only |
| **STEP05** | `documents/components/` Local Pipeline | **PENDING** | Synthea/Landing/Airflow/Spark/OMOP 的设计、代码与合同一致 |
| **STEP06** | Portal / Azure-Fabric 专项模块 | **PENDING** | A3/A4 局限及 OneLake-first、Plan-only 边界正确 |
| **STEP07** | `documents/operations/` 与决策索引 | **PENDING** | 有效运维知识可用，操作限制不丢失 |
| **STEP08** | 切换项目入口、检查引用、验收文档体系 | **PENDING** | 入口唯一、冲突消除、迁移记录完整 |
| **STEP09** | 独立后续工作：初始化同仓库 OpenSpec | **NOT STARTED** | 用户确认开始，Spec 从已核实的业务知识建立 |

**当前整理范围：STEP04（本次状态 PR 合并后完成）。** 全项目 CURRENT / NEXT 以 [PROJECT-STATUS](../status/PROJECT-STATUS.md) 为唯一权威；下一步 STEP05 整理本地业务模块，不提前把 Portal Spark 或 Azure 未定实现细节写成已批准方案。本次未执行 Runner/K8s/PG/Azure Runtime 验证。

## 2. 候选来源（未迁移、不自动成为新权威）

| 领域 | 当前有用的 Legacy 来源 | 目标目录 | 领域权威状态 |
| --- | --- | --- | --- |
| Agent / 开发流程 | [旧 Operations](../../docs/development/PLATFORM-DEVELOPMENT-OPERATIONS-v1.0.zh-CN.md)、[旧 Skill](../../docs/skill/SKILL-cn.md)、[经验](../../docs/runbooks/development-lessons-cn.md)；Self-Runner Main `8f8cb877887540cbed697260c3e8154e218a49c7` 下的执行 Workflow | [开发工作流](../development/DEVELOPMENT-WORKFLOW.md)、[测试规范](../development/TESTING-AND-EVIDENCE.md) | **ACTIVE（PR #168）**：已切换开发流程领域；旧 Skill 中未迁移的技术安全细节继续有效 |
| 系统总体架构 | [V4 中文](../../docs/architecture/Healthcare-Data-Platform-Architecture-and-Implementation.v4.zh-CN.md)、[独立 Generator 设计](../../docs/architecture/TASK-004-INDEPENDENT-SYNTHEA-GENERATORS-AND-AIRFLOW-CONSUMER-v1.0.zh-CN.md)、[Portal 证据](../../docs/platform-portal/validation.md)、[OneLake-first 方案](../../docs/azure-fabric/AZURE-ONELAKE-INFRA-PLAN-ONLY-2026-10-15.md) | [System Overview](../architecture/SYSTEM-OVERVIEW.md)、[Data Flow](../architecture/DATA-FLOW.md)、[Infrastructure](../architecture/INFRASTRUCTURE.md) | **ACTIVE（本次架构 PR 合并后）**：仅总体架构切换；详细组件与当前状态分别待 STEP04–06 |
| 主线状态与证据 | [旧 TASK 状态](../../docs/tasks/TASK-STATUS.md)、[最终 TASK004 证据](../../docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md) 及 Portal/Azure 分项证据 | [PROJECT-STATUS](../status/PROJECT-STATUS.md) | **ACTIVE（本次状态 PR 合并后）**：已切换全项目 CURRENT / NEXT；旧 TASK 文档继续作为历史证据 |
| 本地数据模块 | `apps/`、`airflow/`、`spark/`、`sql/`、`contracts/`、相关 `docs/tasks/` | `documents/components/` | **LEGACY / TO REVIEW** |
| Azure Fabric | [旧 Azure 入口](../../docs/azure-fabric/README.md)、[OneLake-first 方案](../../docs/azure-fabric/AZURE-ONELAKE-INFRA-PLAN-ONLY-2026-10-15.md)、`azure/` | `documents/components/azure-fabric/` | **LEGACY / TO REVIEW** |
| Platform Portal | [旧 Portal 入口](../../docs/platform-portal/README.md)、`platform-portal/` | `documents/components/platform-portal/` | **LEGACY / TO REVIEW** |
| 运维和经验 | `docs/runbooks/`、`kubernetes/`、实际已验收部署配置 | `documents/operations/` | **LEGACY / TO REVIEW** |

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

## 6. 每一步完成时登记

下一 STEP 的 PR 在本文件追加或更新：**领域、旧文件/代码来源、Source SHA、核实的证据及运行时间、冲突决议、新文件路径、ACTIVE/未完成范围、PR 号、合并 SHA**。不要提前猜测 PR 和合并 SHA。

在某领域 ACTIVE 前，新 Agent 仍必须从代码/Contract/当前证据与未迁移的有效旧操作规则获取事实。旧文档中的历史 CURRENT/NEXT 不应作为新一轮自动执行命令。
