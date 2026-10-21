# Tasks

> **ACTIVE — 2026-10-21**。接续已完成的 Trial F4 Terraform Workspace/Lakehouse，不重复基础设施部署。新的 `shared-infra/connection` 与 Fabric Item 发布分开测试、分开授权；只有证据到位才能打勾。

## 1. Source audit and scope

- [x] 1.1 核对 Healthcare Main `e49404ff7fde473d877c13fb37c8ce7ad33e2d4f`、Self-Runner Main `865a8f0eb7fbdcabceb190ac17f3915790ba0e2c`，OpenSpec 当前权属和 Run #39635155333 Attempt 2 的真实 Trial F4 验收。
- [x] 1.2 冻结 Connection/Terraform 与 Notebook/Pipeline/`fabric-cicd` 的独占 Owner、外部 Blob Reader RBAC 和不创建付费 Capacity 的边界。

## 2. Connection — first component

- [ ] 2.1 复用 `modules/connection` 添加 `shared-infra/connection` Root、独立 State、默认禁用/无秘密示例、静态合同和 `init -backend=false`、`validate` CI；合并 Main 并记录准确 PR/Run。
- [ ] 2.2 核实 Fabric 当前 Tenant `AzureBlobs` Connector、认证模式、Reader RBAC、已有 Connection Inventory/Key Vault Secret Reference；记录负向门禁。
- [ ] 2.3 在明确的 Live 授权下仅对 Connection Root 执行受控 Plan/Apply/ID readback/重复 Plan；不得触碰 Workspace/OneLake/Capacity Roots。

## 3. Fabric native Item publishing

- [ ] 3.1 添加 `johnzhang-test` 的真实 Fabric Git Native Notebook/Pipeline 源码与 logicalId，更新对应 CODE.md；先只做无数据写入的 Smoke。
- [ ] 3.2 实现 `fabric-cicd` 受控入口和 Self-Runner 精确 SHA/Outputs/Item 白名单/OIDC、禁用 orphan 删除；测试负向/重复发布合同。
- [ ] 3.3 Live 发布+读回 Notebook/Pipeline（而非 Terraform）、执行无数据写入的 Pipeline→Notebook Smoke；记录 Run/实际 GUID/重复部署证据。

## 4. Business ETL follow-up

- [ ] 4.1 独立 OpenSpec 接管 PG OMOP snapshot Exporter/Manifest READY、Fabric Notebook Delta person/visit_occurrence 和 Pipeline 编排/参数合同。
- [ ] 4.2 真实 Blob Reader→Notebook→Lakehouse E2E；PK/FK/count/DQ/Manifest Hash/重复 export 对账、失败重试；仅在真实证据后声明通过。
- [ ] 4.3 更新 `organize-fabric-terraform-by-workspace` Tasks 3.4/4.4、长期架构和 `PROJECT-STATUS.md` 的实际完成范围；不要把旧 NO APPLY 当新事实。
