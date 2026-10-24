# Proposal

## Why

真实付费 F2 的 Terraform Apply 受 Azure Free Trial 订阅容量配额阻断；用户现已明确决定**只使用现有免费 Fabric Trial F4** 验证基础设施，不创建任何付费 Capacity，也不升级 Azure 订阅。

## What Changes

- 保留当前 `azure-fabric/infra-terraform/fabric-workspace/johnzhang-test/{workspace,onelake}/` Terraform Roots、Modules 和分离 State；不修改 Fabric Workspace 的 Terraform 独占管理规则。
- 建立独立、一次性、可审查的 Self-Runner **Trial-only** GitHub Workflow 和请求合同，Capacity 固定为当前已存在 Trial GUID `3914ac8b-3375-498b-b3c0-1180a1902dd6`；只可对 `johnzhang-test` Workspace 和 `lh_johnzhang_test` Lakehouse 执行 Plan/Apply。
- 不触及 `shared-infra/capacity/`，不运行 `azurerm_fabric_capacity`、Capacity REST suspend/resume、Azure Billing/Upgrade/Quota。
- 真实 Apply 后读取两个 Terraform 输出和再次 Plan，确认独立 State；若试用容量不能由当前 OIDC Service Principal 使用，则记录具体错误，不扩大权限/切付费路径。

## Capabilities

### New Capabilities

- `fabric-trial-free-terraform-validation`：使用已存在免费 Trial F4 的 Workspace/Lakehouse Terraform 实测。

## Impact

不创建付费计算 Capacity。Lakehouse 可能产生少量 OneLake 存储用量；不对现有 Workspace/Trial 容量做删除、暂停或改配置。需要注意 Trial 可能拒绝 SP 关联，测试期间暂不将这个分支归档。
