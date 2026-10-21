# Tasks

> 本 Change 不创建/购买 Capacity；Workspace 仅 Terraform 管理。源码/Workflow 静态测试不等同于取得权限或运行成功。

## 1. Capacity REST 源码（不创建 Workspace）

- [x] 1.1 新建 `fabric-workspace/healthcare-omop/capacity-api/` Trial 只读查询及 Paid ARM 预检/suspend/resume 控制器，不含 Workspace REST 接口。
- [x] 1.2 增加 Capacity 源码合同/负向测试及 GitHub PR 静态 CI；复核 OIDC、资源 ID、防误写、State 独立边界。
- [x] 1.3 更新 Terraform CODE.md 和容量操作 README，明确试用免费、正式容量费用、权限和同一资源只由一个 Owner 管理。
- [ ] 1.4 完成 Healthcare PR 的 CI 验收并合并，记录最终 SHA。

## 2. Self-Runner 运行入口

- [ ] 2.1 开发单独手工 `fabric-capacity-lifecycle.yml`，默认 trial/inspect；Paid suspend/resume 需附加授权/确认开关，禁用任何自动付费写操作。
- [ ] 2.2 为 Workflow 建立离线静态测试，验证参数、无自动触发、受控 checkout、OIDC 和成本门禁；CI PASS 后合并 Main。
- [ ] 2.3 只读 Trial GET 真实身份/权限验证（须明确评估跨会话共享资源操作门禁）；如未获权限或失败，记录为阻塞，不自动扩大 Azure RBAC。
- [ ] 2.4 将来确有正式付费 Capacity 且用户明确授权后，再测试真实 Suspend/Resume；没有付费容量时保持未实施，绝不制造费用。

## 3. Out of scope

- 不开发第二套 Workspace REST CRUD/Assign。
- 不创建付费 Capacity 的 Terraform Root 或自动计费资源；按需单独 OpenSpec。
- 不暂停/恢复当前 Trial，也不自动定时启用付费 Capacity。
