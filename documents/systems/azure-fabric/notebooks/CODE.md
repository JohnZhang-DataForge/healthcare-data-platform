---
status: active
scope: azure-fabric-notebooks-source-map
last_verified: 2026-10-16
source_sha: ddc111db235f9788a08e1b7a6132730e3857707c
---

# Fabric Notebooks — CODE 源码地图

**归属源码根目录：**[`azure-fabric/workspaces/healthcare-omop/notebooks/`](../../../../azure-fabric/workspaces/healthcare-omop/notebooks/)。

当前 `ingestion/` 只有 `.gitkeep` 占位文件，**尚无真实 Notebook Item 源码**；此处的“未实现”不包括基础设施下现存的 Bootstrap。

## 实际拥有的 Fabric 原生源码文件

| 原生源码文件 | 功能 |
| --- | --- |
| （暂无；待确定 Item 身份、Git Integration 与唯一部署责任方后，再登记真实 `*.Notebook/` 文件） | 尚未实现 |

**以后如何更新：**每增加一个真实 Notebook Item，应在上表使用**指向实际文件的相对 Markdown 链接**登记其真实 `.platform`、`notebook-content.py` 及其他生成文件。静态 CODE-map CI 会检查源码完整性、链接归属，并要求新增、删除或迁移文件时在同一个 PR 更新本 `CODE.md`。

现有 [Terraform Notebook Bootstrap](../../../../azure-fabric/infra-terraform/modules/notebook/definitions/notebook-content.py) 故意抛出异常，由 [Azure/Fabric 总 CODE.md](../CODE.md) 导航。不能把它直接改名放入 Workspace 并声称是 Fabric Git 已同步的 Notebook。

**继续阅读：**[Notebooks 职责](README.md) · [Pipelines CODE.md](../pipelines/CODE.md) · [Azure/Fabric 概览](../README.md)。
