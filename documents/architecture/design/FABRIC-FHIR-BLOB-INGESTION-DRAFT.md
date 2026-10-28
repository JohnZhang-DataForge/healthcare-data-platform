---
status: draft
scope: fabric-fhir-r4-blob-to-lakehouse-omop-ingestion
last_verified: 2026-10-27
source_sha: 4596c1cec866032e5753597201b595dd1505b2ae
evidence: [repository-source-review-only]
---

# Fabric FHIR R4 Blob → Spark Notebook → Pipeline → OneLake 入库设计（讨论初稿）

> **DRAFT / 尚未批准架构 / 无运行副作用。** 本稿基于 2026-10-27 Healthcare Main 4596c1cec866032e5753597201b595dd1505b2ae 的源文件与已记录历史证据进行静态分析，未检查此刻 Azure Blob 对象实际字节、Fabric Items 或在线运行状态。用户说明 FHIR 已发布至 Azure Blob；本稿不将该事实扩大为 Fabric Bronze/Silver/OMOP 已入库。没有执行 Notebook、Pipeline、Terraform、Data Writes、部署或付费容量变更。

## 0A. Local DP 源码复盘与代码模块设计（2026-10-27 补充）

**请优先阅读 [Local DP 分层流程与 Fabric 通用代码架构讨论稿](LOCAL-DP-TO-FABRIC-CODE-ARCHITECTURE-DRAFT.md)**：该文基于实际 Local DAG、Synthea Patient/Encounter Adapter、Raw Gate、Processed Candidate、Reconciliation、Writer 和 Publisher 源码区分 **完整分层设计** 与 **实际 NEW_ONLY 精简运行链**，给出了新 Python 包 / adapters / canonical / mapping / quality / publishing / Fabric thin Notebook / Pipeline 的模块树与依赖图。

**修正初稿中“单个 Notebook”的容易误读之处**：MVP 可在一个 Notebook/Spark 会话中组合多个独立 Python 模块，**绝不把所有 ETL 拼成单文件**；严格的 OMOP Person/Visit 多表提交建议增加独立 verify Notebook（或等价只读验证器）。Local 的历史 approved Raw 是 Canonical 数据，并非字节级原始数据；Fabric Bronze 是原始 FHIR Bundle，两者不应简单同名相等。未来 PG→Blob OMOP 快照无需逆变换成 FHIR/Canonical，仍属于独立直通复制路线。

## 0. 目标、边界与现有设计的关系

目标：从已经使用不可变协议发布到 Azure Blob 的 **FHIR R4 Bundle** 中加载 Patient 与 Encounter，经 Fabric Data Pipeline 编排、PySpark Notebook 校验/解析、写入 OneLake Lakehouse Delta，形成带医院/Feed/Request 可追溯身份的 Bronze、Silver 与最小 OMOP person/visit_occurrence 数据产品。

**此链路独立于已经规划的 PostgreSQL OMOP → Azure Blob snapshot → Fabric 分析副本**：那条是“已标准化 OMOP 的复制”，本条是“原始 FHIR → 新的标准化映射”，两条都不应反写 Local PG17，也不能互相冒充相同来源。Local DP 仍是 CSV→S3→Airflow→Spark→PG OMOP 的已验收处理体系。HL7_V2 仍是独立 Producer/Parser/后续 Fabric Change，不偷偷纳入本轮实现。

关联权威资料：
- [已采纳的 FHIR/HL7 MVP 设计](FHIR-HL7-MULTISOURCE-MVP-DESIGN.md)；[跨来源 Fabric Roadmap](HEALTHCARE-V2-MULTISOURCE-FABRIC-ROADMAP-DESIGN.md)。
- [当前 Azure Blob Publisher 实现](../../../local-data-platform/apps/clinical_producers/azure_blob_publisher.py)；[Publisher Plan Contract](../../../local-data-platform/apps/clinical_producers/blob_publish_contract.py)；[只读 Source Handoff](../../../local-data-platform/apps/clinical_producers/source_handoff.py)。
- Local [Canonical Patient](../../../local-data-platform/spark/contracts/canonical/patient-v1.json)、[Canonical Encounter](../../../local-data-platform/spark/contracts/canonical/encounter-v1.json)、[OMOP Person 5.4](../../../local-data-platform/spark/contracts/omop/person-v5.4.json)、[Visit Candidate](../../../local-data-platform/spark/contracts/omop/visit-candidate-v1.json)、[Airflow NEW_ONLY](../../../local-data-platform/airflow/dags/new_only_omop_consumer.py)；现有 [Fabric Notebook](../../systems/azure-fabric/notebooks/README.md) 与 [Pipeline](../../systems/azure-fabric/pipelines/README.md)。
- [Fabric Runtime 实测边界](../../infra/SPARK-PORTABILITY-POC-20261026.md)：Local Spark 3.5.7 内存转换 PASS；Fabric Runtime 2.0 配置已读回，但三次 Notebook 测试未得到有效退出结果，同代码业务计算一致性与 OpenLineage 均未通过；**不得将 Job Completed 视为 PySpark 业务成功。**
- Microsoft 官方：[Azure Blob Shortcut](https://learn.microsoft.com/en-us/fabric/onelake/create-blob-shortcut)、[Notebook activity](https://learn.microsoft.com/en-us/fabric/data-factory/notebook-activity)、[Spark Lakehouse load](https://learn.microsoft.com/en-us/fabric/data-engineering/lakehouse-notebook-load-data)、[Fabric CI/CD options](https://learn.microsoft.com/en-us/fabric/cicd/manage-deployment)。

## 1. 目标数据流

~~~text
dw-synthea frozen Synthea FHIR R4
   └─ Azure Blob Publisher
       ├─ immutable FHIR_R4/fhir/*.json objects; remote GET + SHA/ETag
       └─ landing-manifest.json（最后条件创建，immutable commit boundary）
                       │
                       ▼
     Fabric Data Pipeline：明确指定 Manifest + SHA / 源 Feed
       │  validate parameters → Notebook activity → success/failure routing
       ▼
     Notebook nb_fhir_ingest（先纯校验，再 staging，然后提交）
       │
       ├─ verify manifest, allowed source, object bytes & SHA256
       ├─ Bronze: raw FHIR bytes + source metadata + per-resource provenance
       ├─ Parse Bundle.entry[].resource（先 Patient、Encounter）
       ├─ Silver: canonical_patient / canonical_encounter
       ├─ cross-reference + DQ + source-key-to-OMOP-id crosswalk
       ├─ candidate OMOP person / visit_occurrence（Delta，独立表）
       ├─ reconciliation & readback
       └─ last publish verified COMMITTED batch visibility marker
                        │
                        ▼
     OneLake Lakehouse Delta / SQL analytics read-only views
           + batch audit / source lineage evidence
~~~

简化原则：**MVP 一个 Pipeline + 一个薄的 ingest Notebook + 可独立测试的多模块 Python ETL 核心；严格的 OMOP 跨表验收阶段引入独立 verify Notebook**，不要照搬 Local DP 的十几个中间 Workflow、每个阶段都单独起 SparkApplication、专门 PG SQL Writer。需要离线单测的解析/映射函数可与 Notebook 运行适配层分离；经过规模和故障数据证明后才拆多 Notebook/Pipeline。

### 1.1 精确 Landing 合同（按实际 Publisher 源码，而不是虚构 READY）

实际 Publisher 的终态 Manifest schema_version 为 **healthcare-azure-blob-landing-manifest-v1**，对象路径按以下结构形成：

~~~text
<landing_prefix>/<hospital_id>/<feed_id>/<request_id>/
  ├─ FHIR_R4/fhir/<original-synthea-name>.json
  └─ landing-manifest.json
~~~

Manifest 当前字段：schema_version、hospital_id、feed_id、request_id、source_manifest_sha256、target_format、skipped_non_admissions、objects[]。每个对象记录 blob_key、sha256、size_bytes、source_event_id（FHIR 预期 null）、etag、version_id。**没有可供直接信赖的 READY 布尔字段，也没有直接的 cohort_id**。Manifest 能被读取且验证通过才表示 Publisher 提交完成；不存在即 HOLD（允许孤立但不可消费的已上传 Data Objects）。输入必须是确切 manifest_uri/manifest_key + **其实际 SHA256**，不得根据文件名排序或 Blob List 推断最新可处理批次。

入库业务键候选：source_system = (hospital_id, feed_id, FHIR_R4)，source_batch = request_id，batch_fingerprint = SHA256(规范化 manifest bytes)。同一 request_id + 不同 Manifest/SHA → CONFLICT，绝不作为新批次静默覆写。cohort_id 如需显示须增加**受控版本化扩展合同**或从已核验源 Request 显式传递，不能从文件名猜测，也不允许静默假定当前 Manifest 含此字段。

### 1.2 连接与数据访问（先验证再决策）

**首选验证 Azure Blob Storage → OneLake Lakehouse Files Shortcut（零拷贝读取原始对象）**，不先复制第二份相同 Raw Blob；Fabric Spark 经 Shortcut 使用 OneLake 文件路径读取。此能力有微软官方文档，但在当前 Tenant、所选 Workspace、身份以及 Blob Container 的具体可用性**尚未实测**。必须验证 Connection 类型、最小 Reader RBAC、Workspace/Notebook 身份、授权范围、shortcuts path 和读取实际 bytes；不可把 Writer SP Secret 放进 Notebook 或源代码。

备选：Data Pipeline 的 Copy Activity 将**明确 Manifest 列出的对象**拷贝至 Lakehouse Files staging，然后 Notebook 在 staging 严格校验源与目的 SHA/大小；需要重算成本、物理对象身份与 Copy 的幂等规则。普通 Azure Blob 帐号不可未经核对 HNS 就假定能直接用 ADLS Gen2 的 abfss 源 URI；应使用已支持的 Shortcut/Connection 或受支持的读接口。任何一种模式均不以 Connection 成功代替对象字节已验证。

## 2. Notebook 的边界与处理阶段

参数建议：manifest_uri、manifest_sha256、hospital_id、feed_id、request_id、target_lakehouse、contract_version、execution_mode=validate_only|load、pipeline_run_id。参数由受控 Pipeline 传入并二次校验，禁止任意容器、任意 URI/SQL 路径、对外 URL；不从 Notebook 参数选择未授权 Workspace/付费 Capacity。

**Phase A — preflight（任何持久写之前）**
1. 获取完整 Manifest 原始字节，检查实际 SHA256、schema_version、确切已批准 prefix/container、source identity、target_format=FHIR_R4、FHIR skipped_non_admissions=0，限制对象数/字节规模，拒绝重复键、路径穿越、未知字段及对象列表重复。
2. 对每个 Manifest 对象 HEAD/GET 或 Shortcut 读取**原始字节**，验证长度、SHA256、ETag/Version 可用时的一致性；所选 Spark binaryFile/原始字节读取方法需实机测试，不能使用 read.text 之后重编码来声称 byte-identical。
3. 同批已 COMMITTED + 相同 Manifest/SHA → SKIP 并返回证据；已 COMMITTED + SHA 漂移 → FAIL；部分失败 → 依照版本化、可见性约定恢复，不能无条件重跑。

**Phase B — Bronze（不可变原文）**
- 保存原始 FHIR Bundle 字节或内容哈希与可审计私有路径，以及 hospital_id/feed_id/request_id/object_sha/ingest_run_id/source_manifest_sha；Bronze 保持 append-only/批次版本隔离，禁止以 overwrite 整表覆盖。
- 对小批量多个 Synthea JSON 使用有界并行与明确 Schema 的 Spark 解析，避免 schema inference + 大量 small-file 作长期生产合同。Raw FHIR 允许 bundle 中其它 resourceType，MVP 只解析 Patient/Encounter，不丢弃原文。
- 原文字段可能含姓名、地址等，即使是合成也不发布到公网；进入展示之前独立脱敏白名单。

**Phase C — Silver FHIR → Canonical**
- 必须检查 Bundle.resourceType=Bundle、entry[].resource.resourceType/id、资源键唯一性；为 fullUrl（包括 urn:uuid）和 Patient/id 构建 Bundle 内索引，解析 Encounter.subject.reference = Patient/x、urn:uuid 等真实存在引用；跨文件引用只有获得可验证索引后允许。
- Canonical Patient 首先对齐 Local 合同主键 (source_system, source_record_id) 与 birth_date/gender_code 等；Canonical Encounter 主键 (source_system, source_encounter_id)，对齐 source_person_id、start/end_datetime、encounter_class/source_code，并**保留** Adapter version、source_file/hash、source_batch_id 和源 FHIR 原生 Reference。不得因为 FHIR 无 CSV 里同名字段就凭空填入默认医学语义。
- FHIR gender、race/ethnicity extension、Encounter.class/status/period 到 OMOP Concept 映射是**新 Adapter**，复用 Local 的结构/校验函数思路，而不是复用 CSV 特定映射的结果。未知/缺失必须落 DQ 分类；0/Unknown concept 的用法必须与 OMOP 5.4、当前映射合同逐字段核对，不擅自把空字符串映射成合法值。
- Patient/Encounter Source ID 要用 hospital_id+feed_id 命名空间隔离；禁止不同医院依姓名/出生日期合并患者。未来 crosswalk 是版本化独立映射，不是 MVP 自动去重。

**Phase D — OMOP 候选与持久 ID 映射**
- Silver 可以先落 source-aware canonical；最终 OMOP person/visit_occurrence 使用现有 OMOP 5.4 字段/业务约束和 Local 验收经验，但需要新的 FHIR 专用映射测试。
- FHIR resource.id 是字符串；OMOP person_id/visit_occurrence_id 需要稳定数值 ID。建立受约束 Delta ID-map：(source_system, resource_type, source_record_id) → stable internal/OMOP ID，唯一/冲突检查及明确后续 Update 语义；**不能**假定 hash 截断天然无碰撞或 FHIR ID 是全局唯一。Encounter → Person 的 FK 必须由同一已核验映射得出。
- 首批仅 NEW_ONLY；同源 FHIR 更新、删除、重发的 upsert/correction policy 是显式待决项。未批准前，同一个 source key 的不同 payload hash 应 HOLD，而不是自动改写已验收版本。

**Phase E — Delta 写入、提交可见性、跨表对账（独立 readback verifier 优先）**
- Delta 单表可以提供原子事务/MERGE，但**不要把 person + visit + audit 三个 Delta 表误认为一笔跨表原子提交**。建议将处理结果按 batch_fingerprint / source_record_key 写入版本化 staging（例如 bronze_fhir_bundle_v、silver_fhir_patient_v、silver_fhir_encounter_v、omop_person_candidate_v、omop_visit_candidate_v），并用 _etl_batch_audit 记录 STARTED→VALIDATED→STAGED→RECONCILED→COMMITTED；只有独立读回及外键/数据质量通过后发布终态。
- 提供只消费 **COMMITTED** 版本的 read-only serving views（必要时显式 latest committed 版本），未提交的半成品禁止被视为可用数据。需要进一步审查 ID-map 的幂等并发写法和 read committed view，串行限制相同 Feed/Batch 的竞态；流水线层并发=1 只作为 MVP 的操作约束，不声称获得分布式全局锁。
- 在所有写入前取得当前 manifest 的不可变内容身份；重复提交/两次并发、未知 ACK、同请求新 SHA、临时失败恢复均应有测试。若还未有证明安全的跨表 serving visibility 策略，则仅交付 Bronze/Silver、**不得宣布 OMOP 已 COMMITTED**。
- 读回并对账：manifest object_count / verified bytes；FHIR Bundle Patient/Encounter 资源数、distinct keys、Silver 数、invalid/quarantined 数、OMOP Person/Visit 数、Encounter→Person FK 0 orphan、映射 coverage；最终 reconcile report 含 per-stage hash/rows 和明确不支持的字段。

**Phase F — 可观测性与返回协议**
- 记录 source manifest SHA、hospital/feed/request、Notebook/ Pipeline Run ID、Workspace/Lakehouse、源对象 SHA、contract/adapter Git SHA、表名与最终 Delta 版本、row counts、DQ、readback 证据。
- Notebook Activity Completed 只能证明调度层成功；只有明确返回 business_status=COMMITTED、预定结果 SHA、独立 Delta Readback 成功的三者成立才允许 Pipeline 标记 SUCCESS。真实退出值通道此前未通过测试；采用 Notebook 明确日志+持久审计状态+独立 GET 的二次验证作为最终业务证据，具体 exitValue/Job API 需先完成单独的安全 POC。
- OpenLineage 业务 Dataset 和 Column Facet 需独立验证；Fabric Spark 4.1/Scala 2.13 不得直接加载 Local Scala 2.12 Listener。先让业务入库证据真实可靠，血缘 Adapter 分阶段验证，并记录未捕获的 START-only / RDD lineage gap，不假造 COMPLETE。

## 3. Fabric Pipeline 最小 DAG（MVP）

~~~text
Manual/approved trigger(manifest_uri, sha, source identity)
  → parameter scope check
  → single Notebook Activity: nb_fhir_ingest
       ├─ validate-only OR load
       ├─ preflight/raw/parse/canonical/candidate/reconciliation
       └─ publish committed state only after readback
  → independent verify activity / audit readback
       ├─ actual COMMITTED + validated counts/hash → success evidence
       └─ anything unknown/partial/conflict → explicit FAIL/HOLD
~~~

默认**手工触发或限定 Manifest 的受控 Workflow**；不开放“每当有文件进 Blob 就无条件跑”的自动写入，更不允许 Cloudflare 公网访问者触发付费计算。Pipeline 仅编排与失败处理，不在 Pipeline 表达式中复制 FHIR 字段映射。首版尽量使用 **一个 Spark 会话**节省 Trial 冷启动；何时拆分 Notebook 应基于实际 CU/性能和可观测性，而不是照搬 Airflow 的 Task 数。

推荐源文件未来归属（**此 PR 不建可运行 Item、不编造 .platform logicalId**）：
- azure-fabric/workspaces/healthcare-omop/notebooks/ingestion/nb_fhir_ingest.Notebook/（Fabric 真实 Item 确认后）；可测试纯 Python Adapter 与 Fabric 依赖分离。
- azure-fabric/workspaces/healthcare-omop/pipelines/pl_fhir_ingest.DataPipeline/（真实 pipeline-content.json 和唯一 Item owner）。
- docs/systems 路径仍以现有 documents/systems/azure-fabric/notebooks|pipelines/CODE.md 为导航；未来加/改源码必须同 PR 修改相应 CODE.md。
- 工作空间 Item 部署遵循已采用 fabric-cicd 负责 Notebook/Pipeline，Terraform 只负责既定 Infra/Workspace/Lakehouse/Connection 边界；不能同时由旧 Terraform Notebook/DF Root 与 fabric-cicd 双重管理同一 Item。

## 4. Local DP 经验 → Fabric 保留/优化矩阵

| Local 已验证设计与痛点 | Fabric 必须保留 | 计划优化 |
| --- | --- | --- |
| S3 READY + frozen Manifest、反复读回 | Manifest-last、不变数据身份、字节 Hash、明确批次选择 | 消费现有 Publisher 协议，不再创造第二套 READY 数据源 |
| Airflow NEW_ONLY 显式路由、Claim SKIP | 同 SHA 已提交 SKIP、不同 SHA 冲突、失败恢复 | Pipeline 仅负责调度，批次状态集中于 Delta Audit；减少 DAG/XCom 复杂度 |
| Spark Patient/Visit/Canonical 中间多次物化 | 严格 Adapter/Schema/PK/FK + Reconcile | 一个 Notebook 一次 Spark session 中按逻辑阶段执行，必要时才物化中间结果 |
| PG17 专用 SQL Writer、双 Gate、fencing 与 rollback | 无未授权 Commit、来源冲突阻断、独立读回 | Delta 表内事务 + append-only 版本/最后 commit visibility；**不宣称跨表事务** |
| CSV 特化 Person/Visit 映射 + 18 列 Person Contract | Canonical 合同/OMOP 5.4 字段与语义 | 新增 FHIR Resource parser/Reference Adapter；共享测试规则，不强行复制 CSV 映射 |
| PG source→ID 映射 | 同医院/Feed/Resource stable key + FK | Delta ID-map + 碰撞验证；不让 source id 直接充当 OMOP int |
| Local OpenLineage Spark RDD/START-only gap | Pipeline/Notebook/Entity Run 和 Dataset 证据 | 用真实运行结果与 Audit 产生可核验 lineage，不把 UI 事件视为业务提交 |
| 已记录过 race_code=native 映射缺陷 | 原值、版本化 Concept Map、负向用例 | FHIR 性别/种族/族裔映射单元测试、未知码集中失败分类而非散落代码 |
| Local 一部分脚本/taskNNN 命名遗留 | 组件/Contract 导航与 Git 版本 | 新源码按功能名、不复制 legacy task04 命名；模块可移植性针对 Frozen 输入单测 |

## 5. 数据契约、表建议（均为候选，未创建）

| 层 | 候选表/实体 | 业务键 / 验收 |
| --- | --- | --- |
| Audit | _etl_batch_audit | hospital_id + feed_id + request_id + manifest_sha；保存状态与 run/evidence |
| Bronze | bronze_fhir_bundle_v | source object blob_key + sha256 + batch fingerprint；原文/私有 URI 可回放 |
| Silver | silver_fhir_patient_v | source_system + FHIR Patient.id + committed revision |
| Silver | silver_fhir_encounter_v | source_system + Encounter.id + committed revision，subject FK |
| Mapping | fhir_omop_identity_map | source_system + resourceType + source_record_id → validated numeric OMOP ID |
| OMOP candidate | omop_person_candidate_v | person_id + batch identity + lineage；18 列 Person Contract |
| OMOP candidate | omop_visit_candidate_v | visit_occurrence_id + person_id + batch identity；Visit Contract |
| Serving | committed_person / committed_visit | 只暴露已确认提交的版本、禁止中间不一致状态 |

**命名约束**：上述为逻辑建议，不是已部署表，也不保证单一 Fabric Lakehouse 对任意 schema 命名的物理支持；真实建表、partition/PK 检查和 SQL endpoint 可见性需 Runtime 验收。Delta 不会自动替应用强制传统数据库 FK/唯一约束，Notebook 自己执行这些业务断言。

## 6. 分期交付与验收 Gate

- **G0 Contract/Access**：核验真实 Blob Manifest 样本、确切 Blob URL/Prefix（日志脱敏）、FHIR Bundle 中 entry/resource/id/subject 的真实形状；确定权限与 Shortcut/Copy；不运行 Spark。严格区分 Source Publisher 读回与 Fabric 消费。
- **G1 Offline adapter**：对无 PHI 的冻结合成 FHIR Fixture 做 Patient/Encounter 解析、Reference、同源重复/冲突、缺字段/缺扩展、错误 Concept、哈希、幂等；复用 Local Canonical/OMOP 规范；静态/单测 PASS。
- **G2 Fabric pure smoke**：解决之前 Notebook Create/GetDefinition 的 LRO 和输出不可核验问题；新一轮试验须用户重新批准，不能延续已用尽的三轮自动重试。验证正确发布 Notebook 源 SHA、参数回传、真实输出/退出状态；仅免费受控范围。
- **G3 Bronze**：选 5–10 个新合成 Patient 的新 Request，真实 Blob GET/Shortcut byte-hash 与 Bronze 只写入隔离表；独立数/hash 读回，同 Request rerun SKIP。
- **G4 Silver**：扩到新 100 人 Source Manifest；有效 Patient/Encounter 可全部解析，FK=0 orphan，异常资源隔离留痕，canonical/schema contract PASS；按确定性来源去重，不与 Local patient 直接合并。
- **G5 OMOP / Delta**：稳定 ID-map、Person/Visit 候选、Commit Visibility、多表部分失败可见性保护、独立读回，原始行数→成功行数/错误行数对账；同批 SKIP、冲突 HOLD、并行/未知 ACK 恢复。
- **G6 Pipeline+Lineage**：真实 Pipeline→Notebook 参数/终态与 Audit 绑定，成功/失败/超时都可区分；按实际 Delta dataset 完成 lineage/证据展示，不阻塞已经正确的业务结果验收。
- **G7 Cost/Rollback**：记录每 Run 启动时间、CU、Blob read/Copy 行为、表 Delta 版本、部署 Commit SHA；仅在通过 Safe Operations + Session Coordination 与明确批准后部署。清理只允许明确归属的本轮隔离临时对象，绝不删除历史 Local PG、Blob 或其他 Agent 资源。

通用负向测试：Manifest 缺失/被篡改、相同 request_id 不同 SHA、Blob ETag/sha 漂移、非法 path、非 FHIR 格式、FHIR Bundle 重复 resource id、Encounter 缺 Patient、未知 Concept、重复/并发 Pipeline、partial Delta 表写入、连接/RBAC 失败、Notebook Completed 但无业务 readback、Job 超时、Workspace/Lakehouse 绑定错误。每项应明确 FAIL/HOLD vs expected SKIP，不能仅凭 Pipeline 绿色宣布数据业务成功。

## 7. 本轮需要用户决策（正式实现前）

1. **入库终点**：本轮直接完成 OMOP 5.4 Person + Visit Delta Gold，还是先 Bronze/Silver（推荐 G0–G4 达成后再开受控 OMOP G5）？两条都可在一个 Change 下分阶段。
2. **Blob 接入**：先试 Shortcut 零拷贝（首选），还是 Copy Activity 显式复制到 Files（更容易留冻结副本，但增加开销）？
3. **数据更新模式**：当前 NEW_ONLY（建议 MVP）还是包含同源 Patient/Encounter Update/修正？后者需变更已有幂等/ID-map 合同，不能默认开启。
4. **ID/跨来源**：FHIR 与 Local OMOP 初期完全保留独立 Person ID（建议），或采用版本化已有 crosswalk 的专门联合视图？未经真实 crosswalk 不能合并。
5. **Fabric 实机继续**：旧兼容性 POC 已按三轮失败规则 HOLD；要先独立解决 Notebook 定义读回/退出返回，还是直接进行严格隔离的新调度测试？两者都需用户逐项授权。

## 8. 当前完成度与回退

本次仅 **设计初稿、代码/合同静态检查、独立分支**。未新增业务 Notebook/Pipeline、改写 OpenSpec Current Specs、创建 Delta 表、执行 Azure/K8s/PG Writes、跑第五轮 Fabric 实验或启用 paid capacity。讨论后如方案变更，继续修改本 Draft 与关联 Change；若否决，关闭 Draft PR/删本独立分支即可，业务 Runtime 无需回退。
