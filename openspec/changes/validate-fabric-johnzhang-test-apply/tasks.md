# Tasks

## 1. Prepare isolated Terraform infrastructure

- [x] 1.1 新建 `johnzhang-test/workspace/` 与 `onelake/`，保持原 Modules、独立 Backend State 和 CLI Workspace 合同。
- [x] 1.2 新建正式付费 F2 `shared-infra/capacity/` 及 `modules/capacity/`，不修改 Trial 或旧 Capacity。
- [x] 1.3 新增离线合同/terraform fmt/init(backend=false)/validate CI，并更新 CODE 导航。
- [ ] 1.4 通过 Healthcare PR CI、合并并记录 SHA。

## 2. Execute single authorized real E2E

- [ ] 2.1 Self-Runner 新增一次性 `johnzhang-test` 受控真实 Apply 测试 Workflow，固定 SHA、Root、F2 SKU，并对付费 Capacity 添加失败/成功后暂停及最终读回；CI PASS 合并。
- [ ] 2.2 在真实环境应用前核查 Azure 订阅/权限/配额、容量 SKU/费用、安全保护与无并行冲突。
- [ ] 2.3 Capacity Root 真实 Apply 并读回 ARM ID/Fabric GUID 和 State；如果 API 拒绝、阻断或结果不明必须记录。
- [ ] 2.4 Workspace Root 真实 Plan/Apply `johnzhang-test`，证实与 `healthcare-omop` 分离。
- [ ] 2.5 OneLake Root 真实 Plan/Apply `lh_johnzhang_test`、读回 GUID、重复 Plan 幂等。
- [ ] 2.6 暂停新正式 F2 Capacity，读回确实 Suspended 并记录 Run、SHA、阻塞项和计费风险；不执行 Destroy、不修改旧 State。

## Exclusions

- 不替现有 `healthcare-omop` 做 Import/Apply。
- 不使用 Trial Capacity 作为 AzureARM Terraform-paid Capacity。
- 不允许手工 Workspace REST 创建、变更 Capacity 关联或删除云资源。
