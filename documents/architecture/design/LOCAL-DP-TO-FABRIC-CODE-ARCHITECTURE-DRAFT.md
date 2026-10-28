---
status: draft
scope: local-dp-layered-flow-to-fabric-code-architecture
last_verified: 2026-10-27
source_sha: 4596c1cec866032e5753597201b595dd1505b2ae
evidence: [github-code-readonly]
---

# Local DP 分层数据流与 Fabric FHIR 通用代码架构（讨论稿）

> **DRAFT / 源码级核查，尚未实施、未验收 Runtime。** 基于 Healthcare Main 4596c1cec866032e5753597201b595dd1505b2ae（2026-10-27）的源码与 Contract 静态核对。本文区分 Local 的完整分层设计、历史更细粒度的 Raw/Processed 发布器、当前 NEW_ONLY 受控实际执行链。只在独立 Draft PR #533 中讨论，不合并 Main，不触发 Spark/Fabric/Blob/PG 操作。

## 1. Local DP：通用数据流的设计意图

### 1.1 逻辑层、合同和完成边界

~~~text
[Independent Producer / Synthea source]
  └─ frozen request / source identity / payload
           ↓
[Landing / SeaweedFS S3]
  └─ verified files + immutable manifest LAST
           ↓
[Discovery + Claim / Airflow]
  └─ select exact batch_id + manifest_uri + manifest_sha256
           ↓
[Processing / Source Adapter]
  └─ source-specific CSV parser → typed canonical data + DQ
           ↓
[Canonical Patient / Canonical Encounter]
  └─ source-independent contract + provenance columns
           ↓
[Approved Raw Gate]                # historical fine-grained publisher
  └─ schema/key/metadata/readback + immutable approved manifest
           ↓
[Processed / OMOP Candidate]        # target-specific map
  └─ concept map + person ID mapping + candidate + DQ
           ↓
[Reconciliation + Handoff]
  └─ person/encounter PK/FK, same source/batch, row counts
           ↓
[Writer with claim/fence/authorization]
  └─ one PostgreSQL transaction for Person + Visit + ledger
           ↓
[Independent PostgreSQL readback; replay SKIP]
~~~

**重点不是每层多少 Pod**。Source Adapter 专门处理来源格式；Canonical 定义全平台标准业务语义；Mapper 专门处理目标 CDM；Writer 负责数据库持久状态和并发安全。层之间以 schema/version/Source ID、immutable data、Manifest SHA、DQ readback 交接，新增来源可以替换 Parser，不必重写整个下游。

**关键术语澄清**：历史 Local Person/Visit 的 Raw 是已通过 Gate 的 Canonical Parquet（例如 Canonical Patient Raw），不等于原始 CSV bytes。Processing 是临时或待批准中间层。Fabric 的 Bronze 应保留原始 FHIR bytes；Fabric Silver 才对应被核准的 Canonical。不能根据单词 Raw 把两者直接等同。

### 1.2 当前 NEW_ONLY 真正运行的“精简路径”

~~~text
Synthea NEW_ONLY → health-landing (18 CSV + manifest)
   → Airflow new_only_omop_consumer
   → scan_ready_manifests
   → select_verified_new_only_batch
   → inspect_claim_readonly
   → route_new_only_status
          COMPLETED ───────────────→ SKIP
          ABSENT + explicit opt-in → spark_patient ──┐
                                  → spark_encounter ┤
                                                     ▼
                                            spark_reconcile
                                                     ▼
                                            prepare_writer_handoff
                                      HANDOFF_VERIFIED_NOT_AUTHORIZED
                                                     ▼
                                   explicit writer_commit AND commit secret
                                                     ▼
                                       execute_new_only_writer
                                       PG precommit / fence / single TX
                                                     ▼
                                           independent PG readback
~~~

这条**当前业务 DAG 并没有每次顺序调用历史所有** publish_canonical_patient、visit processed DQ/manifest 等子模块。它直接由两个 Spark Processing 分支产生并读回 Canonical Parquet，统一 Reconciliation，再通过不可变 Writer Handoff 进入受控 PG Writer。旧细粒度 Raw/Processed/Gate 代码仍体现了经过设计的可重用**发布协议**，但不能把历史各步骤误称为当前默认 NEW_ONLY E2E 的全部任务。

当前边界：Discovery 不代表自动 Claim；Spark 成功不授权 OMOP 写入；Writer 的 Handoff 仍是 NOT_AUTHORIZED；Airflow 绿色不代表 PG COMMIT，必须读回。未知 COMMIT ACK 不能自动重复执行。

### 1.3 基于代码的组件索引

| 层 | 实际源代码 / Contract | 本质职责 |
| --- | --- | --- |
| Producer/Handoff | [FHIR Source Handoff](../../../local-data-platform/apps/clinical_producers/source_handoff.py)、[Blob Publisher](../../../local-data-platform/apps/clinical_producers/azure_blob_publisher.py) | 冻结源身份、Source SHA；Publisher 是逐对象远端 GET 后最后写 manifest |
| Manifest / Discovery | [batch_manifest.py](../../../local-data-platform/spark/common/batch_manifest.py)、[scan_ready_batches.py](../../../local-data-platform/apps/landing_discovery/scan_ready_batches.py) | 验 Manifest、文件计数/hash/来源状态，查找可信 Batch |
| Claim / Routing | [batch_ledger.py](../../../local-data-platform/apps/landing_claim/batch_ledger.py)、[new_only_omop_routing.py](../../../local-data-platform/airflow/dags/new_only_omop_routing.py) | EXACT Batch + SHA，ABSENT/COMPLETED/PROCESSING/FAILED 分类和 SKIP |
| Orchestration | [new_only_omop_consumer.py](../../../local-data-platform/airflow/dags/new_only_omop_consumer.py)、[landing_spark_processing.py](../../../local-data-platform/airflow/dags/landing_spark_processing.py) | Airflow 负责运行路由/参数和权限开关，Spark 负责 ETL |
| Source Adapter | [synthea_patient_adapter.py](../../../local-data-platform/spark/apps/person/synthea_patient_adapter.py)、[synthea_encounter_adapter.py](../../../local-data-platform/spark/apps/visit/synthea_encounter_adapter.py) | CSV → Typed Canonical、Provenance、DQ、Processing Parquet + Readback |
| Canonical Contracts | [patient-v1.json](../../../local-data-platform/spark/contracts/canonical/patient-v1.json)、[encounter-v1.json](../../../local-data-platform/spark/contracts/canonical/encounter-v1.json)、[canonical_gate.py](../../../local-data-platform/spark/common/canonical_gate.py) | 两个实体的字段/类型/唯一键/来源元数据 Gate |
| Historical Raw Gate | [publish_canonical_patient.py](../../../local-data-platform/spark/apps/person/publish_canonical_patient.py)、[visit raw preflight](../../../local-data-platform/spark/apps/visit/validate_encounter_raw_for_visit.py) | Canonical 通过 DQ 与 remote Readback 后才批准 Raw |
| Person Mapper | [map_canonical_patient_to_omop.py](../../../local-data-platform/spark/apps/person/map_canonical_patient_to_omop.py)、[person-v5.4.json](../../../local-data-platform/spark/contracts/omop/person-v5.4.json) | Canonical → OMOP Person 18 列；只读 PG person ID map + Concepts |
| Visit Candidate | [map_encounter_to_visit_candidate.py](../../../local-data-platform/spark/apps/visit/map_encounter_to_visit_candidate.py)、[visit-candidate-v1.json](../../../local-data-platform/spark/contracts/omop/visit-candidate-v1.json) | 纯 PySpark DataFrame transform；不进行 I/O/Commit；依赖已核验 Person FK |
| Processed Publication | [processed_visit_writer_core.py](../../../local-data-platform/spark/apps/visit/processed_visit_writer_core.py)、[publish_processed_dq.py](../../../local-data-platform/spark/apps/visit/publish_processed_dq.py)、[publish_processed_manifest.py](../../../local-data-platform/spark/apps/visit/publish_processed_manifest.py) | Candidate 创建并远端读回 → DQ SHA → approved Manifest 最后发布 |
| Reconciliation | [reconcile_person_visit.py](../../../local-data-platform/spark/apps/task004/reconcile_person_visit.py) | exact row counts、PK 唯一性、source/batch 一致、Encounter 对 Patient 无 orphan |
| Writer | [new_only_airflow_writer.py](../../../local-data-platform/apps/omop_writer/new_only_airflow_writer.py)、[precommit_gate.py](../../../local-data-platform/apps/omop_writer/precommit_gate.py)、[dynamic_new_only_commit.py](../../../local-data-platform/apps/omop_writer/dynamic_new_only_commit.py) | 只读预检、显式批准、Claim Lease/Fencing、PG 单事务 Stage/Commit、持久读回 |

### 1.4 为什么它有通用性

- **Source Context贯穿全程**：canonical v1 字段包含 source_system、source_version、source_batch_id、source_ingest_date、source_file/sha/size、adapter_name/version、processing_run_id。下游不用通过文件名猜来源身份。
- **Canonical 对来源无感**：新的 FHIR/HL7 Adapter 只负责转换成统一 Patient/Encounter 业务语义；原有 Concept Mapper 与 Writer 不能反过来决定 FHIR 如何解析。
- **Processed 对目标模型负责**：OMOP CDM 是一种业务数据产品，另外还可以做质量分析或研究视图；数据源 Parser 不应依赖 PG SQL/Delta Table。
- **Manifest/Gate 是发布而非日志**：没有 Data+Dq/readback+最终 Manifest 就不是可消费的已完成版本；半成品不能被 downstream 自动加载。
- **Writer 独立授权**：Candidate/DQ 完成仍不等于数据库提交；最终持久化由单一受控组件审查。

**真实兼容边界**：Local Patient v1 要求非空 birth_date、gender_code、race_code、ethnicity_code；Encounter v1 要求 start/end_datetime、encounter_class、source_code 等。FHIR R4 的可选字段、未结束 Encounter 不能为了通过 v1 Gate 而随意伪造；要么限定已验证的 Synthea Profile，要么定义向后兼容的新 Canonical 版本并显式 quarantine/Unsupported 统计。

## 2. Local 逻辑层与 Fabric 的正确映射

| Local 功能 | Fabric 目标 | 复用/优化原则 |
| --- | --- | --- |
| health-landing + immutable Manifest | 外部 Azure Blob FHIR Landing | 直接消费真实 Publisher v1，不重造 READY |
| temporary Processing | Batch-scoped Bronze/staging | 算子可集中执行，Batch/Provenance 持久隔离 |
| Approved Canonical Raw | Silver Canonical Patient/Encounter（approved） | 延续 Schema/PK/FK/Metadata + approved/readback Gate |
| Processed OMOP Candidate | Delta OMOP Candidate | 纯 DataFrame Mapper，无写入副作用 |
| PG Writer Claim+Fence+single TX | Delta Batch Ledger + staged version + commit visibility | 复用幂等/最终发布语义；**不能复制 PG 跨表原子事务声明** |
| Airflow/KubernetesPodOperator | Fabric Data Pipeline/Notebook Activities | 调度和数据逻辑分开 |
| Local Spark app Python | 版本化可测试 Python wheel + 薄 Notebook | 降低 Notebook 中逻辑耦合、保留单元测试与跨运行时比较 |
| Local PostgreSQL CDM | Fabric OneLake Delta（独立 OMOP data product） | 不反写 PG17；不凭相同源 Patient.id 跨来源合并 |

目标逻辑图：

~~~text
Azure Blob immutable FHIR Bundle objects + verified landing-manifest.json
          ↓
Manifest Reader / Batch Claim Gate [source-specific]
          ↓
Bronze: FHIR 原始字节 / Source+Object Evidence
          ↓
FHIR R4 Adapter: Bundle.entry/resource/fullUrl/reference
          ↓
Canonical Silver: Patient, Encounter + provenance
          ↓
Canonical DQ + PK/FK Reconciliation / approved publication
          ↓
Product router ─┬─ Research / source-quality data products (later)
                └─ OMOP 5.4 Mapper
                        ↓
                  Candidate Person/Visit + stable ID map
                        ↓
                   Staging + Readback + Commit Visibility
                        ↓
                 Serving views of COMMITTED Delta only
~~~

注意：Fabric **Bronze 是原始 FHIR**，Local **Raw 是 Canonical approved**。在新代码里统一采用 Landing / Bronze / Canonical / Candidate / Serving，避免混淆。

## 3. 推荐的 Fabric 代码结构（候选，不创建可运行代码）

**一个 Pipeline 调度逻辑、一个 ingest Notebook + 可选独立 verify Notebook、内部由多模块普通 Python 包实现。** 不把所有业务逻辑塞进 notebook-content.py，也不强制每个 Stage 启动独立 Spark Job。

~~~text
azure-fabric/
├── ingestion/                                  # 通用可测试 Python 工程
│   ├── pyproject.toml                          # 构建版本化 wheel，实际发布待验证
│   ├── contracts/
│   │   ├── ingestion-batch-envelope-v1.schema.json
│   │   └── fhir-r4-synthea-profile-v1.json
│   ├── src/healthcare_ingestion/
│   │   ├── models.py                           # BatchContext, ObjectReceipt, Evidence
│   │   ├── sources/
│   │   │   ├── registry.py                     # 注册来源类型，不使用医院硬编码 if/else
│   │   │   ├── manifest_protocol.py            # 统一读取/校验接口
│   │   │   ├── fhir_blob_manifest.py           # 当前 Publisher v1 adapter
│   │   │   ├── fhir_r4/
│   │   │   │   ├── bundle_parser.py
│   │   │   │   ├── patient_adapter.py
│   │   │   │   ├── encounter_adapter.py
│   │   │   │   └── reference_resolver.py
│   │   │   ├── hl7_v2/                         # 未来独立 Change 才建
│   │   │   └── omop_snapshot/                  # 未来独立 Change 才建
│   │   ├── canonical/
│   │   │   ├── contracts.py                    # pinned Local Canonical contract
│   │   │   ├── patient_gate.py
│   │   │   ├── encounter_gate.py
│   │   │   └── reconciliation.py
│   │   ├── mapping/
│   │   │   ├── concept_mapping.py
│   │   │   ├── identity_map.py
│   │   │   ├── omop_person.py                  # Candidate only
│   │   │   └── omop_visit_occurrence.py        # Candidate only
│   │   ├── quality/
│   │   │   ├── manifest_gate.py
│   │   │   ├── schema_gate.py
│   │   │   └── reference_gate.py
│   │   ├── publishing/
│   │   │   ├── bronze_publisher.py
│   │   │   ├── canonical_publisher.py
│   │   │   ├── delta_candidate_writer.py
│   │   │   ├── batch_ledger.py
│   │   │   ├── commit_visibility.py
│   │   │   └── readback.py
│   │   ├── jobs/
│   │   │   ├── ingest_fhir.py                  # 组合阶段和执行 Gate
│   │   │   └── verify_fhir.py                  # 独立读回与完成判定
│   │   └── runtime/
│   │       ├── fabric_context.py              # Workspace/Lakehouse/Connection
│   │       ├── source_bytes.py                # Blob Shortcut/Copy Reader 接口
│   │       └── notebook_result.py             # Job 与持久结果分离
│   └── tests/
│       ├── fixtures/                           # 仅合成 FHIR/坏例子
│       ├── unit/
│       ├── contract/
│       └── integration/
└── workspaces/healthcare-omop/
    ├── notebooks/ingestion/
    │   ├── nb_fhir_ingest.Notebook/             # 真正 Fabric Item 后才创建
    │   │   ├── .platform
    │   │   └── notebook-content.py             # 仅传参数/调用 Python 核心
    │   └── nb_fhir_verify.Notebook/             # 严格多表提交阶段可启用
    └── pipelines/
        └── pl_fhir_ingest.DataPipeline/
            ├── .platform
            └── pipeline-content.json
~~~

以上是**计划的目录和文件名**，不是当前 Git 中已存在源码。真实 Fabric Item 必须从 Fabric/fabric-cicd 的受控定义导出 .platform/logicalId，不得编造 GUID。添加普通 Python 包和 Notebook/Pipeline 文件时，同一 PR 必须维护 Azure/Fabric 总源码地图及 notebooks/CODE.md、pipelines/CODE.md。

### 3.1 严格依赖方向

~~~text
Pipeline → thin Notebook → jobs / job context
                               ↓
               source manifest + source-specific parser
                               ↓
                        Canonical schema/gate
                               ↓
                    Quality / Reconciliation
                               ↓
                       Product Mapper (OMOP)
                               ↓
                       Publishing / Ledger
                               ↓
                        Fabric runtime ports
                  (Blob Reader, Delta, Notebook API)
~~~

- sources/fhir_r4/**不导入 Delta Writer 或 Notebook**；只实现 Resource 解析 → Canonical。
- canonical/**不访问 Azure Secret、Local PG17 JDBC、K8s S3**；可使用纯 PySpark DataFrame Gate。
- mapping/omop_*.py **不执行写入**；返回 Candidate DataFrame 和所需 Plan/Mapping 证据，仿照现有 map_encounter_to_visit_candidate.py 的纯函数边界。
- publishing/**独占持久副作用**；负责 immutable staging/readback、批次事务状态与最后 visibility Gate；不能假装单表 Delta MERGE 等价于多表原子 COMMIT。
- jobs/* 负责模式选择（validate_only → stage_only → explicit commit）、状态机与证据；Notebook 仅传参数与调用库。
- runtime/* 负责 Fabric Connection、Shortcut/Copy、Delta、Notebook exitValue 等平台适配，避免把环境差异散落在领域代码中。

### 3.2 合同共享，不制造两个互相漂移的 Canonical 真相

**Local Canonical/OMOP 文件仍是既有事实源**，不复制维护同名表定义：
- Canonical Patient v1：local-data-platform/spark/contracts/canonical/patient-v1.json
- Canonical Encounter v1：local-data-platform/spark/contracts/canonical/encounter-v1.json
- OMOP Person 5.4：local-data-platform/spark/contracts/omop/person-v5.4.json
- OMOP Visit Candidate：local-data-platform/spark/contracts/omop/visit-candidate-v1.json

Fabric build 时可以**固定精确源 SHA/hash 将合同放入 wheel/Notebook Resources**，但不在 azure-fabric/ingestion/contracts/ 手动分叉成另一套被独立编辑的 Canonical。若 FHIR 需要区别于 v1 的字段可空性或多来源 Source Identity，应设计明确 versioned delta Canonical Contract，兼容期同时保留旧合同；不能偷偷变更 Local 生产 Schema。

**来源 Manifest 不强行统一原始格式**：FHIR 读取现有 Publisher 的 healthcare-azure-blob-landing-manifest-v1（hospital_id/feed_id/request_id/source_manifest_sha256/target_format/skipped_non_admissions/objects[]；object 有 blob_key/sha256/size_bytes/etag/version_id）；该 Manifest **没有 READY 布尔值，也没有 cohort_id**。将它验证后转换成内部的 IngestionBatchEnvelope，未来 HL7、PG→Blob OMOP snapshot 各实现自己的 Manifest Adapter，统一次级 Context/Status 不修改 Producer 的源合同。

候选 pure interface（示意，非运行实现）：

~~~python
@dataclass(frozen=True)
class BatchContext:
    source_kind: str
    hospital_id: str
    feed_id: str
    request_id: str
    manifest_uri: str
    manifest_sha256: str
    source_manifest_sha256: str
    adapter_version: str

def resolve_verified_batch(manifest_uri: str, sha256: str) -> BatchContext: ...
def verify_original_objects(ctx: BatchContext) -> list: ...
def to_canonical_patient(bundle_df, ctx: BatchContext) -> DataFrame: ...
def to_canonical_encounter(bundle_df, ctx: BatchContext) -> DataFrame: ...
def verify_canonical(patient_df, encounter_df, contract) -> dict: ...
def to_omop_candidate(patient_df, encounter_df, id_map, concepts): ...
def stage_and_readback(ctx, dataframes) -> dict: ...
def verify_and_publish_commit(ctx, evidence) -> dict: ...
~~~

## 4. Fabric 数据阶段与 Local 事务保护的替代实现

### 4.1 Bronze：不可变源证据

- 从**明确传入的** Blob manifest_uri + manifest_sha256 读取 Manifest 真正原始字节、校验 schema/identity/object_list，逐对象校验 size/SHA、必要 ETag/Version。不存在 Manifest → HOLD；不能 Blob List 发现 JSON 就当批次 READY。
- Bronze 保存原始 FHIR Bundle bytes 或已验证的不可变对象引用，附 hospital_id/feed_id/request_id/manifest_sha/object_sha/path 等；**Bundle 对象个数不等于 Patient/Encounter 的资源数**，必须从 entry[].resource.resourceType 实际计数。
- 优先只读验证 Blob Shortcut，失败后由受控 Copy Activity 复制限定的 Manifest 资源再独立读回；不假定 Azure Blob Container 是 ADLS Gen2 HNS。Shortcut 的 URI/Unicode 文件名、实际认证与版本稳定性需实机证明。

### 4.2 Silver：每种来源一个 Adapter，同一业务 Canonical

- FHIR Patient Adapter：实际 Bundle.entry[].resource、logical id、birthDate、gender、race/ethnicity extension 映射至 Canonical。缺失、未知编码进入版本化 DQ/quarantine；不能编造合法 Concept。
- FHIR Encounter Adapter：id、subject.reference（Patient/id、Bundle fullUrl 或 urn:uuid）、class、period、status；缺 end datetime 与 Local v1 合同冲突时必须显式拒绝/隔离或评审新 Canonical v2。
- Canonical 主键：Patient (source_system,source_record_id)，Encounter (source_system,source_encounter_id)，均带文件 SHA、处理批次和 Adapter/Contract 版本；source_system 至少区分 hospital_id/feed_id，不根据生日姓名合并。
- Canonical approval：行数、关键字段、唯一键、same source/batch、Encounter→Patient FK（或明确批准的外部引用范围）、Readback Evidence；审批通过才发布 Silver approved run。

### 4.3 Processed / OMOP Candidate

- 采用独立 OMOP Mapper；Person ID 通过稳定映射表分配，不能把 FHIR 字符串 ID 直接转换为 OMOP 整数，不能认为 hash 截断无冲突。
- Person Candidate 对齐 18 列 OMOP Person 5.4；Visit Candidate 对齐 source Encounter FK、visit_concept、有效 start/end、mapping_contract_sha、ID-map；输入不满足 Contract 时 FAIL/HOLD。
- Candidate 仅是待写数据产品，**即使已保存 Delta staging，也不能称为 Committed OMOP**。

### 4.4 Delta Writer：沿用 Gate/Plan/Readback，重新设计事务

~~~text
DISCOVERED → VERIFIED → CANONICAL_APPROVED
 → CANDIDATE_APPROVED → STAGED → READBACK_VERIFIED → COMMITTED
      same manifest already committed → SKIPPED
      same request different manifest → CONFLICT / HOLD
      partial or unknown ack → HOLD / readonly investigation
~~~

- 建议 audit 主键绑定 (hospital_id,feed_id,request_id,manifest_sha,contract_sha,adapter_version)，每次 attempt 另外保存 run_id、目标 Delta 表版本与 row/hash Evidence。候选采用 batch/run-scoped append-only staging，不覆盖已提交版本。
- **Delta 原子性是单表粒度**：与 Local PG 的 Person+Visit+Ledger single-TX 不同。建议一个**最后提交的可见性记录/指针**关联已独立验证的 Person/Visit/IDMap 版本，Serving 只读取 COMMITTED Run 的 immutable 数据。具体 Audit 写入竞争、版本固定读取与消费者跨表一致性的行为，必须通过并发/partial failure/版本漂移测试才能采用。
- 尚无被验证的多表 Commit Visibility 方案时只交付 Bronze/Silver，不把运行结束标成 OMOP COMMITTED；不用 Local PG Fencing SQL 复制到 Spark。
- UNKNOWN_OUTCOME_NO_RETRY 原则继续适用：失败/超时先独立读 Ledger/Delta 实际持久状态，不盲目重跑。

### 4.5 Pipeline/Notebook 与独立验证

~~~text
pl_fhir_ingest (manual allowlisted manifest_uri+sha)
 → verify permitted batch identity
 → nb_fhir_ingest
      -> Manifest/Bronze/Canonical/DQ/optional Candidate staging
 → nb_fhir_verify (at strict OMOP commit milestone)
      -> NEW context independent Delta readback
      -> check Manifest/Counts/PK/FK/Version/Hash
      -> explicit COMMITTED visibility result only on proven success
 → Pipeline status: COMMITTED / SKIPPED / FAILED / HOLD
~~~

第一阶段可以只有 **一个 Notebook 的 validate_only 或 Bronze+Silver**，在一个 Spark Session 内调用多个模块，降低 Fabric Trial 启动成本；达到多表正式 Commit 时，建议第二个很薄的 verifier Notebook 或同等独立读回执行器。Fabric Notebook Activity 支持参数传入（官方文档：https://learn.microsoft.com/en-us/fabric/data-factory/notebook-activity），但目前旧 Trial 的 exitValue/GetDefinition 三次失败后仍 HOLD，必须有新决策才重新实测。Job Completed/空 exitValue 不是业务 E2E 证据，最终依赖持久化审计和独立数据读回。

## 5. 后续其它来源应当怎么接入

~~~text
Synthea CSV → existing Local S3/Airflow path
FHIR R4    → Azure Blob Manifest v1 → FHIR Adapter ───────────┐
HL7 V2     → Azure Blob Manifest v1 → HL7 Adapter (future) ───┼─→ Canonical
PG OMOP    → Export Snapshot Manifest → direct OMOP Replica ──┘    ↓
                                                        Product routing:
                                                     OMOP / Research / DQ
                                                              ↓
                                                   validated published data
~~~

- FHIR 与 HL7 是不同语法的 Source Adapter，但可以经过同一 Canonical Contract 与统一 DQ；OIE A01 只代表 Admission 子集，不能要求与完整 FHIR Encounter 1:1 对齐。
- PG OMOP Export 已标准化，不必逆转回 FHIR/Canonical 再重新映射；应保持独立 OMOP Source identity 和发布审计。Local PG person_id 与 Fabric FHIR 来源 person_id 不应自动合并，需另一个经验证的跨来源 Crosswalk。
- 为避免过早构造巨大的所有源万能处理器，MVP 先实现 FHIR adapter + 一个通用 Batch/Canonical/Publishing 框架。后续每种来源独立 Change 增加 Adapter，不改 FHIR 的真实验收合同。

## 6. 实施次序（仍未授权开发/运行）

| 切片 | 源码/交付 | Gate |
| --- | --- | --- |
| A. Frozen Manifest contract | sources/fhir_blob_manifest.py, contracts/* | 离线 Byte/SHA/重复对象/Source identity/Demo name negative |
| B. FHIR Adapter and Pure Canonical | sources/fhir_r4/* + canonical/* + quality/* | 5–10 合成 Patient/Encounter、Reference、缺字段/重复 ID 负向、Local Contract 对照 |
| C. Blob access POC | runtime/source_bytes.py | 独立获准 Blob Shortcut/Copy GET、ETag/SHA/Unicode filename 真实读回 |
| D. Silver publication | publishing/canonical_publisher.py | approved gate + immutable evidence + same batch rerun SKIP |
| E. OMOP Candidate | mapping/* | Person 18 columns、Visit FK、Concept Mapping、稳定 ID、Candidate 不授权 Commit |
| F. Delta transaction safety | publishing/batch_ledger.py, commit_visibility.py, readback.py | 并发、部分表写入、同请求 SHA 冲突、未知 ACK、只暴露 committed version |
| G. Fabric thin Items | nb_fhir_ingest/verify + pl_fhir_ingest | 真实 .platform GUID / fabric-cicd 唯一发布责任方 / 受控 Runner；旧 POC HOLD 先解除 |
| H. Business E2E | 真正的新 5–10 后 100 人冻结 Request | 独立 Delta Readback + Rows/Keys/FK/Hash + 成本与 OpenLineage（后者不能假造） |

**开发规范**：新源码全部按模块能力命名；修改实际 Python 或 Notebook/Pipeline 文件时同步 Azure/Fabric CODE.md；不改已经运行的 Local Task004 代码/PG17；任何 Azure Runtime/付费动作另需权限、并行 Session 协调与用户授权。仓库的源设计：[Fabric FHIR 初稿](FABRIC-FHIR-BLOB-INGESTION-DRAFT.md)，本文件仅深化代码和通用流转结构。

## 7. 待讨论的结构性问题

- 是否采纳物理层 **Bronze（原始 FHIR）/ Silver（Approved Canonical）/ Candidate（OMOP）/ Serving（Committed）**，而非机械复制 Local 的 Raw 文件夹名？
- 是否确定 **独立 Python 包 + thin Notebook** 为统一代码模式（推荐）；暂不修改 Local 现有目录及运行源码？
- 首版 **一个 Pipeline、一个 ingest Notebook**，OMOP 多表阶段再增加 independent verify Notebook？
- FHIR 以已有 Synthea NEW_ONLY 实测 Profile 为首个 Canonical v1 范围，缺失/不支持字段显式隔离；Canonical v2 未来再定？
- PG OMOP Snapshot 继续保留直接复制路径，FHIR/HL7 走 Source Adapter；真正多源匹配通过显式 Crosswalk，不碰巧合并 person_id？

## 8. 已核查及限制

已核查：源代码级别 DAG、两个 Spark Processing 路线、Canonical/Raw/Processed 发布器、Pure Candidate Mapper、Reconciliation、Writer 保护与 Publisher Manifest 的现行静态文件。未核查：当前 Azure Blob 原始 R4 Bundle 字节/ETag、Fabric Shortcut 权限、Notebook 实际定义与执行、Delta 跨表读者语义、新 Python 包的构建与版本兼容。

**本轮没有新增任何真实 Python 模块、Notebook Item、Pipeline Item、Fabric 表、S3/PG/Blob 数据或付费 Azure 资源。**
