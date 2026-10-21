# Fabric Capacity lifecycle REST interface (Healthcare OMOP)

这里是**Capacity 的运行态控制**，不是 Workspace 的 REST API。Workspace 的创建、配置及 `capacity_id` 关联仍**完全由 `../workspace/` Terraform Root 管理**；不得由本接口创建/删除/assign Fabric Workspace。

| 模式 | 只读查看 | 暂停 | 恢复 | 所需授权 |
| --- | --- | --- | --- | --- |
| `trial` | Fabric Core `GET /v1/capacities/{id}` | 不支持 | 不支持 | Service Principal 在 Trial Capacity 上为管理员或 Contributor |
| `paid` | Azure ARM `GET Microsoft.Fabric/capacities/{name}` | Azure ARM `POST .../suspend` | Azure ARM `POST .../resume` | Azure 管理的真实 F SKU + 最小权限 Azure RBAC |

## 源码和部署合同

- `capacity_lifecycle.py`：Python 标准库实现，GitHub Actions OIDC -> Entra token；Trial 使用 Fabric API Audience，Paid 使用 ARM Audience。失败不泄露令牌。
- `capacity.json`：仅配置当前已存在的免费试用 Capacity GUID；不是正式容量 ARM 资源，也不是 Terraform State。
- Self-Runner `.github/workflows/fabric-capacity-lifecycle.yml`：手工 mode `trial|paid` 和 operation `inspect|suspend|resume`；默认仅 `trial/inspect`。Workflow 保留用户明确选择的资源和 Git SHA，执行代码位于 Healthcare Main，受试用 ID 固定配置约束。
- 正式模式传入环境变量 `PAID_CAPACITY_ARM_ID`（完整已存在 `/subscriptions/.../resourceGroups/.../providers/Microsoft.Fabric/capacities/<name>`）、匹配 `ARM_SUBSCRIPTION_ID`；不会自动创建、购买、删除或者扩容 Capacity。
- 正式 suspend/resume 必须由手工输入匹配 confirmation，并启用 repository variable `ENABLE_PAID_CAPACITY_OPERATIONS=true`。异步操作需独立 GET 确认状态；未确认不能判 PASS。

## 权限与计费边界

当前试用 F4 是免费 60 天 Capacity，**没有暂停/恢复开关的自动化需求**，使用 Fabric REST API 只读查询现有容量。Service Principal 需额外获得 Capacity Admin/Contributor，才可使用 GET；Workspace 管理员身份不一定等价于 Capacity 权限。

正式 F SKU 的定义/规格由未来另行审批的 Terraform Root 管理；ARM REST 调用仅改变运行态，Terraform 不修改容量规格。Azure 最小 RBAC actions：`Microsoft.Fabric/capacities/read`、`write`、`suspend/action`、`resume/action`。**恢复计费，暂停可能影响全部 Workspace，已有超额计算可能结算，OneLake Storage 计费仍继续**。对共享 Capacity 操作前检查无正在进行的 DAG/查询/用户会话；没有实时确认和批准时不要触发写操作。

官方接口：
- https://learn.microsoft.com/en-us/rest/api/fabric/core/capacities/get-capacity
- https://learn.microsoft.com/en-us/rest/api/microsoftfabric/fabric-capacities/get?view=rest-microsoftfabric-2023-11-01
- https://learn.microsoft.com/en-us/rest/api/microsoftfabric/fabric-capacities/suspend?view=rest-microsoftfabric-2023-11-01
- https://learn.microsoft.com/en-us/rest/api/microsoftfabric/fabric-capacities/resume?view=rest-microsoftfabric-2023-11-01
- https://learn.microsoft.com/en-us/fabric/enterprise/pause-resume
