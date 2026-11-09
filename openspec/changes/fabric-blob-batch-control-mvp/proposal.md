# Proposal — Fabric Blob Batch Control MVP

## Why

LocalDP 已采用 S3 保存不可变 Landing Manifest/Payload，PostgreSQL 保存 Batch Claim/Lease/处理状态；Fabric 当前已有单一 Shared Engine 的 read-only Replay 决策和真实 G4 Silver 数据，但尚无不依赖运行 Fabric Capacity 的正式 Batch 控制状态。用户明确决定：**优先业务 E2E、减少权限/IaC 复杂性**，不为微小状态引入专用 `g5-trust-ledger` Container、第二 Credential 或为每次检查启动 Fabric Delta/SQL。

## What Changes

- **MVP 决策**：仅复用当前 Azure Storage Account `johnzhang`、现有 `landing` Container；不另建 Container。保留 `clinical/v1/<hospital>/<feed>/<request>/...`、已有 FHIR/HL7 原始数据/Manifest/ETag/SHA/不可变交付合同。绝不移动、重命名、复制或删除原始文件。
- 在 **同一个 Container** 内规划虚拟前缀 `_control/v1/`（可变的 Batch Claim/Lease/状态）和 `processed/v1/`（每阶段完成、与真实发布证据绑定的不可变轻量回执，**不是把原始文件搬进去**）。只需少量 JSON/ETag/Lease、Blob REST/SDK 请求，不唤醒 Fabric Capacity 仅为了查状态。
- **单 Credential MVP**：一个已经存在且经核实可读写 `landing` 的 Azure 身份/凭据执行这两个前缀的操作。暂不引入第二身份、细粒度前缀隔离、新 IAM 角色、WORM、Key Vault 密钥或新收费资源。不得从“已有 WorkspaceIdentity Blob Reader 连接”推断其能写；优先核对现有 Publisher/SP 是否可复用。秘密不上传到 Git/日志；保留应用层路径 allowlist、禁止改写原始数据。
- LocalDP 的 PostgreSQL Ledger 继续不动；Shared Engine 保持一套纯 Batch Identity/Replay 决策，Fabric 只是新增 Blob 控制状态存储适配器，不开发第二个业务 Mapper。
- 先落实有限状态、SHA/ETag/原子 Claim、Crash/Unknown ACK、阶段完成回执与不越权的回放逻辑，再真实测试。**不将 Blob 回执等同于 Fabric Delta/Warehouse 原子 COMMIT**。

## Capabilities

### New Capabilities

- `fabric-blob-batch-control-mvp`：复用 Landing Container 的低成本、最简 Blob Batch/Replay 控制层。

### Modified Capabilities

- `fabric-g5-approved-silver-omop-candidate`：引用外部控制层作为低成本可选执行前置；原候选 `g5-trust-ledger` 仅历史离线实验，不是生产依赖；Candidate/Gold 审批与原有 P3.19 生产签名门禁仍然 OPEN。
- `implement-multi-hospital-azure-blob-publisher`：不改变原始 Publisher 的路径、不可变写入或 Manifest-last 合同。

## Impact / Explicit Non-goals

本 PR **只冻结 OpenSpec 设计与交接**；不创建 Blob、Container、目录 Marker、不赋予或改变 RBAC、不修改 Notebook/Pipeline/LocalDP/Shared Wheel，不执行 Azure PUT、不改运行配置。数据平面实现将由下一 Session 在独立 PR/CI 执行。

## Rollback

未来 Adapter 未发布前可以撤回此方案；任何试验前先只读审计既有 prefix 冲突，限定全新合成 Batch，在合成 `_control/v1/` 和 `processed/v1/` 前缀下新增对象，不覆盖/删除生产 Landing 文件。
