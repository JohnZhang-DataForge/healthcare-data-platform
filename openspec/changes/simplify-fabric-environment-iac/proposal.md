# Proposal

## Why

2026-10-20 用户已明确要求回归最初 Azure-Infra 的 `components → modules → environments` 可复用 Terraform 架构。已有 Fabric 管理员部署身份、现成 State Backend、已配置 Landing 数据权限和 Capacity 都应为外部前置，而非普通 Terraform Environment Apply 再开发完整 Bootstrap。当前 `new-environments/` 直接重复声明 Workspace/Lakehouse，三套 Entra App/Seed/双 Tenant 模式也被设计成强制依赖，使简单的多环境部署偏离原目标。

## What Changes

- 建立长期权威 [Fabric Module-first Environment Architecture](../../../documents/architecture/design/FABRIC-TERRAFORM-ENVIRONMENT-ARCHITECTURE.md)：同一可组合 Root、复用 Modules、差异化环境变量及独立 Backend State Keys。
- 已授权账号、Capacity、Landing 数据访问、State Backend 作为正常部署的**外部前置**；不再以 A=B、A≠B、三套新身份或 fresh Bootstrap 组织 Fabric 环境部署。
- Terraform 管 Workspace、Lakehouse、Connection、权限；`fabric-cicd` 管 Notebook/Pipeline。规划统一 Root，把重复资源定义整合回现有 Module 模型。
- 标注早期 Bootstrap 和多环境独立 Root Change 的未来实施路线被取代，历史实现/验收继续保留。
- 本 PR 只做架构文档与 OpenSpec，后续代码、Workflow、云端验收、旧代码清理按本 Change 任务有序进行。

## Capabilities

### New Capabilities

- `fabric-module-first-environment-deployment`：给定预授权部署身份及外部基础设施，以相同 Terraform Modules 和环境/State 配置重建 Fabric 平台。

### Modified Capabilities

- `fabric-multi-environment-terraform` 不再把三套 Backend/Fabric/Reader 身份、独立 Bootstrap Outputs 或特定 Tenant 拓扑当成普通环境部署的强制门槛。

## Impact

文档先行，不改任何 `.tf`、Python、GitHub Workflow、Remote State、Azure/Fabric 资源或计费。变更设计不是已经 Apply；原有资源的 Terraform State 所有权不得因未来重构而被默认替换或删除。
