# Tasks

## 1. Trial-only infrastructure validation design

- [x] 1.1 审核用户免费 Trial F4 `3914ac8b-3375-498b-b3c0-1180a1902dd6`、现有 Workspace/OneLake Terraform Roots、Self-Runner 边界和 Azure Free Trial F2 配额阻断事实。
- [x] 1.2 建立本 Change 的 Proposal、Design、Delta Spec 与试用模式运行门禁；只修改源码导航，不更改付费 Capacity Root。
- [x] 1.3 [Self-Runner PR #198](https://github.com/JohnZhang-DataForge/Self-Runner/pull/198) Trial-only E2E Workflow、静态合同 CI PASS，合并 Main `b0fa4af2594694ed007dedafc314491967a8ccec`。
- [x] 1.4 [Self-Runner PR #199](https://github.com/JohnZhang-DataForge/Self-Runner/pull/199) 提交且合并单一请求，触发 [Run #39635155333](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39635155333)。固定 Healthcare SHA `f2aa9fc601c42ca57537652f9a096144320f4a61` 和已有 Trial GUID `3914ac8b-3375-498b-b3c0-1180a1902dd6`；无付费 Capacity 操作。
> **第一次运行结果（2026-10-21 / Attempt 1，历史失败，后续已修复）：FAIL / Unauthorized。** [Run #39635155333](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39635155333) 完成 AzureRM Backend OIDC 初始化、创建独立 Terraform CLI Workspace `johnzhang-test`（**仅 State 隔离，不是 Fabric 云 Workspace**）、Terraform Validate 和真实 Plan `1 create / 0 update / 0 delete`，并在 Plan 中确认 `capacity_id=3914ac8b-3375-498b-b3c0-1180a1902dd6`。**首次 Workspace Apply 返回 `Error Code: Unauthorized` / `The caller is not authenticated to access this resource`，Request ID `a274a42e-f7c5-4812-b9b4-a4197ef300c8`。** 未得到真实 Workspace GUID，也未开始 OneLake Root；没有创建付费 Capacity，不能宣称全链路 E2E PASS。失败时先核对 Fabric Admin Tenant settings 两项 Service Principal 权限（`Service principals can create workspaces, connections, and deployment pipelines`；`Service principals can call Fabric public APIs`）、其允许组中的当前 Entra Enterprise App `github-terraform`，以及 Trial Capacity Contributor/Admin 授权。此错误不充分证明 Trial 完全不支持 Service Principal；不得盲目开宽租户权限或以 REST API 取代 Workspace Terraform。参考 [Microsoft Developer settings](https://learn.microsoft.com/en-us/fabric/admin/service-admin-portal-developer) 和 [Workspace API prerequisites](https://learn.microsoft.com/en-us/rest/api/fabric/core/workspaces/create-workspace)。待租户设置查明后再发独立受审查的请求重新验证。

- [x] 1.5 **实测 E2E PASS（2026-10-21）**：用户将 Fabric 租户中 `Service principals can create workspaces, connections, and deployment pipelines` 设置保存生效后，原始 [Self-Runner Run #39635155333 — Attempt 2](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39635155333) 成功执行并验证 `johnzhang-test` Workspace Terraform Apply（1 add/0 change/0 destroy，真实 ID `d399f361-bc40-4f88-9615-df138ab8ee3b`）、`lh_johnzhang_test` Lakehouse Terraform Apply（1 add/0 change/0 destroy，真实 ID `5a16b5a1-6274-4b37-8dad-19cb68b5139d`）。OneLake 读取了上游独立 Workspace Remote State 的真实 GUID，两个 Root 采用同名 Terraform CLI Workspace 与不同 Backend Keys。后续分别运行 `terraform plan -detailed-exitcode` 并经 Provider Refresh 确认 `TRIAL_ROOT_NO_DRIFT=workspace` 和 `TRIAL_ROOT_NO_DRIFT=onelake`。真实执行 `TRIAL_F4_WORKSPACE_AND_ONELAKE_E2E=PASS`，`PAID_CAPACITY_CREATED=NO`。此为 Terraform 状态/Provider 刷新和独立 Root 验证；如需 Fabric Portal 或外部 API 单独核验，属于后续可选检查。
- [x] 1.6 更新本 Change 与 `documents/systems/azure-fabric/infra-terraform/CODE.md`，保留初次 Unauthorized 的 Attempt 1 历史与 Attempt 2 成功证据；明确真实 Terraform Workspace、Lakehouse 创建、State Refresh 无漂移和未购买付费 Capacity。

## 2. Exclusions

- 不创建、购买、暂停或恢复任何付费 Fabric Capacity。
- 不触发已保留的 F2 Capacity Apply Workflow；不修改其他 Terraform CLI Workspaces 或老 State。
- 不通过 REST 创建 Workspace 或替换 Terraform 的 Capacity 关联所有权。

## 3. Capacity configuration ownership correction (2026-10-21)

- [x] 3.1 将当前既有 Trial F4 Capacity GUID 作为非秘密资源关联写入各 Workspace Terraform Root 的 `terraform.tfvars`（`johnzhang-test`、`healthcare-omop`）；保留通用 Module、独立 State 和原有真实验收证据，补充配置合同单测。本次仅代码/静态检查，**不运行 Cloud Plan/Apply**。
- [ ] 3.2 Self-Runner 通用 `azure-infra.yaml` 删除 `vars.FABRIC_CAPACITY_ID` / `TF_VAR_capacity_id` 注入，Trial 专用 Workflow 删除固定 GUID 与自动 Push Apply 请求，改为显式手动授权且只从 Healthcare `terraform.tfvars` 读取，静态 CI PASS 后合并。保留历史 Run 证据，不再重跑 Trial 基础设施。
- [ ] 3.3 双仓 Main 和 CI 复核后记录完整证据；此配置调整不代表更换租户已完成真实部署。
