---
status: active
scope: fabric-environment-module-first-target-architecture
decision_date: 2026-10-20
implementation_status: design-agreed-code-refactor-pending
---

# Fabric Terraform 环境部署架构 — 当前账号 / 同名 Workspace / Module-first

> **2026-10-20 最新正式决定（覆盖本项目此前的多账号自动化和独立 State Key 环境方案）。** 当前仅以一个已授权 Fabric 账号为实施目标。**该账号下已存在的 Fabric Workspace 准确名称是 `healthcare-omop`，目前作为 DEV 使用。** 方案已确定，但 Terraform Root/Connection/Workflow 尚未按此修改，未完成真实 Apply 或 Fabric E2E。实施任务入口：[OpenSpec simplify-fabric-environment-iac](../../../openspec/changes/simplify-fabric-environment-iac/tasks.md)。

## 1. 目标与范围

一套现有的 Terraform `components → modules` 源码，在**当前**已授权 Fabric 账号下，利用不同的 **Terraform CLI Workspaces** 管理多个同名 **Fabric Workspaces**，从而创建/管理 Workspace、Workspace IAM、Lakehouse、Connection 等平台资源。第一阶段先让 `healthcare-omop` 真实可管理、可运行。

- 当前 Fabric 管理身份、订阅/Fabric 资格、可用 Capacity、现有 Terraform Remote Backend、已授权 Landing 均为部署前置条件；不在本项目普通 Apply 中创建/购买这些资源。
- **不做**多账号选择、Account Profile、Tenant A/B 拓扑系统、三套身份 Bootstrap 或独立新 Azure Blob/State Backend 的创建系统。
- 以后若换 Fabric 账号，人工调整 Provider/认证、Capacity、Landing 和**隔离的 Backend/State**，可复用同一套 Terraform 源码，也可以新建单独工作目录；不作为本轮自动化范围。
- Fabric Administrator 身份本身不代表自动拥有 Backend 写入、Capacity 管理或 Landing Blob Reader 权限。

## 2. Workspace 的一一对应规则

| 逻辑用途 | Terraform CLI Workspace | 真实 Fabric Workspace | 状态 |
| --- | --- | --- | --- |
| DEV（当前） | `healthcare-omop` | `healthcare-omop` | Fabric Workspace 已人工创建；Terraform 新 Root 接管尚未验证 |
| QA（将来） | 与其 Fabric Workspace 同名 | 创建时再确定准确名称 | 仅规划 |
| PROD（将来） | 与其 Fabric Workspace 同名 | 创建时再确定准确名称 | 仅规划 |

这里的 Terraform CLI Workspace 是通过 `terraform workspace select/new` 选择的 **State 命名空间**，Fabric Workspace 是 Microsoft Fabric 中的真实资源。两者是不同对象，但在**当前项目中强制使用相同的名称**，便于辨认。**禁止使用 Terraform 默认 `default` Workspace 部署。** 不要将 `healthcare-omop` 擅自改名为 `dev` 或 `HDP-Dev`。

Root 将 Workspace 名称交给 Module，例如：

```hcl
module "workspace" {
  source           = "../../modules/workspace"
  workspace_name   = terraform.workspace
  description      = var.description
  capacity_id      = var.capacity_id
  role_assignments = var.role_assignments
}

module "onelake" {
  source         = "../../modules/onelake"
  workspace_id   = module.workspace.workspace_id
  lakehouse_name = var.lakehouse_name
}
```

`terraform.workspace` 决定**名称**，而非自动导入已有 Fabric Workspace。Module Outputs 负责在 Terraform 图中传播真实 GUID；根级 Outputs 可提供 `fabric_workspace_name`、`fabric_workspace_id`、`lakehouse_id`、`connection_id`，供 Workflow 与 `fabric-cicd` 消费。**Outputs 不用于选择 CLI Workspace 或配置 Backend。**

## 3. 模块与源码结构

保留七个原有 `components/` Roots 及 `modules/`，新增一个组合 Root；不恢复已删除的旧 Bootstrap/New Roots。

```text
azure-fabric/infra-terraform/
├── components/
│   ├── workspace/           # 原有 Root：继续保留，避免随意改变旧 State 地址
│   ├── onelake/             # 原有 Root
│   ├── ...                  # 其它旧 Root
│   └── fabric-environment/ # 待开发：当前账号下的统一组合 Root
│       ├── versions.tf
│       ├── providers.tf
│       ├── main.tf
│       ├── variables.tf
│       ├── outputs.tf
│       └── environments/
│           └── healthcare-omop.tfvars
└── modules/
    ├── workspace/           # 复用 Fabric Workspace、IAM
    ├── onelake/             # 复用 Fabric Lakehouse
    └── connection/          # 待开发的可复用 Fabric Blob Connection
```

- **Components/Root**：Provider、AzureRM Backend、环境输入、Module 编排和 Outputs。
- **Modules**：真实 Fabric Resources/IAM、输入验证与 Outputs；不包含账号与 Backend 配置，也不硬编码 `healthcare-omop`。
- **配置**：当前账号下 Workspace 对应的 Capacity、Lakehouse、Landing Connection 等参数；非秘密参数可在 `tfvars`，Credential/Token/Secret 禁止写 Git。
- **资源唯一所有权**：Terraform 管 Workspace/IAM、Lakehouse、Connection；`fabric-cicd` 管 Notebook/Pipeline 业务代码。Warehouse、复杂 OneLake 权限不是首个 MVP 的必要条件。

## 4. Remote State 设计

沿用当前账号已经可用的 AzureRM Backend（例如现有 `johnzhang/tfstate`），给**组合 Root** 配置一个固定基础 Key（示例 `fabric/platform.tfstate`）。对于 Terraform CLI 的 **非 default Workspace**，AzureRM Backend 会维护对应 Workspace 的 State 命名空间；实际 Blob 名称由 Backend 的 Workspace Key 机制派生，必须在首次 Init/Plan 时读回确认。

**不能把两个机制混为一谈**：不再要求 Workflow 按每次部署拼出 `fabric/<environment>/platform.tfstate` 并且同时切换 Terraform CLI Workspace；否则容易重复叠加命名、难以辨认。单纯切换 tfvars 也不代表切换 State。TF CLI Workspace 提供逻辑隔离，不提供独立 Azure RBAC/权限边界。

现有 `dev/*.tfstate`、历史独立 Root State 和 Fabric 云端资源都不能自动迁移、覆盖或清理。尤其 `healthcare-omop` 已存在：
1. 先核对 Fabric Workspace GUID、原 Terraform State 是否已经跟踪此对象。
2. 新组合 Root 下若没有该资源，采取**显式 Import 或经审查的 State Move**，不能直接 Create 同名资源。
3. 首次 Apply 前检验 Plan 无未知资源的 Delete/Replace；不能把空 State 误判为云端无资源。

## 5. GitHub Self-Runner Workflow

继续复用 `Self-Runner/.github/workflows/azure-infra.yaml`，不建立新的账号选择系统。

- **选择 Workspace**：`healthcare-omop` 为现有目标，未来同账号新增后才增加对应选项；选择值用于 `terraform workspace select`，亦作为 Fabric Workspace display name。
- **选择资源操作范围**：允许以 Full Platform 为默认目标；以后如支持 Workspace/Lakehouse/Connection 分别操作，必须保证不因切换开关而使同一 State 其他已管理资源被删除。不得以未经审查的常规 `-target` 作为长期部分部署架构。
- **选择操作**：`plan` 或显式 `apply`；复用有效的 Plan/Apply、安全审查、实际 Source SHA 和运行记录。
- **认证**：Runner 依当前授权身份配置；本地 CLI 认证与 OIDC Runner 认证差异由 Provider/Workflow 做最小兼容调整，不恢复 Bootstrap。
- **输出**：调用 `terraform output` 提供真实 Fabric Workspace/Lakehouse/Connection IDs 给业务部署阶段。

## 6. 实施顺序和验收

先核对当前 Main 的 Workspace/Onelake Modules、State 与 `healthcare-omop`；完成 Connection Module、组合 Root 和 Terraform CLI Workspace 配置；运行静态 CI，之后在明确的真实环境授权下进行 Plan/必要的 Import/Apply。

**第一次验收重点**：当前账号中 `healthcare-omop` 可由 Terraform 正确管理，Lakehouse/Connection 可读回并获得既有 Landing 数据的实际访问；重复 Plan 无意外变更。再用同一 Fabric 账号下另一个新 Workspace 验证复用，最后扩展原 Self-Runner Workflow，并接入 `fabric-cicd`、数据 E2E。

已完成的 `bootstrap/`、`new-environments/`、`tests/`、`tools/` 源码清理仍是历史已完成事项，不重做；架构定稿不等于成功 Terraform Apply。

**长期架构在本文件；实际实施进度、PR/Run 证据只由 [Active OpenSpec Change](../../../openspec/changes/simplify-fabric-environment-iac/tasks.md) 管理。**
