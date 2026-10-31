> **2026-10-31 RETIRED / CLOUD DECOMMISSION PENDING:** The `johnzhang-test` test deployment workstream is no longer active. Test-only Self-Runner workflows removed in PR #350; Native Smoke source/publisher removed from current Healthcare branch. Historical logs and completed checks below remain for audit. **Previously applied Trial F4 Workspace/Lakehouse still require actual Azure/Fabric inventory and Terraform State readback followed by a reviewed controlled teardown.** Never infer a cloud destroy from code deletion. Shared Trial Capacity, `healthcare-omop` and Storage/State backend are out of scope.

# Tasks

## 1. Prepare isolated Terraform infrastructure

- [x] 1.1 新建 `johnzhang-test/workspace/` 与 `onelake/`，保持原 Modules、独立 Backend State 和 CLI Workspace 合同。
- [x] 1.2 新建正式付费 F2 `shared-infra/capacity/` 及 `modules/capacity/`，不修改 Trial 或旧 Capacity。
- [x] 1.3 新增离线合同/terraform fmt/init(backend=false)/validate CI，并更新 CODE 导航。
- [x] 1.4 [Healthcare PR #360](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/360) 的 20/20 CI PASS，已合并 Main `8ebcecd38b5dabe4d959f29020d6b4fe1cfc891f`。静态验收成功不意味着云资源已创建。

## 2. Execute single authorized real E2E

- [ ] 2.1 Self-Runner 新增一次性 `johnzhang-test` 受控真实 Apply 测试 Workflow，固定 SHA、Root、F2 SKU，并对付费 Capacity 添加失败/成功后暂停及最终读回；CI PASS 合并。
> 首次受控 Plan-only 实测：[Self-Runner PR #187](https://github.com/JohnZhang-DataForge/Self-Runner/pull/187) 提供入口，[PR #188](https://github.com/JohnZhang-DataForge/Self-Runner/pull/188) 触发 [Run #39603150226](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39603150226)，绑定 Healthcare SHA `8ebcecd38b5dabe4d959f29020d6b4fe1cfc891f`。AzureRM Backend 初始化、真实现有 OMOP 资源组读取及计划 `1 add / 0 change / 0 destroy` PASS；但最终 Plan FAIL：`data.fabric_capacity.created` 在 Capacity 创建前按 display_name 提前查询，出现 `Unable to find Capacity ... fcjohnzhangtest`。修复策略为 `depends_on = [module.capacity]`，让数据源延后到 Apply 阶段。**本次未执行 Apply、没有创建付费容量，不算真实 E2E PASS；等修复后复测 Plan。**

> 受控 Plan-only 修复复验：[Healthcare PR #361](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/361) 的 20/20 CI PASS，合并 Main `033dd9c1c43929b8dac2390406d2c55268f7e267`；`depends_on = [module.capacity]` 修复了提前查询未来 Capacity 的数据源缺陷。Self-Runner [PR #189](https://github.com/JohnZhang-DataForge/Self-Runner/pull/189) 基于更新 SHA 触发 [Run #39603819808](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39603819808) **SUCCESS**：真实 AzureRM Backend/OIDC 初始化、现有 OMOP RG 读回和 F2 Capacity Plan **1 add / 0 change / 0 destroy**，`data.fabric_capacity.created` 已明确延后到 Apply 时读取，锁定/释放 State 成功。没有运行 Terraform Apply，没有新增付费 Capacity；Workspace/OneLake 尚未真实 Plan/Apply，正式容量付费批准、Apply 后暂停/账单审计仍待验证。此证据不能勾选 Tasks 2.2–2.6。

- [ ] 2.2 在真实环境应用前核查 Azure 订阅/权限/配额、容量 SKU/费用、安全保护与无并行冲突。

> **2026-10-21 真实 Apply 失败（前置条件，禁止盲重试）**：Self-Runner [PR #193](https://github.com/JohnZhang-DataForge/Self-Runner/pull/193) 的单次受控 [Run #39623814666](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39623814666) 已经以用户明确授权触发真实 F2 Terraform Apply，但 Azure 对 `fcjohnzhangtest` 的 `CreateOrUpdate` 返回 **HTTP 409 / MissingSubscriptionRegistration**：目标 Azure Subscription 尚未注册 `Microsoft.Fabric` Resource Provider。Capacity Root 的真实 Plan 为 1 add/0 change/0 destroy；创建阶段被拒，因而没有执行 Workspace 与 OneLake Apply。失败后 ALWAYS Suspend 调用 6 次 ARM GET 均 HTTP 404；独立 [Post-run Watchdog #39624113762](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39624113762) 又 6 次 ARM GET HTTP 404，均表明此目标 Capacity 不存在。两套暂停步骤标记失败是因为**无已创建容量可暂停**，不是已发现收费资源仍在运行。未验证任何 Capacity/Workspace/Lakehouse 创建成功，不应将 Task 2.3–2.6 标记完成。
>
> **HOLD / 下一步**：对准确的目标 Azure Subscription 注册 `Microsoft.Fabric` Resource Provider（订阅级变更，需用户批准或手工操作）并只读验证 `registrationState`；之后再使用新审查的请求/SHA进行真实 Apply。不要重复使用已合并的付费请求文件、不要自动扩大 SKU；现有 Trial 和 `healthcare-omop` 不受影响。失败现象/恢复策略见 [微软官方说明](https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/resource-providers-and-types)。

- [ ] 2.3 Capacity Root 真实 Apply 并读回 ARM ID/Fabric GUID 和 State；如果 API 拒绝、阻断或结果不明必须记录。
- [ ] 2.4 Workspace Root 真实 Plan/Apply `johnzhang-test`，证实与 `healthcare-omop` 分离。
- [ ] 2.5 OneLake Root 真实 Plan/Apply `lh_johnzhang_test`、读回 GUID、重复 Plan 幂等。
- [ ] 2.6 暂停新正式 F2 Capacity，读回确实 Suspended 并记录 Run、SHA、阻塞项和计费风险；不执行 Destroy、不修改旧 State。

## Exclusions

- 不替现有 `healthcare-omop` 做 Import/Apply。
- 不使用 Trial Capacity 作为 AzureARM Terraform-paid Capacity。
- 不允许手工 Workspace REST 创建、变更 Capacity 关联或删除云资源。
