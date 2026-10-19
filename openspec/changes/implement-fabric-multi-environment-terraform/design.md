# Design

## Context

权威方案：[Fabric Multi-Environment Rebuild](../../../documents/architecture/design/FABRIC-MULTI-ENVIRONMENT-REBUILD-DESIGN.md)；已有 Terraform：[ARCHITECTURE](../../../documents/systems/azure-fabric/infra-terraform/ARCHITECTURE.md)；Preflight 已由 PR #247 合并 Main，归档 PR #248 合并。本阶段仅新建隔离环境，旧环境与七 Root 原有 dev State 保持原状。

## Identity and state isolation

Backend 身份属于旧 Storage 的 Entra Tenant A，仅允许读取/写入被明确批准的新 `fabric/<env>/...` State Key；Fabric Provider 部署身份属于目标 Tenant B，只在新 Workspace/Capacity/Lakehouse/Connection 权限域内使用。避免以共享的 `AZURE_TENANT_ID` 同时承担两者；通过显式且可审核的独立 Provider/Backend 配置和 GitHub OIDC 权限映射实施。Backend 的 Blob RBAC 可能需要容器级授予，不能把 key 前缀当作天然的 Azure RBAC 隔离边界。

## Ownership

- `johnzhang/landing`：稳定原始数据，Blob Reader 只读；不新建、Import、Destroy。
- `johnzhang/tfstate`：稳定 Backend；原 `dev/*.tfstate` 原样保留；新 `fabric/<env>/...` 键不可复用。
- Terraform：只拥有新 Workspace/Capacity attachment、Lakehouse、Blob Connection（Provider schema 未验证前禁止实现虚构 resource）。
- fabric-cicd：未来拥有 Notebook 和 DataPipeline，显式排除 Lakehouse；不得调用 orphan unpublish。
- 已存在旧 Workspace/现存 State：必须先 inventory 并单独取得 Import/Adopt 授权，本阶段拒绝猜测同名资源安全。

## Incremental implementation

1. 核查 Terraform versions/providers/backend、现有 Workspace/OneLake Modules 与 Preflight 合同的差距，固定 Provider schema 和认证能力；只读代码审计。
2. 在新环境专属路径实现 Backend key 参数构造和分身份配置；禁止旧 dev key、未知 Secret、缺少 Tenant 信息；添加离线负向测试。
3. 新 Workspace 与 Lakehouse Root/Modules 复用或封装；明确 dependency/outputs 和 Capacity 前置。
4. 单独根据锁定版本的 Provider schema 实现 Connection Root/Module；跨 Tenant Reader 只能在后续真实授权的连接验证中确认。
5. 更新 CODE.md、Runbook，提供仅静态或不访问云端的 CI 证据。可能触及云端/State 的 Terraform init/plan 必须独立申请操作授权。
6. 经 PR 合并后记录 Main SHA/Run，只有达到本 Change 的相应验收门槛才能归档。

## Validation and rollback

逐小 PR 验证 `terraform fmt`（本地）/语法与静态约束、Python 单测、OpenSpec Strict/Trusted Gate/Docs Links；不把 Mock/Plan 通过称为部署验收。保留旧 Root 完全不改；新路径可通过 Git 回退，绝不以 Destroy 作为回退。

## Out of scope

不实现 Notebook/Pipeline fabric-cicd、自动 Apply、Blob 批次发布、业务 E2E、跨租户真实连通测试以及旧 Workspace 清理。
