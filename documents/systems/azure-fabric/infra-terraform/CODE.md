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

## Task 2.5 离线 CI 与 Runbook 安全收口（未完成真正部署验收）

- [Fabric Preflight Workflow](../../../../.github/workflows/fabric-environment-preflight.yml)：在 GitHub-hosted runner 使用 Terraform 1.13.0 **仅执行 `fmt -check -diff`** 检查 Connection HCL；单元测试独立检查该 Workflow 不能调用 Init/Plan/Apply/Destroy 或云端命令。不下载 Fabric Provider，不获取 OIDC Token 或访问 Remote State。
- [离线 CI 防越权测试](../../../../azure-fabric/infra-terraform/tests/test_fabric_ci_offline.py)：阻止在 Preflight Workflow 中加入带云端副作用的 Terraform/Azure/Fabric 操作。
- [新账号 Bootstrap Runbook](../../../engineering/operations/FABRIC-ACCOUNT-BOOTSTRAP-RUNBOOK.md#2a-task-2425connection-凭据与上线前最小证据清单目前-hold)：整理三身份、AzureBlobs 参数、Key Vault 引用、State/Connection 库存、准入与停止条件，真实云端核验仍需独立授权。
- **仅通过格式/静态检查不得把 OpenSpec 2.1–2.5 标记为已真正部署**；旧 Self-Runner `azure-infra.yaml` 完全不涉及本轮。

## Fabric infrastructure Bootstrap Profile（OpenSpec `bootstrap-fabric-infrastructure`，仅离线）

- [严格 Bootstrap Profile validator](../../../../azure-fabric/infra-terraform/tools/fabric_bootstrap_profile.py)：两模式、Tenant A/A′/B、Storage/State、OIDC 目标、付费 Capacity 全部 fail-closed；**不接触云端**。
- [Bootstrap Profile 合同](../../../../azure-fabric/infra-terraform/bootstrap/PROFILE-CONTRACT.md) 与 [故意无效示例](../../../../azure-fabric/infra-terraform/bootstrap/bootstrap-profile.example.json)：新资源命名、独立 Bootstrap 初始 State、人工保管/费用/权限门槛。
- [Bootstrap Profile 测试](../../../../azure-fabric/infra-terraform/tests/test_fabric_bootstrap_profile.py)：正常、非法、重复、跨租户、费用 HOLD 与 Secret 阻断；由 [现有 Fabric 离线 CI](../../../../.github/workflows/fabric-environment-preflight.yml) 运行。Task 1.1 的静态合同不等于 Task 1.2 身份/OIDC、Task 2 Terraform 或已部署。

## Bootstrap Identity + OIDC（OpenSpec Task 1.2，纯离线）

- [Identity/OIDC validator](../../../../azure-fabric/infra-terraform/tools/fabric_bootstrap_identity.py)：独立 Seed/Backend/Reader/Fabric 主体；两套受保护 GitHub Environment 与 Repo/Ref 精确校验，验证新创建的三个互异 Client ID 格式，所有实际权限验证均为 false。
- [Identity Contract](../../../../azure-fabric/infra-terraform/bootstrap/IDENTITY-CONTRACT.md) 与 [非敏感虚构请求](../../../../azure-fabric/infra-terraform/bootstrap/identity-request.example.json)：不创建或 Adopt 旧 `github-terraform` Application；Task 2.2 才会真正声明 Terraform Source。
- [Negative/Replay Tests](../../../../azure-fabric/infra-terraform/tests/test_fabric_bootstrap_identity.py)：测试跨租户、OIDC PR/Branch 拒绝、角色隔离与密钥泄露防护，由现有纯离线 CI 验证。

## Capacity 账单审批与 Provider 官方合同（OpenSpec 1.3 / 2.1）

- [Capacity approval validator](../../../../azure-fabric/infra-terraform/tools/fabric_capacity_approval.py) · [负向单测](../../../../azure-fabric/infra-terraform/tests/test_fabric_capacity_approval.py)：请求与分离账单记录严格匹配，但无论是否填写完整审批字段都保持 `paid_creation_authorized=false`，**不授权支付**。
- [Capacity Billing Contract](../../../../azure-fabric/infra-terraform/bootstrap/CAPACITY-APPROVAL-CONTRACT.md)：独立审查责任人、SHA/预算/时间限制、复用模式和受保护 Environment 成本控制。
- [官方 Provider/ARM Freeze](../../../../azure-fabric/infra-terraform/bootstrap/PROVIDER-SCHEMA-REFERENCE.md)：版本选择、跨 Tenant provider alias、Blob container 范围 RBAC、Fabric Capacity ARM 2023-11-01 的准确字段与待核实项。

## Bootstrap Identity Terraform Root (OpenSpec 2.2; code-only, NOT DEPLOYED)

- [Identity Root entry and safety](../../../../azure-fabric/infra-terraform/bootstrap/identity/README.md), [pinned Terraform backend/provider](../../../../azure-fabric/infra-terraform/bootstrap/identity/versions.tf), [separate Tenant A/B providers](../../../../azure-fabric/infra-terraform/bootstrap/identity/providers.tf).
- [Entra app/SPN/group/OIDC resources](../../../../azure-fabric/infra-terraform/bootstrap/identity/main.tf), [default-deny variables](../../../../azure-fabric/infra-terraform/bootstrap/identity/variables.tf), [unverified ID outputs](../../../../azure-fabric/infra-terraform/bootstrap/identity/outputs.tf). Never import or automatically adopt old apps.
- [Identity Root source checks](../../../../azure-fabric/infra-terraform/tests/test_fabric_bootstrap_identity_root.py): source-only static gates and local HCL fmt. No Azure/Fabric/Graph/remote State or real credential check.

## Bootstrap Storage/Backend/RBAC Root（OpenSpec Task 2.3，静态源码）

- [Storage Root 总览](../../../../azure-fabric/infra-terraform/bootstrap/storage/README.md)、[Provider + 独立 Local State](../../../../azure-fabric/infra-terraform/bootstrap/storage/versions.tf)、[Tenant A/Subscription](../../../../azure-fabric/infra-terraform/bootstrap/storage/providers.tf)、[默认拒绝变量](../../../../azure-fabric/infra-terraform/bootstrap/storage/variables.tf)、[Fresh-only Storage/Containers/RBAC](../../../../azure-fabric/infra-terraform/bootstrap/storage/main.tf)、[非敏感未验证输出](../../../../azure-fabric/infra-terraform/bootstrap/storage/outputs.tf)。
- `reuse-existing` 只接受外部已有 `johnzhang` ARM ID 的引用，**不创建、不查询、不导入、不分配 RBAC**；`fresh-bootstrap` 只有独立审批标记齐备才可声明新 RG、Storage、private Containers。Backend Operator 仅新 tfstate Container Contributor，Blob Reader 仅新 Landing Container Reader；实际 Tenant A 的服务主体 Object ID/State/网络必须人工独立验证。
- [Storage/RBAC 静态安全测试](../../../../azure-fabric/infra-terraform/tests/test_fabric_bootstrap_storage_root.py) 与 GitHub-hosted CI 只运行 Python 和 `terraform fmt -check`；没有 Terraform Init/Validate/Plan/Apply、Azure API 或付费 Capacity 操作。旧 Self-Runner 与七 Root 原样保留。

## Fabric Capacity AzAPI Root（OpenSpec Task 2.4，静态代码，付费 HOLD）

- [独立 Capacity Root](../../../../azure-fabric/infra-terraform/bootstrap/capacity/README.md)、[Terraform / AzAPI 固定版本](../../../../azure-fabric/infra-terraform/bootstrap/capacity/versions.tf)、[Tenant B/订阅 Provider](../../../../azure-fabric/infra-terraform/bootstrap/capacity/providers.tf)、[费用与资源批准变量](../../../../azure-fabric/infra-terraform/bootstrap/capacity/variables.tf)、[Fabric Capacity ARM 声明](../../../../azure-fabric/infra-terraform/bootstrap/capacity/main.tf)、[待人工读回输出](../../../../azure-fabric/infra-terraform/bootstrap/capacity/outputs.tf)：默认复用，不读取/修改旧 Capacity；创建 F SKU 需要独立审查标志，全部默认 false。
- [Capacity Root 安全测试](../../../../azure-fabric/infra-terraform/tests/test_fabric_bootstrap_capacity_root.py) + CI `terraform fmt -check`：验证 2023-11-01 ARM 属性、费用门禁、无自动 Suspend/Resume；源代码绝不自行 Init/Plan/Apply，输出 Azure ARM ID **不能当作** Fabric Workspace Capacity UUID，后续需独立验证。
