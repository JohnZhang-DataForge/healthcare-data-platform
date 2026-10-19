---
status: active
scope: azure-fabric-system-overview
last_verified: 2026-10-18
source_sha: 8ad52828599ae95cda95eda4d888fc601ebfdfdc
---

# Azure / Microsoft Fabric — OMOP 云端分析子系统

> **唯一系统总导航**：本文说明整体业务架构、组件分工和验收范围；总源码导航见 [CODE.md](CODE.md)，各组件的 README 解释职责，CODE 定位源码。全项目实时 CURRENT/NEXT 以 [Project Status](../../engineering/status/PROJECT-STATUS.md) 为准。

## 系统目标与真实边界

> **新确认的目标设计（尚未实施）**：[Fabric 多环境可重建架构](../../architecture/design/FABRIC-MULTI-ENVIRONMENT-REBUILD-DESIGN.md) 已确定采用 Terraform + Self-Runner GitHub Actions + fabric-cicd，复用现有 Blob/Backend，Fabric 环境使用独立身份和 State Key；**这不会改变下文的 Plan-only、Workspace 手工建立与业务 Item 尚未完成的当前事实**。

Azure/Fabric 与本地 [Data Platform](../data-platform/README.md) 平级。本地 PostgreSQL OMOP 是权威数据源，Azure/Fabric 用于构建可重建的云端分析副本。现阶段批准的 OneLake-first 数据流：

```text
本地 PostgreSQL OMOP（权威库）
  → 一致性只读 Exporter + 不可变 Manifest（待开发）
  → 已有 Azure Blob Landing
  → Fabric Data Pipeline 编排（业务实现待开发）
  → Fabric PySpark Notebook（DQ / PK / FK / Delta 加载，待开发）
  → OneLake Lakehouse / Delta（分析副本）
```

**现状不能误报为 E2E 完成**：已存在 Terraform 基础设施定义；七个独立 Root 曾于 2026-10-16 在新路径下完成 **Plan-only** 验证，未据此证明 Apply、Fabric Item 已创建或实际数据已装载。Warehouse 是可选能力而非 MVP 前置条件。详细证据见 [Terraform 技术架构](infra-terraform/ARCHITECTURE.md#verified-plan-evidence)。

## 组件总表

| 组件 | 组件说明 / 源码地图 | 当前实际源码 | 实现与验收边界 |
| --- | --- | --- | --- |
| **Terraform Infrastructure** | [README](infra-terraform/README.md) · [CODE](infra-terraform/CODE.md) · [ARCHITECTURE](infra-terraform/ARCHITECTURE.md) | [`azure-fabric/infra-terraform/`](../../../azure-fabric/infra-terraform/) | 七个 Root/Module、IAM、OIDC、Remote State；只有 Plan-only 证据 |
| **Fabric Notebooks** | [README](notebooks/README.md) · [CODE](notebooks/CODE.md) | [`workspaces/healthcare-omop/notebooks/`](../../../azure-fabric/workspaces/healthcare-omop/notebooks/) | 目前只有 `.gitkeep`，没有 `*.Notebook/` 原生 Item |
| **Fabric Pipelines** | [README](pipelines/README.md) · [CODE](pipelines/CODE.md) | [`workspaces/healthcare-omop/pipelines/`](../../../azure-fabric/workspaces/healthcare-omop/pipelines/) | 目前只有 `.gitkeep`，没有 `*.DataPipeline/` 原生 Item |

`healthcare-omop` 是**已有 Fabric Workspace 的名称**，不是本次要创建的新 Workspace。源码结构分为基础设施 `infra-terraform/` 与未来 Fabric 原生业务 Item 的 `workspaces/healthcare-omop/`；建 Git 目录**不会**自动创建 Fabric Item 或连通 Fabric Git。

```text
azure-fabric/
├── infra-terraform/
│   ├── components/               # 七个独立 Terraform Root
│   └── modules/                  # 对应实现模块及权限定义
└── workspaces/
    └── healthcare-omop/
        ├── notebooks/
        │   └── ingestion/        # 未来 *.Notebook Item 归类
        └── pipelines/            # 未来 *.DataPipeline Item
```

## Terraform 与 Fabric Git 的交付所有权

现有 [Terraform Notebook Bootstrap](../../../azure-fabric/infra-terraform/modules/notebook/definitions/notebook-content.py) **故意抛出 `RuntimeError`**；Terraform Pipeline 在未提供真实 Notebook GUID 时运行 [Fail Activity](../../../azure-fabric/infra-terraform/modules/data-factory/definitions/pipeline-disabled.json)。[Notebook Activity JSON](../../../azure-fabric/infra-terraform/modules/data-factory/definitions/pipeline-notebook.json) 只是模板，**并非已经运行的业务处理**。这些定义继续归 Terraform，而不是未来 Fabric Git 业务源码。

引入真正的 Fabric Item 时，应保留 Fabric 生成的 `.platform` 和真实 Notebook/Pipeline Item 文件，**不得虚构 Item ID**。必须核实已有 GUID，并为每个 Item 选择 **Terraform 或 Fabric Git 中唯一交付责任方**，避免双向同步覆盖。可复用 Python 库的构建、部署、运行环境应独立明确，不要把任意辅助源码塞入 Git 同步的 Item 文件夹。参考 [Fabric Notebook Source Control](https://learn.microsoft.com/en-us/fabric/data-engineering/notebook-source-control-deployment) 与 [Fabric Git Item Format](https://learn.microsoft.com/en-us/fabric/cicd/git-integration/source-code-format)。

## 本地 Exporter、测试和独立对账

只读 PostgreSQL Exporter、不可变 Manifest、Hash/Schema/PK/FK 校验、Blob 发布、云端幂等写入及独立跨平台 Reconciliation 均**尚未实现**。过去 `azure-fabric/exporter/` 和 `azure-fabric/tests/` 只有空占位 `.gitkeep`，已被清理；**删除占位不代表放弃能力**。未来 Exporter 应作为本地业务流程开发，并按实际部署与 API 契约确定源码/测试位置，不将它伪装为 Workspace 原生 Item。

**可重建架构的首个安全开发切片**：新增 [离线环境 Preflight](infra-terraform/CODE.md#fabric-多环境离线-preflight新增静态工具不接触云资源) 和 [新账号人工前置 Runbook](../../engineering/operations/FABRIC-ACCOUNT-BOOTSTRAP-RUNBOOK.md)，保护旧 State/Workspace。**Terraform 本体与 Self-Runner 部署仍保持原状，跨 Tenant 自动部署尚未实现。**

## 源码导航、安全与验收

- [总 CODE](CODE.md)：跨组件源码归属，细节交给各组件 CODE；[Terraform CODE](infra-terraform/CODE.md)：七个 Root/Module、Bootstrap、IAM 和执行入口。
- [Terraform ARCHITECTURE](infra-terraform/ARCHITECTURE.md)：State/OIDC/Import/权限及 **2026-10-15/16 历史 Plan-only Run**。
- [全局数据流](../../architecture/DATA-FLOW.md) · [Safe Operations](../../engineering/operations/SAFE-OPERATIONS.md) · [当前项目状态](../../engineering/status/PROJECT-STATUS.md)。

[Self-Runner Azure-Infra-TF](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/.github/workflows/azure-infra.yaml) 当前正式执行路径为 `healthcare/azure-fabric/infra-terraform/components/$COMPONENT`。旧 `azure/infra-terraform/` 已从 Main 退役、历史可追溯。**该工作流存在 Apply 选项不等于已获得授权；本文档迁移未运行 Plan/Apply/Destroy。**
