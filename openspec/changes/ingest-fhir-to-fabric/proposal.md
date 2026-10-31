# Proposal

## Why

Azure Blob FHIR R4 Producer 已有 Manifest-last 和远端字节验证；但 Fabric 尚无完成验收的 Intake → Canonical → OMOP 入库链。Local DP 的 Canonical/Mapper/DQ/Reconciliation/Writer 经验应保留业务合同和安全语义，而非原样搬运 Airflow/K8s/PG 的物理流程。

2026-10-30 讨论决定采用 **Bronze 原始事实 → Silver 持久 Canonical Patient/Encounter Delta → Gold OMOP CDM 5.4**，来源格式差异由插件化 Source/Entity Adapters 在 Bronze→Silver 消化，Silver 之后复用共享引擎。用户已于 2026-10-31 正式批准设计入库作为开发依据；此 Change 的业务云端实施仍未开始。

## What Changes

- Intake 以精确 Manifest SHA + 对象 byte/hash 验证放行；Bronze 原始数据通过 OneLake Shortcut（优先 POC）或 Copy，附 Delta receipt；不无条件重复复制。
- PySpark FHIR Patient/Encounter adapters → Canonical Silver managed Delta table，含 Source Identity、版本、DQ、quarantine、approved readback；HL7/CSV Adapter 留待独立 Change。
- Silver → shared OMOP Mapper + Concept/Stable ID + Reconciliation → Candidate → Gold Person/Visit；优先研究 Warehouse 内短 T-SQL 多表事务 Publisher，失败回退全 Delta committed visibility 的独立评审，不虚称跨系统 ACID。
- 未来从 Local 纯 DataFrame/Contract 提炼 **唯一 Shared Engine Wheel**，保留 Local runtime；Fabric **Notebook 是实际 PySpark ETL**，Pipeline 负责编排，Environment 发布固定版本共享包；Fabric 原生 Copy/Shortcut/Spark/Delta 负责 I/O，不预建独立 Fabric I/O/runtime Wheel。dbt 暂非 MVP 必需。
- 区分 Source Batch、Processing Version、Publication ID，完整覆盖 replay/冲突/未知 ACK；首先解决旧 Fabric Notebook definition/exitValue HOLD，再逐 Gate 实机证明。

## Capabilities

### New Capabilities
- `ingest-fhir-to-fabric`（拟建，**未部署**）：受控 FHIR Blob → Bronze → approved Silver Canonical Patient/Encounter → 经独立验证的 OMOP Gold Person/Visit。

### Modified Capabilities
- 无运行中的能力；不变更现有 Local、Publisher、HL7 OIE、PG Snapshot 和 Fabric Items。

## Impact and authority

详见 [2026-10-30 架构决策](../../../documents/architecture/design/FABRIC-MEDALLION-CANONICAL-ADR-20261030.md)、[Local 代码复盘](../../../documents/architecture/design/LOCAL-DP-TO-FABRIC-CODE-ARCHITECTURE-DRAFT.md)。本次只修改 Git 设计文档，可在 GitHub CI/保护条件满足时合并 main 作为开发依据；不运行 Spark/Fabric/Blob/PG/K8s、不创建表和 paid capacity。


2026-10-31 权威最终执行决策：[Fabric Native Notebook/Pipeline/Environment ADR](../../../documents/architecture/design/FABRIC-NATIVE-NOTEBOOK-PIPELINE-ENVIRONMENT-ADR-20261031.md)。
