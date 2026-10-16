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
| **STEP01** | `documents/` 入口、Agent 规则、治理规则、迁移表，根 `AGENTS.md` | **BOOTSTRAP**（合并后视为完成） | 新 Agent 能发现并遵守规则；没有业务文件改动 |
| **STEP02** | `documents/development/` 完整工作流与测试规范 | **PENDING** | 当前 PR/Self-Runner、STEP、脚本、测试流程与真实实现一致 |
| **STEP03** | `documents/architecture/` 当前总体架构 | **PENDING** | 正确区分 Synthea 解耦后的现状与 V4 历史设计 |
| **STEP04** | `documents/status/` 当前唯一项目状态 | **PENDING** | TASK004、TASK005、Azure、Portal 状态均有明确证据和时间 |
| **STEP05** | `documents/components/` Local Pipeline | **PENDING** | Synthea/Landing/Airflow/Spark/OMOP 的设计、代码与合同一致 |
| **STEP06** | Portal / Azure-Fabric 专项模块 | **PENDING** | A3/A4 局限及 OneLake-first、Plan-only 边界正确 |
| **STEP07** | `documents/operations/` 与决策索引 | **PENDING** | 有效运维知识可用，操作限制不丢失 |
| **STEP08** | 切换项目入口、检查引用、验收文档体系 | **PENDING** | 入口唯一、冲突消除、迁移记录完整 |
| **STEP09** | 独立后续工作：初始化同仓库 OpenSpec | **NOT STARTED** | 用户确认开始，Spec 从已核实的业务知识建立 |

**本次执行范围只有 STEP01**；下一步先做 STEP02，不同时开展架构、Status 和 OpenSpec 改造。

## 2. 候选来源（未迁移、不自动成为新权威）

| 领域 | 当前有用的 Legacy 来源 | 目标目录 | 领域权威状态 |
| --- | --- | --- | --- |
| Agent / 开发流程 | [旧 Operations](../../docs/development/PLATFORM-DEVELOPMENT-OPERATIONS-v1.0.zh-CN.md)、[旧 Skill](../../docs/skill/SKILL-cn.md)、[经验](../../docs/runbooks/development-lessons-cn.md) | `documents/development/` | **PARTIAL**：新通用规则有效；细节待 STEP02 |
| 系统总体架构 | [V4 中文](../../docs/architecture/Healthcare-Data-Platform-Architecture-and-Implementation.v4.zh-CN.md)、[独立 Generator 设计](../../docs/architecture/TASK-004-INDEPENDENT-SYNTHEA-GENERATORS-AND-AIRFLOW-CONSUMER-v1.0.zh-CN.md) | `documents/architecture/` | **LEGACY / TO REVIEW** |
| 主线状态与证据 | [旧 TASK 状态](../../docs/tasks/TASK-STATUS.md)、[最终 TASK004 证据](../../docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md) | `documents/status/` | **LEGACY / TO REVIEW** |
| 本地数据模块 | `apps/`、`airflow/`、`spark/`、`sql/`、`contracts/`、相关 `docs/tasks/` | `documents/components/` | **LEGACY / TO REVIEW** |
| Azure Fabric | [旧 Azure 入口](../../docs/azure-fabric/README.md)、[OneLake-first 方案](../../docs/azure-fabric/AZURE-ONELAKE-INFRA-PLAN-ONLY-2026-10-15.md)、`azure/` | `documents/components/azure-fabric/` | **LEGACY / TO REVIEW** |
| Platform Portal | [旧 Portal 入口](../../docs/platform-portal/README.md)、`platform-portal/` | `documents/components/platform-portal/` | **LEGACY / TO REVIEW** |
| 运维和经验 | `docs/runbooks/`、`kubernetes/`、实际已验收部署配置 | `documents/operations/` | **LEGACY / TO REVIEW** |

## 3. 每一步完成时登记

下一 STEP 的 PR 在本文件追加或更新：**领域、旧文件/代码来源、Source SHA、核实的证据及运行时间、冲突决议、新文件路径、ACTIVE/未完成范围、PR 号、合并 SHA**。不要提前猜测 PR 和合并 SHA。

在某领域 ACTIVE 前，新 Agent 仍必须从代码/Contract/当前证据与未迁移的有效旧操作规则获取事实。旧文档中的历史 CURRENT/NEXT 不应作为新一轮自动执行命令。
