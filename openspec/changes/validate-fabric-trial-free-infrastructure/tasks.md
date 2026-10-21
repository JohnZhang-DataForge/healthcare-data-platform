# Tasks

## 1. Trial-only infrastructure validation design

- [x] 1.1 审核用户免费 Trial F4 `3914ac8b-3375-498b-b3c0-1180a1902dd6`、现有 Workspace/OneLake Terraform Roots、Self-Runner 边界和 Azure Free Trial F2 配额阻断事实。
- [x] 1.2 建立本 Change 的 Proposal、Design、Delta Spec 与试用模式运行门禁；只修改源码导航，不更改付费 Capacity Root。
- [x] 1.3 [Self-Runner PR #198](https://github.com/JohnZhang-DataForge/Self-Runner/pull/198) Trial-only E2E Workflow、静态合同 CI PASS，合并 Main `b0fa4af2594694ed007dedafc314491967a8ccec`。
- [x] 1.4 [Self-Runner PR #199](https://github.com/JohnZhang-DataForge/Self-Runner/pull/199) 提交且合并单一请求，触发 [Run #39635155333](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39635155333)。固定 Healthcare SHA `f2aa9fc601c42ca57537652f9a096144320f4a61` 和已有 Trial GUID `3914ac8b-3375-498b-b3c0-1180a1902dd6`；无付费 Capacity 操作。
> **实际运行结果（2026-10-21）：FAIL / Unauthorized。** [Run #39635155333](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39635155333) 完成 AzureRM Backend OIDC 初始化、创建独立 Terraform CLI Workspace `johnzhang-test`（**仅 State 隔离，不是 Fabric 云 Workspace**）、Terraform Validate 和真实 Plan `1 create / 0 update / 0 delete`，并在 Plan 中确认 `capacity_id=3914ac8b-3375-498b-b3c0-1180a1902dd6`。**首次 Workspace Apply 返回 `Error Code: Unauthorized` / `The caller is not authenticated to access this resource`，Request ID `a274a42e-f7c5-4812-b9b4-a4197ef300c8`。** 未得到真实 Workspace GUID，也未开始 OneLake Root；没有创建付费 Capacity，不能宣称全链路 E2E PASS。失败时先核对 Fabric Admin Tenant settings 两项 Service Principal 权限（`Service principals can create workspaces, connections, and deployment pipelines`；`Service principals can call Fabric public APIs`）、其允许组中的当前 Entra Enterprise App `github-terraform`，以及 Trial Capacity Contributor/Admin 授权。此错误不充分证明 Trial 完全不支持 Service Principal；不得盲目开宽租户权限或以 REST API 取代 Workspace Terraform。参考 [Microsoft Developer settings](https://learn.microsoft.com/en-us/fabric/admin/service-admin-portal-developer) 和 [Workspace API prerequisites](https://learn.microsoft.com/en-us/rest/api/fabric/core/workspaces/create-workspace)。待租户设置查明后再发独立受审查的请求重新验证。

- [ ] 1.5 成功后独立读回 Workspace/Lakehouse、State 和重复 Plan；若 Fabric Trial 不支持 OIDC Service Principal 则 FAIL/HOLD 并记录 Provider 具体错误，不自动使用 REST API 代替 Terraform。
- [ ] 1.6 根据实际执行修订 CODE 导航与验收证据，避免将静态 CI 当作云端部署成功。

## 2. Exclusions

- 不创建、购买、暂停或恢复任何付费 Fabric Capacity。
- 不触发已保留的 F2 Capacity Apply Workflow；不修改其他 Terraform CLI Workspaces 或老 State。
- 不通过 REST 创建 Workspace 或替换 Terraform 的 Capacity 关联所有权。
