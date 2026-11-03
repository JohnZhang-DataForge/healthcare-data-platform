# Proposal

## Why

Fabric G4 已在真实 Lakehouse 验证 FHIR Bronze/Silver Delta Approval，G5 独立负责 Silver → OMOP Candidate；但 Fabric 侧尚无正式独立、可查询、可幂等提交的 OMOP CDM 5.4 Gold。用户已在现有 `healthcare-omop` Workspace 手动建立 Warehouse `dw-omop-5.4`，已提供 SQL TDS Endpoint。本 Change 不再用 Terraform 创建第二个 Warehouse。

## What Changes

- 独立建设 Fabric OMOP Foundation F0–F3，与现有 G5 保持独立 PR、OpenSpec、运行验收。
- F0：使用 Self-Runner 原有 GitHub OIDC，以严格只读的 Fabric REST item readback + Warehouse SQL SELECT 验证身份、Endpoint、数据库与 Capacity；然后才定义、部署 OHDSI 官方 CDM 5.4 全部 SQL Schema 并读回。
- F1：独立 Identity Map、Vocabulary（含正式版本、许可、Concept 合法性）和 Ledger；禁止使用 Local PostgreSQL 的运行时映射。
- F2：Spark 从现有 Silver Delta 转换为 Candidate，Warehouse 内用受控 T-SQL 多表事务写入正式 OMOP，保障 ID/FK/重跑幂等。
- F3：以 G4 Approved 100 Patient/5,918 Encounter 为独立输入，真实 COMMIT、DQ、独立读回、Replay SKIP，与 G5 Pipeline 最终集成。

## Capabilities

### New Capabilities

- `fabric-omop-foundation`: 在 Fabric Warehouse 中独立部署/维护 OMOP CDM 5.4 与安全 Writer。

### Modified Capabilities

- 无。本 Change 不改 G4/G5 Notebook、Pipeline 和 Local DP 的运行时。

## Impact

- Git: Healthcare OpenSpec，未来受控 SQL Schema Project、测试、组件 CODE map；Self-Runner 独立只读 SQL probe Workflow。
- Cloud target: **已有** Workspace `healthcare-omop` / Warehouse `dw-omop-5.4` / SQL Endpoint，**不创建 Warehouse，不触碰现有 Bronze/Silver，不自动启动或暂停 Capacity**。
- All live schema/data writes require reviewed SQL, exact target and separate execution gate; F0 read-only probe has no SQL DDL/DML.

## Rollback

- 当前首批只有 Git 文档和只读 probe，无云端修改，撤销 PR 即回退。
- 未来 Warehouse Schema 迁移要先做 diff/plan、批次级可恢复策略，禁止默默 DROP 或把未经证实的 COMMIT 标为成功。
