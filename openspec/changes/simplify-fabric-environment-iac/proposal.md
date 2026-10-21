# Proposal

## Why

2026-10-20 用户再次收敛 Microsoft Fabric Terraform 范围：**当前只部署现有 Fabric 账号，不开发多账号 Account Profile/自动切换**。当前账号下已有人工创建的 Fabric Workspace，准确名称为 `healthcare-omop`，当前作为 DEV 使用。未来可以在**同一账号**下增加其他 Fabric Workspaces。保持已有 `components → modules` 的可复用架构，优先实现并真实验证 Fabric 平台，而不是重新建设 Bootstrap。

## What Changes

- **账号范围**：仅当前已授权的 Fabric 管理/部署身份；可用 Capacity、已授权 Landing、Terraform Backend 仍为外部前置。Workflow 不提供多账号选择，不开发双 Tenant/三身份/Seed Bootstrap。将来换账号时手工修改认证和配置，使用隔离 Backend/State 后复用源码；不作为本 Change 验收。
- **同名约定**：Terraform CLI Workspace 名称与目标 Fabric Workspace `display_name` 完全一致。首个目标固定为现有名称 `healthcare-omop`，DEV 仅为业务环境标签，并非另一 Workspace 名。必须使用非 `default` Terraform Workspace。
- **单组合 Root**：复用现有 `modules/workspace`、`modules/onelake` 与 IAM，增加 `modules/connection`，使用 `terraform.workspace` 传入 Fabric Workspace 名称；输出真实 Workspace/Lakehouse/Connection IDs 供其他 Modules 和 `fabric-cicd` 使用。
- **State 隔离**：当前账号使用同一个预先存在的 AzureRM Backend，按 Terraform CLI Workspace 维护各自 State；不得误认为只需更换 tfvars，也不得自动挪动历史 State 或接管已有云端 Workspace。
- **执行**：在原 `Self-Runner/.github/workflows/azure-infra.yaml` 基础上支持选择目标 Workspace、已明确的资源操作范围和 Plan/Apply；首版优先完整组合 Root，禁止用关闭其他资源定义的方式实施部分部署。
- **真实验收**：先核对 `healthcare-omop` 的已有 Terraform State 和云端资源所有权，按需显式 Import/State Move，不能重复创建；再真实 Plan/Apply、API 读回、Landing 可用性和幂等验证。同账号第二个 Workspace 的部署作为后续复用验收。
- Notebook 与 Pipeline 业务定义继续由 `fabric-cicd` 发布，Terraform 不同时管理相同业务 Items。

## Capabilities

### New Capabilities

- `fabric-module-first-environment-deployment`：当前 Fabric 账号中，以 Terraform CLI Workspace 名确定同名 Fabric Workspace、复用 Modules、隔离 State、输出真实资源 ID。

### Modified Capabilities

- 本 Change 不再要求多个 Fabric 账号/跨 Tenant 自动选择，也不恢复已删除的 Bootstrap、新独立 Roots 或对应 Tools/Tests。原旧 Change 仅作历史记录。

## Impact

本次仅修订架构文档和 **Active** OpenSpec，不修改 Terraform 源码、GitHub Workflow、Backend、State、现有 Fabric Workspace 或云端权限。架构定稿不代表真实 Apply 或 E2E 成功。
