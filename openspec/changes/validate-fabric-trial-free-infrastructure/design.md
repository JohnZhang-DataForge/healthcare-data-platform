# Design

## Decisions

1. **身份与容量**：用当前 GitHub OIDC Service Principal；`TF_VAR_capacity_id` 注入固定已有 Trial GUID `3914ac8b-3375-498b-b3c0-1180a1902dd6`。此 GUID 是 Workspace Terraform 的关联引用，不是 Azure ARM Capacity。禁止 Capacity 付费 Root、ARM CREATE/RESUME/PAUSE。
2. **Roots 与远程 State**：`johnzhang-test/workspace` 使用 AzureRM Backend 基础 Key `fabric-workspace/workspace.tfstate` + Terraform CLI Workspace `johnzhang-test`。OneLake 使用 `fabric-workspace/onelake.tfstate` + 同名 CLI Workspace，远程读真实 Workspace GUID；不碰 `healthcare-omop` 的 CLI/State。
3. **执行**：Runner Main 仅在审查并合并固定 JSON 请求文件后触发；请求锁定 SHA、workspace、lakehouse、Trial GUID、模式和操作。先 `terraform plan` 检查无 update/delete/replace 后 Apply Workspace；验证真实输出后再 Apply OneLake；两 Root 再次 Plan 验证幂等。如 Workspace 失败，不碰 OneLake。
4. **边界与状态**：不自动恢复/停止试用 Capacity；Trial 无对应 ARM 生命周期，既不创建也不管理。Provider 对 Trial 的支持仍属待实测；失败记 FAIL 并停止，禁止以 REST API 创建 Workspace。
5. **验收证据**：双仓 Main SHA、PR/Run ID、Workspace/Lakehouse GUID、独立 State 和二次 Plan 结果；静态校验不等于创建完成。

## Amendment — Capacity reference ownership (2026-10-21)

上述 Decisions 1/3 记录首次 E2E 的**历史实现**，而非长期部署合同。现行规定：每个 `fabric-workspace/<name>/workspace/terraform.tfvars` 存放各自已存在 Capacity 的 `capacity_id`；`modules/workspace` 保持通用，Workflow 不注入 `TF_VAR_capacity_id`、不在 Self-Runner Git/Repo Variables 存放 Capacity GUID。不同租户只需更新该 Terraform 配置与 OIDC/Backend 身份设置。一次性历史 Self-Runner JSON 请求停止作为执行入口，专用复验采用明确手动确认，不在源码改动时自动 Apply；不触碰已有远程 State、不创建/修改付费 Capacity。

## Amendment — Workspace Portal administrator access (2026-10-21)

Fabric Tenant Admin 身份不自动获得普通 Workspace 成员访问权限：已有 Workspace 经 Terraform Service Principal 创建，`role_assignments={}` 表示没有显式 Portal 用户成员。两个 Workspace Terraform Root 增加可选 `portal_admin_user_object_id`，只允许经核实 Entra User Object ID（GUID）或 null。设置后由现有 Module 的 `fabric_workspace_role_assignment.additional` 管理 `User/Admin`；不需要新增 Terraform Provider、Microsoft Graph `User.Read.All` 权限、Self-Runner Repo Variable 或在 Runner 保存对象 ID。null 明确不创建授权；如果目标身份已被其他 State 或 Portal 管理，禁止盲目重复管理/创建。先离线 CI，实际权限变更须批准的单 Root Plan/Apply 与读回。更换租户只变更相应 Workspace Root `terraform.tfvars`、OIDC/Backend 前置仍另行处理。
