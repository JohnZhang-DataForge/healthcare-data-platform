# Tasks

## 1. Trial-only infrastructure validation design

- [x] 1.1 审核用户免费 Trial F4 `3914ac8b-3375-498b-b3c0-1180a1902dd6`、现有 Workspace/OneLake Terraform Roots、Self-Runner 边界和 Azure Free Trial F2 配额阻断事实。
- [x] 1.2 建立本 Change 的 Proposal、Design、Delta Spec 与试用模式运行门禁；只修改源码导航，不更改付费 Capacity Root。
- [ ] 1.3 开发独立 Self-Runner Trial-only Workspace → Lakehouse Plan/Apply Workflow 及静态合同测试，CI PASS 并合并。
- [ ] 1.4 提交唯一受审查的试用执行请求，记录 Runner Run ID 与真实结果；不得另建/升级付费 Capacity。
- [ ] 1.5 成功后独立读回 Workspace/Lakehouse、State 和重复 Plan；若 Fabric Trial 不支持 OIDC Service Principal 则 FAIL/HOLD 并记录 Provider 具体错误，不自动使用 REST API 代替 Terraform。
- [ ] 1.6 根据实际执行修订 CODE 导航与验收证据，避免将静态 CI 当作云端部署成功。

## 2. Exclusions

- 不创建、购买、暂停或恢复任何付费 Fabric Capacity。
- 不触发已保留的 F2 Capacity Apply Workflow；不修改其他 Terraform CLI Workspaces 或老 State。
- 不通过 REST 创建 Workspace 或替换 Terraform 的 Capacity 关联所有权。
