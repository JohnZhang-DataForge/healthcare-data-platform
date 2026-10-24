---
status: superseded
scope: historical-fabric-bootstrap-operator-runbook
last_verified: 2026-10-20
---

# Fabric Bootstrap 历史操作手册（已退役）

> **不要按照旧 Seed/OIDC/三套 App 或 `new-environments` 步骤执行。** 2026-10-20 已决定以已经授权的 Fabric 部署账号、可用 Capacity、现成 Landing 和现存 Terraform State 为前置，继续原有 `components → modules → environment tfvars` 架构。旧 Bootstrap 源码和本手册原版由 [清理前 Git 快照](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/d95da9f0e62c77b025d466e51f78ad9a48241158/documents/engineering/operations/FABRIC-ACCOUNT-BOOTSTRAP-RUNBOOK.md) 保留，用于追溯而非操作。

## 当前可用的工作入口

- [Module-first 正式架构](../../architecture/design/FABRIC-TERRAFORM-ENVIRONMENT-ARCHITECTURE.md)；[当前实施 Tasks](../../../openspec/changes/simplify-fabric-environment-iac/tasks.md)
- [Terraform 当前 Root/Module 代码地图](../../systems/azure-fabric/infra-terraform/CODE.md)
- [Self-Runner 原 Azure-Infra Workflow](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/.github/workflows/azure-infra.yaml)（现存工作流，配置与 Terraform State 需按目标环境审查）
- [共享资源安全操作规范](SAFE-OPERATIONS.md)

新账号/环境首次执行前，确认部署身份有实际 Fabric/Capacity 权限、已有 Backend 数据读写/锁定权限、Landing 的预授权访问与连接器网络条件；对新环境使用独立 State Key，先执行和审核真实 Terraform Plan，再 Apply。**旧 `dev/*.tfstate`、已存在 Azure Blob、Workspace、业务数据不会因 Git 源码清理而自动改变，且不得被新环境未经审查接管。**
