# Tasks

> **ACTIVE — 2026-10-21**。接续已完成的 Trial F4 Terraform Workspace/Lakehouse，不重复基础设施部署。新的 `shared-infra/connection` 与 Fabric Item 发布分开测试、分开授权；只有证据到位才能打勾。

## 1. Source audit and scope

- [x] 1.1 核对 Healthcare Main `e49404ff7fde473d877c13fb37c8ce7ad33e2d4f`、Self-Runner Main `865a8f0eb7fbdcabceb190ac17f3915790ba0e2c`，OpenSpec 当前权属和 Run #39635155333 Attempt 2 的真实 Trial F4 验收。
- [x] 1.2 冻结 Connection/Terraform 与 Notebook/Pipeline/`fabric-cicd` 的独占 Owner、外部 Blob Reader RBAC 和不创建付费 Capacity 的边界。

## 2. Connection — first component

- [x] 2.1 复用 `modules/connection` 添加 `shared-infra/connection` Root、独立 State、默认禁用/无秘密示例、静态合同和 `init -backend=false`、`validate` CI；合并 Main 并记录准确 PR/Run。
- [ ] 2.2 核实 Fabric 当前 Tenant `AzureBlobs` Connector、认证模式、Reader RBAC、已有 Connection Inventory/Key Vault Secret Reference；记录负向门禁。
- [ ] 2.3 在明确的 Live 授权下仅对 Connection Root 执行受控 Plan/Apply/ID readback/重复 Plan；不得触碰 Workspace/OneLake/Capacity Roots。

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
