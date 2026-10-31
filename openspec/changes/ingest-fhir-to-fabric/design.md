# Design — 2026-10-30 Architecture Decision

**Data architecture + Fabric-native code layout adopted 2026-10-31; runtime NOT authorized.** 执行架构以 [Fabric-native ADR](../../../documents/architecture/design/FABRIC-NATIVE-NOTEBOOK-PIPELINE-ENVIRONMENT-ADR-20261031.md) 为准，数据业务以 [Medallion ADR](../../../documents/architecture/design/FABRIC-MEDALLION-CANONICAL-ADR-20261030.md) 为准。2026-10-27 的两份重复 Draft 已从当前 Git 树清理；需要历史实现细节时按 Medallion ADR 的固定 Git Commit 追溯。

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
4. Local 纯 DataFrame/Contract 算法逐步抽离至唯一 `shared-data-engine` Wheel；Fabric Pipeline 调度实际 PySpark Notebook，Environment 安装发布 Shared Wheel；Shortcut/Copy/Spark/Delta 使用 Fabric 原生能力，**不预建第二个 Fabric I/O/Runtime Wheel**。Local 运行代码不动，真实 Spark/Python 兼容独立验证。
5. Gold 首选研究 **Warehouse staging + Warehouse 内 Person/Visit/IDMap/Ledger 显式 T-SQL 单事务**；跨 Lakehouse→Warehouse 不属于同一事务，Warehouse PK/FK/UNIQUE NOT ENFORCED 需应用层检验。纯 Delta 多表 visibility 作为未定的备选；不能把 Delta 单表 ACID 冒充跨表原子。Gold COMMITTED 依独立数据读回。
6. MVP 必须使用 **Fabric Pipeline + 真正运行 PySpark ETL/DQ/Delta/readback 的 Notebook + Fabric Environment + 唯一 Shared Wheel**；dbt 暂不引入；Lakehouse SQL Endpoint 只读，不可用其 T-SQL 写 Silver Delta。
7. Source Batch (hospital/feed/request + manifest SHA)、Processing Version (adapter/contract/mapping/code SHA)、Publication ID (committed target version) 分离；已提交同版本重跑 SKIP、同 request 新 SHA 冲突 HOLD、未知 ACK 先只读核验。

## Final Fabric-native execution decision (2026-10-31)

[Authoritative Native Notebook/Pipeline/Environment ADR](../../../documents/architecture/design/FABRIC-NATIVE-NOTEBOOK-PIPELINE-ENVIRONMENT-ADR-20261031.md) replaces earlier separate Fabric ingestion wheel and I/O framework proposals. Notebook is real Spark ETL; Pipeline orchestrates; Environment publishes exactly one Shared Engine wheel. Cloud mutation is not authorized.

## Concrete repository and Fabric delivery file plan

Practical file-by-file source layout, actual Local files to extract, verified existing Terraform/Trial-native Item paths, target Lakehouse schemas and P0–P5 development slices: [FABRIC-FHIR-PRACTICAL-SOURCE-LAYOUT](../../../documents/architecture/design/FABRIC-FHIR-PRACTICAL-SOURCE-LAYOUT.md). This is an actionable planning artifact, **not a list of files already created**. The currently running Local DP and current Terraform State remain untouched. Before new source: reconcile updated Main, verify Live Lakehouse GUID/schema and extend CODE-map/forbidden-import static tests.

## Source-directory governance confirmed 2026-10-30

[Authoritative shared package and Agent ownership policy](../../../documents/engineering/development/SHARED-DATA-ENGINE-STRUCTURE-AND-OWNERSHIP.md) fixes one `healthcare_data_engine` package for pure DataFrame Contract/Source Adapter/Canonical/OMOP Mapping/DQ/Identity Plan/Reconciliation; platform I/O/transactions remain in Local or Fabric adapters. The `shared-data-engine/AGENTS.md` scoped instructions and root `AGENTS.md` enforce the read-before-change process for future agents; old Local `spark/contracts/` is still authoritative. Standard `src/` is allowed only for independent installable packages, not for duplicated Local source trees. Existing Local runtime files and currently deployed behavior are unchanged.

**Future code gate**: before the first new Python module, extend CODE-map CI for `shared-data-engine` + Fabric Native Notebook/Pipeline/Environment + Warehouse owner paths, with negative tests for forbidden shared→platform imports and missing CODE.md ownership; do not mark this automated gate complete based on documentation.

## Still open / implementation gates

- Shortcut/Copy 实机 RBAC、Blob 保留及 byte hash；Fabric 旧 Notebook GetDefinition/exitValue 三轮失败仍 HOLD，未经授权不再重跑。
- Gold Warehouse T-SQL Writer 在 Trial/费用/并发下的可靠性 POC；如不适用，重新审查全 Delta visibility。
- Canonical v2、Update/reprocessing policy、ID source namespace/crosswalk，及部署/成本/血缘验收都需独立版本化审查。
- 本次无云资源、数据、代码构建、Pipeline、Fabric Item 和 paid capacity 变更；未来实施门槛见 [tasks](tasks.md)。


## 2026-10-31 Authorized Native bootstrap (narrow permission update)

用户本轮授权创建 healthcare-omop 所需原生 Item；此前无云写许可声明仅对原历史阶段有效。本轮范围仅为三种 Native Item 的受控创建与真实定义导出。

Single writer = trusted Self-Runner/main GitHub OIDC Fabric REST; existing Terraform continues to own Workspace/Lakehouse/Connection and MUST NOT also create the same Items.
Trust boundary = untrusted PR runs GitHub-hosted mocked tests without id-token; only merged Main fixed-name bootstrap uses OIDC. No arbitrary URL/method/workspace/body.
Create-if-absent names: nb_fhir_ingest (Notebook), pl_fhir_ingest (DataPipeline), env_healthcare (Environment). GET inventory before every POST; refuse name/type ambiguity; nonidempotent POST never auto-retried; if acknowledgement unclear, mark HOLD and GET inventory.
LRO: handle HTTP 201/202 and bounded GET /v1/operations/<id>, followed by workspace list + Get Item independent readback. Fabric getDefinition is a POST with read-only semantics; export only real returned bytes to artifact; never guess .platform/logicalId.
Safety: no paid Capacity operation, Spark execution, Environment Publish, OneLake/Blob write or Terraform state mutation in bootstrap. No automatic delete/rollback after partial create: preserve resource IDs and disclose HOLD.
After readback: separately review exported .platform/Git integration and CODE maps, publish immutable Shared Wheel, bind Notebook and Pipeline, and only then consider explicitly gated small synthetic runtime validation.

## Live evidence qualification: Git connection not yet configured

Actual Fabric resource creation and definition export both succeeded in Self-Runner Runs 41242815706 and 41243074326. Follow-up GET `/workspaces/{id}/git/connection` in Run 41243367360 returned `NotConnected`. The REST-exported `.platform` files contain all-zero logicalId; treat as unbound initial Fabric API response, not Git-authoritative source definitions. Native source registration in Healthcare Git and Environment Publish are still pending; no business Spark run/data writes occurred.
