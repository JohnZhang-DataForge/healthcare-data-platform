---
status: active
scope: azure-fabric-notebooks-overview
last_verified: 2026-10-16
source_sha: ddc111db235f9788a08e1b7a6132730e3857707c
---

# Fabric Notebooks — 快照校验与 Delta 加载

Notebooks 组件属于现有的 `healthcare-omop` Fabric Workspace。未来真正的 Fabric 原生 Notebook Item 源码保存在 [`azure-fabric/workspaces/healthcare-omop/notebooks/`](../../../../azure-fabric/workspaces/healthcare-omop/notebooks/)，其中 `ingestion/` 用于组织云端数据接入 Notebook。

## 组件职责

未来 Notebook 从 Data Pipeline 接收 `export_id` 和 `manifest_uri`，读取**已由本地 PostgreSQL 导出**并发布至 Azure Blob 的 OMOP 快照，核验 Manifest 状态、文件哈希、行数、Schema、主键唯一性及外键关系，完成有失败保护、可重跑的 OneLake Delta 加载。

Notebook **不重新执行**本地 Synthea、Canonical 或 OMOP 映射。Pipeline 负责编排；Notebook 负责 PySpark 数据处理和内部数据质量检查；最终跨平台独立对账属于另外的验收能力。

## 当前状态与未来源码

**当前状态：业务 Notebook 尚未开发。** `ingestion/` 目前只有 `.gitkeep`，没有真正的 `*.Notebook/` Item，且仓库目录本身不证明 Fabric Git Integration 已连接。

现有 [Terraform Notebook Bootstrap](../../../../azure-fabric/infra-terraform/modules/notebook/definitions/notebook-content.py) 会故意抛出 `RuntimeError`，属于基础设施的安全占位代码，**不属于此处未来的业务 Notebook 源码**。

开始接入真实 Item 时，须保留 Fabric 生成的 `.platform`、`notebook-content.py` 等真实文件，核对现有 Notebook GUID、Runtime 和授权，并确定由 Fabric Git 还是 Terraform 负责部署，避免双重管理。不能为了补齐目录而手工伪造 Item 元数据。

**相关入口：** [Notebooks CODE.md](CODE.md) · [Pipelines](../pipelines/README.md) · [Azure/Fabric 系统](../README.md) · [Azure/Fabric 总源码地图](../CODE.md)。
