---
status: active
scope: azure-fabric-source-map
last_verified: 2026-10-16
source_sha: ddc111db235f9788a08e1b7a6132730e3857707c
---

# Azure / Microsoft Fabric — CODE 源码导航

本文件记录**当前 Git Main 中真实存在的 Azure/Fabric 源码和配置入口**，不把计划中的功能当成已实现能力。系统职责见 [README](README.md)；全项目代码命名规则见 [开发规范](../../engineering/development/CODE-ORGANIZATION-AND-NAMING.md)，真实环境操作须遵守[安全操作规范](../../engineering/operations/SAFE-OPERATIONS.md)。

当前 Terraform 的执行源码位于 `azure-fabric/infra-terraform/`。原 `azure/infra-terraform/` 尚保留但不应并行执行；Self-Runner 已切换到新目录，七个组件在新路径下的 Plan-only 检查通过。Fabric 原生 Notebook/Pipeline 的源码归属由下方两个组件 CODE.md 分别维护。

## 一、Terraform 基础设施导航

[Terraform 开发入口](../../../azure-fabric/infra-terraform/README.md) · [IAM、OIDC、State 技术设计及历史 Plan](../../../azure-fabric/infra-terraform/docs/ARCHITECTURE.md) · [Git 忽略配置](../../../azure-fabric/infra-terraform/.gitignore)

`components/<component>/` 是具有独立远程 Terraform State 的 Root Module，`modules/<component>/` 是定义资源与权限的 Child Module。Root 通过相对路径 `../../modules/<component>` 引用实现。远程 State Key 保持 `dev/<component>.tfstate`，目录迁移没有改变实际资源定义或 State Key。

| Terraform 组件 | Root 与环境参数源码 | Module 实现源码 | 当前边界 |
| --- | --- | --- | --- |
| Storage | [Root](../../../azure-fabric/infra-terraform/components/storage/modules.tf) · [dev.tfvars](../../../azure-fabric/infra-terraform/components/storage/environments/dev.tfvars) | [资源定义](../../../azure-fabric/infra-terraform/modules/storage/main.tf) · [IAM](../../../azure-fabric/infra-terraform/modules/storage/iam.tf) | 复用已有 Blob Landing；新增容器 RBAC 为可选 |
| Workspace | [Root](../../../azure-fabric/infra-terraform/components/workspace/modules.tf) · [dev.tfvars](../../../azure-fabric/infra-terraform/components/workspace/environments/dev.tfvars) | [资源定义](../../../azure-fabric/infra-terraform/modules/workspace/main.tf) · [IAM](../../../azure-fabric/infra-terraform/modules/workspace/iam.tf) | Workspace 已手工创建；纳入 Terraform 管理前必须验证及 Import |
| OneLake | [Root](../../../azure-fabric/infra-terraform/components/onelake/modules.tf) · [dev.tfvars](../../../azure-fabric/infra-terraform/components/onelake/environments/dev.tfvars) | [Lakehouse](../../../azure-fabric/infra-terraform/modules/onelake/main.tf) · [IAM（Preview）](../../../azure-fabric/infra-terraform/modules/onelake/iam.tf) | Lakehouse 定义/Plan 已通过；不代表已 Apply |
| Notebook | [Root](../../../azure-fabric/infra-terraform/components/notebook/modules.tf) · [dev.tfvars](../../../azure-fabric/infra-terraform/components/notebook/environments/dev.tfvars) | [Notebook Item 定义](../../../azure-fabric/infra-terraform/modules/notebook/main.tf) · [安全占位代码](../../../azure-fabric/infra-terraform/modules/notebook/definitions/notebook-content.py) | 仅 Bootstrap；故意抛出异常，没有业务 ETL |
| Data Factory | [Root](../../../azure-fabric/infra-terraform/components/data-factory/modules.tf) · [dev.tfvars](../../../azure-fabric/infra-terraform/components/data-factory/environments/dev.tfvars) | [Data Pipeline Item 定义](../../../azure-fabric/infra-terraform/modules/data-factory/main.tf) | Fabric Data Pipeline Item，不是 `azurerm_data_factory`；尚未业务运行 |
| Warehouse | [Root](../../../azure-fabric/infra-terraform/components/warehouse/modules.tf) · [dev.tfvars](../../../azure-fabric/infra-terraform/components/warehouse/environments/dev.tfvars) | [资源定义](../../../azure-fabric/infra-terraform/modules/warehouse/main.tf) · [IAM 边界](../../../azure-fabric/infra-terraform/modules/warehouse/iam.tf) | 可选后续组件，不是 OneLake-first MVP 前置条件 |
| Foundation IAM | [Root](../../../azure-fabric/infra-terraform/components/foundation-iam/modules.tf) · [dev.tfvars](../../../azure-fabric/infra-terraform/components/foundation-iam/environments/dev.tfvars) | [共享 IAM](../../../azure-fabric/infra-terraform/modules/foundation-iam/iam.tf) | 管理可选的 RG 级共享权限；不重复管理组件专属授权 |

**其他 Root 文件：**各组件还包含 `versions.tf`、`providers.tf`、`variables.tf`、`outputs.tf`、`iam.tf` 等，具体职责见 [Terraform README](../../../azure-fabric/infra-terraform/README.md)。上表是直接可用的**主要源码入口**，不是声称已逐文件枚举全部 Terraform 文件；当前 CODE-map CI 对 Fabric 原生 Notebook/Pipeline 文件实施严格归属检查，但未对全部 Terraform 文件实施同等级的完整性校验。

## 二、Terraform 持有的 Fabric Bootstrap 源码

这些文件目前由 Terraform Module 引用；**不属于将来 Fabric Git Item 业务源码**。

| 实际源码文件 | 用途与安全边界 |
| --- | --- |
| [`modules/notebook/definitions/notebook-content.py`](../../../azure-fabric/infra-terraform/modules/notebook/definitions/notebook-content.py) | 参数单元 `export_id`、`manifest_uri`；故意失败的 Bootstrap，不是可执行的数据加载程序 |
| [`modules/data-factory/definitions/pipeline-disabled.json`](../../../azure-fabric/infra-terraform/modules/data-factory/definitions/pipeline-disabled.json) | Notebook GUID 未配置时触发 Fail Activity，不会假装加载成功 |
| [`modules/data-factory/definitions/pipeline-notebook.json`](../../../azure-fabric/infra-terraform/modules/data-factory/definitions/pipeline-notebook.json) | Notebook Activity 模板及参数表达式；不代表端到端已运行 |
| [`modules/data-factory/main.tf`](../../../azure-fabric/infra-terraform/modules/data-factory/main.tf) | 根据 `notebook_id` 选择失败保护或 Notebook 定义，不得绕过失败门禁 |
| [`modules/notebook/main.tf`](../../../azure-fabric/infra-terraform/modules/notebook/main.tf) | 从受版本控制的占位代码定义 Fabric Notebook Item，不包含 Exporter、DQ 或 Delta Writer |

## 三、未来 Fabric Workspace 业务源码

| 组件源码入口 | 当前状态 | 单一源码导航 |
| --- | --- | --- |
| [`workspaces/healthcare-omop/notebooks/ingestion/`](../../../azure-fabric/workspaces/healthcare-omop/notebooks/ingestion/) | 只有 `.gitkeep`，尚无 `*.Notebook/` Item | [Notebooks CODE.md](notebooks/CODE.md) |
| [`workspaces/healthcare-omop/pipelines/`](../../../azure-fabric/workspaces/healthcare-omop/pipelines/) | 只有 `.gitkeep`，尚无 `*.DataPipeline/` Item | [Pipelines CODE.md](pipelines/CODE.md) |

这里的 `healthcare-omop` 指向已有 Workspace 名称。真正接入 Fabric Git Integration 时，必须保留 Fabric 生成的 `.platform` 等元数据，并明确 Git 同步与 Terraform 的 Item 交付权属，防止两个来源覆盖同一对象。可复用的独立 Python 库及本地 Exporter 应在明确运行环境/部署方式之后单独确定源码路径，**不要塞入 Fabric 原生 Item 的元数据结构中**。

本地 OMOP 一致性只读 Exporter、Manifest、独立对账和测试仍是待开发能力；旧 `azure-fabric/exporter/`、`azure-fabric/tests/` 均只是已删除的空目录占位。初版不需要为 Reconciliation 额外建立没有执行入口的空组件目录。

## 四、Workflow、证据与维护约束

- [Azure-Infra-TF 执行器](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/.github/workflows/azure-infra.yaml) 仅在明确触发时运行，支持七个 Root、`environment=dev` 和 `operation=plan|apply`（默认 Plan）。当前实际入口为 `healthcare/azure-fabric/infra-terraform/components/$COMPONENT`，执行旧 `azure/` 副本可能与远程 State 发生冲突。
- [Terraform 验证证据](../../../azure-fabric/infra-terraform/docs/ARCHITECTURE.md#verified-plan-evidence)记录历史 Plan Run。Plan 成功并不等于 Apply、Delta 数据写入或业务 E2E 完成；不能根据本文件授予部署权限。
- [当前项目状态](../../engineering/status/PROJECT-STATUS.md) 是进度唯一权威，`CODE.md` 只负责真实源码导航。

**维护要求：**在 `workspaces/healthcare-omop/notebooks/` 或 `pipelines/` 中新增、删除、移动真实原生源码文件时，必须在**同一个 PR**更新对应组件的 `CODE.md`。CI 会检查非占位文件的缺失、失效、重复或错误归属，以及变更是否同步修改所属 CODE.md。Terraform 源码变更仍需单独审查 IAM、State、Import 和运行风险；目前 CI **尚不保证**逐一登记每个 `.tf` 文件。
