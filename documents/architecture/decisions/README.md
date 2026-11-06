---
status: active
scope: architecture-decision-index
last_verified: 2026-11-05
source_sha: e384777a093a402449eac8dadadd46772bdcf92e
---

# Architecture Decisions — 长期架构决策索引

> 这里记录**已经批准**的长期决定及取代关系，不维护第二套 CURRENT/NEXT。Fabric 临床语义的正式依据是 [Medallion Canonical ADR (2026-10-30)](../design/FABRIC-MEDALLION-CANONICAL-ADR-20261030.md)，执行/唯一 Wheel 的正式依据是 [Fabric-native ADR (2026-10-31)](../design/FABRIC-NATIVE-NOTEBOOK-PIPELINE-ENVIRONMENT-ADR-20261031.md)；[系统总览](../SYSTEM-OVERVIEW.md) 是人类导航而非替代 ADR。旧 2026-10-16 快照请使用[固定提交](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/e384777a093a402449eac8dadadd46772bdcf92e/documents/architecture/decisions/README.md)，其早期云端假设不再标记为当前。

| ID | 已批准的架构决定 | 实现 / 验收边界 |
| --- | --- | --- |
| **D-01** | Synthea Producer 独立，Airflow 消费指定 READY/immutable S3 Batch | NEW_ONLY Person/Visit 本地 PG17 [真实验收](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md)；UPDATE_ONLY/MIX_DATA 未全面实现 |
| **D-02** | 本地 PG17 CDM 的真实写入由独立 Writer/Claim/Fencing/Ledger 事务管理 | 已验证 Local Person/Visit COMMIT 与 Replay SKIP；Local 的数据权威不代表 Fabric 独立 FHIR Gold 自动同步。见 [OMOP Writer](../../systems/data-platform/omop/README.md) |
| **D-03** | Portal 采用 OpenLineage + Marquez 官方 Web + 独立 PG14 | A3/A4 分项证据存在，完整业务 Local/Fabric Dataset/Job 关联未获验收。[Portal](../../systems/platform-portal/README.md) |
| **D-04** | **2026-10-30 当前 Fabric 新主线**：Synthetic FHIR R4 source → Bronze verified facts → Approved Canonical Silver Delta → shared OMOP Candidate → controlled Warehouse Gold | G4 Silver 100/5,918 已验证；Warehouse Schema/Vocabulary 已建立，但正式 Concept Profile、Candidate/Gold COMMIT/Pipeline E2E 未验收。见 [Medallion ADR](../design/FABRIC-MEDALLION-CANONICAL-ADR-20261030.md) 和 [E2E Tasks](../../../openspec/changes/fabric-fhir-omop-unified-e2e/tasks.md) |
| **D-05** | 新代码按组件+业务功能命名，历史 Task/Step 源码保留实际依赖 | 禁止新 `taskNNN` 业务根；原 Local Task 路径不得在没有消费者证据时批量迁移。[Code Organization](../../engineering/development/CODE-ORGANIZATION-AND-NAMING.md) |
| **D-06** | OpenSpec 管 Change/Tasks，GitHub PR 与受控 Self-Runner 实证分离 | 设计合并、离线 CI 和实际云端 DML 均是不同门禁。[Lifecycle](../../engineering/development/OPENSPEC-DEVELOPMENT-LIFECYCLE.md) |
| **D-07** | 本地 Runtime 源码归 `local-data-platform/`，Fabric Runtime 源码归 `azure-fabric/`；历史调用路径保持兼容 | 源码根目录已经存在，Local 旧 Task 路径仍未完成全量安全重构；勿沿用旧“只是拟议命名、代码未移动”状态。[Local 目录与 Owner](../../systems/data-platform/README.md) |
| **D-08** | **2026-10-30/31 批准的核心复用架构**：CSV/FHIR/HL7 Source/Entity Adapter 各自负责格式，Canonical Patient/Encounter 合同唯一；**Silver 后共用**业务 Mapper、Concept Profile、DQ、Identity Plan 与 Reconciliation；Local 和 Fabric 分别拥有物理 Writer | 只有一个 `healthcare_data_engine` Wheel，不建立第二套 Fabric Mapper/I/O Wheel。Shared 0.1.3 已包含 FHIR/Canonical/OMOP Candidate，但 Local 既有生产代码还没有全量迁移到同一包；HL7 shared adapter 为未来独立工作。见 [Shared Ownership](../../engineering/development/SHARED-DATA-ENGINE-STRUCTURE-AND-OWNERSHIP.md) |
| **D-09** | **旧 PG→Blob→OneLake 路线保留为独立的分析快照数据产品**，**不再**是 Fabric 唯一 MVP 或 FHIR/Canonical 链路的前置 | Read-only PG Exporter 与 Fabric snapshot E2E 尚未实现；已标准化的 PG OMOP 快照无须反向转换为 Canonical。旧 2026-10-16 Snapshot-first 描述只供历史追溯。[Data Flow](../DATA-FLOW.md) |

任何新 ADR/Change 均不得在本索引里将未执行的 Local Shared 迁移、FHIR Gold SQL COMMIT、Snapshot Exporter 或业务级 Lineage 声称为已完成；只通过准确 PR/Run、代码和持久读回更新状态。
