---
status: active
scope: azure-fabric-pipelines-source-map
last_verified: 2026-10-16
source_sha: ddc111db235f9788a08e1b7a6132730e3857707c
---

# Fabric Data Pipelines — CODE 源码地图

**归属源码根目录：**[`azure-fabric/workspaces/healthcare-omop/pipelines/`](../../../../azure-fabric/workspaces/healthcare-omop/pipelines/)。

该目录当前只有 `.gitkeep` 占位文件，**尚无真实 Data Pipeline Item 源码**。


**2026-10-21：**新增 `johnzhang-test` Trial Smoke 原生 Pipeline 源码（Git 中已存在，**未通过 fabric-cicd 云端发布**）。`healthcare-omop` 原目录仍只有历史占位项。

- [`pl_trial_smoke.DataPipeline/.platform`](../../../../azure-fabric/workspaces/johnzhang-test/pipelines/pl_trial_smoke.DataPipeline/.platform) — 稳定 logicalId / Pipeline Item 身份。
- [`pl_trial_smoke.DataPipeline/pipeline-content.json`](../../../../azure-fabric/workspaces/johnzhang-test/pipelines/pl_trial_smoke.DataPipeline/pipeline-content.json) — 仅一个 `TridentNotebook` 活动，使用同 Workspace 的 Notebook logicalId，不含自动调度。
- [工作空间级源码说明](../../../../azure-fabric/workspaces/johnzhang-test/README.md) · [静态测试](../../../../.github/quality/tests/test_fabric_native_smoke_source.py)。

## 实际拥有的 Fabric 原生源码文件

| 原生源码文件 | 功能 |
| --- | --- |
| （暂无；待确认 Item 身份和唯一部署责任方后，再登记真实 `*.DataPipeline/` 文件） | 尚未实现 |

**以后如何更新：**新增真实 Data Pipeline Item 时，应将其实际的 `.platform`、`pipeline-content.json` 及其他生成文件以**逐文件相对 Markdown 链接**登记在上表。静态 CODE-map CI 会检查源码完整性和归属；新增、删除或迁移源码时，必须在同一 PR 更新本 `CODE.md`。

Terraform 中的[默认失败保护定义](../../../../azure-fabric/infra-terraform/modules/data-factory/definitions/pipeline-disabled.json)和[Notebook Activity 模板](../../../../azure-fabric/infra-terraform/modules/data-factory/definitions/pipeline-notebook.json)继续由[总 CODE.md](../CODE.md)中的基础设施部分导航；它们不是已运行的 Fabric 原生 Git Item。

**继续阅读：**[Pipelines 职责](README.md) · [Notebooks CODE.md](../notebooks/CODE.md) · [Azure/Fabric 概览](../README.md)。
