---
status: active
scope: data-flow-architecture
last_verified: 2026-11-05
source_sha: e384777a093a402449eac8dadadd46772bdcf92e
---

# Healthcare 数据流 — 多来源 Canonical、Shared Engine、双平台发布

> **业务数据流入口**。与 [总体架构](SYSTEM-OVERVIEW.md) 配套，规范来源差异与 Canonical 之后的共享阶段。业务语义以 [Medallion ADR](design/FABRIC-MEDALLION-CANONICAL-ADR-20261030.md) 为准，物理执行以 [Fabric Native ADR](design/FABRIC-NATIVE-NOTEBOOK-PIPELINE-ENVIRONMENT-ADR-20261031.md) 为准；本页只区分数据流、已有实证和待验收环节。2026-10-16 只读旧总览中 PG→Azure 复制是**独立未来支线**，不再是唯一或当前 Fabric 业务主线。

## A. 数据来源与统一 Canonical 合同

| 来源与运行状态 | Source/Entity Adapter | Canonical 产物 | 非共享的部分 |
| --- | --- | --- | --- |
| 本地 Synthea CSV（NEW_ONLY Person/Visit 已验收） | Local CSV Patient/Encounter Adapter；未来逐模块提炼到 Shared | `patient-v1.json`、`encounter-v1.json` 对应的 Patient/Encounter | S3、Airflow、Local Spark 作业、PG JDBC/Writer |
| Azure FHIR R4（合成 G4 Silver 已验收） | Shared `adapters/fhir_r4/{patient,encounter}.py` | **相同 Local Canonical v1 字段语义/冻结 Contract SHA**；Fabric Approved Silver Delta | Blob source verification、Notebook、Delta Publisher |
| HL7 v2 / OIE producer（共享 HL7 Adapter 未验收） | 预期 HL7 PID/PV1 Adapter；必须独立开发测试 | 相同 Canonical Contract 或经过批准的新版本 | OIE 与 HL7 特定语义、Producer / ACK |

完整处理原则：

```text
CSV ── CSV Adapter ──┐
FHIR ─ FHIR Adapter ─┼── Canonical Patient + Encounter Contract
HL7 ── HL7 Adapter ──┘                │
                                     ▼
              ONE platform-neutral Shared Data Engine
                  Candidate Mapper / Concept Mapping Profile
                  Quality / Identity Planning / Reconciliation
                                     │
                         ┌───────────┴────────────┐
                         ▼                        ▼
                   Local PG writer          Fabric Warehouse writer
```

**注意**：这张图表达已批准的**最终共享设计**，不表示当前 Local 旧 Writer/Mapper 已经整体改为 import Shared Wheel。Local 的历史 Person/Visit 转换和 PG Writer 仍在运行；Fabric 的 Shared 0.1.3 FHIR/Canonical/OMOP Candidate 已实现并在其证据范围内测试。共享纯函数必须逐组件抽取、对比行为后才替换本地既有代码。Source-specific Code Mapping 用经审核的版本化 Profile 传入相同 Mapper，不能直接把 FHIR LOINC 词汇同名匹配当作正确 Person Race/Ethnicity/Visit Concept。

## B. 本地 NEW_ONLY CSV → PostgreSQL OMOP（历史实机已验收）

```text
Synthea 3.3.0 → 18 CSV + immutable S3 manifest/SHA
  → SeaweedFS health-landing → Airflow new_only_omop_consumer (manual)
  → Local Spark Patient/Encounter Canonical + Person/Visit mapping + DQ
  → controlled PG Writer: Claim/Fencing/Identity Maps/Stage/Checkpoint/Ledger
  → cdm.person + cdm.visit_occurrence one atomic COMMIT
  → independent PG readback / completed-batch replay SKIP
```

- 本地 Generator 与 Airflow 消费者独立；Discovery 每 15 分钟不等于自动业务写入。NEW_ONLY DAG `schedule=None`，必须显式选择 Batch 并符合独立 Writer 授权。
- 历史 TASK004 真实批次的 Person/Visit COMMIT 与 SKIP 有 [最终验收](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md)，不是此刻 PG 行数的在线统计。
- UPDATE_ONLY、MIX_DATA、Condition/Drug/Procedure/Observation 域、Local 生产全面 Shared 化不应从此结果推导为已完成。见 [Local 文档入口](../systems/data-platform/README.md)、[Local OMOP Writer](../systems/data-platform/omop/README.md)。

## C. Fabric FHIR R4 → Bronze → Approved Canonical Silver → OMOP Gold（当前开发）

```text
Verified synthetic FHIR Patient/Encounter Azure Blob + signed-off Manifest SHA
   ↓  native Fabric Pipeline orchestrates, Notebook physically reads + executes Spark
Bronze: source raw snapshot/receipt
   ↓  Shared FHIR Adapter, Canonical v1 validation, source-reference FK + DQ
Silver: persisted canonical_patient, canonical_encounter, quarantine, Approval
   ↓  only approved Silver, pinned source/processing/mapping versions
Shared OMOP Person/Visit Candidate Mapper + approved Concept Profile
   ↓  stable ID preview + independently verified prior Map/Gold/Allocator/Ledger
Candidate Delta physical write/readback/approval (NOT YET ACCEPTED)
   ↓  one fenced Warehouse writer, re-read state inside TX
Warehouse cdm.person + cdm.visit_occurrence + etl.identity_map/id_allocator/batch_ledger
   ↓  independent SQL readback, reconciliation, unknown-ACK read-before-retry
GOLD COMMITTED (NOT YET ACCEPTED)
```

| 确切里程碑 | 已核对的证据范围 | 待办 / 不得宣称 |
| --- | --- | --- |
| Engine 0.1.3 | Environment Published、独立 Spark 4.1 Import PASS | 正式 Gold 运行未验收 |
| G3 / G4 | 真实合成 FHIR Bronze；100 Patient + 5,918 Encounter 的 Delta Silver Approved/Q0、独立读回与 Replay SKIP | 没有 Candidate Gold 的业务 COMMIT |
| F0/F1 | 39 空 CDM 表、9 Vocabulary 表、5 空 ETL/Audit 管理表；Vocabulary 28,703,753 行及分项 DQ | Release/License/Domain 审核不完整 |
| P1/G5 | 已从真实 Silver 读取来源代码、执行 F1 vocabulary lexical SELECT；无法把词汇名称匹配直接当医学映射 | 正式 Mapping Profile SHA/审批、真实 Candidate Delta |
| F2 | `identity_plan` / `silver_identity` ID Preview、合成 Warehouse ROLLBACK 验收 | Identity Map/Gold/COMMITTED Ledger 的真实事务与 Pipeline E2E |

**映射和 ID 安全边界**：Silver 只包含 Canonical Source ID，不存正式 Person/Visit OMOP INT ID；Mapping Profile 需按源代码、有效日期、Domain、Standard、License 审核；新 ID Preview 不是持久化预约。Candidate 与 Warehouse Writer 的先后接口仍由 [Active E2E Tasks](../../openspec/changes/fabric-fhir-omop-unified-e2e/tasks.md) 决议，禁止预先将临时 ID 写入目标表。Warehouse 的 NOT ENFORCED 约束要求独立 PK/FK/跨医院唯一性校验。所有实际 DML、Capacity 和执行仍受 [Safe Operations](../engineering/operations/SAFE-OPERATIONS.md) 限制。

## D. Local PG OMOP → Fabric 分析副本（独立未来路线）

```text
Local PG17 committed and conformed OMOP CDM
   → read-only, cross-table-consistent Exporter (NOT IMPLEMENTED)
   → versioned Azure Blob snapshot + manifest (NOT E2E VERIFIED)
   → Fabric Notebook/Pipeline analytic-load adapter (NOT E2E VERIFIED)
   → OneLake analytical copy (FUTURE PRODUCT)
```

**与 C 不同**：这里的输入是已有 OMOP Gold，不需回退为 Source CSV/FHIR 或重做 Canonical/OMOP Conversion。Local PG 是本地提交数据的权威，不表示已自动同步 Fabric 当前的独立临床 Gold。旧 2026-10-15 Terraform 三项 Plan-only 及 `nb_omop_snapshot_load` 提案属于历史快照产品设计，不能代替 2026-11-05 实存 FHIR Notebook/Pipeline/Lakehouse/Warehouse 的状态。保留 [旧数据流固定 Git 版本](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/8d276dc7a121c15396a9ce328fcfea4688a795ae/documents/architecture/DATA-FLOW.md) 供历史追溯。

## E. OpenLineage / Marquez（数据血缘元数据，非业务提交）

```text
Local Airflow / standalone Spark OpenLineage  → Marquez API → PG14 metadata → native Web
Fabric Notebook/Runner future publisher      ────────────────────────┘
```

A3 Airflow Provider 与 A4 Spark Listener 已有分项真实 Smoke，不能因此宣称整条业务 Job/Run/Dataset I/O 映射成功。Fabric 到 Marquez 的业务级集成、Gold 数据集对应和端到端血缘仍需独立验证。入口：[Portal](../systems/platform-portal/README.md)；开发归属、成本与调度不得混同 Fabric Gold 业务验收。

## F. 验收状态的命名

- **CANONICAL_VALIDATED**：仅指合同/结构检查；不等于 Delta 数据已经成功落地。
- **SILVER_APPROVED**：已持久化并独立读回两实体数据、DQ/PK/FK 和 Approval 记录。
- **OMOP_CANDIDATE_VERIFIED**：数据候选及 ID/Mapping/DQ 审核过，**不是** Warehouse COMMITTED。
- **GOLD_COMMITTED**：唯一受控 Writer 在目标事务中成功提交且经独立 SQL 读回；同版 Replay 不二次写入，未知 ACK 必须先查持久状态。

每一步均使用实际 Source Batch、Processing Version、Publication ID 和精确 SHA；文档和测试的 PASS 不能替代平台物理提交证据。
