# Proposal

## Why

现有 Fabric Trial F4 Capacity 已免费激活，而用户要求 **Workspace 始终只由 Terraform 管理**；Capacity ID 是 Workspace 配置引用，并不代表 Workspace Terraform 管理/购买 Capacity。本变更仅补充可复用的 Capacity 运行态 REST API，试用只读、付费容量受控暂停和恢复节约计算费用。不要创建第二套 Workspace REST 部署架构。

## What Changes

- 在 `azure-fabric/infra-terraform/fabric-workspace/healthcare-omop/capacity-api/` 开发功能模块 `capacity_lifecycle.py`，只使用明确的 Capacity API。不得调用任何 Workspace REST 创建、Assign、删除、修改。
- Trial：现有 F4 GUID 只读 `GET /v1/capacities/{capacityId}`，只允许 inspect。试用期限免费，不承诺支持 API 暂停/恢复。
- Paid：针对将来通过独立 Terraform 管理并由明确 Azure ARM Resource ID 指向的现有正式 F SKU，支持 GET、`POST /suspend` 和 `POST /resume`；不创建、不购买、不扩容、不删除 Capacity。
- Self-Runner 单独手工 Workflow，默认 Trial inspect；Paid 操作需操作者显式输入 `mode=paid`，`ENABLE_PAID_CAPACITY_OPERATIONS=true`，操作确认以及 Azure 最小 RBAC；没有自动定时 Resume、没有 push 自动 Write。
- Python 标准库 + GitHub OIDC，不记录令牌；静态合同/单元测试不触碰 Azure。

## Capabilities

### New Capabilities

- `fabric-capacity-runtime-lifecycle`：Trial read-only 与 paid Capacity 生命周期受控运维接口。

## Impact

不会改动现有 `modules/workspace`、Workspace Terraform Root、`capacity_id`、OneLake 或旧 State。新的付费 Capacity 的 Terraform 创建/规格管理是另一个需成本批准的任务。本 PR 不实际调用云端 API，尤其不执行 suspend/resume。
