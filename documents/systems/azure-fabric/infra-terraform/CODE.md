---
status: active
scope: azure-fabric-terraform-source-map
last_verified: 2026-10-20
source_sha: null
---

# Azure / Fabric Terraform — CODE 源码导航

> **最新批准目标架构（2026-10-20）**：按真实 Workspace/资源类型部署，详见 [Fabric Terraform Workspace-scoped Architecture](../../../architecture/design/FABRIC-TERRAFORM-ENVIRONMENT-ARCHITECTURE.md) 和 [当前 OpenSpec Change](../../../../openspec/changes/organize-fabric-terraform-by-workspace/tasks.md)。Workspace、OneLake 和 Shared Storage 独立 Roots 已加入源码；Self-Runner Workflow 已切换新目录。旧 `components/` / `fabric-environment/` 保留为历史源码，不迁移旧 State。Storage 已有真实 Plan PASS，Workspace 因缺少 Capacity GUID 在预检阶段阻断；Fabric 资源未 Apply。Notebook/Pipeline 新资源由 `fabric-cicd` 独占创建和发布。

> **CODE.md 按增量列出实际源码；Task 2.1 仅新增 Workspace Root，不代表整体重构完成。**将来基于 [Module-first 新架构](../../../architecture/design/FABRIC-TERRAFORM-ENVIRONMENT-ARCHITECTURE.md) 复用已有 Modules、建立统一环境 Root 的源码提交，必须在同 PR 更新本页和相关 CI/Workflow 导航。

> **唯一 Terraform 组件源码导航（ACTIVE）**。只登记当前 Main 应有的 Root/Module；功能说明见 [README.md](README.md)，历史 State/Plan 证据见 [ARCHITECTURE.md](ARCHITECTURE.md)。此处源码存在不代表云资源已部署或批准 Apply。

## Terraform 根目录与工作流

- [Terraform 源码根目录](../../../../azure-fabric/infra-terraform/) · [`.gitignore`](../../../../azure-fabric/infra-terraform/.gitignore)
- [Self-Runner Azure-Infra-TF Workflow](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/.github/workflows/azure-infra.yaml)：正式部署入口 `fabric-workspace/<workspace_name>/<resource_type>/`；非 default Terraform CLI Workspace 同名、独立 Backend Key，单 Root Plan/Apply；[Workspace Plan Run #39538646279](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39538646279) 因 `FABRIC_CAPACITY_ID` 为空在预检阶段 FAIL，未进入 Terraform。
- [Shared Infra Workflow](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/.github/workflows/azure-infra-shared.yaml)：独立 `shared-infra/storage/`；[真实 Storage Plan Run #39538288616](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39538288616) SUCCESS，OIDC/Backend/已有资源查询 PASS，未 Apply/Destroy。
- **Root/Module 关系**：每个 `components/<name>/modules.tf` 调用 `../../modules/<name>`，Root 保存 `versions.tf`、`providers.tf`、`variables.tf`、`outputs.tf`、`iam.tf` 和 `environments/dev.tfvars`。每个 Root 远程 State key 独立为 `dev/<component>.tfstate`。

## 新 Workspace-scoped Terraform Root（Task 2.1）

- [`healthcare-omop/workspace/main.tf`](../../../../azure-fabric/infra-terraform/fabric-workspace/healthcare-omop/workspace/main.tf)：直接调用 [`modules/workspace`](../../../../azure-fabric/infra-terraform/modules/workspace/main.tf)，从 Git 父目录获得 Workspace display_name。
- [`versions.tf`](../../../../azure-fabric/infra-terraform/fabric-workspace/healthcare-omop/workspace/versions.tf)：独立 AzureRM Backend 基础 Key `fabric-workspace/workspace.tfstate`；实际 Terraform CLI Workspace 必须为 `healthcare-omop`（禁止 `default`）。
- [`outputs.tf`](../../../../azure-fabric/infra-terraform/fabric-workspace/healthcare-omop/workspace/outputs.tf)：发布真实 `fabric_workspace_id`、`fabric_workspace_name`，且使用 Output Preconditions 阻断 CLI Workspace/目录不一致的 Plan。
- [`variables.tf`](../../../../azure-fabric/infra-terraform/fabric-workspace/healthcare-omop/workspace/variables.tf) · [`iam.tf`](../../../../azure-fabric/infra-terraform/fabric-workspace/healthcare-omop/workspace/iam.tf) · [`terraform.tfvars`](../../../../azure-fabric/infra-terraform/fabric-workspace/healthcare-omop/workspace/terraform.tfvars)：要求运行时显式传入已有 Capacity GUID（`TF_VAR_capacity_id` / `-var`）；额外 IAM 默认空；不保存凭据。
- [`providers.tf`](../../../../azure-fabric/infra-terraform/fabric-workspace/healthcare-omop/workspace/providers.tf)：继承已使用的 Fabric OIDC。
- [`Workspace Root 单测`](../../../../.github/quality/tests/test_fabric_workspace_root.py) · [`Terraform CI`](../../../../.github/workflows/fabric-provider-init-validate.yml)：仅 `fmt`、`init -backend=false`、`validate` 与静态合同，不连接 Azure，不执行 Plan/Apply。
- **Self-Runner Workflow 已切换**；新 Workspace Root 尚未完成真实 Plan/Apply。旧 Root/State 原样保留。

## 新 OneLake/Lakehouse Root（Task 2.2）

- [`healthcare-omop/onelake/main.tf`](../../../../azure-fabric/infra-terraform/fabric-workspace/healthcare-omop/onelake/main.tf)：调用 [`modules/onelake`](../../../../azure-fabric/infra-terraform/modules/onelake/main.tf)，并通过 `terraform_remote_state.workspace.outputs.fabric_workspace_id` 取得上游真实 GUID；没有 State/Output 时禁止回退到静态 GUID。
- [`versions.tf`](../../../../azure-fabric/infra-terraform/fabric-workspace/healthcare-omop/onelake/versions.tf)：独立 Backend 基础 Key `fabric-workspace/onelake.tfstate`，使用 `healthcare-omop` CLI Workspace。
- [`terraform.tfvars`](../../../../azure-fabric/infra-terraform/fabric-workspace/healthcare-omop/onelake/terraform.tfvars)：Lakehouse 名称 `lh_omop_analytics` 及现有 Backend Storage 配置，不包含 Workspace GUID/Secrets；后端配置更换账号时与 Workspace Root 同步。
- [`iam.tf`](../../../../azure-fabric/infra-terraform/fabric-workspace/healthcare-omop/onelake/iam.tf) · [`providers.tf`](../../../../azure-fabric/infra-terraform/fabric-workspace/healthcare-omop/onelake/providers.tf)：OneLake IAM 默认 `{}`，保留现有 Module 的 Provider Preview 兼容设置。
- [`outputs.tf`](../../../../azure-fabric/infra-terraform/fabric-workspace/healthcare-omop/onelake/outputs.tf)：Lakehouse ID、Files/Tables 路径、角色 ID 和上游 Workspace ID。
- [`OneLake Root 合同单测`](../../../../.github/quality/tests/test_fabric_onelake_root.py) · [`Terraform CI`](../../../../.github/workflows/fabric-provider-init-validate.yml)：仅离线静态检查；**上游缺失时的真实 Plan 失败验证**仍属于 OpenSpec Task 4.3。

## Shared Infra 只读 Storage Root（Task 2.4）、跨 Root 合同（Task 2.5）

- [`shared-infra/storage/main.tf`](../../../../azure-fabric/infra-terraform/shared-infra/storage/main.tf)：仅调用现有 `modules/storage` 查询 OMOP Resource Group 与 `johnzhang` Storage Account；新增 RBAC 默认 `{}`，不创建 Storage、Capacity 或 Connection。
- [`versions.tf`](../../../../azure-fabric/infra-terraform/shared-infra/storage/versions.tf)：独立固定 AzureRM Backend Key `shared-infra/storage.tfstate`，Shared Infra 使用其自身 default CLI Workspace。
- [`terraform.tfvars`](../../../../azure-fabric/infra-terraform/shared-infra/storage/terraform.tfvars)：当前已存在的 OMOP、johnzhang、landing；不存储秘密。
- [`Shared Storage 静态 CI`](../../../../.github/workflows/fabric-provider-init-validate.yml) 和 [`跨 Root 合同测试`](../../../../.github/quality/tests/test_fabric_cross_root_contract.py)：静态验证独立 Key、Workspace 同名、Workspace→OneLake Remote State、不可回退硬编码 GUID、禁止新树管理 Notebook/Pipeline、无 Capacity 创建。远程读回与真实 Plan 由 Self-Runner Workflow 提供运行证据。
- Connection / Capacity 创建 / Shared IAM 根目录按实际需要单独实施；**本次没有额外收费资源或角色分配**。

## 七个 Root / Module 源码地图

| Root | Root、环境与 Provider | Module 与 IAM | 职责和限制 |
| --- | --- | --- | --- |
| `storage` | [Root](../../../../azure-fabric/infra-terraform/components/storage/modules.tf) · [dev.tfvars](../../../../azure-fabric/infra-terraform/components/storage/environments/dev.tfvars) · [providers.tf](../../../../azure-fabric/infra-terraform/components/storage/providers.tf) | [main.tf](../../../../azure-fabric/infra-terraform/modules/storage/main.tf) · [iam.tf](../../../../azure-fabric/infra-terraform/modules/storage/iam.tf) · [outputs.tf](../../../../azure-fabric/infra-terraform/modules/storage/outputs.tf) | 已有 Azure Storage/Blob 查询；可选 Blob RBAC；不重新创建已有账户或 Landing |
| `workspace` | [Root](../../../../azure-fabric/infra-terraform/components/workspace/modules.tf) · [dev.tfvars](../../../../azure-fabric/infra-terraform/components/workspace/environments/dev.tfvars) · [providers.tf](../../../../azure-fabric/infra-terraform/components/workspace/providers.tf) | [main.tf](../../../../azure-fabric/infra-terraform/modules/workspace/main.tf) · [iam.tf](../../../../azure-fabric/infra-terraform/modules/workspace/iam.tf) · [outputs.tf](../../../../azure-fabric/infra-terraform/modules/workspace/outputs.tf) | Fabric Workspace 与角色分配；手工 Workspace 必须先核对 State/Import |
| `onelake` | [Root](../../../../azure-fabric/infra-terraform/components/onelake/modules.tf) · [dev.tfvars](../../../../azure-fabric/infra-terraform/components/onelake/environments/dev.tfvars) · [providers.tf](../../../../azure-fabric/infra-terraform/components/onelake/providers.tf) | [main.tf](../../../../azure-fabric/infra-terraform/modules/onelake/main.tf) · [iam.tf](../../../../azure-fabric/infra-terraform/modules/onelake/iam.tf) · [outputs.tf](../../../../azure-fabric/infra-terraform/modules/onelake/outputs.tf) | Fabric Lakehouse 与预览数据访问规则；`data_access_roles={}` 默认不授予权限 |
| `notebook` | [Root](../../../../azure-fabric/infra-terraform/components/notebook/modules.tf) · [dev.tfvars](../../../../azure-fabric/infra-terraform/components/notebook/environments/dev.tfvars) · [providers.tf](../../../../azure-fabric/infra-terraform/components/notebook/providers.tf) | [main.tf](../../../../azure-fabric/infra-terraform/modules/notebook/main.tf) · [iam.tf](../../../../azure-fabric/infra-terraform/modules/notebook/iam.tf) · [outputs.tf](../../../../azure-fabric/infra-terraform/modules/notebook/outputs.tf) | Fabric Notebook Item 壳与受控 Bootstrap；Bootstrap 故意失败，非业务 ETL |
| `data-factory` | [Root](../../../../azure-fabric/infra-terraform/components/data-factory/modules.tf) · [dev.tfvars](../../../../azure-fabric/infra-terraform/components/data-factory/environments/dev.tfvars) · [providers.tf](../../../../azure-fabric/infra-terraform/components/data-factory/providers.tf) | [main.tf](../../../../azure-fabric/infra-terraform/modules/data-factory/main.tf) · [iam.tf](../../../../azure-fabric/infra-terraform/modules/data-factory/iam.tf) · [outputs.tf](../../../../azure-fabric/infra-terraform/modules/data-factory/outputs.tf) | Fabric Data Pipeline Item；未绑定真实 Notebook GUID 时保持 Fail |
| `warehouse` | [Root](../../../../azure-fabric/infra-terraform/components/warehouse/modules.tf) · [dev.tfvars](../../../../azure-fabric/infra-terraform/components/warehouse/environments/dev.tfvars) · [providers.tf](../../../../azure-fabric/infra-terraform/components/warehouse/providers.tf) | [main.tf](../../../../azure-fabric/infra-terraform/modules/warehouse/main.tf) · [iam.tf](../../../../azure-fabric/infra-terraform/modules/warehouse/iam.tf) · [outputs.tf](../../../../azure-fabric/infra-terraform/modules/warehouse/outputs.tf) | 可选 Fabric Warehouse；非首阶段必选 |
| `foundation-iam` | [Root](../../../../azure-fabric/infra-terraform/components/foundation-iam/modules.tf) · [dev.tfvars](../../../../azure-fabric/infra-terraform/components/foundation-iam/environments/dev.tfvars) · [providers.tf](../../../../azure-fabric/infra-terraform/components/foundation-iam/providers.tf) | [main.tf](../../../../azure-fabric/infra-terraform/modules/foundation-iam/main.tf) · [iam.tf](../../../../azure-fabric/infra-terraform/modules/foundation-iam/iam.tf) · [outputs.tf](../../../../azure-fabric/infra-terraform/modules/foundation-iam/outputs.tf) | Resource Group 级可选共享角色；`shared_role_bindings={}` 默认无新增授权 |

上表直接定位七个 Root 的核心文件；每个 Root 还包含 [上文说明的](../../../../azure-fabric/infra-terraform/components/) `variables.tf`、`outputs.tf`、`versions.tf` 与 `iam.tf`。**Module 定义资源与权限，Root 选择资源及参数，`dev.tfvars` 提供环境值；源码有定义不代表远程资源已实际创建。**

## Fabric Item 安全 Bootstrap（归 Terraform 管理）

| 实际源文件 | 归属与安全边界 |
| --- | --- |
| [`modules/notebook/main.tf`](../../../../azure-fabric/infra-terraform/modules/notebook/main.tf) | 定义 Terraform 管理的 Notebook Item，引用受控 Bootstrap |
| [`notebook-content.py`](../../../../azure-fabric/infra-terraform/modules/notebook/definitions/notebook-content.py) | 带 `export_id`、`manifest_uri` 参数的 Bootstrap，**故意抛出 RuntimeError** |
| [`modules/data-factory/main.tf`](../../../../azure-fabric/infra-terraform/modules/data-factory/main.tf) | 依据 Notebook ID 选择 Pipeline Item 定义 |
| [`pipeline-disabled.json`](../../../../azure-fabric/infra-terraform/modules/data-factory/definitions/pipeline-disabled.json) | 缺少 Notebook GUID 时的 Fail Activity |
| [`pipeline-notebook.json`](../../../../azure-fabric/infra-terraform/modules/data-factory/definitions/pipeline-notebook.json) | Notebook Activity 模板；不是已运行的业务 Pipeline |

这些 Bootstrap 文件不属于未来 `azure-fabric/workspaces/healthcare-omop/notebooks/` 或 `pipelines/` 中的 Fabric Git 原生业务 Item。后者由 [Notebooks CODE](../notebooks/CODE.md) 和 [Pipelines CODE](../pipelines/CODE.md) 负责；未来真实 Item 的 `.platform` 元数据和 Terraform 交付权属必须先完成审查。


## 清理后的真实源码边界

- [原有 `components/`](../../../../azure-fabric/infra-terraform/components/)：七个独立 Terraform Roots 属于历史源码，**新 Workflow 不再执行**；所有旧 State 保留，不做 Import/迁移。
- [原有 `modules/`](../../../../azure-fabric/infra-terraform/modules/)：包含 Workspace/Role Assignment、Lakehouse 及其它原先存在的模块；**此轮没有删除或重写**。
- [Provider CI](../../../../.github/workflows/fabric-provider-init-validate.yml)：从新 Bootstrap Roots 验证改为七个旧 Root/Module 的离线 `fmt`、`init -backend=false`、`validate`。
- **已移除且无现行入口**：`bootstrap/`、`tests/`、`tools/`、`new-environments/` 和只为被删 Preflight 工具服务的 `environments/fabric-environment.example.json`；**不要通过本页当作当前源码引用**。
- **未来开发**：在保留旧 Root/Module 架构的前提下，为实际需要的 Connection 增加正式 Module；新增测试与配置跟随所管理的功能，不恢复失效 Bootstrap 合同。

当前实施任务见 [`organize-fabric-terraform-by-workspace`](../../../../openspec/changes/organize-fabric-terraform-by-workspace/tasks.md)；`simplify-fabric-environment-iac` 是已过期历史 Change。

## 历史组合 Root（保留源码，但不作为新部署入口）

- [`components/fabric-environment/`](../../../../azure-fabric/infra-terraform/components/fabric-environment/README.md)：一个 Fabric/Terraform 同名 Workspace 的组合 Root；首个已有目标是 `healthcare-omop`。不重建现有 Workspace，首次真实部署前必须核对历史 State 并显式 Import。
- [`main.tf`](../../../../azure-fabric/infra-terraform/components/fabric-environment/main.tf)：调用原 `modules/workspace`、`modules/onelake` 与新 Connection Module，且通过 `terraform.workspace` 命名。
- [`outputs.tf`](../../../../azure-fabric/infra-terraform/components/fabric-environment/outputs.tf)：Workspace 名称、真实 Workspace/Lakehouse/Connection IDs 和 OneLake 路径。
- [`healthcare-omop.tfvars.example`](../../../../azure-fabric/infra-terraform/components/fabric-environment/environments/healthcare-omop.tfvars.example)：**非可直接 Apply** 的示例。真实 Capacity、Reader 权限和既有 Workspace Import 均未验证。
- [`modules/connection/`](../../../../azure-fabric/infra-terraform/modules/connection/main.tf)：可复用 Azure Blob Fabric Connection，支持 WorkspaceIdentity 或已有 Key Vault Secret Reference 的 ServicePrincipal；不创建 Storage/RBAC/Key Vault，默认禁用。
- [`Fabric Provider CI`](../../../../.github/workflows/fabric-provider-init-validate.yml)：保留七个原 Root Init/Validate，另验证组合 Root 与 Connection Module。CI 只运行 `init -backend=false` 与 Validate，未触发远端 State、Fabric Apply 或联通性验证。

**实际状态**：旧组合 Root 和 Connection 源码不再构成部署入口；新 Self-Runner 只执行 Workspace-scoped/Shared Infra 新 Roots。旧 State 不迁移。

## 部署就绪修订：当前 Workspace 参数来源

- [正式非秘密配置 `healthcare-omop.tfvars`](../../../../azure-fabric/infra-terraform/components/fabric-environment/environments/healthcare-omop.tfvars)：当前已有 Workspace 的固定源码输入；不使用 `.tfvars.example` 作为正式计划。
- 运行时从 Self-Runner 仓库变量传入 `FABRIC_CAPACITY_ID`（必须是当前真实分配的容量）和 `FABRIC_WORKSPACE_ID`（必须是已存在 Workspace 的真实 GUID）；可选 `FABRIC_LANDING_CONNECTION_CONFIG` 为非秘密 Connection JSON 元数据，凭据仍不得入 Git。
- Self-Runner 正式 `azure-infra.yaml` 输入是 `workspace_name`、`resource_type`、`operation`，只选择新 Root 与新 State。Workspace 真实 Plan 需要 Runner 预先配置当前已有 Capacity 的 GUID（`FABRIC_CAPACITY_ID`），2026-10-20 首次预检因该变量为空而阻断。
- 实际的 Terraform Workspace State、Import、Connection/Capacity/权限都需要真实授权验证；本节仅是源码导航与配置合同。
