# Design

## Context

权威方案：[Fabric Multi-Environment Rebuild](../../../documents/architecture/design/FABRIC-MULTI-ENVIRONMENT-REBUILD-DESIGN.md)；已有 Terraform：[ARCHITECTURE](../../../documents/systems/azure-fabric/infra-terraform/ARCHITECTURE.md)；Preflight 已由 PR #247 合并 Main，归档 PR #248 合并。本阶段仅实现**隔离的 Fabric Control Plane Root 离线开发**，旧环境与七 Root 原有 dev State 保持原状。**2026-10-19 用户已批准 Bootstrap as Code + Terraform Capacity 创建能力的上层修订设计**；Bootstrap 实施必须以独立 OpenSpec Change 切分，不把已完成的静态 Terraform Root 误认为已具备引导权限。

## Approved dependency revision (2026-10-19)

- 统一目标：`Bootstrap as Code -> Terraform Fabric control plane -> fabric-cicd -> E2E`。减少换账号时的 Portal 操作，允许首次具权限管理员 Seed 授权及租户设置确认；**不能从无权限 Tenant 自行提权**。
- `reuse-existing`：复用受保护 `johnzhang/landing` 和 `johnzhang/tfstate`，新 State Key `fabric/<env>/...`；不可将旧 State/Workspace 直接 Import/Adopt/Destroy。
- `fresh-bootstrap`：独立 Bootstrap Root/State 创建应用、SPN、Groups、GitHub OIDC、必要最小 RBAC、可选新 Storage/Backend 与可选 Fabric Capacity；Bootstrap 初次 State 必须避免后端循环依赖，State 转移单独审核。新环境在 Backend 准备完成后才可以安全 Plan。
- **Capacity**：用户批准由 Terraform 选择引用已存在 Capacity 或显式创建付费 F SKU；**不纳入动态 Suspend/Resume/按任务暂停功能**。付费创建应为 default-deny，按 SKU/region/subscription/费用独立批准，未批准不允许实际创建。
- 现有硬编码 `johnzhang` 的合同和 Root 在 **reuse-existing** 模式下仍有效；fresh-bootstrap 要求以后另行实现环境化，不通过本次纯文档变更直接替换。当前 A→A′ 与未来 A→B 保留三身份隔离。
- **Change 边界**：本 Change 继续拥有 Workspace/Lakehouse/Connection 的离线实现与接入门槛；身份/Backend/Capacity Bootstrap 应单独设计并验收。后续跨 Change 只使用经过验证的非敏感 Outputs，保护 legacy State 与 Self-Runner。

## Identity and state isolation

Backend 身份访问现有 Storage 的 Entra Tenant A；Fabric Provider 部署身份使用目标 Fabric Tenant（当前同为 A，未来可以为 B）。当前实际配置是 **A→A′（同一 Tenant，不同用户；自动化仍须独立的应用身份）**，未来保留 **A→B（不同 Tenant）**。本项目不得把两个不同用户误判为两个 Tenant。独立环境代码不得写死两 Tenant 相等或不等。Backend 仅允许使用明确批准的 `fabric/<env>/...` State Key；Fabric 身份只在授权的 Workspace/Capacity/Lakehouse/Connection 权限域中使用。避免以共享的 `AZURE_TENANT_ID` 同时承担两者；通过显式且可审核的独立 Provider/Backend 配置和 GitHub OIDC 权限映射实施。Backend 的 Blob RBAC 可能需要容器级授予，不能把 key 前缀当作天然的 Azure RBAC 隔离边界。

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

## Verified topology correction (2026-10-19)

- Entra Default Directory ID `899a04e8-8d3d-486c-88a1-7bdeb22d5f1a` was confirmed by user-provided Azure Portal screenshot and matches `az account show`; the secondary `johnzhang-fabric` user was created inside the same directory. This establishes the current **same-tenant** topology, not separate application/service-principal credentials.
- Offline Preflight now labels same Tenant IDs `same-tenant` and differing IDs `cross-tenant`, without rejecting either. `fabric_deployment_target` continues to reject identical Backend/Fabric **client application IDs** and identity–environment tenant mismatch. User IDs are not Client IDs.
- Live OIDC federation, Service Principal creation, Container RBAC, Fabric permissions and remote-state inventory remain outside this static change. Cross-tenant data access is a separate runtime acceptance gate, not implied by a passing profile.
