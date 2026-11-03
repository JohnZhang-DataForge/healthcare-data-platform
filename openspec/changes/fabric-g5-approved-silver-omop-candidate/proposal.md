# Proposal

## Why

G3/G4 已经在 Fabric 真实验证原始 FHIR Bronze、100 Patient / 5,918 Encounter 的 Silver Approval 与独立物理 Delta 读回、Replay；异常合成请求 P99/E5893/Q26 被隔离且没有 Approval。当前 `pl_fhir_ingest` 仍默认 HALT，Shared Engine 0.1.1 只有 Canonical，尚无被 Fabric 复用的 OMOP Person/Visit Candidate。不能把 Silver Approved、单一 Pipeline SUCCESS 或 Dev Delta Snapshot 误作 Gold COMMITTED / Azure WORM。

## What Changes

- 增加 **G5 Silver Approval → OMOP Candidate** 的显式输入/输出契约：只接受目标批次同 SHA、同 processing、两张真实 Silver Delta 与独立 Approval fence；Quarantine/HOLD/partial/Unknown ACK 绝不放行。
- 在唯一 `healthcare_data_engine` 中提取无 I/O 的版本化 OMOP Person/Visit candidate mapping / identity-plan / FK/DQ，引用原 Local v1/v5.4 合同和 Mapping Profile，避免复制 Local/Fabric business logic。
- Fabric Notebook 负责真实 approved Silver Delta 独立读回及 Candidate 写入/重读；Candidate 没有 Gold publisher/commit 权限，已有 G4 数据不得覆写。
- Pipeline 仍默认 HALT、不设 schedule、不自动 retry；先实现 G5 read-only 编排和参数保护，再通过独立审批验证实际 Pipeline run。
- 独立记录 Git SHA、Wheel hash、Environment Published readback、Fabric Spark Job/Pipeline Run 和物理 Delta Readback；出现 Capacity pre-Spark 与业务 DQ 明确区分。

## Capabilities

### New Capabilities

- `fabric-g5-approved-silver-omop-candidate`：已批准 Silver 的受控、可回放 OMOP Person/Visit Candidate 与 Pipeline E2E 阶段检查。

### Modified Capabilities

- `ingest-fhir-to-fabric`：保留现有 G3/G4 真实验收与安全门；不重新发布已接受的 Bronze/Silver。

## Impact

Scope: `shared-data-engine/`、Fabric 原生 `nb_fhir_ingest` / `pl_fhir_ingest`、离线 CI、两个组件 CODE.md、OpenSpec。Local DP 和 Gold/Warehouse Writer 不变。WORM、Azure Manifest 真篡改与网络 unknown-ACK 是独立待验收任务，不归入 G5 PASS。

## Rollback

合并前可撤销 Feature Branch；发布前任何新 Wheel 必须独立构建 SHA/Publish；已写 Candidate 不删除、不覆盖，先隔离并做独立只读诊断。不得将尚未通过真实执行的 Gate 标为完成。
