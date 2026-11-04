# Proposal

## Why

已有真实 G4 Approved Silver（100 Patient / 5,918 Encounter / Q0）和 F0/F1 Warehouse、Vocabulary、F2 Preview。G5 Source Readonly 真实 Spark 验收已完成，但 P1 映射审计、正式 Candidate、Gold 原子写入和 E2E 仍是不同的未完成门禁。之前由两个 Agent 分别推进，缺少统一的可追踪验收。

## What Changes

- 建立单一 FHIR R4 → Bronze → Silver → Candidate → OMOP Warehouse Gold → DQ/Replay → Pipeline E2E 的端到端验收链，关联而不复制现有 G4/G5/F0–F3 OpenSpec。
- 新增纯 Python 的 P1 Concept Mapping Profile 只读预检：实际来源代码频数、正式 Vocabulary release 与 SHA、标准 Concept Domain、有效日期和禁止截断的字段全部绑定；未经临床审查不得宣布正式批准。
- 后续分阶段实现 P2 稳定 ID、P3 Candidate Delta、P4 单写入者事务、P5 Pipeline。
- 保留既有 Workspace-only Warehouse 和真实 G4 数据，默认 HALT，未批准不写入，不自动重试或调度。

## Capabilities

### New Capabilities

- `fabric-fhir-omop-unified-e2e`: 统一对账、授权、不可混淆的 Candidate/Gold/Replay 验收。

## Impact

源代码：`azure-fabric/warehouse/omop-foundation/writer/` 及其离线测试，随后 G5 Shared Engine、Notebook、Self-Runner 和原生 Pipeline。真实运行需独立 PR、CI、审查和明确授权。当前 P1 辅助工具只做离线预检，不发布 Wheel，也不操作真实云端数据。
