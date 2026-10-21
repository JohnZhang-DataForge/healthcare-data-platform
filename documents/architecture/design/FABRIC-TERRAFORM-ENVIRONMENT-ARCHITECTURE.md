---
status: active
scope: fabric-environment-single-root-module-first
decision_date: 2026-10-20
implementation_status: source-consolidated-live-state-pending
---

# Fabric Terraform — 当前账号唯一 Root 与同名 Workspace

> 单个当前已授权 Fabric 账号；唯一部署入口
> [`components/fabric-environment`](../../../azure-fabric/infra-terraform/components/fabric-environment/README.md)；
> 权威实施任务 [OpenSpec](../../../openspec/changes/simplify-fabric-environment-iac/tasks.md)。
> 旧 Terraform Roots/Modules 已从当前工作树清理，历史源码与远端 State 均可查，**未执行 State 迁移或云端 Apply**。

## 目标结构

```text
Self-Runner Azure-Infra-TF (workspace name + inspect/adopt/plan/apply)
           │
           ▼
azure-fabric/infra-terraform/
  components/
    fabric-environment/        # 唯一 Terraform Root
      main.tf / variables.tf / providers.tf / outputs.tf / versions.tf
      environments/
        healthcare-omop.tfvars # 已有人工作空间的非秘密配置
  modules/
    workspace/                 # Workspace + Workspace IAM
    onelake/                   # Lakehouse + 可选 OneLake IAM
    connection/                # 可选 Azure Blob connection
           │
           ▼
当前 Fabric 账号内的 Fabric Workspaces
```

Terraform CLI Workspace 与 Fabric Workspace **严格同名**：
`healthcare-omop` → `healthcare-omop`；新输入 `healthcare-qa` →
新同名 Fabric Workspace。`terraform.workspace` 传入 Workspace Module，
Lakehouse 用 `module.workspace.workspace_id`，Root 输出真实资源 GUID。
`default` CLI Workspace 禁止用于实际部署。

## 前置条件与权属

必须已具备：当前账号中有权限的非交互式部署身份；已有可用 Capacity；
已授权 Landing Azure Blob 和 Reader 身份；可读写的 AzureRM Terraform
Backend（现有 Storage `johnzhang` / `tfstate`）。**不自动创建/购买**
Capacity、Storage、Tenant、Subscription、Entra App 或多账号 Profile。

唯一 Root 的 Backend 基础 Key `fabric/platform.tfstate` 固定。
Terraform CLI Workspace 提供独立 State；不另按 `dev` 等环境名称拼接 Key。
以前的七个独立 Roots 及五个不再使用的 Modules 已从 Main 移除，
但 `dev/*.tfstate`、旧对象和资源历史**不会因此被删除或清空**。
旧源码可见
[历史快照](https://github.com/JohnZhang-DataForge/healthcare-data-platform/tree/20a6449000fe10eac642ab2dbcef37976339572b/azure-fabric/infra-terraform)。

## 新建与既有资源接管

- **已有 `healthcare-omop`**：先核对其真实 GUID、Capacity、历史
  State 的同 GUID 所有权，显式 `adopt/import` 后再 Plan/Apply；不能重复
  Create。旧 State 如果仍有相同 GUID，先处理迁移，不能直接导入两份 State。
- **全新 Workspace**：输入合规新名称即可选择/创建同名 Terraform
  CLI Workspace，默认参数即可 Plan/Apply 同名 Fabric Workspace、
  IAM、Lakehouse；可选 per-Workspace `tfvars` 为非秘密个性化输入。
  此路径必须保留 Plan 审查，未实际调用前不宣称已创建。
- **Connection**：仅在 Reader 身份可用时启用；
  Fabric Connection 是账号/租户级资源，不是 Fabric Workspace Item。
- **业务 Notebook/Pipeline**：继续由 `fabric-cicd` 维护，非 Terraform
  旧占位 Modules；不能双重拥有。

## 验收

完成静态 `fmt`、`init -backend=false`、`validate`、
Root/Module/Workspace CI 后，必须再通过真实 Runner 的 OIDC、
Backend State 所有权盘点、明确 Import（如需）、Plan/Apply、API
读回、Landing 可读性和再次 Plan 无漂移，才能声称部署成功。
