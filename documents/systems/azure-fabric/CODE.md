---
status: active
scope: azure-fabric-source-map
last_verified: 2026-10-18
source_sha: 8ad52828599ae95cda95eda4d888fc601ebfdfdc
---

# Azure / Microsoft Fabric — CODE / 源码总导航

> **系统级 CODE 只负责跨组件源码归属；详细源文件导航放在对应组件 CODE.md。** 功能和架构见 [系统 README](README.md)，真实进度只看 [PROJECT-STATUS](../../engineering/status/PROJECT-STATUS.md)。源码位置存在不代表资源已 Apply 或业务端到端成功。

## 组件源码归属

| 组件 | 源码目录 | 唯一组件源码地图 | 约束 |
| --- | --- | --- | --- |
| Terraform | [`azure-fabric/infra-terraform/`](../../../azure-fabric/infra-terraform/) | [Terraform CODE.md](infra-terraform/CODE.md) · [安全设计和历史 Plan](infra-terraform/ARCHITECTURE.md) | 七个 Root/Module，IAM、远程 State、Fabric Item Bootstrap；未证明 Apply |
| Notebooks | [`workspaces/healthcare-omop/notebooks/`](../../../azure-fabric/workspaces/healthcare-omop/notebooks/) | [Notebooks CODE.md](notebooks/CODE.md) | 仅 `.gitkeep` 占位；真实 Item 需保留 Fabric 自动生成的 `.platform` |
| Pipelines | [`workspaces/healthcare-omop/pipelines/`](../../../azure-fabric/workspaces/healthcare-omop/pipelines/) | [Pipelines CODE.md](pipelines/CODE.md) | 仅 `.gitkeep` 占位；Fabric Pipeline Item 不等于独立 Azure Data Factory Account |

## 跨组件依赖与源码边界

- [Self-Runner Azure-Infra-TF Workflow](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/.github/workflows/azure-infra.yaml) 正式执行 `fabric-workspace/<workspace_name>/<resource_type>/`，而 [Azure-Infra-Shared-TF](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/.github/workflows/azure-infra-shared.yaml) 独立执行 `shared-infra/storage/`。旧 `components/` 路由已经停用；Storage Plan 真实成功，Workspace Plan 因 Runner 缺 Capacity GUID 在预检阶段阻断。
- Terraform [Notebook 安全 Bootstrap](../../../azure-fabric/infra-terraform/modules/notebook/definitions/notebook-content.py) 和 [Pipeline Fail Activity](../../../azure-fabric/infra-terraform/modules/data-factory/definitions/pipeline-disabled.json) **归 Terraform 管理**；所有 Root/Module、Provider 和 IAM 文件请参阅 [Terraform CODE.md](infra-terraform/CODE.md)，此处不复制整张 Terraform 文件表。
- 本地只读 OMOP Exporter、不可变 Manifest、云端 Delta Loader、独立对账尚待开发；过去空的 `exporter/` 和 `tests/` 占位已删除，未来源码归属须依据真实运行位置另行确定。
- Terraform State、已有 Workspace/Blob/Entra 角色以及 Fabric Item GUID 应单独核验。历史七 Root Plan-only [验收记录](infra-terraform/ARCHITECTURE.md#verified-plan-evidence)不代表云端业务 E2E。

## CODE.md 维护要求

Fabric Notebook/Pipeline 新增、删除、移动或改名源码时，**同一 PR** 修改所属 [Notebooks CODE](notebooks/CODE.md) 或 [Pipelines CODE](pipelines/CODE.md)，使用现有 CODE-map CI 验证。Terraform Root/Module、Provider、权限和主要执行入口改变时同步更新 [Terraform CODE](infra-terraform/CODE.md) 并审查 IAM/State/Import；现有 CI **不保证逐一覆盖每个 .tf 文件**。

Azure/Fabric 的 README/CODE/技术说明都在 `documents/systems/azure-fabric/`；源码区只保留真正的程序、Terraform 配置、模板以及 Fabric Item 生成的机器可读元数据，不维护第二份说明性文档。

## Trial-only fabric-cicd publisher (2026-10-21)

- [`azure-fabric/deployment/trial_smoke_publisher.py`](../../../azure-fabric/deployment/trial_smoke_publisher.py): scope-validated Fabric Trial Notebook/Pipeline Git-native publishing facade; `validate` no cloud calls; `publish` requires independently read live Workspace/Lakehouse Terraform outputs, exact confirmation, Fabric identity, fresh item inventory and post-publish API readback. Does not delete or orphan-cleanup Items; initial publish rejects pre-existing same-name Items until ownership resolution.
- [offline tests](../../../.github/quality/tests/test_fabric_trial_smoke_publisher.py) and [static CI](../../../.github/workflows/fabric-trial-smoke-publisher-static.yml): no Fabric API nor Terraform Remote State access in CI. Real Self-Runner pin/authorization will be separate reviewed change.
