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
- [x] 3.2 Self-Runner 通用 `azure-infra.yaml` 删除 `vars.FABRIC_CAPACITY_ID` / `TF_VAR_capacity_id` 注入，Trial 专用 Workflow 删除固定 GUID 与自动 Push Apply 请求，改为显式手动授权且只从 Healthcare `terraform.tfvars` 读取，静态 CI PASS 后合并。保留历史 Run 证据，不再重跑 Trial 基础设施。
- [x] 3.3 双仓 Main 和 CI 复核后记录完整证据；此配置调整不代表更换租户已完成真实部署。

> **代码合并与静态 CI 证据（2026-10-21）**：Healthcare [PR #378](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/378) 已合并 Main `3e1320562a24c5feec05be484bb43429ba73c646`，最终 PR HEAD `06923bfa8177484ff13a5f190e7a14f10c5d0591`，GitHub 21/21 Checks PASS（包含 Terraform `init -backend=false` / `validate`、静态合同、OpenSpec、文档检查）。Self-Runner [PR #207](https://github.com/JohnZhang-DataForge/Self-Runner/pull/207) 已合并 Main `29094515eeb84f79a89c34061e55becd96e7d9ad`，最终 PR HEAD `93534e08ecbe6b34308faef788804acf9a56054f`，`check-azure-infra-workflows` 与 `trial-only-contract` **2/2 SUCCESS**（[Workflow Run #39653016673](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39653016673)、[Run #39653016666](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39653016666)）。原 Self-Runner Trial JSON 文件已从 Main 删除，F4 E2E Workflow 不再响应 Git Push，专用重跑需手动 40 位 Healthcare SHA 与精确确认。**本轮 0 Cloud Plan/Apply、0 Capacity 创建/修改、0 Workspace/Lakehouse 重建；先前真实 E2E 结果保留。** 后续新租户仍需准备身份/OIDC、Backend 和已有免费 Trial Capacity 并更新相应 Workspace `terraform.tfvars`。

## 4. Fabric Portal user Workspace Admin via Terraform (2026-10-21)

- [x] 4.1 因 Fabric Admin 账号可在管理员治理列表查见 `johnzhang-test`，但普通 Workspaces 列表看不见，确认源码 `role_assignments = {}` 不会添加业务用户。双 Workspace Root 增加 `portal_admin_user_object_id`（默认 null、UUID 校验）及通过现有 `modules/workspace` 的 `fabric_workspace_role_assignment` 合并授予 `principal_type=User`、`role=Admin`；当前用户 UPN 仅作为对象 ID 查询提示，不能冒充 GUID。补充离线测试、CODE 映射。此任务只证明可复用代码机制，**尚未授予真实权限**。
- [ ] 4.2 取得 `johnzhang-fabric@guangbinzhang8888gmail.onmicrosoft.com` 对应 Entra **User Object ID** 的可核实值（不同于 Tenant ID、Client ID、Service Principal Object ID）；写入 `johnzhang-test/workspace/terraform.tfvars`，并按实际目标决定是否写入 `healthcare-omop`。使用受控权限/State 检查确认不会导入重复已有成员；经批准执行现有 Workspace 单 Root Plan/Apply，独立 Fabric Workspace 成员读回及用户普通工作区列表可见性验证。若已存在手工同一用户授权，先按独立变更决定 import/ownership，避免重复创建。
- [ ] 4.3 上述真实授权验收及无不相关资源漂移后，追加 PR/Run、实际 Workspace GUID、Member role 与用户 Portal 可见性证据；不得声称只凭静态通过就修复了 Portal 访问。

- [x] 4.4 用户提供拟授权的 Entra User Object ID `670194b1-b1ff-41af-971a-a61438061f39`；仅写入 `johnzhang-test/workspace/terraform.tfvars`，另一实例 `healthcare-omop` 保持 null。补充静态回归断言和 CI；ID 与目标用户身份的 Entra 目录关联、现有权限是否已存在，仍需在真实执行前核对。

> **2026-10-21 用户 Object ID 配置变更**：已将用户提供的 `670194b1-b1ff-41af-971a-a61438061f39` 写入 Terraform 实例变量，仅影响 `johnzhang-test` 的目标成员配置。PR/静态 CI 与将来的真实 IAM Apply 分开记录；不得因用户提供 UUID 就断言其归属已由 Entra 目录读回验证，或断言已部署/已可在普通 Portal 列表查看。未触碰 `healthcare-omop`、容量、OneLake、State 或 Self-Runner。
