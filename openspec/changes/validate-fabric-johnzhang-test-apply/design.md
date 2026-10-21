# Design

- **正式付费 Capacity Root** `shared-infra/capacity/` → `modules/capacity/` → `azurerm_fabric_capacity`，State `shared-infra/capacity.tfstate`、Terraform CLI `default`。只引用已存在 OMOP Resource Group；型号锁定 F2，Region East US；`data.fabric_capacity` 用于获得真实 Fabric Capacity GUID 与 ARM ID 分离。管理员包含当前部署身份与已存在 Fabric 管理员。
- **Fabric Workspace Root** `fabric-workspace/johnzhang-test/workspace/`，Terraform CLI `johnzhang-test`，原共享 Workspace Module，`TF_VAR_capacity_id` 从 Capacity Root 已成功 Apply 的 Output 读取；不使用 Trial GUID，不另建 Workspace REST 接口。
- **OneLake Root** `fabric-workspace/johnzhang-test/onelake/`，同名 CLI Workspace，`lh_johnzhang_test`，跨 Root 读取 `fabric_workspace_id`。
- 三 Roots 没有 Apply-All 常规入口；本次为有限范围 E2E 执行固定三次独立 Root 的 Plan/Apply，每次先审查生成的 Plan，禁止 Delete/Replace。绝不触碰 `healthcare-omop`、旧 `dev` 或 `fabric/platform` States。
- 付费 Capacity 资源创建会开始计费。必须在动作前记录 SKU=F2、目标 RG/region、所属订阅、计费风险；失败和成功后都要调用已实现的 ARM suspend REST，GET 确认状态。REST 操作不得创建或管理 Workspace。
- 停止规则：未经批准的变更、Azure quota/RBAC/provider fail、未知 post-apply 状态、暂停无法确认 → HOLD 并报告收费风险。不能自动销毁或越权修复。测试后暂停会使 Workspace/Lakehouse 暂不可用，但保留 Terraform State 和资源供后续恢复。
