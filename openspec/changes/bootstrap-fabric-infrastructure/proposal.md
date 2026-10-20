# Proposal

## Why

现有 [Fabric 多环境架构设计](../../../documents/architecture/design/FABRIC-MULTI-ENVIRONMENT-REBUILD-DESIGN.md) 已于 2026-10-19 明确批准 **Bootstrap as Code + Terraform + GitHub Actions + fabric-cicd**。当前 `implement-fabric-multi-environment-terraform` 只具备受保护的新环境 Workspace/Lakehouse/Connection 离线 Terraform Root，仍依赖人工预备 Entra Apps/SPN、GitHub OIDC、RBAC、State Backend、Fabric Capacity。换 Tenant 或账号后不能仅凭代码重建。

需要一个独立且最小权限的 Bootstrap 层：管理员首次授予必要启动权限，其余可编排身份与基础资源用代码创建；同时明确哪些操作必须保留人工审批。**批准 Capacity 可由 Terraform 创建，不代表现在授权付费创建。**

## What Changes

- 新增 `bootstrap/` 目标 Terraform 边界，支持 `reuse-existing` 和 `fresh-bootstrap` 两种互斥模式；输入合同不得包含 Secrets，不得默认接管旧 `johnzhang/landing`、`tfstate` 或已存在 Fabric Workspace。
- Bootstrap 计划管理 Entra Applications、Service Principals、授权 Groups、Repo/Environment 精确范围的 GitHub OIDC Federation、最小 RBAC；Backend Operator、Fabric Deployer、Blob Reader 三种身份保持独立，同租户 A→A′ 与跨租户 A→B 均需显式 Tenant/Provider 定位。
- Fresh Bootstrap 的 Storage/Container 与 Remote State 以独立的初始 Bootstrap State 启动，避免自举循环；复用现有模式仅查询或接受已独立核验的 ID，Import/Adopt 必须单独授权。
- Fabric Capacity 提供 `reuse-existing`（默认）与 `create-new`（付费、默认拒绝）两条路径；创建前固定 Subscription、SKU、Region、成本审核证据和审批；**不开发自动 Suspend/Resume 或随任务动态创建/销毁**。
- 增加纯离线配置合同、负向测试、离线 CI、输出交接清单；完成后将已验证的非敏感 Bootstrap Outputs 交给原 Fabric Control Plane Change，真实执行必须走独立安全审批。

## Capabilities

### New Capabilities

- `fabric-infrastructure-bootstrap`：在受控启动授权下，使新 Tenant/Subscription 的 Identity、OIDC、Storage/State 与可选 Capacity 以 IaC 安全且可重复地建立或显式引用。

### Modified Capabilities

- 现有 `fabric-multi-environment-terraform` 将来接收受验证的 Bootstrap Outputs，但本 Change 不直接修改既有 Workspace/Lakehouse/Connection Root 的状态或资源所有权。

## Impact

本 Change 初次提交**仅为设计与任务合同**；不执行 Terraform `init/plan/apply/destroy/import`、Azure/Fabric API 写操作、创建付费 Capacity、修改 GitHub Secrets、读取或迁移远端 State，也不调用旧 Self-Runner `azure-infra.yaml`。后续代码按小 PR 与独立授权实施。
