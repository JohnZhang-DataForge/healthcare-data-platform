# Systems — 系统文档总入口

> **ACTIVE**。本地 Data Platform、Azure/Fabric、Platform Portal 原有三个子系统与新建的 Showcase 契约组件均在 `documents/systems/` 维护唯一的 README/CODE 文档入口。当前已有的历史运行/Plan 证据不等于迁移过程中重新部署或实时验收。

| 子系统 | 系统总说明 | 系统 CODE 导航 | 子组件 |
| --- | --- | --- | --- |
| Local Data Platform | [README](data-platform/README.md) | [Airflow CODE](data-platform/airflow/CODE.md) / [Spark CODE](data-platform/spark/CODE.md) 等组件导航 | Synthea、Landing、Airflow、Spark、OMOP |
| Azure / Microsoft Fabric | [README](azure-fabric/README.md) | [CODE](azure-fabric/CODE.md) | Terraform、Fabric Notebooks、Pipelines |
| Platform Portal | [README](platform-portal/README.md) | [CODE](platform-portal/CODE.md) | Marquez、PostgreSQL14、Airflow OpenLineage、Spark OpenLineage |
| Healthcare Showcase（P0 契约） | [README](showcase/README.md) | [CODE](showcase/CODE.md) | 公网快照 Schema、Mock、只读展示与触发 API 契约（未部署） |

**职责区分**：Data Platform 管业务摄取/处理/OMOP 提交；Azure/Fabric 管云端分析副本；Portal 管旁路 OpenLineage/Marquez 观测。Portal 的 Airflow/Spark 子组件不是第二套业务 ETL。当前项目事实与下一步只读 [PROJECT-STATUS](../engineering/status/PROJECT-STATUS.md)，真实操作遵循 [Safe Operations](../engineering/operations/SAFE-OPERATIONS.md)。

旧 `documents/components/platform-portal/`、`documents/components/azure-fabric/` 及 `azure/` 已从 Main 退役，固定历史 Commit 可追溯；源码目录只保留真实配置、程序、Manifest 和测试，说明文档收口在 `documents/systems/`。
