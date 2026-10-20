# Proposal

> **SUPERSEDED FOR FUTURE IMPLEMENTATION（2026-10-20）**：旧 `new-environments/` 独立 Root/强制 Bootstrap 输出不再是新代码方向，保留旧讨论与实测范围。新权威为 [Module-first 架构](../../../documents/architecture/design/FABRIC-TERRAFORM-ENVIRONMENT-ARCHITECTURE.md) · [新 Tasks](../simplify-fabric-environment-iac/tasks.md)。

## Why

Fabric 多环境离线 Preflight 已由 PR #247 验收并于 PR #248 归档，但现有 Terraform 七 Root 和 Self-Runner `azure-infra.yaml` 仍面向旧 `dev` State/单租户身份，不能安全重建独立的新 Fabric 环境。需要基于已批准的 [Fabric Multi-Environment Rebuild Design](../../../documents/architecture/design/FABRIC-MULTI-ENVIRONMENT-REBUILD-DESIGN.md) 实施新环境专用、可审查的 Terraform Control Plane。

## What Changes

- 新环境只使用 `fabric/<environment>/{workspace,onelake,connection}.tfstate`；后端继续使用已有 `johnzhang/tfstate`，但绝不迁移或覆盖旧 `dev/*.tfstate`。
- 明确 Backend Tenant A 与 Fabric Provider Tenant B 的独立认证输入、Oidc/Secret 边界和离线校验；同租户仍允许但凭据职责隔离。
- 重用或安全适配既有 Workspace/Lakehouse Module，单独审查 Blob Connection Provider schema，避免与未来 fabric-cicd 的 Notebook/Pipeline 所有权冲突。
- 开发静态 CI/单元测试，最后才设计受控 Self-Runner Plan 入口；不自动执行 Plan、Apply、Destroy。

## Capabilities

### New Capabilities

- `fabric-multi-environment-terraform`：通过显式环境、独立状态及分租户身份约束 Terraform Workspace/Lakehouse/Connection Control Plane。

### Modified Capabilities

- 新环境 Terraform 部署路径，与旧七 Root 的 dev 模式并行存在，不能静默替换、导入或重置旧状态。

## Approved architecture revision (2026-10-19)

上层目标已批准调整为 **Bootstrap as Code + Terraform + GitHub Actions + fabric-cicd**。身份（Backend Operator/Fabric Deployer/Blob Reader）、GitHub OIDC、最小 RBAC、可选 Storage/Backend 和 Capacity 可由**独立 Bootstrap Change** 通过 IaC 管理；Capacity 支持复用已有或有费用审批地创建付费 F SKU，**不做自动暂停/恢复**。此项是架构决策，而非云端创建授权。

本 Change 原来的新环境 Workspace/Lakehouse/Connection Root 继续保持隔离的静态验收任务；`johnzhang` 固定合同是已有资产 `reuse-existing` 模式的适配，`fresh-bootstrap` 的新 Backend/Identity/Capacity 输入需要后续 Change 另行实现和审核。批准新架构**不表示**可以 Destroy/Import 旧 Storage/State/Workspace 或无审批购买 Capacity。

## Impact

仅在独立实施 PR 和静态检查通过后提供可部署的 Terraform 定义。本 Change 的建立不授权 Azure/Fabric API、Terraform init/plan/apply/destroy、RBAC 写入、旧 Workspace 迁移或 Blob/State 删除。后续 fabric-cicd + Self-Runner 完整部署需独立 Change。
