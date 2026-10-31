# Design — 2026-10-30 Architecture Decision

**Data architecture confirmed; Draft PR, runtime NOT authorized.** 权威详细决策：[ADR — Bronze → Canonical Silver → OMOP Gold](../../../documents/architecture/design/FABRIC-MEDALLION-CANONICAL-ADR-20261030.md)。保留 [2026-10-27 Fabric 初稿](../../../documents/architecture/design/FABRIC-FHIR-BLOB-INGESTION-DRAFT.md) 与 [Local 源码复盘](../../../documents/architecture/design/LOCAL-DP-TO-FABRIC-CODE-ARCHITECTURE-DRAFT.md) 作为依据；若冲突，ADR 优先。

## Adopted design

```text
Blob Manifest + Byte SHA → Intake
→ Bronze (Shortcut / Copy, raw source + Delta receipt)
→ PySpark FHIR Source/Entity Adapter + Canonical DQ
→ Silver Lakehouse Delta (canonical_patient / canonical_encounter, approved)
→ Shared OMOP Mapper + Concept + Stable Identity + Reconciliation
→ Candidate staging
→ Gold OMOP 5.4 person / visit_occurrence (verified controlled publication)
```

1. Bronze 保留原始事实（或可验证的不可变源引用），不是 Local 已核准 Canonical Raw；Shortcut 不等于来源对象不可变，保留/权限须 POC。
2. Silver 必须持久化二维 Canonical Delta table，附 Source/Contract/Processing 版本、质量报告和 approved 证据。FHIR Patient/Encounter 由独立 Adapter 转换；HL7/CSV Adapter 后续独立 Change。现实 FHIR Optional 与 Local v1 nonnull 冲突时 quarantine 或另审 Canonical v2，禁止造值。
3. Silver 之后复用源无关 OMOP Person/Visit Candidate Mapper、Concept、ID、DQ/PK/FK 和 Reconciliation；按版本化 Profile 处理编码差异。不同来源不按姓名生日自动合并 Patient。
4. 将 Local 纯 DataFrame/Contract 引擎逐步抽离到未来 `shared-data-engine`，Fabric 特有 I/O 和 Writer 留在 `azure-fabric`；目前 Local 生产链不改，Spark 3.5.7 / Fabric Runtime 2.0 需独立兼容验收。
5. Gold 首选研究 **Warehouse staging + Warehouse 内 Person/Visit/IDMap/Ledger 显式 T-SQL 单事务**；跨 Lakehouse→Warehouse 不属于同一事务，Warehouse PK/FK/UNIQUE NOT ENFORCED 需应用层检验。纯 Delta 多表 visibility 作为未定的备选；不能把 Delta 单表 ACID 冒充跨表原子。Gold COMMITTED 依独立数据读回。
6. MVP 一个 Fabric Pipeline + 薄 Notebook + 可测试 PySpark 包；dbt 暂不引入；Lakehouse SQL Endpoint 只读，不可用其 T-SQL 写 Silver Delta。
7. Source Batch (hospital/feed/request + manifest SHA)、Processing Version (adapter/contract/mapping/code SHA)、Publication ID (committed target version) 分离；已提交同版本重跑 SKIP、同 request 新 SHA 冲突 HOLD、未知 ACK 先只读核验。

## Source-directory governance confirmed 2026-10-30

[Authoritative shared package and Agent ownership policy](../../../documents/engineering/development/SHARED-DATA-ENGINE-STRUCTURE-AND-OWNERSHIP.md) fixes one `healthcare_data_engine` package for pure DataFrame Contract/Source Adapter/Canonical/OMOP Mapping/DQ/Identity Plan/Reconciliation; platform I/O/transactions remain in Local or Fabric adapters. The `shared-data-engine/AGENTS.md` scoped instructions and root `AGENTS.md` enforce the read-before-change process for future agents; old Local `spark/contracts/` is still authoritative. Standard `src/` is allowed only for independent installable packages, not for duplicated Local source trees. Existing Local runtime files and currently deployed behavior are unchanged.

**Future code gate**: before the first new Python module, extend CODE-map CI for `shared-data-engine` + `azure-fabric/ingestion` + Warehouse owner paths, with negative tests for forbidden shared→platform imports and missing CODE.md ownership; do not mark this automated gate complete based on documentation.

## Still open / implementation gates

- Shortcut/Copy 实机 RBAC、Blob 保留及 byte hash；Fabric 旧 Notebook GetDefinition/exitValue 三轮失败仍 HOLD，未经授权不再重跑。
- Gold Warehouse T-SQL Writer 在 Trial/费用/并发下的可靠性 POC；如不适用，重新审查全 Delta visibility。
- Canonical v2、Update/reprocessing policy、ID source namespace/crosswalk，及部署/成本/血缘验收都需独立版本化审查。
- 本次无云资源、数据、代码构建、Pipeline、Fabric Item 和 paid capacity 变更；未来实施门槛见 [tasks](tasks.md)。
