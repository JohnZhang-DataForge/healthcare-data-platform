# Design

## Decisions

1. **身份与容量**：用当前 GitHub OIDC Service Principal；`TF_VAR_capacity_id` 注入固定已有 Trial GUID `3914ac8b-3375-498b-b3c0-1180a1902dd6`。此 GUID 是 Workspace Terraform 的关联引用，不是 Azure ARM Capacity。禁止 Capacity 付费 Root、ARM CREATE/RESUME/PAUSE。
2. **Roots 与远程 State**：`johnzhang-test/workspace` 使用 AzureRM Backend 基础 Key `fabric-workspace/workspace.tfstate` + Terraform CLI Workspace `johnzhang-test`。OneLake 使用 `fabric-workspace/onelake.tfstate` + 同名 CLI Workspace，远程读真实 Workspace GUID；不碰 `healthcare-omop` 的 CLI/State。
3. **执行**：Runner Main 仅在审查并合并固定 JSON 请求文件后触发；请求锁定 SHA、workspace、lakehouse、Trial GUID、模式和操作。先 `terraform plan` 检查无 update/delete/replace 后 Apply Workspace；验证真实输出后再 Apply OneLake；两 Root 再次 Plan 验证幂等。如 Workspace 失败，不碰 OneLake。
4. **边界与状态**：不自动恢复/停止试用 Capacity；Trial 无对应 ARM 生命周期，既不创建也不管理。Provider 对 Trial 的支持仍属待实测；失败记 FAIL 并停止，禁止以 REST API 创建 Workspace。
5. **验收证据**：双仓 Main SHA、PR/Run ID、Workspace/Lakehouse GUID、独立 State 和二次 Plan 结果；静态校验不等于创建完成。
