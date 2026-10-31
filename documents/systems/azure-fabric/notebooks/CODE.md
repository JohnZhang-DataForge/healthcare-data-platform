---
status: active
scope: azure-fabric-notebooks-source-map
last_verified: 2026-10-16
source_sha: ddc111db235f9788a08e1b7a6132730e3857707c
---

# Fabric Notebooks — CODE 源码地图

**真实 Native Item 归属：** `azure-fabric/workspaces/healthcare-omop/nb_fhir_ingest.Notebook/`（Fabric Git Integration 自动生成的根级目录）。[`notebooks/ingestion/`](../../../../azure-fabric/workspaces/healthcare-omop/notebooks/ingestion/) 为旧占位目录，不是 Native Item 定义。

**2026-10-31 真实初始化完成：** Fabric Portal 将 `nb_fhir_ingest` Item 原生定义同步到 GitHub `fabric/native-bootstrap-20261031`，Commit `a6c3d0d6`；`.platform` 的 logicalId 非零。Notebook 内容当前只有 `# No content`，不意味着 P2 FHIR Spark ETL 已发布。


**2026-10-31：**旧 `johnzhang-test` Trial Native Notebook/Pipeline Smoke 及其测试已正式从源码树退休（Self-Runner [PR #350](https://github.com/JohnZhang-DataForge/Self-Runner/pull/350)、Healthcare 清理 PR）。不再维护该测试 Workspace 的原生 Item 文件。历史 Item 定义可查阅 [退役前固定 Git 历史](https://github.com/JohnZhang-DataForge/healthcare-data-platform/tree/e4640eb4ce4edd8570ca60c9ad2c1b6152941743/azure-fabric/workspaces/johnzhang-test)，不得照旧发布。**曾通过 Terraform Apply 的 Workspace/Lakehouse 尚未确认云端删除，等待独立 State-aware teardown。**

## 实际拥有的 Fabric 原生源码文件

| 原生源码文件 | 功能 |
| --- | --- |
| [nb_fhir_ingest.Notebook/.platform](../../../../azure-fabric/workspaces/healthcare-omop/nb_fhir_ingest.Notebook/.platform) | Fabric Git 同步的真实 Notebook Item 元数据；不要手工改 logicalId |
| [nb_fhir_ingest.Notebook/notebook-content.py](../../../../azure-fabric/workspaces/healthcare-omop/nb_fhir_ingest.Notebook/notebook-content.py) | 已将 P2 单一实现迁入 Git Native Notebook，含 Fabric cell、参数和启动 HOLD；尚未手工 Update from Git |

**以后如何更新：**每增加一个真实 Notebook Item，应在上表使用**指向实际文件的相对 Markdown 链接**登记其真实 `.platform`、`notebook-content.py` 及其他生成文件。静态 CODE-map CI 会检查源码完整性、链接归属，并要求新增、删除或迁移文件时在同一个 PR 更新本 `CODE.md`。

现有 [Terraform Notebook Bootstrap](../../../../azure-fabric/infra-terraform/modules/notebook/definitions/notebook-content.py) 故意抛出异常，由 [Azure/Fabric 总 CODE.md](../CODE.md) 导航。不能把它直接改名放入 Workspace 并声称是 Fabric Git 已同步的 Notebook。

**继续阅读：**[Notebooks 职责](README.md) · [Pipelines CODE.md](../pipelines/CODE.md) · [Azure/Fabric 概览](../README.md)。
