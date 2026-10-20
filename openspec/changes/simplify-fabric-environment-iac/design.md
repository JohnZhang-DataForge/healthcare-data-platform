# Design

## Context

源代码已有旧 `components/workspace/modules.tf` → `../../modules/workspace`、`components/onelake/modules.tf` → `../../modules/onelake`、环境 `dev.tfvars` 与对应 Self-Runner `azure-infra.yaml` 执行模式；新 `new-environments/{workspace,onelake,connection}` 却直接定义新的 Terraform Fabric Resources。此前两个 OpenSpec Change 把双 Tenant、三套独立 Entra App、Seed Bootstrap、fresh/reuse Storage 合同作为新 Fabric 环境的前置。

## Decisions

1. **外部前置**：Fabric 部署身份具有目标资源权限、可用 Capacity、现有可访问 Terraform Backend 和已配置 Landing 访问。Fabric Administrator 角色本身不保证 Azure RBAC/Backend/Capacity 权限；不在源码里假设无条件可用。用户创建、Subscription、Trial 和付费采购不是环境 Root 的职责。
2. **Module-first**：保留旧 `components → modules → environment tfvars` 的分层，以唯一 `components/fabric-environment` 作为组合 Root；复用 Workspace IAM 和 Lakehouse 资源，新增可复用 Connection Module。避免复制同一 Resource 到多个 Root。
3. **环境独立**：Provider 登录、Capacity、Workspace、Connection 与 State Key 为输入；将新环境 Key 定义为 `fabric/<env>/platform.tfstate`，但不自动迁移或覆盖历史 `dev/*.tfstate` 或新旧独立 Root State。
4. **责任隔离**：Terraform 创建 Workspace/Lakehouse/Connection 和授权；`fabric-cicd` 发布 Notebook/Pipeline；禁止对同一 Item 的双重写入。
5. **执行策略**：真实 `terraform init/plan/apply` 及运行读回才是云端验收；GitHub-hosted CI 的 `init -backend=false` / `validate` 仅静态证据。旧 Self-Runner workflow 留作可复用执行基础，统一入口验收后才退役旧路径。
6. **清理边界**：保留历史源码、Terraform State 和旧 Change 记录；当新环境完整 E2E 验收，才统一清理已无依赖的重复 `new-environments`、不必需 Bootstrap 及专属 CI，不能因重构自动销毁云端资源。

## Phases

- D0：本 PR 提交权威设计、Proposal/Design/Delta Spec/Tasks，并把历史方案与当前决策消歧。
- D1：盘点七个旧 Root、三个新 Root、Modules、测试、Workflow 与 State 资源所有权；实现可复用 Modules 和组合 Fabric Root。
- D2：按环境配置完成 Terraform 格式、Provider Schema、Static CI、State Key 负向测试；更新 CODE.md 源码导航。
- D3：选新的隔离 State 与已授权账户执行真实 Plan/Apply，读回资源及 Blob Connection；第二账号或环境重复部署验证可复用与幂等。
- D4：接入 fabric-cicd 与真实业务数据 E2E；完成无用代码/CI/文档引用的可核查清理。

## Risks and recovery

- 旧 Roots 可能已有 State，新的资源 Address 不同；不得用简单复制/删文件方式处理已有资源，先独立创建新环境或独立审核 State Move/Import。
- 每套环境必须拥有不同 State Key；Key 前缀本身不是 Azure RBAC 隔离机制。
- Landing Connector 认证模式（如 Workspace Identity 或 SP）必须符合实际 Provider/云端支持并具有已验证权限；不在 Git 提交凭据值。
- Fabric Capacity 不自动购买付费 SKU；无授权的 Existing Capacity/Trial 不因 TF 存在定义就可以强制使用。
- 本设计 PR 没有任何部署授权，也不得声称云端状态变化。历史任务数据保留、代码回滚 Git，云端回滚必须根据真实 State 所有权另议。

## References

- [长期架构](../../../documents/architecture/design/FABRIC-TERRAFORM-ENVIRONMENT-ARCHITECTURE.md)
- [旧 Root/Module 源码地图](../../../documents/systems/azure-fabric/infra-terraform/CODE.md)
- [旧 Bootstrap Change](../bootstrap-fabric-infrastructure/tasks.md)
- [旧多环境 Change](../implement-fabric-multi-environment-terraform/tasks.md)
