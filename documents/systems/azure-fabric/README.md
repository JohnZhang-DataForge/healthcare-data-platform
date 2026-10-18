---
status: active
scope: azure-fabric-system-overview
last_verified: 2026-10-16
source_sha: ddc111db235f9788a08e1b7a6132730e3857707c
---

# Azure / Microsoft Fabric — OMOP 云端分析副本

Azure/Fabric 与本地 Data Platform 是**平级子系统**。本地 PostgreSQL OMOP 是权威数据源；未来通过只读快照导出到现有 Azure Blob Landing，再由 Fabric Data Pipeline 编排 PySpark Notebook，将经过校验的数据加载至 OneLake Lakehouse。

**注意状态边界：**以上是既定的 OneLake-first 目标架构，**不是云端业务链路已经验收**。现有 Terraform 已建立资源定义，七个组件在新源码路径下的 Plan-only 回归通过；不代表执行了 Apply，也不代表 Notebook/Pipeline 已运行或 Delta 已入库。Warehouse 属于可选后续能力。

## 一、源码结构与组件归属

[Azure/Fabric 源码总入口](../../../azure-fabric/README.md) 目前只有两个主要源码区域：

| 源码位置 | 职责与相关组件文档 | 当前实现状态 |
| --- | --- | --- |
| [`infra-terraform/`](../../../azure-fabric/infra-terraform/README.md) | 七个独立 Terraform Root、配套 Module、权限及远程 State | IaC 已存在；新路径七组件 Plan-only 通过，**无 Apply 结论** |
| [`workspaces/healthcare-omop/notebooks/`](../../../azure-fabric/workspaces/healthcare-omop/notebooks/) | [Notebooks 说明](notebooks/README.md) · [源码地图](notebooks/CODE.md)；负责快照读取、Schema/DQ/PK/FK 校验与 Delta 写入 | 只有空目录占位；没有真实 `*.Notebook/` 原生 Item |
| [`workspaces/healthcare-omop/pipelines/`](../../../azure-fabric/workspaces/healthcare-omop/pipelines/) | [Pipelines 说明](pipelines/README.md) · [源码地图](pipelines/CODE.md)；负责参数、编排、监控与失败阻断 | 只有空目录占位；没有真实 `*.DataPipeline/` 原生 Item |

`healthcare-omop` 是**已有 Fabric Workspace 的名称**，不是需要新建的 Workspace。仓库下的 `workspaces/` 只是未来 Fabric Git Integration 的源码目录；建目录不会建立 Fabric Item，也不代表已经连接 Git。Terraform 定义与 Fabric 原生 Git Item 必须先确定资源 ID 和**唯一交付责任方**，不能同时独立覆盖同一个 Item。

## 二、数据流与职责边界

```text
本地 PostgreSQL OMOP（权威库）
  → 一致性只读 Exporter + 不可变 Manifest（未来开发）
  → 已有 Azure Blob 快照 Landing
  → Fabric Data Pipeline（未来业务源码：workspaces/.../pipelines/）
  → Fabric PySpark Notebook（未来业务源码：workspaces/.../notebooks/）
  → OneLake Lakehouse / Delta（云端分析副本）
```

当前 [Terraform Notebook Bootstrap](../../../azure-fabric/infra-terraform/modules/notebook/definitions/notebook-content.py) 故意抛出 `RuntimeError`；[Pipeline 的 Fail Activity](../../../azure-fabric/infra-terraform/modules/data-factory/definitions/pipeline-disabled.json) 则在未配置真实 Notebook GUID 时主动失败。**这两者都不是已实施的业务 ETL**，不可直接复制到空的 Fabric Git Item 目录并宣称 E2E 已通。

本地只读 Exporter、Manifest 完整性校验、云端幂等写入和独立跨平台 Reconciliation 仍需实现。旧 `azure-fabric/exporter/`、`azure-fabric/tests/` 只是已删除的空占位；删除占位不代表放弃这些能力，它们也不是 Fabric Workspace 原生 Item。

## 三、原 Azure Terraform README 的知识归属

旧 [`azure/infra-terraform/README.md`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/41be1aba4d8b730b2a9e17fadfc0450e6aec5095/azure/infra-terraform/README.md) 已从 Main 退役，但可在固定 Git 快照中阅读；其长期有效内容已分类整理，不在 `documents/` 重复全文：

| 原文主题 | 当前主要查阅位置 |
| --- | --- |
| 系统定位、OneLake-first 与未实施范围 | 本文件、[系统源码总入口](../../../azure-fabric/README.md) |
| 七个 Terraform Root/Module 与开发入口 | [新 Terraform README](../../../azure-fabric/infra-terraform/README.md) |
| IAM 权属、OIDC、State 隔离、Import、旧 Smoke 注意事项 | [Terraform 技术架构](../../../azure-fabric/infra-terraform/docs/ARCHITECTURE.md) |
| 实际源码路径、Bootstrap、模块之间的依赖 | [Azure/Fabric CODE.md](CODE.md) |
| 历史 Plan Run/新路径回归证据 | [Terraform 技术架构的验收记录](../../../azure-fabric/infra-terraform/docs/ARCHITECTURE.md#verified-plan-evidence) |
| 已完成与待开发状态 | [项目状态](../../engineering/status/PROJECT-STATUS.md) |

**维护原则：** `documents/` 负责给人和 Agent 阅读的系统说明与源码导航；Terraform 目录中的 README/技术文档负责 IaC 的实现细节和安全限制，不再复制另一份 CURRENT/NEXT。旧 `azure/` 已从 Main 删除，当前 Terraform 仅以 `azure-fabric/infra-terraform/` 为源码入口。

Self-Runner 已指向 `azure-fabric/infra-terraform/`。历史七个组件的 Plan-only 证据不构成资源创建或业务入库的证据；本次文档整理也不触发 Plan/Apply。

**继续阅读：** [CODE.md](CODE.md) · [Notebooks](notebooks/README.md) · [Pipelines](pipelines/README.md) · [整体数据流](../../architecture/DATA-FLOW.md) · [安全操作规范](../../engineering/operations/SAFE-OPERATIONS.md)。

