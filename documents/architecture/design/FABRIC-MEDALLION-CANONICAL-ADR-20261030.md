---
status: architecture-decided-implementation-pending
decision_date: 2026-10-30
scope: azure-fabric-fhir-bronze-silver-canonical-omop-gold
implementation_status: design-only
source_baseline_sha: 4596c1cec866032e5753597201b595dd1505b2ae
---

# ADR 2026-10-30 — Fabric Bronze → Canonical Silver → OMOP Gold

> **本文为 Bronze/Silver/Gold 业务语义权威。** 2026-10-31 最终 [Fabric Native Notebook/Pipeline/Environment ADR](FABRIC-NATIVE-NOTEBOOK-PIPELINE-ENVIRONMENT-ADR-20261031.md) 是 Notebook/PL/Environment/Wheel/Git 目录权威，之前 Fabric I/O 第二包目录提议不再适用。 2026-10-30 讨论已确定数据分层、Source Adapter 解耦与 Canonical 后共享转换，但 **没有**授权实机部署、paid capacity、合并 main 或改动现有 Local DP。原 2026-10-27 初稿与 Local 源码复盘仍是历史证据；与本 ADR 冲突时以本 ADR 为准。

## 1. 确定的数据模型及数据流

~~~text
Hospital A CSV      Hospital B FHIR R4      Hospital C HL7 v2
        \                  |                  /
           Producer / Azure Blob Landing (immutable + manifest-last)
                               |
              Intake manifest + exact source identity + bytes SHA256
                               |
        BRONZE · Lakehouse Files Shortcut (prefer) / controlled Copy
        Raw bytes or immutable source pointer + Delta object receipt/evidence
                               |
             PySpark Source Parser + Entity Adapter (pluggable)
        CSV patients/encounters | FHIR Patient/Encounter | HL7 PID/PV1
                               |
          Canonical normalization + versioned DQ + quarantine + FK
                               |
         SILVER · Lakehouse managed Delta relational tables (persistent)
                    canonical_patient / canonical_encounter
                + source provenance / contract version / publication
                               |
              Shared OMOP Mapper + Concept Mapping + Stable ID
              + Person/Visit candidate + reconciliation
                               |
            GOLD · OMOP CDM 5.4 person / visit_occurrence
                    verified transaction/publishing boundary
                               |
                 read-only serving / SQL / reporting
~~~

- **Landing** 是外部来源交付区，唯一可消费入口是显式 `landing-manifest.json` + 真实 SHA256。现有 Publisher v1 的完成语义是 **manifest-last 且独立远端 GET**，不含 READY boolean，也不含 cohort_id；不能用 Blob List 或文件名猜最新批次。
- **Intake** 校验合法 source、hospital/feed/request 身份、字节 hash、大小、对象清单、可访问性/版本、重复/冲突。Intake 是业务放行 Gate，不是医学字段转换。失败对象不发布到 Silver。
- **Bronze** 保存原始事实而非 Canonical：可以采用仍在 Blob 的不可变原始 JSON/HL7/CSV，经 OneLake Shortcut 读取，并在 Delta Receipt 记录 object SHA、URI、source batch、version、run 证据；也可按需 Copy 冻结到 OneLake Files。可选 raw-payload Delta 必须保留未经业务修改的原始数据；**不要求为了称作 Bronze 就无条件复制两份**。Shortcut 不保证源文件自己不可变，需验证 Blob 保留/删除权限/版本；不满足时强制 Copy + 读回。
- **Silver** 是持久化 **Canonical Model** 的二维 Delta 表：`canonical_patient`、`canonical_encounter`，后续扩充 observation/condition。字段含 source-system namespace + source record ID、clinical semantics、来源 SHA、contract/adapter/processing version。通过 Schema/PK/FK/DQ/数据读回才成为 **approved Silver**；quarantine 与 reject metrics 独立保存。**Silver 不包含最终 OMOP Person ID，不能当作临时一次性文件用完即删。**
- **Gold** 负责 OMOP CDM 5.4 业务模型（当前 Person、Visit Occurrence）。Approved Silver → 共享 mapper/Concept/Identity → 独立 Candidate → 一次受控 Gold 发布，最后独立读回验证。**Gold COMMITTED 由 Publisher 证明，不由 Notebook/Pipeline 成功状态猜测。**

## 2. Source / Entity 插件解耦与可复用内核

Adapter 做**来源解析与医学语义正规化**，并输出统一的 Canonical Candidate：

| Source parser | Entity adapter | Silver table | 执行范围 |
| --- | --- | --- | --- |
| FHIR R4 Bundle（fullUrl、urn:uuid、relative ref） | Patient, Encounter | canonical_patient, canonical_encounter | **本 PR 首期 MVP** |
| Synthea CSV | patients.csv, encounters.csv | 同一 Canonical contract | Local 已有实现；Fabric 迁移另立 Change |
| HL7 v2 ADT | PID、PV1 等 | 同一 Canonical contract | OIE 现有 Producer 独立运行；Fabric adapter 未来 Change |

- Source Adapter 不 import OMOP Mapper、Warehouse Writer、Notebook 或平台密钥；Canonical Engine 不应依赖 FHIR/HL7/CSV 的文件路径。
- **Silver 之后原则上共用** OMOP Person/Visit mapper、Concept Mapping、Identity Mapping、DQ、Reconciliation 和出版合同。来源特定 Concept/代码含义通过 **版本化 Mapping Profile** 输入；不能仅因列名相同就断言不同医院语义完全一致。
- Local 的 [patient-v1.json](../../../local-data-platform/spark/contracts/canonical/patient-v1.json)、[encounter-v1.json](../../../local-data-platform/spark/contracts/canonical/encounter-v1.json)、[person-v5.4.json](../../../local-data-platform/spark/contracts/omop/person-v5.4.json)、[visit-candidate-v1.json](../../../local-data-platform/spark/contracts/omop/visit-candidate-v1.json) 是既有基线；构建时 pin 来源 SHA/hash，**不复制维护第二套可能漂移的 Contract**。Local Patient v1 的 birth_date/gender/race/ethnicity 非空、Encounter v1 end_datetime 非空：真实 FHIR 可缺，必须按冻结 Synthea Profile 隔离或另评审 Canonical v2，禁止凭空补造临床事实。
- 不跨医院依姓名/生日自动合并 Patient，FHIR resource.id 不是全局 ID；同医院更换 feed 也需要显式 source namespace/crosswalk 决策。现有 Local PG→Fabric OMOP Snapshot 是 **已标准化复制**，不必逆向重新经过 Canonical，属于独立交付数据产品。

## 3. 最终 Fabric Native 执行与源码归属（2026-10-31）

~~~text
shared-data-engine/                           # one future Python wheel, pure business DataFrames
  src/healthcare_data_engine/
    adapters/fhir_r4/ canonical/ mapping/omop/ identity/ quality/ reconciliation/
azure-fabric/workspaces/healthcare-omop/       # Fabric native Git Item definitions
  notebooks/ingestion/nb_fhir_ingest.Notebook/  # actually executes Spark ETL
  pipelines/pl_fhir_ingest.DataPipeline/        # workflow orchestration
  environments/env_healthcare.Environment/      # published shared wheel
azure-fabric/infra-terraform/                   # existing infra state; unchanged
local-data-platform/                           # existing Local DP; unchanged
~~~

**Notebook + Pipeline mandatory**: Pipeline orchestrates, Notebook executes visible PySpark source verification, native Spark/Delta I/O, Shared FHIR/Canonical/OMOP DQ and independent data readback. Fabric Environment installs and Publish-es the **single** Shared Engine wheel. There is no planned `azure-fabric/ingestion/`, `runtime/` or general I/O wheel. Contract authority stays in Local, frozen by hash until approved migration.

**Gold Warehouse T-SQL POC**: approved Candidate stages first, then within Warehouse short explicit transaction publishes Person/Visit/IdentityMap/Ledger; failure ROLLBACK. Lakehouse→Warehouse data transfer is outside this transaction, and UNIQUE/FK constraints are NOT ENFORCED, requiring explicit application-level checks. All-Delta committed-visibility is an alternative needing separate evidence.

Fabric Workspace git folder and native Item GUIDs must be read back from Fabric, never guessed; Terraform owns approved Infra/Workspace/Lakehouse/Connection, Fabric Git owns Notebook/Pipeline/Environment. Existing `johnzhang-test` Trial publishing code and Local runtime are untouched. **Full normative details**: [Native Fabric ADR](FABRIC-NATIVE-NOTEBOOK-PIPELINE-ENVIRONMENT-ADR-20261031.md).


## 4. Batch / Processing / Publication 三种身份及状态

| 身份 | 典型字段 | 稳定规则 |
| --- | --- | --- |
| **Source Batch** | hospital_id、feed_id、request_id、manifest_sha256 | 源字节身份证；同 request 不同 SHA = CONFLICT/HOLD |
| **Processing Version** | adapter_sha、canonical_contract_sha、mapping/concept_sha、code_sha | 相同源可以经批准用修复后的规则重算；不静默覆盖旧结果 |
| **Publication ID** | approved batch + processing version + target product + committed version | 对消费方发布的确切版本；不会通过重跑冒充新提交 |

`DISCOVERED → MANIFEST_VERIFIED → BRONZE_VERIFIED → SILVER_APPROVED → OMOP_CANDIDATE_VERIFIED → GOLD_STAGED → GOLD_COMMITTED`；状态分支包含 `SKIPPED`（同版本完成）、`FAILED`（明确失败）、`HOLD`（冲突/未知 ACK/超时，需要只读调查）。Silver 和 Gold 可以独立逐阶段完成，不把前者成功当后者完成。Publication 只能由唯一受控 Writer 判定，必须保留 Source、Processing、Delta/Warehouse readback/row/FK/Mapping evidence。

## 5. 实施顺序与验收（设计确认 != 运行授权）

| Gate | 最小验收 | 状态 |
| --- | --- | --- |
| G0 | Manifest 原始 bytes、对象 SHA/ETag、权限/Source Profile/Shortcut 保留策略核实 | 未运行 |
| G1 | 离线合成 FHIR Patient/Encounter Bundle parser、Reference、DQ/quarantine、Contract/坏输入测试 | 未实现 |
| G2 | 修复历史三次 Trial Notebook definition / GetDefinition LRO / exitValue 空结果问题；实际源 SHA + 输出读回 | **HOLD，需要新授权** |
| G3 | 新 5–10 Patient Manifest → Bronze raw byte/ref + receipt；同版本 rerun SKIP | 未运行 |
| G4 | 新 100 Patient Manifest → Silver canonical_patient/encounter Delta；Schema/PK/FK/count/hash、quarantine readback | 未运行 |
| G5 | Shared Mapper → OMOP Person/Visit Candidate；stable ID、Concept、FK 和重算一致性 | 未运行 |
| G6 | Warehouse Gold Writer POC：person/visit/idmap/ledger 全提交或全回滚；并发/Unknown ACK/约束异常；独立读回；不可行再评审纯 Delta | 未运行 |
| G7 | Pipeline E2E、真实 lineage、单次启动/计算成本、失败恢复与隔离回滚 | 未运行 |

**明确未决：** Shortcut vs Copy 的真实 RBAC/保留；Warehouse Gold 能力与成本/备选 Delta；FHIR 更新/Canonical v2；identity crosswalk；Fabric 旧 POC HOLD 的后续授权。首版限定 FHIR NEW_ONLY、Patient/Encounter；HL7/CSV Fabric Adapter、PG OMOP Snapshot、dbt 均为独立未来 Change。原 Local DP、Azure Publisher、当前 Blob、PG、K8s 不修改；没有任何 Fabric 实机、表、Notebook、Warehouse、paid capacity 操作。

## 6. 历史来源与决策追溯

早期两份讨论稿已从当前源码树退休（2026-10-31），**不再参与 Agent 执行规范或新代码设计**；如需追溯，可以访问合并时的固定 Git 快照，而不是在 Main 维护重复草稿：

- [2026-10-27 FHIR Blob 初稿（Git 历史）](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/7060cbb673ea9bcea1de9311f58c1a4145316b35/documents/architecture/design/FABRIC-FHIR-BLOB-INGESTION-DRAFT.md)：仅供核查旧 Manifest 和早期设想，当前业务规范以上文 ADR 为准。
- [2026-10-27 Local DP → Fabric 代码复盘（Git 历史）](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/7060cbb673ea9bcea1de9311f58c1a4145316b35/documents/architecture/design/LOCAL-DP-TO-FABRIC-CODE-ARCHITECTURE-DRAFT.md)：旧 DAG/Adapter 源码复盘细节，实际复用文件与步骤以 [Fabric 实战源码清单](FABRIC-FHIR-PRACTICAL-SOURCE-LAYOUT.md) 为准。
- OpenSpec [proposal](../../../openspec/changes/ingest-fhir-to-fabric/proposal.md)、[design](../../../openspec/changes/ingest-fhir-to-fabric/design.md)、[tasks](../../../openspec/changes/ingest-fhir-to-fabric/tasks.md)。
