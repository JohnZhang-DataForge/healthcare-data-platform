---
status: active
scope: azure-fabric-pipelines-overview
last_verified: 2026-10-16
source_sha: ddc111db235f9788a08e1b7a6132730e3857707c
---

# Fabric Data Pipelines — 编排与失败控制

Pipelines 组件属于现有的 `healthcare-omop` Fabric Workspace。未来 Fabric 原生 Data Pipeline Item 的源码保存在 [`azure-fabric/workspaces/healthcare-omop/pipelines/`](../../../../azure-fabric/workspaces/healthcare-omop/pipelines/)。

## 组件职责

未来 Data Pipeline 接收 `export_id`、`manifest_uri`，调用真实的 [Fabric Notebook](../notebooks/README.md)，处理执行顺序、任务参数、运行监控和失败阻断。只有 Notebook 的实际数据处理与必要验收完成后，才允许报告批次加载成功。

这里的 **Fabric Data Pipeline Item** 不是单独的 Azure Data Factory 服务资源，也不承担 Notebook 内部的 PySpark 转换逻辑。

## 当前状态与未来源码

**当前状态：业务 Pipeline 尚未开发。** 本目录现在只有 `.gitkeep` 占位，没有 `*.DataPipeline/` Item，也没有通过目录操作建立 Fabric Git Integration。

Terraform 目前保存了[默认 Fail Activity 定义](../../../../azure-fabric/infra-terraform/modules/data-factory/definitions/pipeline-disabled.json)和[未实际执行的 Notebook Activity 模板](../../../../azure-fabric/infra-terraform/modules/data-factory/definitions/pipeline-notebook.json)。真实 Notebook GUID 与处理程序到位前，必须保留失败保护，不能改成空的成功执行。

新增原生 Item 时，应保留 Fabric 实际生成的 `.platform`、`pipeline-content.json` 等文件，明确 Item 身份和由 Fabric Git / Terraform 哪一方负责交付，防止配置漂移或双重覆盖。

**相关入口：** [Pipelines CODE.md](CODE.md) · [Notebooks](../notebooks/README.md) · [Azure/Fabric 系统](../README.md) · [源码根目录](../../../../azure-fabric/README.md)。
