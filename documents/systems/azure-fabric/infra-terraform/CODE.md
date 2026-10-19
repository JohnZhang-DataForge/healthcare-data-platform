---
status: active
scope: azure-fabric-terraform-source-map
last_verified: 2026-10-18
source_sha: 8ad52828599ae95cda95eda4d888fc601ebfdfdc
---

# Azure / Fabric Terraform — CODE 源码导航

> **唯一 Terraform 组件源码地图（ACTIVE）**。本页按 8ad52828599ae95cda95eda4d888fc601ebfdfdc 的 Git 树核对实际存在的文件，只记录源码归属、入口和关联依赖。功能介绍见 [README.md](README.md)，IAM/State/操作安全及历史验收见 [ARCHITECTURE.md](ARCHITECTURE.md)。**任何源码链接都不意味着已部署或允许 Apply**。

## Terraform 根目录与工作流

- [Terraform 源码根目录](../../../../azure-fabric/infra-terraform/) · [`.gitignore`](../../../../azure-fabric/infra-terraform/.gitignore)
- [Self-Runner Azure-Infra-TF Workflow](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/.github/workflows/azure-infra.yaml)：从 Healthcare `main` 检出源代码，`root=healthcare/azure-fabric/infra-terraform/components/$COMPONENT`；手动选择 `environment=dev` 与 `operation=plan|apply`（默认 Plan）。
- **Root/Module 关系**：每个 `components/<name>/modules.tf` 调用 `../../modules/<name>`，Root 保存 `versions.tf`、`providers.tf`、`variables.tf`、`outputs.tf`、`iam.tf` 和 `environments/dev.tfvars`。每个 Root 远程 State key 独立为 `dev/<component>.tfstate`。

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

## Fabric 多环境离线 Preflight（新增静态工具，不接触云资源）

- [fabric_environment_preflight.py](../../../../azure-fabric/infra-terraform/tools/fabric_environment_preflight.py)：纯本地验证新 Fabric 环境 JSON、禁止旧 `dev` State Key / 旧 Workspace 冲突、输出隔离的 `fabric/<environment>/<component>.tfstate` 目标；**不运行 Terraform，不访问 Azure/Fabric**。
- [fabric-environment.example.json](../../../../azure-fabric/infra-terraform/environments/fabric-environment.example.json)：故意包含无效占位符的非部署示例；真实配置不提交 Git，Secret 永远由受保护变量提供。
- [test_fabric_environment_preflight.py](../../../../azure-fabric/infra-terraform/tests/test_fabric_environment_preflight.py)：标准库 Unit Tests，覆盖合法和失败输入、状态隔离、敏感字段阻断。
- [新账号人工前置 Runbook](../../../engineering/operations/FABRIC-ACCOUNT-BOOTSTRAP-RUNBOOK.md)：Tenant/Capacity/RBAC/OIDC/Blob Reader 的手工工作和旧 Workspace 安全处理。

**本轮代码不修改上方七个 Terraform Root 或正式 Self-Runner `azure-infra.yaml`，并不意味着跨租户 IaC 已可使用。** 后续独立 Change 才能将 Preflight 接入受控 Deployment Workflow。

## 重要配置和权限入口

- [Storage IAM](../../../../azure-fabric/infra-terraform/modules/storage/iam.tf) 与 [Workspace IAM](../../../../azure-fabric/infra-terraform/modules/workspace/iam.tf)：Blob 数据权限、Workspace 成员权与 Azure 管理平面权限必须分别核对。
- [OneLake IAM](../../../../azure-fabric/infra-terraform/modules/onelake/iam.tf) 与 [Provider 配置](../../../../azure-fabric/infra-terraform/components/onelake/providers.tf)：OneLake Data Access Security 为预览能力；默认空授权不等于已授权。
- [Foundation IAM](../../../../azure-fabric/infra-terraform/modules/foundation-iam/iam.tf)：只管理可选共享 RG 权限；不能自动接管现存 Service Principal/OIDC。
- [Workspace State/Import 约束](ARCHITECTURE.md#iam-and-existing-resource-boundaries)：既有资源不因 Terraform 配置出现便可安全直接 Apply。
- [历史七组件 Plan-only 证据](ARCHITECTURE.md#verified-plan-evidence)：结果仅证明对应历史 SHA/Run 的 Plan，**不是现时部署/数据端到端验证**。

**维护要求**：未来调整 Root/Module/Bootstrap 的文件名、真实入口或权限所有者时，应在同一 PR 更新本 CODE.md。本次文档迁移未改动任何 `.tf`、`.tfvars`、`.json`、`.py` 或 Workflow。

## 新环境 Backend / Fabric 身份离线合同（尚未部署）

- [fabric_deployment_target.py](../../../../azure-fabric/infra-terraform/tools/fabric_deployment_target.py)：使用已验证环境 JSON 和明确区分的 Tenant A Backend / Tenant B Fabric 客户端 UUID，生成无副作用的 Backend State Key 与部署摘要；**不运行 Terraform、不使用 OIDC Token，也不访问云端**。
- [test_fabric_deployment_target.py](../../../../azure-fabric/infra-terraform/tests/test_fabric_deployment_target.py)：覆盖跨租户/同租户独立主体、身份不匹配、共用身份、旧 State Key 和 Secret 字段拒绝。
- 此工具不是 Terraform Backend 的真实初始化器；OIDC federated credentials、RBAC、State 是否已被使用以及远端 Workspace 存在性仍未验证。

## 新环境 AzureRM Backend 参数离线生成（Task 2.1 第一批）

- [fabric_backend_config.py](../../../../azure-fabric/infra-terraform/tools/fabric_backend_config.py)：基于已验证身份和新环境，逐组件生成 `johnzhang/tfstate` 的 `fabric/<env>/<component>.tfstate` 后端参数预览；不写文件、不执行 Terraform、不会访问 Remote State。
- [test_fabric_backend_config.py](../../../../azure-fabric/infra-terraform/tests/test_fabric_backend_config.py)：检验三 Root 独立 Key、跨环境隔离、拒绝旧 State、非授权组件、错误 Storage、Secret/输出注入。
- **实施边界**：后续仍需独立 Terraform Root 和受控执行 Workflow；此处没有实际初始化 Backend 或验证真实 State 不存在。

## 独立新环境 Terraform Root 骨架（Task 2.1 第二批）

- [New-environments README](../../../../azure-fabric/infra-terraform/new-environments/README.md)：独立 Root 的严格非部署边界及身份分工。
- [Workspace Root](../../../../azure-fabric/infra-terraform/new-environments/workspace/versions.tf)、[OneLake Root](../../../../azure-fabric/infra-terraform/new-environments/onelake/versions.tf)、[Connection Root](../../../../azure-fabric/infra-terraform/new-environments/connection/versions.tf)：保留隔离的 Partial AzureRM Backend 和 Fabric OIDC Provider；Workspace、Lakehouse、Connection 均已在新环境 Root 声明受审批保护的 Resource，但**未部署**。
- [静态安全测试](../../../../azure-fabric/infra-terraform/tests/test_fabric_root_skeleton.py)：检查三 Root 必要配置，阻止提前添加资源和认证混用；GitHub-hosted CI 验证。未经单独授权绝不执行 Terraform init/plan/apply/destroy。

## 新环境 Azure Blob Connection Root（Task 2.4 第五批，仅离线源码）

- [Connection Root](../../../../azure-fabric/infra-terraform/new-environments/connection/main.tf) · [variables.tf](../../../../azure-fabric/infra-terraform/new-environments/connection/variables.tf) · [outputs.tf](../../../../azure-fabric/infra-terraform/new-environments/connection/outputs.tf)：定义唯一的 `fabric_connection.azure_blob`，凭据选项为 ServicePrincipal + **现存 Key Vault Connection Secret Reference** 或独立验证的 WorkspaceIdentity；只输出新 Connection ID。
- [Connection 安全和 Provider v1.13.0 Schema](../../../../azure-fabric/infra-terraform/new-environments/connection/SCHEMA.md)：冻结 `AzureBlobs/AzureBlobs` 和 `account/domain`，要求库存、domain、Blob Reader 权限、Reader/Fabric/Backend 三身份以及手工审批。所有审批默认 false；`prevent_destroy` 和不跳过真实连接测试。凭据值不进入 HCL/State 输入。
- [Connection Root 离线测试](../../../../azure-fabric/infra-terraform/tests/test_fabric_connection_root.py) 和 [独立 Root 测试](../../../../azure-fabric/infra-terraform/tests/test_fabric_root_skeleton.py)：静态守门/错误回归，经 [Fabric Environment Preflight CI](../../../../.github/workflows/fabric-environment-preflight.yml) 执行。
- **状态**：仅在活跃 OpenSpec `implement-fabric-multi-environment-terraform` 内实现本次源码。未实测 Provider Init/Plan/Apply、Remote State、Fabric Connection 库存、Reader RBAC/OIDC、跨租户 WorkspaceIdentity；新 Root 不连接旧 `dev/*.tfstate`，与 Self-Runner 旧工作流独立。不得把源码声明视为真实 Azure/Fabric 资源。
