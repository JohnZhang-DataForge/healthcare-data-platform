# Azure + Microsoft Fabric / 文档入口

> **当前状态：PLANNED — NOT DEPLOYED / NOT VERIFIED（2026-10-14）**。本目录针对本地已验收 OMOP CDM 向 Azure/Fabric 的最小云端分析扩展，**不**表示 Azure/Fabric 已经部署。

## 首先阅读

- [Azure/Fabric 最小实现方案 v1.0](AZURE-FABRIC-MINIMAL-IMPLEMENTATION-PLAN-v1.0.zh-CN.md) — 架构、四个组件、Terraform、Self-Runner、远程 State、Entra/OIDC、身份权限、成本、阶段和验收。
- [全项目 Agent 文档入口](../README.md) — 本地最新状态和入口。
- [TASK 状态](../tasks/TASK-STATUS.md) — 当前业务开发权威状态；Azure 计划与 TASK005 独立。

**Cloud MVP：** 本地 OMOP PostgreSQL → Python 一致性快照 → Azure Blob/ADLS Gen2 → Fabric Data Factory + PySpark Notebook → Fabric Warehouse OMOP 分析副本。云端不重新实施本地 ETL。

**下一步：AZ-00 READ ONLY** — 只读确认 Azure Subscription / Fabric 资格、已有 Self-Runner Workflow、Runtime 和角色；实际创建 Azure 资源须另行授权。

> 云端方案以节省成本、最小可运行 Demo、证据真实、与本地现有平台零破坏为原则。
