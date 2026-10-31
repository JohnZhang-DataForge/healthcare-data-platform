> **2026-10-31 RETIREMENT NOTICE:** Historical Trial `johnzhang-test` Native smoke source, Trial Publisher and Self-Runner workflow requests have been retired (Self-Runner PR #350; current Healthcare cleanup PR). Previously checked off tasks remain historical evidence only and are **not authorization to redeploy**. Retire cloud Workspace/Lakehouse only after inventory + Terraform State preflight and independently reviewed teardown; `healthcare-omop` and shared Trial Capacity are excluded.

# Tasks

> **ACTIVE — 2026-10-21**。接续已完成的 Trial F4 Terraform Workspace/Lakehouse，不重复基础设施部署。新的 `shared-infra/connection` 与 Fabric Item 发布分开测试、分开授权；只有证据到位才能打勾。

## 9. 2026-10-31 johnzhang-test source retirement

- [x] 9.1 正式退役 `johnzhang-test` 原生 Notebook/Pipeline Smoke 定义、专用 `trial_smoke_publisher.py`、相关离线测试与静态 CI；Self-Runner PR #350 已取消旧 Apply/Publish/付费 F2 测试触发；修复 CODE 索引及 ADR/OpenSpec 引用。**仅 Git 源码清理；曾真实 Terraform Apply 的 Trial F4 Workspace/Lakehouse 和远程 State 必须独立核对并受控销毁，未完成时保留 Terraform Roots。**

## 1. Source audit and scope

- [x] 1.1 核对 Healthcare Main `e49404ff7fde473d877c13fb37c8ce7ad33e2d4f`、Self-Runner Main `865a8f0eb7fbdcabceb190ac17f3915790ba0e2c`，OpenSpec 当前权属和 Run #39635155333 Attempt 2 的真实 Trial F4 验收。
- [x] 1.2 冻结 Connection/Terraform 与 Notebook/Pipeline/`fabric-cicd` 的独占 Owner、外部 Blob Reader RBAC 和不创建付费 Capacity 的边界。

## 2. Connection — first component

- [x] 2.1 复用 `modules/connection` 添加 `shared-infra/connection` Root、独立 State、默认禁用/无秘密示例、静态合同和 `init -backend=false`、`validate` CI；合并 Main 并记录准确 PR/Run。
- [x] 2.2 核实 Fabric 当前 Tenant `AzureBlobs` Connector、认证模式、Reader RBAC、已有 Connection Inventory/Key Vault Secret Reference；记录负向门禁。
- [x] 2.3 在明确的 Live 授权下仅对 Connection Root 执行受控 Plan/Apply/ID readback/重复 Plan；不得触碰 Workspace/OneLake/Capacity Roots。

## 3. Fabric native Item publishing

- [x] 3.1 添加 `johnzhang-test` 的真实 Fabric Git Native Notebook/Pipeline 源码与 logicalId，更新对应 CODE.md；先只做无数据写入的 Smoke。
- [x] 3.2 实现 `fabric-cicd` 受控入口和 Self-Runner 精确 SHA/Outputs/Item 白名单/OIDC、禁用 orphan 删除；测试负向/重复发布合同。
- [ ] 3.3 Live 发布+读回 Notebook/Pipeline（而非 Terraform）、执行无数据写入的 Pipeline→Notebook Smoke；记录 Run/实际 GUID/重复部署证据。

## 4. Business ETL follow-up

- [ ] 4.1 独立 OpenSpec 接管 PG OMOP snapshot Exporter/Manifest READY、Fabric Notebook Delta person/visit_occurrence 和 Pipeline 编排/参数合同。
- [ ] 4.2 真实 Blob Reader→Notebook→Lakehouse E2E；PK/FK/count/DQ/Manifest Hash/重复 export 对账、失败重试；仅在真实证据后声明通过。
- [ ] 4.3 更新 `organize-fabric-terraform-by-workspace` Tasks 3.4/4.4、长期架构和 `PROJECT-STATUS.md` 的实际完成范围；不要把旧 NO APPLY 当新事实。

## 2026-10-21 Task 2.1 源码/静态验收

- [Healthcare PR #372](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/372) 增加可选共享 Connection Root、独立 `shared-infra/connection.tfstate`、默认 `connection=null`、Terraform 源码导航与离线测试。
- 首次 CI Run [#39640775701](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39640775701) 的 Connection Job 仅因 `terraform fmt` 格式对齐失败；修正后 HEAD `696ab602dda498a5b2d120dd5c008e772c503836` 的 **21/21 CI Check PASS**，包含 `terraform validate / shared-infra / connection`、OpenSpec Trusted Gate 和 Documentation Links。
- **只验证源码/静态**：未初始化 Remote Backend、未 Plan/Apply、没有创建 Connection、Notebook/Pipeline、Workspace/Lakehouse 或付费 Capacity。任务 2.2–4.3 不因本次通过而完成。

## Task 3.1 — Git-native source candidate (2026-10-21)

- 新增 `azure-fabric/workspaces/johnzhang-test/` 下 Notebook/Pipeline 原生源码，使用固定且不同的 Git `.platform` logicalId；Pipeline Notebook activity 使用 Notebook logicalId + 全零 Workspace ID（相同 Workspace Fabric 自动绑定候选）。
- 提交静态反向约束：源码不得读/写 Blob/Delta，Pipeline 无 schedule、无隐式 workspace-specific GUID；只管理 Notebook/Pipeline，不管理 Workspace/Lakehouse。
- PR #374 的静态/门禁 **6/6 PASS**，Task 3.1 只表明 Git Native 源码和离线合同完成；真实 Fabric 发布、Item GUID 映射与运行仍属于 3.2–3.3，绝不在本任务宣称已云端创建。

- [Healthcare PR #374](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/374) 对原生 Notebook/Pipeline 采用独立静态验收；精确 HEAD `ec168ecfe848b98fdf3d62e8e662f3c7ee441e29` **6/6 CI PASS**，没有云端副作用。后续源码如有新提交，以新 HEAD CI 为准。

## Task 3.2 — Publisher source candidate (2026-10-21)

- 加入 Trial-only `trial_smoke_publisher.py` 的 `validate`（完全离线）和 `publish`（严格确认、Workspace/OneLake Terraform 真实 Outputs、限定 Notebook/Pipeline 的 Git 源、拒绝不明已有同名 Item、使用 `fabric-cicd`、发布后 API 读回），绝不清理 orphan Items。更新 CODE.md、单元测试。
- Self-Runner [PR #204](https://github.com/JohnZhang-DataForge/Self-Runner/pull/204) 已合并 Main `4d31fcd17fba15f57f52bd08ad8ec4f9cfe9e01b`，新增手工 Workflow `fabric-trial-native-item-publish.yml`，默认 `validate`；只有明确 `publish` 和固定确认字符串才允许云端创建。Self-Runner 静态 [Run #39642722530](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39642722530) **PASS**。Healthcare 侧 publisher 静态检查在 [PR #375](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/375) 合并后与本 Task 一并纳管；真实 Runner `validate` 和 Fabric `publish` 尚待独立执行/验收。**Task 3.2 的勾选仅代表代码与静态接力已实现，不代表任何连接/Item 真实创建或运行。**

## Self-Runner Validate-only 真实接力验收 — 2026-10-21

- Self-Runner [PR #205](https://github.com/JohnZhang-DataForge/Self-Runner/pull/205) 合并 Main `767e6f79e5643de994e6d4bb192ab18e415ed0bc` 后，通过严格 JSON `requests/fabric-trial/native-item-validate.json` 触发受审查的 **validate-only** 模式；Push 无 `publish` 能力。
- [Fabric Native Item Workflow Run #39643321246](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39643321246) **SUCCESS**，严格检出 Healthcare Main `23fa496c2ecf3c5255e77a505a497992a823e44e`；日志包含 `MODE=validate`、`SOURCE_CONTRACT=PASS`、`FABRIC_NOTEBOOK` logicalId、`OFFLINE_SOURCE_VALIDATION=PASS`、`REMOTE_STATE_READ=NO`、`FABRIC_ITEMS_WRITTEN=NO`。
- 同一 Self-Runner 合并 Push 还触发了旧 Generic Task Workflow [Run #39643321189](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39643321189)，因缺少预期的 `requests/task*` 新请求而 Fail Gate（`Expected one newly committed task request; got []`），**与 Fabric native-item workflow 无关**。这是独立的旧通用触发器问题，不据此重跑、修改或宣称 Fabric CI 失败。
- **边界**：这里只验证 Runner 接力和源码合同，不读取 Remote State、不调用 Fabric Publish、不启动 Notebook/Pipeline、不创建收费 Capacity。真正云端 Item Publish、重复部署、Notebook/Pipeline Activity、OMOP 双表 E2E 继续留在 Task 2.2–2.3 / 3.3 / 4.x 未完成栏。

## 2026-10-21 — Storage/Connection 只读预检开发（未做 Live）

- 核对 Healthcare Main `f83b46e830787ebcb4f3e37776e1b47c25913868`、Self-Runner Main `29094515eeb84f79a89c34061e55becd96e7d9ad`；Healthcare 无开放 PR，Self-Runner Local DP 其它 PR 不触碰。Connection Root `terraform.tfvars` 仍为 `connection = null`、Storage 仍只查询现有 Azure account/landing，不创建新资源。
- Task 2.2 下增加 **read-only inspection**：通过 GitHub OIDC 对 ARM subscription tenant、现有 Storage、account-scope role assignments 和 Fabric `supportedConnectionTypes`/`connections` 做实时查询；如果两 Tenant 不同，WorkspaceIdentity 不支持跨租户，必须评估 ServicePrincipal 等经实际许可的路径。测试仅是 offline，不可将 inspection 等同于 Blob Reader 授权、Connection Apply 或 Notebook 读取。
- 本阶段保持 Task 2.2/2.3/3.3 **未完成**；须先取得精确运行证据并复核既有连接名称、Reader identity、Notebook code credential support、Storage 网络限制后决定 `connection != null` 与未来受控 Apply。严禁从 read-only 检查推断存在数据通路。

## 2026-10-21 — Workspace Identity Terraform 进入代码开发阶段

- [已核查 Read-only Run #39694852934](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39694852934) 表明本次部署配置 Storage/Fabric Tenant 相同，AzureBlobs 支持 WorkspaceIdentity 的 user-controlled-code 使用，现有匹配 Connection 名称列表为空。Storage account scope 有 2 项角色分配但尚未独立核准具体 Reader principal，**不可据此声明 Azure Blob 权限已生效**。
- 沿 Task 2.2 增补 `modules/workspace` 可选 `SystemAssigned` Identity，默认关闭；只在 `fabric-workspace/healthcare-omop/workspace/terraform.tfvars` 启用，输出后续 RBAC 所需 Service Principal Object ID。不触碰 `johnzhang-test`，不创建/升级/购买 Capacity。
- 该代码批次需先独立 PR/CI；合并后仅运行明确授权的 `healthcare-omop/workspace` Terraform Plan，核对原地 Update / 无 Delete/Replace 和当前 State ID 读取。**Plan 不等于 Apply**；Identity Apply 和 Storage Blob Data Reader 授权必须由独立安全检查及审批后执行。Task 2.2、2.3、3.3 保持未完成，直到真实 Connection/Notebook Blob read evidence 到位。

## 2026-10-21 — Workspace Identity real Plan evidence (NO APPLY)

- Healthcare PR #388 merged after 21/21 CI PASS: Main 5114dacff0318167582c0f08eb8fec6a8f453cdc. Module identity defaults disabled, only healthcare-omop opts in. johnzhang-test and Trial F4 untouched.
- Self-Runner PR #214 merged as 46b87fd9b6be0820dfb989f920df34cbd6339107. Plan-only Run https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39698376237 SUCCESS. Reviewed Healthcare SHA pinned. Existing workspace state refreshed: 745ce03b-15b6-4870-b0e5-8c5750aa18dc; portal Admin role also refreshed.
- Terraform Plan: 0 to add, 1 to change, 0 to destroy. Only resource module.workspace.fabric_workspace.current will update in-place (identity SystemAssigned); workspace_identity_principal_id remains known after apply. FABRIC_APPLY_EXECUTED=NO and DESTROY_EXECUTED=NO.
- No identity exists from this operation, Blob RBAC remains ungranted/unverified, no Fabric Connection/Notebook/data E2E. Next: obtain separate authorization for healthcare-omop Workspace identity Apply and Object ID readback; plan/grant Storage Blob Data Reader on existing landing scope through reviewed storage Terraform; configure Connection and verify Notebook read. Keep Tasks 2.2, 2.3, 3.3, 4.2 unchecked.

## 2026-10-21 — Identity Apply first failure and gated diagnosis

- User-authorized manual Self-Runner Azure-Infra-TF **Run #39699719585** `apply / healthcare-omop / workspace` reached Fabric Provision Identity LRO at 2026-10-21 20:27 ET. Refresh/Plan successful (`0 add, 1 change, 0 destroy`), Apply resource `fabric_workspace.current` failed with `Could not update resource: Failed to create workspace identity. / Long Running Operation: "Failed"; Error Code: InternalError / "Failed"; Request ID: 075c45dc-a140-41a5-9476-d9f3bb7ae8df`. Terraform did **not** report successful Apply/identity output. No Storage RBAC or Connection attempt.
- Microsoft Fabric official troubleshooting recommends inspecting Workspace settings > Workspace identity for **Failed** provisioning, waiting one hour before deleting *the failed identity* and 5 minutes after deletion before recreation. **This is NOT permission to delete anything**; inspect current state first, especially if identity was partially created. Workspace Identity is supported on Trial Capacity; purchased F SKU is required for trusted-workspace access to firewall-enabled storage, not for creating the identity.
- Add OIDC/GET-only inventory for a named Workspace and exact runner app's explicitly assigned Workspace role, without access tokens/secret printing. Re-run existing Connection inspection only; no Terraform Apply, no workspace identity creation attempt. If Fabric API does not expose identity provisioning state, use UI or Microsoft support correlation Request ID above.


## 2026-10-21 — Fabric Workspace Identity Apply 失败后读回（GET only）

- Self-Runner [Run #39700370845](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39700370845) 使用已审核 Azure/Fabric OIDC Service Principal，固定 Healthcare 来源 Main `56e8eeb991af05b5205e46afd814e4a6e231a942`。真实 `GET /v1/workspaces` + `GET /v1/workspaces/{id}` + `GET /v1/workspaces/{id}/roleAssignments`：`TARGET_WORKSPACE_ID=745ce03b-15b6-4870-b0e5-8c5750aa18dc`，`WORKSPACE_IDENTITY_IN_FABRIC_API=ABSENT`，`WORKSPACE_CAPACITY_ID=3914ac8b-3375-498b-b3c0-1180a1902dd6`，`RUNNER_SERVICE_PRINCIPAL_EXPLICIT_WORKSPACE_ROLES=["Admin"]`，`TENANT_RELATION=SAME`。`CLOUD_RESOURCE_WRITES=NO`，不访问 Terraform backend。
- 这排除了 Runner 缺少显式 Workspace Admin 及 Capacity 被更换这两种直接解释；**无法证明根因**，因为 GET Workspace API 不提供 Identity provisioning 的 Failed 状态。原始失败为 `InternalError / Failed`、Fabric Request ID `075c45dc-a140-41a5-9476-d9f3bb7ae8df`。目前不能说 Identity 已经创建。
- 后续操作：到 Fabric portal `healthcare-omop` → Workspace settings → Workspace identity 查看是否为 `Failed`。官方首次创建故障指导：若 Failed，先等待约一小时，再删除**失败的 Identity**（绝不删除 Workspace 或数据），删除完成再等待 5 分钟才考虑重新创建；须先对当前状态核对并由用户明确授权云端变更。若 UI 无 Failed 或仍报 InternalError，携带 Request ID / Run 和时戳向 Microsoft 支持核查 Tenant/Entra 后台。**禁止盲目重试 Apply 或擅自删除**。
- 不要因为使用免费 Trial F4 而假定无法创建 Identity：微软官方文档允许任意容量创建 Identity；付费 F SKU 限制的是受防火墙限制的 Storage Trusted Workspace Access。后续 Storage RBAC / Connection / Notebook Blob read 依然未执行。

## 2026-10-21 — Workspace Identity 成功 Apply；Landing Reader 配置阶段

- 用户已按 Fabric Workspace identity `Failed` 官方恢复路径删除失败 Identity，再通过手工 Self-Runner [Workspace Plan #39707295376](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39707295376) 和 [Workspace Apply #39707407989](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39707407989) 真实执行。Apply 返回 `Resources: 0 added, 1 changed, 0 destroyed`，现有 Workspace ID 仍为 `745ce03b-15b6-4870-b0e5-8c5750aa18dc`；Terraform 输出 `workspace_identity_principal_id=1ae64649-a7c3-497e-9fe3-69b37d27c453`（**Entra Service Principal Object ID，不是 Application ID**）。源码 SHA `a78cbe1dac9abda7a435acbd82c3ed0275f10042`。完成了 Workspace Identity 创建，但没有 Storage RBAC、Connection 或 Notebook 数据读取。
- 最小 Landing Blob Reader 变更由 **Shared Storage Root** 独立执行：Storage account `johnzhang`、已有 container `landing` 不重建。只以 `Storage Blob Data Reader` 角色授权该容器；通过具名 `healthcare-omop` Terraform Remote State `workspace_identity_principal_id` 自动取得新 Object ID，禁止硬编码新身份 GUID。读 State 的 AzureRM Backend 具名 Workspace 配置来自本实例 `terraform.tfvars`；不影响 `johnzhang-test`。
- 变更审批顺序：源码 PR → offline CI → Main → 只读 Azure ARM 精确 RBAC 枚举（防重复已有角色）→ **仅 shared-infra/storage 真实 Plan** → 必须核对只添加单个容器 Reader、没有任何 delete/replace，再独立授权 Apply 和 readback。部署 Principal 必须具有 `Microsoft.Authorization/roleAssignments/write`；只具 RG Contributor 不足。Role Assignment 的生效可能延迟。未执行或未确认前，不勾选 Task 2.2/2.3/4.2。

## 2026-10-21 — Live Shared Storage Reader Plan evidence

- [Healthcare PR #395](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/395) passed 21/21 CI and merged Main `b022865e89f4a570ef355083297a5547f0bad7fa`. Using named `healthcare-omop` Terraform Workspace State rather than hard-coded Entra identity ID, Shared Storage Root may create container-scope `Storage Blob Data Reader` only. Existing Storage Account/Container are data sources and remain externally owned.
- [Self-Runner PR #221](https://github.com/JohnZhang-DataForge/Self-Runner/pull/221) merged Main `6ac6ad33c0be675da669af4f5146ea690ba5c168`; [Live Plan #39708299828](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39708299828) **SUCCESS**: Remote State output resolves exact Object ID `1ae64649-a7c3-497e-9fe3-69b37d27c453`; only `module.storage.azurerm_role_assignment.landing["healthcare_omop"]` has action `create`. `Plan: 1 to add, 0 to change, 0 to destroy`; scope `/subscriptions/56107520-5920-4e96-9833-5441ded0a90c/resourceGroups/OMOP/providers/Microsoft.Storage/storageAccounts/johnzhang/blobServices/default/containers/landing`, `role_definition_name=Storage Blob Data Reader`. `APPLY_EXECUTED=NO` and `DESTROY_EXECUTED=NO`.
- Before any Reader Apply, record read-only Azure ARM `roleAssignments` metadata at the Storage account and Landing container scopes to screen out pre-existing duplicate/ancestor grants. The `atScope()` ARM filter includes grants at or above the requested scope and excludes child-scope grants; report Object ID/roleDefinitionId/actual scope only, no token, and fail closed if unreadable. Afterwards only allow separately approved, in-plan container RBAC Apply. Fabric Connection/Notebook still pending.

## 2026-10-21 — Azure RBAC inventory check after Reader Plan (no RBAC Apply)

- Healthcare [PR #396](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/396), Main `422ec69ff6ef5ee0eaf31c7f1a09c6b4f7058b96`: read-only ARM `roleAssignments` inventory at existing `johnzhang` account and `landing` container, with role-definition, principal, and true scope metadata; 21/21 offline CI successful. Self-Runner [PR #222](https://github.com/JohnZhang-DataForge/Self-Runner/pull/222) initially failed [Run #39708881683](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39708881683) before API due to AWK matching both top-level `storage_account_name` and the nested Workspace remote State backend account key. Fixed with Self-Runner [PR #223](https://github.com/JohnZhang-DataForge/Self-Runner/pull/223) / Main `d92f0fac1ded980ab7e68c017fe334a082b2eefa`, scope variable parsing to root-level declarations and add regression unit test.
- [GET-only inspection Run #39709115042](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39709115042) **SUCCESS**: `LANDING_SCOPE_APPLICABLE_ROLE_ASSIGNMENTS` returned four entries for two pre-existing principals `b83443b5-3f20-4b62-97a6-3022a1c25eac` and `ed31f755-7526-4505-978f-0e72f0258e45` (2 of them Blob Data Contributor at `landing` scope); account-scope API returned two inherited principal assignments. **None matches the new Workspace Identity Object ID `1ae64649-a7c3-497e-9fe3-69b37d27c453`.** Workspace GET independently returns `WORKSPACE_IDENTITY_IN_FABRIC_API=PRESENT`, `WORKSPACE_IDENTITY_PRINCIPAL_ID=1ae64649-a7c3-497e-9fe3-69b37d27c453`, unchanged Workspace/Capacity IDs. No cloud write or Terraform backend accessed by this inspection. Remaining limitation: inherited grants by group membership not exhaustively resolved, so verify post-Apply effective access with a real Blob read.
- One planned Reader: [Storage Plan Run #39708299828](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39708299828), `1 add / 0 change / 0 destroy` at `johnzhang/landing`, principal from Terraform remote Workspace State Output. **READY FOR EXPLICIT USER-AUTHORIZED SHARED STORAGE APPLY**, but no Apply has occurred. After approval use Self-Runner `Azure-Infra-Shared-TF` `resource_type=storage`, `operation=apply`, `branch=main`. Confirm `APPLY_EXECUTED=YES` and repeat `plan` returning No changes; re-inspect role and perform Blob read, then separately activate Connection and Notebook/Pipeline runtime E2E. Task 2.2/2.3/4.2 remain unchecked.

## 2026-10-21 — Reader Apply blocked by Azure authorization; Connection candidate staged, not applied

- User authorized Storage Reader Apply + follow-on Connection. Existing workflow could not be dispatched through this GitHub connector, so a one-use SHA/scope/principal/role guarded push request was reviewed through Self-Runner [PR #225](https://github.com/JohnZhang-DataForge/Self-Runner/pull/225) (offline CI pass). Live [Run #39710092180](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39710092180): reviewed Healthcare SHA `4379bfba19fc64ef0f069464ad6be560d0308073`, Plan `1 add/0 change/0 destroy`, `APPROVED_SINGLE_LANDING_READER_PLAN=PASS`. Azure `azurerm_role_assignment.landing["healthcare_omop"]` CREATE failed HTTP **403 AuthorizationFailed**: Runner app `856e4185-315e-49b8-88a4-8fd058c94484` / Object ID `ed31f755-7526-4505-978f-0e72f0258e45` lacks `Microsoft.Authorization/roleAssignments/write` on `.../storageAccounts/johnzhang/blobServices/default/containers/landing`. No Reader grant in State or Azure from this run, no Connection created. Do not mark tasks complete.
- The temporary push Apply entry/request was revoked via Self-Runner [PR #226](https://github.com/JohnZhang-DataForge/Self-Runner/pull/226), restoring original manual-Apply/push-Plan-only gate. Do not try to bypass Azure RBAC with code. An Azure IAM Owner/RBAC Admin must grant the Runner scoped RBAC assignment capability (prefer container-only Role Based Access Control Administrator with ABAC condition restricting assignable role to Storage Blob Data Reader). After privileges propagated, repeat guarded Plan→Apply→RBAC GET→No Change Plan.
- Separately prepare a **no-secret** WorkspaceIdentity AzureBlobs Connection candidate `healthcare-omop-landing-blob` on account `johnzhang`, domain `blob.core.windows.net`, `allow_user_code=true`. The Fabric Connector supports WorkspaceIdentity, but its **test connection is not supported**: Terraform module uses `skip_test_connection=true` for WorkspaceIdentity; actual Notebook/Pipeline read must prove access. Keep this in PR/CI only until Reader grant accepted, then controlled Connection Plan/Apply. No Storage, Capacity, Workspace, OneLake, or Item resources managed by this Root.

## 2026-10-21 — Connection Provider real Plan compatibility

- [Healthcare PR #398](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/398) merged Main `7482be8c34ba62e39f21b5ba0ebd249134edf81c` after 21/21 static CI, staging `healthcare-omop-landing-blob` with WorkspaceIdentity, no secret, user-controlled code allowed. Self-Runner [PR #227](https://github.com/JohnZhang-DataForge/Self-Runner/pull/227) adds push **Connection Plan-only**, retaining the Connection Apply hard gate.
- Live [Connection Plan Run #39710912279](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39710912279) reached Fabric Provider `microsoft/fabric v1.13.0` but failed in Plan with `Unsupported skip test connection: The skip test connection value is not supported`, because WorkspaceIdentity + `skip_test_connection=true` was rejected. No Fabric Connection created, no data read or RBAC change. Change module to `skip_test_connection=false` for 1.13.0 compatibility and repeat Plan; do not equate this setting with a supported WorkspaceIdentity status check. Wait for actual Azure Storage Reader grant before Connection Apply.


## 2026-10-21 — Connection Plan PASS; live Reader permission remains blocked

- Correction PR [Healthcare #400](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/400) 21/21 CI PASS merged Main `ae257cdb72c287801c590303fb37c5ec37e92af4`; `fabric_connection.credential_details.skip_test_connection=false` is required for provider 1.13.0 WorkspaceIdentity, while direct Fabric connection-status validation for WorkspaceIdentity is not supported.
- [Self-Runner PR #228](https://github.com/JohnZhang-DataForge/Self-Runner/pull/228) merged Main `6815369e8d6b5a25df3eec57f0d7ad59f3704c8f`; real [Connection-only Plan Run #39711208455](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39711208455) **SUCCESS**, exact Healthcare SHA `ae257cdb72c287801c590303fb37c5ec37e92af4`, `1 add / 0 change / 0 destroy`, single resource `module.azure_blob_connection[0].fabric_connection.current ACTIONS=create`. Proposed `healthcare-omop-landing-blob` `AzureBlobs`, `account=johnzhang`, `domain=blob.core.windows.net`, `credential_type=WorkspaceIdentity`, `allow_usage_in_user_controlled_code=true`. Log says `APPLY_EXECUTED=NO`, `DESTROY_EXECUTED=NO`. **NO Connection exists from this Plan.**
- **Critical unresolved prerequisite:** User-authorized Storage Reader [Apply Run #39710092180](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39710092180) failed Azure HTTP 403 at `Microsoft.Authorization/roleAssignments/write`; Self-Runner SP app `856e4185-315e-49b8-88a4-8fd058c94484` / Object ID `ed31f755-7526-4505-978f-0e72f0258e45` has no role-assignment write permission at `johnzhang/landing` container. An Owner/RBAC Administrator must delegate a narrowly constrained `Role Based Access Control Administrator` (container scope, restrict allowed assignment to Storage Blob Data Reader) or manually grant Reader then explicitly import/adopt the preexisting role assignment rather than Terraform creating a duplicate. Do NOT grant Storage Account Contributor as a replacement; it does not provide roleAssignments/write.
- Until real Reader `Apply`, `GET readback`, and zero-drift Plan succeed, do not enable Connection Apply (Self-Runner intentionally blocks it), run Notebook as success, or mark Tasks 2.2/2.3/4.2 complete. Trial F4, Workspace, Lakehouse, Azure Blob data remain unchanged.

## 2026-10-22 — Reader and Connection Apply confirmed; exact Connection GET required
- User authorized proceeding after manually granting Azure IAM `Role Based Access Control Administrator` with condition only `Storage Blob Data Reader` / `healthcare-omop`, container-scoped. [Self-Runner Reader Run #39774912636](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39774912636): `1 added / 0 changed / 0 destroyed`, `APPROVED_SINGLE_LANDING_READER_PLAN=PASS`, role assignment ID `29d6147a-121a-e3b0-773a-cef63273b643`; [read-only Run #39775311388](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39775311388) verifies roleDefinition GUID `2a2b9908-6ea1-4ae2-8e65-a410df84e7d1` on exactly `landing` for Identity Object ID `1ae64649-a7c3-497e-9fe3-69b37d27c453`. One-time RBAC Apply entry revoked by Self-Runner PR #236.
- [Self-Runner Connection Apply #39775898394](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39775898394) passed `1 added / 0 changed / 0 destroyed` for `module.azure_blob_connection[0].fabric_connection.current`; Fabric Connection ID `92d67d9c-7a9d-4619-bcf3-2b48b5b93788`, AzureBlobs, WorkspaceIdentity, account `johnzhang`. One-time Apply pathway removed by PR #238. Both operations were pinned to Healthcare SHA `db693afebb20bd7c7ff818dea0ed6831d953e1a4`.
- **Validation issue:** The subsequent [GET-only inspection #39776214810](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39776214810) still shows `EXISTING_ACCOUNT_AZURE_BLOBS_CONNECTION_NAMES=[]`, because the existing list inspector only selects connections whose *list item* exposes `connectionDetails.parameters`. This result does NOT refute Terraform's successful Connection creation: add an independent authorized GET `/v1/connections/92d67d9c-7a9d-4619-bcf3-2b48b5b93788` and validate exact ID, AzureBlobs type, account and domain without credentials. **Do not mark runtime E2E PASS until actual Blob read succeeds.**

## 2026-10-22 — Correct Fabric GET Connection response schema

- Direct-ID GET-only [Run #39776890205](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39776890205) reached existing ID and expected name/type, but inspector failed `Fabric Connection account/domain did not match` because it incorrectly sought creation `connectionDetails.parameters` in a GET response. Microsoft's `GET /v1/connections/{id}` and LIST contracts return only `connectionDetails: {type, path}` (https://learn.microsoft.com/en-us/rest/api/fabric/core/connections/get-connection). Update exact-ID validation and inventory discovery to match `path` (with account and domain) rather than expecting `parameters`. No Cloud writes or new Connection. Re-run exact-ID GET to complete Control Plane readback. Data plane read remains unverified.


## 2026-10-22 — Task 2.2 / 2.3 real acceptance (Azure RBAC + Fabric Connection)

- User authorized follow-on after manually delegating container-level constrained RBAC Administrator to `github-terraform`. Self-Runner [PR #235](https://github.com/JohnZhang-DataForge/Self-Runner/pull/235), [Apply Run #39774912636](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39774912636): exact approved `Storage Blob Data Reader` for Workspace Identity Object ID `1ae64649-a7c3-497e-9fe3-69b37d27c453` on existing `OMOP/johnzhang/landing`; `Apply complete! Resources: 1 added, 0 changed, 0 destroyed`, role assignment `29d6147a-121a-e3b0-773a-cef63273b643`. GET-only [Run #39775311388](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39775311388) independently read back container-scoped role, role GUID `2a2b9908-6ea1-4ae2-8e65-a410df84e7d1`. Temporary Apply trigger removed by Self-Runner PR #236. Subsequent [Storage Plan #39777806327](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39777806327) **No changes**.
- Self-Runner [PR #237](https://github.com/JohnZhang-DataForge/Self-Runner/pull/237), [Connection Apply Run #39775898394](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39775898394): Terraform approved exact one AzureBlobs/WorkspaceIdentity Connection `healthcare-omop-landing-blob` with `allow_usage_in_user_controlled_code=true` and account `johnzhang`; `Apply complete! Resources: 1 added, 0 changed, 0 destroyed`; Connection ID `92d67d9c-7a9d-4619-bcf3-2b48b5b93788`. Temporary Apply trigger removed by PR #238. First inspection incorrectly expected CREATE parameters in GET/LIST responses; corrected via Healthcare PRs #409/#410 to official Fabric `connectionDetails.path` schema. Final [GET-only Run #39777494344](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39777494344) **SUCCESS**: exact Connection ID, name, AzureBlobs type, account and path read back, and Fabric Workspace Identity unchanged. Subsequent [Connection Plan #39778085770](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39778085770) **No changes**.
- These cloud operations satisfy Tasks **2.2 and 2.3** (Control Plane). No paid Capacity/Storage creation or Blob contents mutated. **Task 3.3 (Fabric Notebook/Pipeline native Item publish+smoke) and Task 4.2 (actual Blob Reader -> Fabric Notebook -> Lakehouse business E2E) remain unverified/unchecked.** Connection creation and the Provider's `skip_test_connection=false` are not proof of actual Blob read. Fabric Trial F4 remains unchanged.
