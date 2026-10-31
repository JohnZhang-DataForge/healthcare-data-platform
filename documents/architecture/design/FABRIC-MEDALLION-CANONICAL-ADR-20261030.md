---
status: architecture-decided-implementation-pending
decision_date: 2026-10-30
scope: azure-fabric-fhir-bronze-silver-canonical-omop-gold
implementation_status: design-only
source_baseline_sha: 4596c1cec866032e5753597201b595dd1505b2ae
---

# ADR 2026-10-30 — Fabric Bronze → Canonical Silver → OMOP Gold

> **本文件是 PR #533 的权威架构决策。** 2026-10-30 讨论已确定数据分层、Source Adapter 解耦与 Canonical 后共享转换，但 **没有**授权实机部署、paid capacity、合并 main 或改动现有 Local DP。原 2026-10-27 初稿与 Local 源码复盘仍是历史证据；与本 ADR 冲突时以本 ADR 为准。

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

## 3. 物理执行与源码归属

~~~text
shared-data-engine/                              # 未来代码抽离目标，当前不存在
  contracts/                                    # Pin 现有 Local Canonical/OMOP 合同
  src/healthcare_data_engine/
    source_adapters/fhir_r4/{bundle,patient,encounter,reference}.py
    source_adapters/csv/                         # 未来复用 Local
    source_adapters/hl7_v2/                      # 未来
    canonical/{contract,gate}.py
    mapping/omop/{person,visit,concept,identity}.py
    quality/   reconciliation/
  tests/{unit,contract,cross_runtime}/
azure-fabric/
  ingestion/                                    # Fabric I/O、Publisher、Job ports
    src/healthcare_fabric/
      intake/{manifest_v1,blob_reader}.py
      publishing/{bronze_receipt,silver_delta,candidate_delta}.py
      gold/{warehouse_writer,delta_visibility_fallback}.py
      jobs/ingest_fhir.py
  workspaces/healthcare-omop/
    notebooks/ingestion/nb_fhir_ingest.Notebook/
    pipelines/pl_fhir_ingest.DataPipeline/
local-data-platform/                            # 当前现有运行路径：不在本 PR 变更
~~~

- **PySpark 优先**：解析嵌套 FHIR、Reference、Source→Canonical、Canonical→OMOP Candidate。一个受控 Pipeline 调度一个薄 Notebook / Spark Session，业务模块为可单测 Python package；不是一个庞大的 notebook-content.py，也不机械复刻 Airflow 十几个 Task。
- **Gold Writer 首选 POC = Fabric Warehouse T-SQL**：Approved Candidate 先独立加载到 Warehouse staging、验证 readback，然后在 **Warehouse 内短显式事务** 提交 `person`、`visit_occurrence`、`identity_map`、`batch_ledger`；失败 ROLLBACK。**跨 Blob/OneLake Lakehouse/Warehouse 传输本身不是同一个事务**。Warehouse PRIMARY/UNIQUE/FK 是 NOT ENFORCED，必须使用应用级唯一性/外键/并发冲突验证。是否在当前 Trial 和成本条件下可行，**尚未决定和验证**。
- **备选 Gold = 全 Delta**：如果 Warehouse 不可行，另行设计 immutable Candidate staging + COMMITTED visibility + readback；Delta **单表原子性**不意味着 Person/Visit/Audit 跨表原子。未经负向/并发测试不得宣布正式 COMMITTED。
- **SQL/dbt**：适合 Silver 之后的关系建模、文档/测试和 Warehouse SQL 项目，**不作为本 MVP 依赖**。Lakehouse SQL Analytics Endpoint 只读，不能依赖它以 T-SQL 更新 Silver Delta；Silver 使用 Spark 写。
- `fabric-cicd` 拥有 Fabric Notebook/Pipeline/Environment 等代码物件；Terraform 仅管理经批准的 Infra/Workspace/Lakehouse/Connection，不能双重管理。Fabric Runtime 2.0 与 Local Spark 3.5.7 的 PySpark/Scala/Python/Listener 差异必须双端核验。

官方运行时参考：
- Blob shortcut: https://learn.microsoft.com/en-us/fabric/onelake/create-blob-shortcut
- Lakehouse SQL read-only: https://learn.microsoft.com/en-us/fabric/data-engineering/lakehouse-sql-analytics-endpoint
- Warehouse multi-table TX: https://learn.microsoft.com/en-us/fabric/data-warehouse/transactions
- Warehouse NOT ENFORCED constraints: https://learn.microsoft.com/en-us/fabric/data-warehouse/table-constraints

## 3A. Shared Engine 目录和 Agent 归属规范（2026-10-30 确认）

`shared-data-engine/` 的完整目录/功能放置、唯一 owner、禁止的依赖方向、Contract 单一权威、Wheel 固定版本、双端测试和渐进迁移规则已正式确定，见 [Shared Data Engine Directory & Ownership](../../engineering/development/SHARED-DATA-ENGINE-STRUCTURE-AND-OWNERSHIP.md)。根 `AGENTS.md` 和 `shared-data-engine/AGENTS.md` 为开发 Agent 提供必须先读的短规则。

这项决定只确认**未来源码组织和行为约束**：当前只创建 scoped Agent 规则和组件文档导航，尚未创建 Python 包、真实 Shared Wheel、Fabric Notebook/Pipeline 或移动 Local 运行源码。Shared/Local/Fabric 新代码提交之前必须扩展相应 CODE-map CI，进行 Contract/negative/cross-runtime 测试。旧目录候选与此规则冲突时以新规则为准。

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

- [Fabric FHIR 2026-10-27 初稿](FABRIC-FHIR-BLOB-INGESTION-DRAFT.md)（保留实现细节及 Manifest 协议证据；冲突时以本 ADR 为准）
- [Local DP → Fabric 代码复盘](LOCAL-DP-TO-FABRIC-CODE-ARCHITECTURE-DRAFT.md)（Local 逻辑流程与 NEW_ONLY 实际 DAG 的区分）
- OpenSpec [proposal](../../../openspec/changes/ingest-fhir-to-fabric/proposal.md)、[design](../../../openspec/changes/ingest-fhir-to-fabric/design.md)、[tasks](../../../openspec/changes/ingest-fhir-to-fabric/tasks.md)。
