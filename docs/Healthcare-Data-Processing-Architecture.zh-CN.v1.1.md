# Healthcare Data Platform — 数据处理架构与开发规范

> **文档状态：V1.1 — Healthcare 专用开发基线（目标目录 V2，尚待实施）**  
> **制定日期：2026-10-07**  
> **适用范围：** Kubernetes + SeaweedFS（S3 API）+ Spark/PySpark + Airflow + PostgreSQL OMOP CDM；未来可映射到 OneLake / Microsoft Fabric。  
> **主要用途：** 统一医疗数据接入契约、目录、格式校验、作业边界、质量门禁、幂等、审计与编排规则，作为后续代码开发、PR 审查、运行手册和架构说明的共同依据。
> **版本修订：** V1.1 取消跨行业零售示例，改为 Synthea + 模拟医院 Epic FHIR Bulk 交付；明确医疗格式规范、文件名策略与来源注册表；不会照搬任何企业内部流程。

## 0. 文档约定与设计边界

- 本文中的 **MUST / 必须** 表示新开发的强制约束；**SHOULD / 应当** 表示默认推荐，若偏离须在设计评审中说明。
- 所有 `s3://...` 均为**对象键设计示例**，并非断言对象已经存在。Spark 使用 `s3a://...` 访问同一对象存储。
- `2026-10-07`、示例 batch/run ID 仅用于说明；真实作业必须由接入/编排程序生成与校验，**不得写死日期、批次或 113 行**。
- 本文重点是**数据流与开发契约**，不是集群 Helm/Kubernetes 逐条部署手册。
- 全部数据流例子均属**医疗行业**；Synthea 样例基于本项目已验证的合成数据；医院 Epic 示例为**虚构接口合同和合成数据**，不表示 Epic 产品或某医院实际采用该文件结构。
- 本设计独立于任何公司的内部组件名与实现；采用业界通用的 intake / adapter / quality gate / canonical / product / audit 作为设计概念，并按医疗数据特点自行定义契约。
- **已实现**与**目标设计**严格区分：当前 `person` 流程已跑通；以下新目录、新 processing 工作区、通用 Canonical Contract、审计等尚需迁移/开发。

## 1. 架构目标与不变原则

1. **接入与用途解耦。** Source Adapter 处理源系统差异；下游 OMOP Mapper 只依赖稳定的 Canonical Contract，不读取源系统特有文件布局。上游交付可为文件、FHIR API 导出或 HL7 消息流，不能把所有数据源都假设成手工上传 CSV。
2. **Landing 原样保留。** 进入 Landing 的源 payload 不被业务转换修改；新增 `manifest.json` 是平台控制元数据，不修改源文件。
3. **按交付/批次追踪、按运行隔离。** `batch_id` 由接入平台分配或校验（可关联上游交付 ID），`run_id` 标识一次 ETL 运行；同批次可以有多个重跑，不得覆盖原文件或历史中间结果。
4. **先验收后发布。** 解析、映射或 DQ 失败的数据进入隔离/待处理，不得被误认为已发布的 Canonical 或 Product 数据。
5. **可恢复且幂等。** 同一批次、相同输入重复运行，不生成新的业务身份或重复加载 CDM；重新处理使用新的 `run_id` 并留下记录。
6. **完整可追溯。** 最终记录可追溯到输入 batch、源对象 key/校验和、代码版本、mapping 版本、运行与质量结果。
7. **安全边界清晰。** 可能解密出的明文仅放受限的临时 Processing 工作区；不得出现在 Git、普通日志或公共分析产品中。
8. **目录不是数据质量/状态数据库。** 状态、批准版本、任务历史使用 manifest + 控制表/审计事件管理，不能只靠对象是否存在来判断成功。

## 2. 全链路与组件职责

```mermaid
flowchart TD
    S[Source systems / files / APIs] --> L[Landing: immutable source payload]
    L --> I[Intake & routing: match / hold / reject]
    I -->|matched| P[Processing: isolated job workspace]
    I -->|hold or reject| Q[Status / error record]
    P --> A[Source adapter: decrypt, parse, normalize]
    A --> G{Canonical DQ gate}
    G -->|fail| Q
    G -->|pass| R[Raw: canonical entities]
    R --> K[Identity linking / stable IDs, optional resolution]
    K --> M[Product mapper: OMOP / research / ML]
    M --> H{Product DQ gate}
    H -->|fail| Q
    H -->|pass| D[Processed: approved product run]
    D --> T[PostgreSQL ETL stage]
    T --> U[Transactional UPSERT / MERGE]
    U --> C[OMOP CDM serving]
    C --> O[Reconciliation / operational metrics]
    I -.-> J[Append-only audit journal]
    G -.-> J
    H -.-> J
    U -.-> J
    O -.-> J
```

| 组件/层 | 职责 | 不应承担的职责 |
|---|---|---|
| **Landing** (`health-landing`) | 接收、校验哈希、保留源文件和交付元数据 | 将 Epic/Synthea 强行改成统一字段 |
| **Intake / Routing** | 根据已注册医疗接口、传输通道、格式、契约版本、资源类型及内容校验选择 Adapter；匹配/待处理/拒绝 | 强迫所有医院按同一个文件名命名；只靠扩展名猜临床含义 |
| **Processing** (`health-processing`) | 每次运行独立工作目录；解密、解析、临时产物、拒绝记录、DQ 报告 | 作为永久的 Canonical 或最终产品区 |
| **Source Adapter** | 按具体已注册接口解析 Synthea CSV、FHIR JSON/NDJSON、HL7 v2 等，处理 profile/编码/字段语义并映射到 Canonical Schema | 把厂商名称当格式标准；直接依赖 `cdm.person` 的最终表设计 |
| **Canonical DQ Gate** | 格式、Schema、必填、唯一性、引用与异常比例检查；放行/隔离 | 仅打印 PASS 而仍发布失败数据 |
| **Raw** (`health-raw`) | 保存**已通过门禁的 Canonical Parquet**，保留 lineage | 再保留源私有列名作为全局契约 |
| **Identity / Stable ID** | 稳定将源身份键映射到平台实体键；跨源合并身份为独立可选能力 | 把每次 Spark 行号当作稳定主键 |
| **Product Mapper** | Canonical → OMOP / research / analytics / ML 等用途转换 | 针对不同来源重新解析原始 CSV/HL7 |
| **Product DQ Gate** | 校验目标 Schema、术语 concept、关系、行数与产品约束 | 使用未经批准的输出供服务端读取 |
| **Processed** (`health-processed`) | 保存目标产品版本和每次成功运行的不可变数据快照/增量 | 用源系统作为顶层产品目录；把历史 run 全量一并读取 |
| **Serving** (PostgreSQL `etl` → `cdm`) | Stage、事务性 UPSERT、约束检查、查询服务 | 将 Spark `append` 直接当作幂等加载 |
| **Journal / Recon / OpIntel** | 审计事件、行数与校验和对账、指标、告警、运行状态 | 保存原始患者敏感明文或密码 |
| **Airflow** | 依赖、并行、重试、参数传递、任务状态和门禁执行 | 替代 Spark 进行大规模解析转换 |

**注意术语：** 本项目的 `health-raw` 是 **Canonical Raw（结构已标准化）**，不是未经处理的源文件；未经处理的原文属于 `health-landing`。

### 2.1 医疗行业数据格式：优先遵守现有标准，而非自创统一文件名

本平台采用**两层契约**，二者不可混淆：

1. **行业数据/消息标准**：FHIR R4（可附 US Core 或其他 IG/Profile）、FHIR Bulk Data（NDJSON + export manifest）、HL7 v2（按消息类型/版本/接口指南）、C-CDA（XML）、以及经医院双方确认的 CSV/数据库抽取规范。标准定义数据内容与交换语义，**不统一要求所有医院把文件命名为 `patients.csv`**。
2. **平台接入契约（Intake Contract）**：定义来源身份、接口 ID、版本、传输、批次/文件清单、校验和、数据类型、隐私处理与 Adapter。这是**我们自己定义并可执行的接入标准**，不冒充 HL7 官方标准。

| 输入方式 | 内容应该符合什么 | 原始名称/交付方式 | 平台如何确定类型 |
|---|---|---|---|
| Synthea CSV | 与固定 Synthea exporter 版本及配置相符的 CSV 字典 | 例如 `patients.csv`、`encounters.csv` | 注册的 Synthea 适配器 + CSV header/Schema |
| FHIR R4 REST/Bundle | FHIR Resource/Bundle、约定的 Profiles/IG | API 响应内容、JSON Bundle；可能没有源文件名 | endpoint + `resourceType` + profile 验证 |
| FHIR Bulk Data | Bulk Data IG；导出清单引用的 NDJSON 资源文件 | `Patient-001.ndjson` 等**示例名，并非标准规定名称** | 原生 export manifest 的 `output[].type` + 资源逐行验证 |
| HL7 v2 | 指定消息版本、事件类型、接口实现指南 | MLLP 消息流或双方约定的文件包；未必有文件名 | `MSH` 头、消息类型/版本 + segment/字段规则 |
| C-CDA / XML | 与约定 CDA 模板和实现指南一致 | XML 文档，名称由发送方确定 | 文档头、templateId 和 XML 校验 |
| 自定义 CSV/加密包 | 双方确认的 schema + 版本 + 编码/分隔符 + 加密约定 | 任意原始名称；可附 GPG/PGP 加密 | source registry + 声明格式 + 实际解析验证 |

**原则：格式合规要求严格，原始文件命名默认宽松。** 只在某条来源接口合同显式规定 `filename_pattern` 的情况下，才对该接口启用文件名匹配检查。`*.csv`、`*.json`、`*.ndjson`、`*.pgp` 只能作为线索，绝不能替代数据实际校验。

FHIR 官方验证支持结构、cardinality、terminology binding 与 profile 检查；FHIR Bulk Data 规定 NDJSON 输出和 `output[]` 文件清单；HL7 v2 允许本地定义的 `Z` segments。**因此版本 + Profile/Implementation Guide + source-specific contract 是必要的**，不是只记录厂商名。[参考标准见第 15 章](#15-医疗行业标准依据与设计取舍)。

### 2.2 文件命名策略：不要求医院改名，但平台接入必须可追溯

默认采用 `filename_policy = preserve`：

- **保留原始相对路径、文件名和字节**到 Landing 的 `payload/`，不根据猜测自动改名。
- 平台统一生成 `source` / `source_version` / `ingest_date` / `batch_id` 等 **S3 外壳路径**以及 `manifest.json`。医院不需要自己按该路径上传，也不必须提供我们的 manifest。
- SFTP、API、消息流由 Intake Connector 接入后**生成/补全平台 manifest**；如果上游已有 FHIR Bulk export manifest，保留为 *source manifest*，另外产生我们的平台 manifest，不能混为一谈。
- 一个传入文件可包含多个实体，多份文件可形成一个实体，故不假设 `filename = entity`。
- 上传目标 key 冲突时，通过 `batch_id` / 唯一交付标识与 checksum 判断重复、冲突或新批次；原文件名相同不是错误。
- 对于未登记格式、无法认证来源、不支持的 Profile/版本、内容冲突：**先 ON_HOLD/REJECT，不边猜边强制转换**。

当医院确实愿意与我们签订固定文件命名/打包协议，可以配置 `filename_policy = contract_pattern`，但它只影响这一条接口，不影响平台其他医院；**核心兼容逻辑始终依赖内容与契约，而非文件名**。

## 3. S3 Bucket 与物理目录规范（目标 V2）

### 3.1 Bucket 清单

| Bucket | 内容与保留策略 |
|---|---|
| `health-landing` | 已接收的源 payload + landing manifest；默认不可覆盖（逻辑不可变） |
| `health-processing` | **新增目标 Bucket**；运行级临时/隔离区，限制访问并设置生命周期清理策略 |
| `health-raw` | 已发布的 Canonical 实体数据，按 source batch 保存 |
| `health-processed` | OMOP 等数据产品的运行结果，按产品/版本/dataset/run 保存 |
| `health-archive` | 长期保存的审计事件、保留期到达后的归档、批准后的历史交付记录（具体生命周期另定） |
| `postgres-backup` | 数据库备份；**不属于业务数据的 ETL 层级** |

> 创建 `health-processing` 之前，先验证访问控制、空间、清理规则；**不得把当前已经跑通的旧路径直接删掉**。

### 3.2 Landing：固定接入外壳，自由 payload

```text
s3://health-landing/
└── source=<logical_source>/
    └── source_version=<interface_version>/
        └── ingest_date=<YYYY-MM-DD>/
            └── batch_id=<batch_id>/
                ├── manifest.json
                └── payload/
                    └── <source-provided relative paths and filenames>
```

**约束：**

- `source` 是**平台 source registry 中的唯一逻辑接入源 ID**（医院/部署实例/接口共同确定），不能仅使用厂商名 `epic` 混淆多个医院；例如 `hospital_a_epic_fhir_bulk`、`hospital_b_epic_hl7_adt`。可用 `source_instance`、`interface_id` 字段明确标识。
- `source_version` 是平台注册的**接口契约版本标签**，不一定等于 Epic 软件版本，也不等于 FHIR R4 或 US Core 版本。FHIR 的 `fhir_version`、`implementation_guide`、`profiles`，HL7 的 `message_version` / `message_type` 在 manifest/registry 中分别记录，必要时将源契约标签指向固定组合。
- `ingest_date` 是该批**首次接收日期（UTC 日期）**，不能被重跑日期替换。
- `batch_id` 是同一逻辑来源内可唯一识别的接收批次；**同一 batch_id、不同内容/哈希不可静默覆盖**。批次 ID 应避免路径分隔符与不安全字符。
- 只在 `payload/` 内保留源系统原始组织结构：Synthea 的 `csv/*.csv`、Epic 自定义 extract、FHIR Bundle JSON、HL7 `.hl7` 或 PGP 加密文件均可。
- 原始文件同名完全允许，只要完整对象 key 不冲突。真实重复投递用 manifest/校验和识别。
- `manifest.json` 由接入平台生成/补充，是**平台控制文件**，不要求发送医院按我们的 JSON 规范提交；`payload/` 保持原样。对于已有 FHIR Bulk 导出 manifest，它是**源协议输出**，须分别保存/引用。大型批次可引用外部完整文件清单。

### 3.3 Processing：按源批次和运行分隔的隔离工作区

```text
s3://health-processing/
└── source=<logical_source>/
    └── source_version=<interface_version>/
        └── ingest_date=<YYYY-MM-DD>/
            └── batch_id=<batch_id>/
                └── entity=<canonical_entity>/
                    └── run_id=<safe_run_id>/
                        ├── job_request.json
                        ├── work/
                        │   ├── decrypted/       # 仅加密输入需要，严格限制/及时清理
                        │   ├── parsed/          # 临时解析结果（可选）
                        │   └── normalized/      # 待发布 Canonical 数据
                        ├── rejects/             # 错误记录或引用（避免泄露 PII）
                        ├── dq/
                        │   └── result.json
                        ├── next_stage_request.json  # 成功后下游任务请求（可选）
                        └── run_manifest.json
```

- Processing 中间产物是**运行级**，多个重试/回放使用不同 `run_id`；同一次 Spark task 的内部重试应避免写到其他运行目录。
- `job_request.json` 是**本次运行的输入请求/执行参数**，由路由/编排阶段写入；处理成功后的下游交接可以另写 `next_stage_request.json`。不要把二者混作同一个含义。
- `work/normalized/` 只有通过 DQ 后才能复制/发布到 Raw。Spark 临时文件的 `_SUCCESS` 仅说明某次写文件成功，**不等同 DQ PASS**。
- 如果接口约定 PGP 加密，解密后应按真实内容识别格式，例如某个 `.ndjson.pgp` 文件内容确为 NDJSON 时可在受限工作区以 `.ndjson` 处理；文件后缀不是解密成功或 Schema 合规的证据。
- `decrypted/` 和 `rejects/` 应严格控制权限、保留期、日志输出；生产数据要求传输/静态加密并遵循机构合规要求。

### 3.4 Raw：统一 Canonical Schema、保留来源血缘

```text
s3://health-raw/
└── canonical_version=<version>/
    └── entity=<canonical_entity>/
        └── source=<logical_source>/
            └── source_version=<interface_version>/
                └── ingest_date=<YYYY-MM-DD>/
                    └── batch_id=<batch_id>/
                        ├── manifest.json
                        └── data/
                            ├── part-00000-....snappy.parquet
                            └── _SUCCESS
```

- **Entity 优先**：例如 `patient`、`encounter`、`condition`、`procedure`、`medication`、`observation`。名称必须由 Canonical Schema Registry 定义，不从源文件名直接推断。
- **Raw = Canonical**：相同 `canonical_version` + `entity` 的字段名、类型、业务含义、空值/编码规则必须一致，无论数据来自哪里。
- Source、版本、批次仍保留在路径和记录 lineage 中，不代表 Raw Schema 继续依赖源系统。
- 一个源文件可以拆到多个 Canonical Entity；多个源文件也可以合成为一个 Entity。不要假设文件到表是一对一。
- 业务主键至少包含**逻辑来源 + 源实体主键**的作用域；不同医院重复的 MRN、FHIR `Patient.id` 不应被误合并。
- `canonical_version` 只表达内部数据契约版本，独立于 `source_version` 和 OMOP 版本。
- **对象布局注意：** 读取 Parquet 只指向 `.../data/`；`manifest.json` 放在上一层，避免 Spark 在读取整个前缀时误扫控制文件。`_SUCCESS` 是 Spark 写在 `data/` 内的提交标记。
- 发布策略：优先写 Processing 临时前缀、校验并门禁 PASS 后再复制/发布到新的不可变 Raw batch 路径；不能在消费者可读的 Raw 路径上进行部分覆盖。

Canonical `patient` v1 的**示意字段**（真正字段清单与类型须单独登记和测试）：

```text
source_system, source_instance, interface_id, source_record_id, source_batch_id,
birth_date, death_date, gender_code, gender_code_system,
race_code, race_code_system, ethnicity_code, ethnicity_code_system,
address_line, city, state, postal_code, latitude, longitude,
source_payload_ref, ingested_at, canonical_version, ...
```

> 此处仅是实体方向示例，不是已经批准的逐字段 Canonical schema。**不同来源的代码值必须连同 code system / identifier system 等语义信息处理**，不能假设原字符串相同就表示相同概念。FHIR 的多个 identifier、extensions、编码版本可能需要子实体/扩展字段；不能为了简单 schema 静默丢失必要信息。姓名/SSN 等直接标识字段必须最小化并单独定义权限与脱敏策略。

### 3.5 Processed：按产品/模型发布，不把 source 写死在顶层

```text
s3://health-processed/
└── product=<product_name>/
    └── product_version=<version>/
        └── dataset=<target_dataset>/
            └── processing_date=<YYYY-MM-DD>/
                └── run_id=<safe_run_id>/
                    ├── manifest.json
                    └── data/
                        ├── part-00000-....snappy.parquet
                        └── _SUCCESS
```

- `product=omop` 可包含 `dataset=person`、`visit_occurrence`、`condition_occurrence`、`drug_exposure`、`procedure_occurrence`、`measurement` 等。
- 以后还可有 `product=research`、`product=ml_features`、`product=analytics`；**Processed 不局限于 OMOP**。
- `product_version=5.4.3` 对 OMOP 指 **OMOP CDM 目标 Schema 版本**；Mapper/业务规则版本另记 `mapping_version`。
- `processing_date` 为作业运行的 UTC 日期；`run_id` 表示本次产品输出，可关联 Airflow DAG Run ID（必要时编码为路径安全字符串）。
- 一个 Processed run 可引用多个 source batch，输入清单必须写入 manifest；如果同时整合多个来源，**身份匹配策略必须明确**。
- 每个 `run_id` 目录原则上不可覆盖。**消费端不得递归读取所有历史 run 的 Parquet**，否则会重复数据；应通过已批准的 `published_run_id`/catalog 指针或数据库加载控制表选择输入。
- `manifest` 必须表明本次产物是 **snapshot** 还是 **incremental/change set**，以及下游适用的加载方式与水位线。不要默认每一个 run 都是一张完整表。

### 3.6 Archive 与 Journal 目录

```text
s3://health-archive/
└── journal/
    └── event_date=<YYYY-MM-DD>/
        └── run_id=<safe_run_id>/
            └── event_id=<unique_event_id>.json
```

每个审计事件只新增对象，不修改既有事件。对象存储的真正 WORM / Object Lock、版本化及法定保留能力需要**单独验证和配置**，不能因为目录名叫 `journal` 就声称具备物理不可篡改性。

## 4. 三种 ID、三个版本、两种时间

| 名称 | 定义 | 生成方/生命周期 | 典型用途 |
|---|---|---|---|
| `batch_id` | 平台标识的逻辑接收批次，必要时与上游 delivery/export ID 关联 | 接入平台分配/验证；重跑保持不变 | 去重、补数、输入定位 |
| `run_id` | 一次具体 ETL 执行/尝试的 ID | 编排平台；新尝试产生新值 | 工作目录、日志、重试、产品版本 |
| `source_record_id` | 来源内部记录标识（例如 FHIR resource ID、HL7 消息控制 ID、Synthea UUID） | 上游系统；与 source scope / identifier system 组合使用 | 源记录关联与稳定键 |
| `source_instance` / `interface_id` | 医院部署实例与接口通道标识 | 平台来源注册表 | 识别同厂商不同医院、格式与接入配置 |
| `upstream_delivery_id` | 上游传输任务、FHIR export 请求或消息交付标识（可选） | 上游或 Connector | 幂等与交付级对账 |
| `source_version` | 注册的源接口契约版本（独立于标准版本） | 数据源注册表 | 选择 Adapter/格式规范与策略 |
| `canonical_version` | 本平台统一实体 Schema 版本 | Canonical Contract | Source Adapter 输出、下游输入 |
| `product_version` | 目标数据产品 Schema 版本 | Product Contract，如 OMOP CDM 5.4.3 | 下游兼容性 |
| `ingest_date/time` | 平台首次接收到该批的时间 | Intake | 到达延迟、批次归档 |
| `event_time/date` | 业务记录实际发生时间 | 源数据，经过语义解析 | 业务窗口与事件分析 |
| `processing_time/date` | 本次流水线执行时间 | Airflow/作业运行 | run 追踪和运行指标 |

**主键与幂等：** `etl.person_id_map` 当前使用 `(source_system, source_person_id)` 唯一定位 Synthea person。多医院/多接口接入时，`source_system` 必须是足够唯一的**逻辑来源标识**，或扩展为 `(source_instance, source_person_id)` 等复合键。**稳定 ID 映射不等于跨系统同一患者识别**；跨源身份解析是独立的可选阶段，需明确匹配策略、质量阈值和人工复核机制。

## 5. Manifest / Job Request / DQ 的最小契约

以下为**建议的最小 v1 JSON 契约**；真正上线之前，应落地 JSON Schema、字段校验、示例数据与测试。时间统一使用带 `Z` 的 UTC ISO 8601。

### 5.1 Landing `manifest.json` 示例（平台生成，Synthea）

以下 JSON 只列出两条文件项，`file_inventory_complete=false` 表示**为了展示而省略其余项**。正式落地要有完整文件清单和计算出的 sha256；`<...>` 是文档占位符，不是有效生产值。

```json
{
  "manifest_version": "1.1",
  "source": "synthea",
  "source_instance": "synthea_lab",
  "interface_id": "synthea_csv_export",
  "source_version": "synthea-3.3.0-csv-v1",
  "upstream_format_version": "v3.3.0",
  "batch_id": "synthea-20261005-pop100-atlanta",
  "upstream_delivery_id": null,
  "ingested_at": "2026-10-07T20:00:00Z",
  "transport": "local_generator_to_s3",
  "payload_format": "text/csv",
  "filename_policy": "preserve",
  "delivery_type": "batch",
  "source_parameters": {
    "seed": 20261005,
    "population": 100,
    "state": "Georgia",
    "city": "Atlanta"
  },
  "files": [
    {
      "path": "payload/csv/patients.csv",
      "original_filename": "patients.csv",
      "entity_hint": "patient",
      "sha256": "<computed-sha256>",
      "size_bytes": "<computed-integer>"
    },
    {
      "path": "payload/csv/encounters.csv",
      "original_filename": "encounters.csv",
      "entity_hint": "encounter",
      "sha256": "<computed-sha256>",
      "size_bytes": "<computed-integer>"
    }
  ],
  "file_inventory_complete": false
}
```

**关键**：`entity_hint` 是平台注册 Adapter 的推断/配置结果，**不是行业标准强制的文件名字段**。收到上游文件时，由 Connector 建立文件清单，校验成功后可登记完整 manifest。记录 `original_filename` 可以支持源端沟通与错误定位。

### 5.2 Processing `job_request.json` 示例

```json
{
  "job_contract_version": "1.0",
  "run_id": "patient-20261007T201000Z-001",
  "batch_id": "synthea-20261005-pop100-atlanta",
  "source": "synthea",
  "entity": "patient",
  "adapter": "synthea_patient",
  "adapter_version": "v1",
  "canonical_version": "v1",
  "input_manifest_uri": "s3://health-landing/source=synthea/source_version=synthea-3.3.0-csv-v1/ingest_date=2026-10-07/batch_id=synthea-20261005-pop100-atlanta/manifest.json",
  "input_payload_uri": "s3://health-landing/source=synthea/source_version=synthea-3.3.0-csv-v1/ingest_date=2026-10-07/batch_id=synthea-20261005-pop100-atlanta/payload/csv/patients.csv",
  "requested_action": "normalize_and_validate",
  "requested_at": "2026-10-07T20:10:00Z"
}
```

**注意：** 这里的 URI 由 Intake 按 manifest 解析/生成；不能把固定日期和 Synthea 文件路径硬编码进可复用 DAG。

### 5.3 `dq/result.json` 示例

```json
{
  "run_id": "patient-20261007T201000Z-001",
  "entity": "patient",
  "gate": "canonical_admission",
  "status": "PASS",
  "checks": {
    "input_checksum": "PASS",
    "schema": "PASS",
    "required_fields": "PASS",
    "primary_key_uniqueness": "PASS",
    "type_cast": "PASS"
  },
  "input_rows": 113,
  "accepted_rows": 113,
  "rejected_rows": 0,
  "checked_at": "2026-10-07T20:13:00Z"
}
```

真实检查项与严重级别须由 Entity/Product Contract 指定。例如不存在的 concept、错误的 patient 外键为阻断项；其他低风险异常可采用经批准阈值的 `WARN`，不能静默跳过。

### 5.4 Processed `manifest.json` 示例

```json
{
  "manifest_version": "1.0",
  "product": "omop",
  "product_version": "5.4.3",
  "dataset": "person",
  "run_id": "person-20261007T202000Z-001",
  "processing_date": "2026-10-07",
  "canonical_version": "v1",
  "mapping_version": "person-map-v1",
  "load_semantics": "incremental_upsert",
  "inputs": [
    {
      "source": "synthea",
      "batch_id": "synthea-20261005-pop100-atlanta",
      "entity": "patient",
      "raw_manifest_uri": "s3://health-raw/canonical_version=v1/entity=patient/source=synthea/source_version=synthea-3.3.0-csv-v1/ingest_date=2026-10-07/batch_id=synthea-20261005-pop100-atlanta/manifest.json"
    }
  ],
  "output_rows": 113,
  "dq_status": "PASS",
  "status": "APPROVED",
  "code_revision": "<git-commit-sha>"
}
```

`APPROVED` 是经 Product Gate 和发布控制确认后的状态，**不是只要 Spark 写出 `_SUCCESS` 就自动批准**。上线时 `code_revision` 必须是真实 Git commit。

### 5.5 来源注册表（Source Registry / Interface Contract）

**平台应该强制注册接口契约，而不是强制所有合作医院统一文件名。** 一家医院可以注册多个通道；同一个厂商的不同医院仍是不同 source。推荐使用 Git 版本化注册配置（真实密钥不入 Git）：

```yaml
# 示例：lab Synthea CSV contract，不是要求外部医院按此命名文件
source_id: synthea
source_instance: synthea_lab
interface_id: synthea_csv_export
contract_version: synthea-3.3.0-csv-v1
transport: generated_batch
payload_format: text/csv
filename_policy: preserve
adapter: synthea_csv_v3_3
schema_contract: contracts/sources/synthea/v3.3.0/
accepted_entities: [patient, encounter, condition, medication, procedure, observation]
requires_sender_manifest: false
require_platform_manifest: true
validation:
  require_checksum: true
  reject_unregistered_schema: true
  check_source_record_keys: true
```

另一个医院 FHIR 接口的**假设性合同**：

```yaml
source_id: hospital_a_epic_fhir_bulk
source_instance: hospital_a_epic_prod
interface_id: fhir_bulk_export
contract_version: hospital-a-fhir-r4-v1
transport: fhir_bulk_api
payload_format: application/fhir+ndjson
filename_policy: preserve
adapter: fhir_r4_bulk
fhir_version: 4.0.1
implementation_guides:  # 根据与医院实际协商的支持范围填写
  - "http://hl7.org/fhir/us/core/ImplementationGuide/hl7.fhir.us.core"
require_source_export_manifest: true
require_platform_manifest: true
accepted_resource_types: [Patient, Encounter, Condition, Observation]
validation:
  validate_fhir_structure: true
  validate_applicable_profiles: true
  validate_resource_references: true
  require_checksum: true
```

**不宣称该接口已在 Epic 实机验证**。这里的 `implementation_guides` 仅演示如何登记约定的 IG，实施时须固定准确版本和适用 Profile，不应无条件要求所有 FHIR 资源都满足某个 US Core Profile。发送方不提供我们的 platform manifest 也能接入：Connector 可以根据认证来源、实际内容和下载成功清单自行建立。

| 配置策略 | 含义 | 默认 |
|---|---|---|
| `filename_policy: preserve` | 保留原始文件名与子目录，不要求统一命名 | **推荐** |
| `filename_policy: contract_pattern` | 仅对特定接口按双方协商的命名正则额外检查 | 可选 |
| `require_platform_manifest` | 接入平台保存可追踪的文件与批次 metadata | **必须** |
| `requires_sender_manifest` | 需要供应方另提供专属清单 | 默认否，除非协议规定 |
| 内容/Schema/Profile 验证 | 按真实格式和约定 profile 校验 | **必须** |

## 6. 路由、失败状态、质量门禁和发布协议

### 6.1 Intake 路由状态

| 状态 | 触发条件示例 | 处理方式 |
|---|---|---|
| `MATCHED` | 来源、接口版本、payload 类型与已注册 Adapter 匹配 | 创建 job_request，进入 Processing |
| `ON_HOLD` | 未支持的接口版本、缺少交付清单、等待授权/人工判定 | 保留原文件，阻止进入 Raw；补配置后重试 |
| `REJECTED` / `ERROR` | 校验和错误、损坏文件、恶意/不允许内容、必需元数据冲突 | 隔离、写错误事件，不能静默改写源文件 |

**路由优先级：** 已认证的发送通道/来源注册表 → 声明的接口/格式/版本 → 批次/来源 manifest → 实际 payload 解析和 Schema/Profile 校验。文件名正则仅在指定接口合同启用，不能仅靠扩展名或文件名称证明合规。HL7 v2 应解析 `MSH`；FHIR JSON/NDJSON 应检查 `resourceType`、结构和适用的 Profile；CSV 应用源版本 schema/header 检查。

### 6.2 两级 Quality Gate

1. **Canonical Gate**：Processing → Raw 前，检查源契约、解析、字段类型、必填、源主键重复、引用完整性、拒绝量/比例。失败则 Raw **不发布**。
2. **Product Gate**：Canonical → Processed/Serving 前，检查 OMOP 字段类型、必填、标准术语 concept、稳定 ID、业务域/关系映射、重复键、输出行数与 recon。失败则 Processed **不批准、Serving 不加载**。

**最小发布协议：**

```text
create isolated run → write temporary output → validate DQ
→ finalize data prefix and manifest → register approved run
→ allow downstream consume → append audit event
```

需要明确无原子重命名的 S3 存储语义：对象批量复制不天然原子。发布时以**先完成内容、后登记批准 run**作为读者可见性边界；下游必须只消费登记为批准的运行，而不是对 bucket 递归扫描。

### 6.3 幂等与恢复规则

- 同一个 `(source, batch_id, payload checksum)` 再投递应识别为重复；同 key 不同 checksum 必须报冲突或生成新批次，不能覆盖。
- 每次重新执行都创建新的 `run_id`，并引用相同的 `batch_id`；同一批下历史运行可查。
- Raw batch 输出确定性/逻辑唯一；再次发布必须先比对内容与元数据。不能覆盖一个已获批准的不同结果。
- `etl.person_id_map` / `etl.visit_occurrence_id_map` 类表必须使用稳定、带来源作用域的唯一键；禁止 `row_number()` 为重新运行的数据随机换主键。
- Spark JDBC → **独立 Stage** → PostgreSQL 事务 UPSERT；禁止直接盲目 append 目标 CDM。
- Stage 必须按批/运行隔离或串行清空使用；当前单表 `TRUNCATE etl.person_stage` **仅适用于串行 Lab**，有并发 DAG 时必须切换为 `run_id`-scoped stage/锁机制，避免并发互相清空。
- `snapshot` 与 `incremental` 产物的 recon 与回滚方式不同，必须在 manifest 中声明，不得简单把某个 run 的行数当成全表最终总数。

## 7. 稳定身份与可选 Entity Resolution

当前单来源已实现：

```text
Synthea patient UUID
       ↓ etl.person_id_map
integer cdm.person.person_id
```

目标扩展（不能简单混为一谈）：

```text
source-scoped patient keys (Epic MRN, FHIR Patient.id, Synthea UUID)
       ↓ stable source identity mapping
source-specific person identity
       ↓ optional, governed identity resolution
enterprise person identity
       ↓ OMOP mapping
cdm.person.person_id
```

- Source Adapter 的职责是**准确解释源标识和编码**；跨源患者去重/合并是单独受管控流程。
- 不允许把相同 MRN 数值当成全球同一患者；要考虑 assigning authority、医院实例、标识系统、有效期与变更。
- 可选 Identity Resolution 未启用时，下游只按当前明确的来源作用域键关联，不进行未经授权的患者合并。

## 8. 文件流转完整示例 A：Synthea CSV → OMOP `cdm.person`

> **示例目标路径：V2 设计。** 当前集群上已经跑通的 `person` 113 行流程仍使用旧 S3 key；本示例描述**迁移后应该如何流转**，不是当前对象已经在 V2 路径存在。

### 8.1 收到整个 Synthea batch（Landing）

```text
s3://health-landing/
└── source=synthea/
    └── source_version=synthea-3.3.0-csv-v1/
        └── ingest_date=2026-10-07/
            └── batch_id=synthea-20261005-pop100-atlanta/
                ├── manifest.json
                └── payload/
                    ├── csv/
                    │   ├── patients.csv           # 113 行
                    │   ├── encounters.csv         # 5,799 行
                    │   ├── conditions.csv         # 4,152 行
                    │   ├── medications.csv        # 5,467 行
                    │   ├── procedures.csv         # 16,994 行
                    │   ├── observations.csv       # 76,588 行
                    │   └── ... (其他 CSV)
                    └── SOURCE_INFO.txt
```

完整 payload 结构由 Synthea 导出和交付包决定，不能拿 `patients/`、`encounters/` 当作所有系统必须遵守的目录。`manifest` 列出实际 18 个 CSV 文件与 checksum。

### 8.2 Intake/Processing 对 `patient` 的运行

```text
s3://health-processing/
└── source=synthea/source_version=synthea-3.3.0-csv-v1/
    ingest_date=2026-10-07/
    batch_id=synthea-20261005-pop100-atlanta/
    entity=patient/
    run_id=patient-20261007T201000Z-001/
    ├── job_request.json
    ├── work/
    │   └── normalized/
    │       └── data/part-00000-....parquet      # 尚未发布
    ├── dq/result.json                         # 113 accepted, 0 rejected, PASS
    ├── rejects/                               # 无拒绝记录时可为空或不存在
    ├── next_stage_request.json                # 可选
    └── run_manifest.json
```

处理程序：**Synthea-specific `synthea_patient_adapter`**，负责字段标准化/类型转换，并生成 `Canonical patient v1`，不负责写 `cdm.person`。当前同类能力来自 `apps/ingest-patients-raw.py`，重构时需要改为正式 Canonical Contract。

### 8.3 Gate PASS 后，发布 Canonical Raw

```text
s3://health-raw/
└── canonical_version=v1/
    └── entity=patient/
        └── source=synthea/source_version=synthea-3.3.0-csv-v1/
            ingest_date=2026-10-07/
            batch_id=synthea-20261005-pop100-atlanta/
            ├── manifest.json                   # adapter 版本 / lineage / DQ / 113 行
            └── data/
                ├── part-00000-....snappy.parquet
                └── _SUCCESS
```

**这时**可以从不同 Source 获得统一的 `patient` 字段语义；不过 source lineage 仍在路径/列中。读取时使用 `.../data/`，不包含 manifest。

### 8.4 Canonical → OMOP 产品映射

```text
Canonical patient Parquet
    + stable source key → etl.person_id_map
    + gender/race/ethnicity → OMOP vocabulary concept
    ↓ OMOP person mapper
s3://health-processed/
└── product=omop/product_version=5.4.3/
    dataset=person/processing_date=2026-10-07/
    run_id=person-20261007T202000Z-001/
    ├── manifest.json                       # 113 行, mapping version, input batches
    └── data/
        ├── part-00000-....snappy.parquet  # 18 个 OMOP person 字段
        └── _SUCCESS
```

当前已有相近代码 `apps/map-person-omop.py`，但它的映射值仍部分写死在 Python 中；**V2 应读取版本化 Mapping Contract**，并让 Mapper 只依赖 canonical 字段。

### 8.5 Processed → Stage → OMOP CDM

```text
health-processed/.../dataset=person/.../data/*.parquet
    ↓ PySpark JDBC loader
PostgreSQL etl.person_stage                   # run 隔离待增强
    ↓ SQL transaction / UPSERT
PostgreSQL cdm.person
    ↓ row count / FK concepts / stage comparison
Operational reconciliation + append-only journal
```

**现有实验已验收结果：** 113 名源患者 → 113 条 `cdm.person`，唯一 person ID 113，概念校验 0 异常，Stage/CDM 差异 0；重复执行后行数仍为 113。此验收对应**旧路径上的现有实现**，不是 V2 迁移验收。

### 8.6 从 Patient 扩展到其他业务实体

```text
CSV / FHIR / HL7 source payload
      ↓ adapter (source-specific)
Canonical patient / encounter / condition / procedure / medication / observation
      ↓ product mapping (source-agnostic, domain-specific)
OMOP person / visit_occurrence / condition_occurrence /
     procedure_occurrence / drug_exposure / measurement / observation
```

**注意非一对一：** 一个源文件可分流至多个 Canonical/OMOP 表（如 observations 到 `measurement` 或 `observation`）；一张 OMOP 表也可能汇集多个源文件/来源。不能以原始 CSV 文件个数决定 Spark Job 或 OMOP 表的数量。

## 9. 文件流转完整示例 B：模拟医院 Epic FHIR R4 Bulk Data → OMOP

> **纯虚构的医院接口实例，只演示医疗行业数据路径和处理规则。** `hospital_a_epic_fhir_bulk` 是假想的已注册数据源；下面的文件名、行数、日期、export 流程并非 Epic 对外接口的官方承诺。真实 Epic 接口支持范围、认证方式、FHIR 版本、US Core Profiles 及是否允许 `$export` 必须以医院实际配置/协议为准。

### 9.1 外部交付：FHIR Bulk Data 输出清单与 NDJSON

假设医院 A 与平台约定 FHIR R4 Bulk Data 接口。本次导出包含 `Patient` 和 `Encounter`，在 FHIR Bulk Data 中，**协议侧的完成状态返回 output manifest**，其中 `output[].type` 与 `output[].url` 描述各输出文件；NDJSON 中一行一个 FHIR Resource，而**`Patient_0001.ndjson` 这样的文件名只是任意示例**。不要求医院将文件改名为 `patients.csv`。

示意的源协议输出（只展示结构；正式源响应还需遵守相应 IG 的其他要求）：

```json
{
  "transactionTime": "2026-10-07T15:00:00Z",
  "request": "https://example-hospital.invalid/fhir/$export?_type=Patient,Encounter",
  "requiresAccessToken": true,
  "output": [
    {"type": "Patient", "url": "https://example-hospital.invalid/exports/Patient_0001.ndjson"},
    {"type": "Encounter", "url": "https://example-hospital.invalid/exports/Encounter_0001.ndjson"}
  ]
}
```

Intake Connector 用授权方式取回源文件，**按字节原样保存 NDJSON**；需要保留的源响应元数据应先去掉 token、临时签名 URL 和敏感认证参数。平台随后生成自己的 `manifest.json`，不要把源 export manifest 误当作平台批次契约。

### 9.2 Landing：平台外壳统一，FHIR 文件名保留

```text
s3://health-landing/
└── source=hospital_a_epic_fhir_bulk/
    └── source_version=hospital-a-fhir-r4-v1/
        └── ingest_date=2026-10-07/
            └── batch_id=fhir-export-20261007-001/
                ├── manifest.json                 # 平台生成：来源、文件哈希、类型、批次
                ├── source_export_metadata.json   # 净化后的源导出元信息（如需保留）
                └── payload/
                    ├── Patient_0001.ndjson      # 上游实际交付名称（示例）
                    └── Encounter_0001.ndjson    # 不强制重命名
```

`manifest.json` 必须能定位受限保存的源 manifest（如确需保存）或净化后的 `source_export_metadata.json`、上游 export job ID、关联 FHIR IG/Profile、文件清单和校验和。带临时签名的下载 URL、访问 token、敏感查询参数不得进入一般权限下的元数据对象。例如文件项可以是：

```json
{
  "path": "payload/Patient_0001.ndjson",
  "original_filename": "Patient_0001.ndjson",
  "declared_resource_type": "Patient",
  "payload_format": "application/fhir+ndjson",
  "sha256": "<computed-sha256>"
}
```

**真实性判定**：必须逐行检查 NDJSON 是否为合法 FHIR R4 Resource（如 `resourceType=Patient`）、适用 Profile、标识符/引用规则及文件哈希；**不能因为名字含 `Patient` 就视为 Patient**。

### 9.3 Processing：按 `source + batch + entity + run` 运行 Adapter

```text
s3://health-processing/
└── source=hospital_a_epic_fhir_bulk/
    └── source_version=hospital-a-fhir-r4-v1/
        └── ingest_date=2026-10-07/
            └── batch_id=fhir-export-20261007-001/
                └── entity=patient/
                    └── run_id=patient-fhir-20261007-001/
                        ├── job_request.json
                        ├── work/
                        │   ├── parsed/                 # 解析结果（可选）
                        │   └── normalized/
                        │       └── data/
                        │           └── part-00000-....snappy.parquet
                        ├── rejects/
                        ├── dq/result.json
                        └── run_manifest.json
```

Source Adapter（示例名 `fhir_r4_bulk_patient_adapter`）负责：

1. 根据 **FHIR Bulk output manifest** 指定 `Patient` 文件，不假设真实文件名；校验文件与下载一致。
2. 按 NDJSON 格式逐行解析 FHIR Resource，检查 `resourceType` 与约定的 FHIR R4/Profile，必要时记录 `OperationOutcome` 错误/拒绝原因。
3. 解析 `Patient.id`、`Patient.identifier[]` 的 system/value、`birthDate`、`gender` 等字段；**不得把医院 MRN 与 FHIR `resource.id` 直接混为一谈**。
4. 转换为 `Canonical patient v1`，保留 provenance、来源 ID 和编码 system；缺失的字段按正式 Contract 处理，不凭空造值。
5. 在 Canonical Gate PASS 之后才批准发布到 Raw。

### 9.4 Raw：同一个 Canonical Schema，和 Synthea 的 Raw 可以共用 Mapper

```text
s3://health-raw/
└── canonical_version=v1/
    └── entity=patient/
        └── source=hospital_a_epic_fhir_bulk/
            └── source_version=hospital-a-fhir-r4-v1/
                └── ingest_date=2026-10-07/
                    └── batch_id=fhir-export-20261007-001/
                        ├── manifest.json
                        └── data/
                            ├── part-00000-....snappy.parquet
                            └── _SUCCESS
```

这里的数据**字段含义、类型、编码信息**必须符合与 Synthea patient 相同的 `Canonical patient v1` Contract；来源、标识符作用域与批次 provenance 则继续保留。并非不同医院一律会提供相同的 Race/Ethnicity 信息，也不得假定跨来源代码和值必然一致。

### 9.5 Product：共用 Canonical → OMOP Mapper，身份范围清晰

```text
Canonical patient (source=hospital_a_epic_fhir_bulk)
    + source-scoped stable identity mapping
    + clinical code-system-aware mapping
    + optional governed cross-system patient matching
              ↓ OMOP person mapper
s3://health-processed/
└── product=omop/
    └── product_version=5.4.3/
        └── dataset=person/
            └── processing_date=2026-10-07/
                └── run_id=person-fhir-20261007-001/
                    ├── manifest.json
                    └── data/
                        ├── part-00000-....snappy.parquet
                        └── _SUCCESS
              ↓ PostgreSQL stage + transactional UPSERT
PostgreSQL cdm.person
              ↓ reconciliation + audit
```

**复用的是** Canonical Schema / Product Mapper / 发布 / 稳定键 / DQ / 审计机制；**不要求复用** Synthea CSV Adapter 或原始文件目录。具体不同来源合并到同一个 `cdm.person` 时，须先定义机构/系统标识符作用域与身份匹配策略，不允许默认同名/同 MRN 即同一人。

### 9.6 HL7 v2 的交付同样适用（无需伪装成 FHIR）

另一个未来可扩展的输入是医院 ADT（HL7 v2）消息：

```text
Hospital HL7 v2 ADT (例如 MLLP 消息流)
   ↓ Mirth / HL7 Connector（接收、ACK/NACK、记录安全回执）
   ↓ Landing：保存原始消息字节或受控消息批次 payload
   ↓ hl7v2_adt_adapter（根据 MSH 版本/消息事件/接口指南解析）
   ↓ Canonical patient / encounter（按内容决定）
   ↓ DQ Gate → Raw → OMOP product(s)
```

- HL7 消息流**不一定有上游文件名**。Connector 可生成安全的对象名（例如消息控制 ID 的脱敏引用 + 随机 ID），并保留 `MSH` 里必要的 source/message metadata。
- 本地定义 `Z` segments 是 HL7 v2 的一种扩展机制，需按医院实施指南解析；未知扩展按契约记录或隔离，不能静默认为标准字段。
- **不是所有 HL7 v2 消息都要先转成 JSON**。为了下游消费可以生成规范化中间表示，但原始内容和语义应保留，是否 JSON 是 Adapter 的技术选择。

**关键结论：** 所有接入都遵守我们的来源注册、批次身份、manifest、验证/审计规则；不同医疗协议保留各自的原生文件布局和解析方式。目录外壳复用，**不强制原文件名相同，也不复制其他企业的文件路由实现**。

## 10. Airflow、Spark 和 PostgreSQL 的任务分工

### 10.1 建议 DAG 边界（按 batch 参数化）

```text
register_and_verify_batch
   ↓
route_source_and_create_job_request
   ↓
submit_source_adapter_spark_application
   ↓
canonical_dq_gate
   ├─ FAIL → quarantine / hold / audit → STOP
   └─ PASS
        ↓
publish_canonical_raw
   ↓
prepare_or_lookup_stable_ids
   ↓
submit_product_mapper_spark_application
   ↓
product_dq_gate
   ├─ FAIL → reject_product / audit → STOP
   └─ PASS
        ↓
approve_product_run
   ↓
load_postgres_stage
   ↓
transactional_upsert_cdm
   ↓
reconcile_and_journal
   ↓
mark_batch_product_complete
```

- Airflow **传入** `source`、`source_version`、`ingest_date`、`batch_id`、`run_id`、manifest URI、合同版本；不在 DAG 里逐个写死文件名。
- SparkApplication 负责重计算和 JDBC data movement；Airflow 不直接处理整批 DataFrame。
- PostgreSQL 负责 `INSERT ... ON CONFLICT DO UPDATE` / `MERGE`、约束与事务边界；写入前用 run-scoped stage 或串行锁。
- `person` 成功并准备稳定映射后，`visit_occurrence` 才能引用稳定 person ID；condition/procedure/drug 等按 person/visit 依赖执行，互不依赖的 domain 可以并行。
- 与 Dag Run 对应的 `run_id` 必须在所有 Spark job、Processing、Raw/Processed manifest、审计事件中可关联；数据产品的发布 ID 不要求等于 Airflow 的技术 task attempt ID。

### 10.2 开发代码结构建议（目标，非现状）

```text
spark/
├── common/
│   ├── s3_io.py
│   ├── jdbc_io.py
│   ├── contracts.py
│   ├── dq_gates.py
│   ├── manifest.py
│   ├── id_mapping.py
│   └── audit.py
├── adapters/
│   ├── synthea/
│   │   ├── patient.py
│   │   └── encounter.py
│   ├── epic_fhir/
│   └── hl7v2/
├── products/
│   └── omop/
│       ├── person.py
│       ├── visit_occurrence.py
│       └── condition_occurrence.py
└── contracts/
    ├── canonical/
    ├── products/
    └── mappings/

airflow/dags/
├── healthcare_ingestion.py
└── healthcare_omop.py

sql/
├── etl_control/
├── omop_staging/
└── upsert/
```

使用 source-specific Adapter + domain-specific Mapper；公用代码负责 I/O、运行上下文、DQ、审计、JDBC 与幂等发布。**不应为每个 CSV 复制五份互相独立的公共逻辑**。

## 11. 审计、Reconciliation 与运维指标

### 11.1 最小审计事件

每一个关键状态变化至少要记录：

```text
run_id, batch_id, source, entity/product/dataset,
event_type, event_time_utc, status, input_manifest_uri,
output_manifest_uri, row_counts, reject_counts,
dq_status, adapter_version, mapping_version, code_revision,
error_class, correlation_id
```

推荐事件：`BATCH_RECEIVED`、`ROUTE_MATCHED`、`ROUTE_ON_HOLD`、`NORMALIZATION_STARTED`、`CANONICAL_DQ_PASSED`、`RAW_PUBLISHED`、`PRODUCT_DQ_PASSED`、`PRODUCT_APPROVED`、`CDM_LOAD_COMMITTED`、`RECON_PASSED`、`RUN_FAILED`。审计事件 append-only；可变最新状态可另存在 PostgreSQL `etl.pipeline_run` 等控制表中。

### 11.2 最小 Recon

- 输入文件数、对象 checksum、源记录总数（可确定时）。
- Canonical 接受/拒绝/隔离记录数；数据拆分或聚合时记录明确公式，而不是假设 input=output。
- Processed dataset 输出数、唯一键数、缺失主键/概念数。
- Stage 行数、UPSERT 插入/更新计数（如果能够可靠区分）、CDM 本批次有效记录数。
- Source ID ↔ OMOP ID 匹配成功率，Person/Visit 外键完整性。
- 运行时长、重试次数、失败阶段、数据新鲜度和延迟。

**示例（`person`，现有单批次）：** `113 Landing → 113 Canonical → 113 Processed → 113 Stage → 113 CDM`，reject=0，stage/CDM diff=0。但其他域存在一对多/拆分/过滤时，不得机械要求行数完全相等，应使用各 domain 的 recon 规则。

## 12. 安全、保留与操作约束

1. 各层独立访问权限：Landing 接入、Processing 解密、Canonical 使用者、Product 发布者、数据库写入者应尽可能分离。
2. 密钥/数据库密码只来自 Kubernetes Secret 或受管 Secret 系统；不写进 manifest、DAG、SQL 文件、Git、日志。
3. PGP 解密后的明文是高敏中间数据；仅在受限区域短期保留，处理完成/失败都按策略清理，并记录清理状态。
4. 真实患者数据必须按适用合规要求进行访问、脱敏、加密、审计及保留管理；本地 Synthea 为合成数据也要演练安全控制。
5. `health-processing` 可按运行状态+保留策略清理；Landing、Raw、Processed、Journal 的保留与归档是**分别配置的策略**，不要用统一自动删除。
6. 当前本地 SeaweedFS S3 endpoint 为集群内 HTTP 测试环境。未来涉及真实数据或跨不可信网络时应启用 TLS、网络隔离、最小权限及合适的加密/密钥管理。
7. 文件路径、manifest 与日志不得随意写患者姓名、SSN、MRN 等直接标识；仅用不包含敏感信息的批次和运行标识。

## 13. 已实现状态、差距与 V2 迁移顺序

### 13.1 截至本次讨论的已验证能力

| 功能 | 当前状态 |
|---|---|
| Synthea v3.3.0 CSV 生成、校验（18 个 CSV） | ✅ 已实现 |
| SeaweedFS `health-landing` 上传及 SHA256 校验 | ✅ 已实现（**旧 key**） |
| PySpark patients CSV → typed Raw Parquet + DQ | ✅ 已实现（**当前仅 Synthea 适配**） |
| 稳定 `etl.person_id_map` | ✅ 已实现（113 个 source ID） |
| PySpark Raw → OMOP-ready `person` Parquet + DQ | ✅ 已实现（**旧 key + 部分硬编码 mapping**） |
| Spark JDBC → `etl.person_stage` → PostgreSQL `cdm.person` | ✅ 已实现 |
| `cdm.person` 113 行、重复执行幂等、概念与差异校验 | ✅ 已验证 |
| 通用 Landing/Raw/Processed V2 key + manifests | ⏳ 目标设计，**尚未迁移** |
| 新增 `health-processing` bucket 与 run 工作区 | ⏳ 目标设计，**尚未创建/验证** |
| 正式 Canonical v1 schema registry、通用 Source Adapter | ⏳ 待设计/实现 |
| 批次/运行路由、DQ 发布控制、Journal、Recon 控制表 | ⏳ 待实现 |
| 全流程 Airflow healthcare DAG | ⏳ 尚未把现有手工脚本正式串联 |
| `visit_occurrence` 等其他临床 domain | ⏳ 后续开发 |

### 13.2 推荐重构顺序（严禁直接删旧数据）

**阶段 A：契约优先**

1. 确定 `source` 来源注册表、**原始文件名 preserve 默认策略和按合同可选的命名校验**、batch/run ID 生成规则与路径解析工具。
2. 固化 Canonical `patient` v1 字段、类型、可空/编码规则及 JSON Schema/数据质量断言；明确当前 Raw 与真正通用 Canonical 的差异。
3. 固化 3 类 manifest、`job_request.json`、DQ result 的 Schema 与验证程序。
4. 在新路径上建立一个测试批次。旧路径、旧代码暂留可回滚。

**阶段 B：Person V2 端到端迁移**

5. 配置 `health-processing` bucket、ACL、生命周期与独立 `run_id` 目录。
6. 调整当前 `03` 上传逻辑，生成 Landing V2 manifest 与 `payload/`；校验上传前后哈希一致。
7. 将当前 `04/05` 拆分为 Synthea patient Adapter + Canonical Gate + Raw 发布；Raw 仅发布 PASS 批次。
8. 将当前 `10/11` 改成从 Canonical Contract 读取，配置化人口学 mapping；写 Processed V2、验证并批准 run。
9. `12` 的 JDBC/SQL 继续复用已经证明有效的 Stage→UPSERT 模式，改为 run-scoped stage/安全锁，并使用 manifest 动态计数与批次级对账。
10. 新旧两条流程对照：113 个稳定 person_id、OMOP 行内容、概念映射、Source lineage 相符。**先验收再切换消费者**。

**阶段 C：平台化与扩展**

11. 加入不可变事件日志、控制表、Recon/运行指标、failure/hold/replay 测试。
12. 用 Airflow 按 batch/run 参数化串联上述作业，明确重试、批准发布和失败停止条件。
13. 完成 `encounter → visit_occurrence`；Person + Visit 均稳定后提炼公共 Source Adapter / Product Mapper / DQ / JDBC 模块。
14. 再扩展 condition、procedure、drug、observation，并先用**合成 FHIR R4/NDJSON**作为第二种输入验证跨源 Canonical 与 OMOP 解耦；真实 Epic/HL7 接口需另行注册、测试与授权。
15. 只有当新路径完成验收、消费者已切换、保留策略批准后，才规划旧 smoke-test 和旧 batch 对象的归档/清理。

### 13.3 V2 最小验收清单

- [ ] 两个不同 source、相同原始文件名不会覆盖；同 source 的不同 batch 文件名可重复；医院非固定命名仍能按 manifest/内容正确路由。
- [ ] 同 source、同 batch、相同 checksum 重投递被识别为重复；不同 checksum 拒绝覆盖。
- [ ] 不支持的 FHIR Profile/Schema/接口版本进入 `ON_HOLD`，不产生 Raw 发布；单靠文件名匹配不能放行。
- [ ] 错误文件 checksum / Schema / 主键缺失触发 DQ FAIL，Processed/CDM 不被更新。
- [ ] Processing 每次运行具有不同 `run_id`；失败后可回放，原输入及历史审计可追踪。
- [ ] Raw `entity=patient` 跨不同 Source 保证 Canonical 字段语义一致。
- [ ] Consumer 仅读取已批准的 `data/` 前缀，不误读 manifest 或历史 run。
- [ ] OMOP mapper 使用稳定身份映射、版本化 concept mapping；不硬编码 Synthea 路径。
- [ ] `person` V2 在与现有测试数据等价的输入下输出 113 条有效记录，Source ID ↔ person ID 不变化。
- [ ] JDBC Stage / SQL UPSERT 重跑不增加重复的 `cdm.person` 行；Stage 与 CDM 差异为 0。
- [ ] 全链路可按 `source + batch_id + run_id` 追溯并查询 DQ/Recon 状态。
- [ ] 在并行任务情况下，两个 run 不会互相清空同一 Stage 或覆盖 Product 输出。

## 14. 最终开发约束（PR 审查条款）

1. **新增来源**：先注册医院/接口/版本与格式契约，再增加 Adapter；默认不要求上游改名；禁止为了 Epic 改掉已有 Canonical Patient 的字段语义。
2. **新增 OMOP 域**：优先复用公共 I/O、Run Context、DQ、Stage/UPSERT、Journal；只写 domain-specific mapping 和校验规则。
3. **禁止硬编码**：真实 `batch_id`、`run_id`、输入 S3 key、行数、Secret、日期必须参数化；demo fixture 可以在测试中显式固定。
4. **Schema 变更**：改变列语义/类型须评估 `canonical_version` 升级与旧版读取兼容性；改变 OMOP target version 需单独发布迁移。
5. **输出发布**：每次新 run 独立前缀，先校验后批准；消费者只使用批准 run，不能扫描所有历史 run。
6. **不可变与补数**：不覆盖原始 Landing payload、已发布批次和 Journal 事件；修复使用新 batch 或新 run，并保留关联链。
7. **可复现**：代码、配置、Mapping Contract 进 Git；源合成数据可以再生成，密钥、加密明文、真实敏感数据绝不进 Git。
8. **已验证的旧实现**：重构前保留可工作的脚本和旧对象，并记录迁移差异；不允许未经验证直接以 V2 替换现有生产/实验消费者。

## 15. 医疗行业标准依据与设计取舍

本节说明**哪些规则来自正式行业规范，哪些是本平台自主约定**。标准会持续更新；开发时应锁定实际采用版本，不因为“最新版”变化就无审查升级。

| 依据 | 官方资料 | 对本平台的约束或启发 | 不能据此宣称什么 |
|---|---|---|---|
| HL7 FHIR R4 | [FHIR R4 JSON](https://www.hl7.org/fhir/R4/json.html)、[FHIR R4 Validation](https://hl7.org/fhir/R4/validation.html) | 按资源结构/类型/约定 Profile 验证内容；FHIR `Resource.id`、identifier system 与 source lineage 分开 | FHIR 要求所有数据交付成固定文件名 |
| US Core IG | [HL7 US Core IG](https://hl7.org/fhir/us/core/) | 美国医疗互操作的常见 FHIR profile 约束参考；接口须明确其 IG/profile 版本 | 所有医院/全部 FHIR resource 必须无条件满足最新 US Core |
| FHIR Bulk Data IG | [HL7 Bulk Data Export](https://hl7.org/fhir/uv/bulkdata/en/export.html) | 标准化 `output` manifest 与 NDJSON；优先根据 `type`/内容判断资源，处理 export 成功/异常 | 标准规定 `Patient_001.ndjson` 这一具体文件名 |
| HL7 v2 | [HL7 v2 Chapter 2](https://hl7.eu/HL7v2x/v281/std281/ch02.html) | 按 `MSH`、消息类型和医院接口规范解析，允许本地 `Z` segment | HL7 v2 天然统一所有医院字段用法、文件打包与命名 |
| Synthea | [Synthea 文档与 Exporter](https://github.com/synthetichealth/synthea)、[CSV Exporter 配置](https://github.com/synthetichealth/synthea/blob/master/src/main/resources/synthea.properties) | 为本 Lab 提供可重现、已固定版本和 exporter 配置的合成 CSV；未来可生成 FHIR | Synthea CSV 字段是各家医院统一采用的医疗行业标准 |
| ONC / 医疗接口指南 | [ONC Standards Hub](https://healthit.gov/certification-health-it/standards-hub/) | 按用例选定适用的 IG、实施约束与术语系统 | 一个标准能覆盖所有场景的传输格式和接入文件名 |

**平台自有而非 HL7 标准的内容：** `source=.../source_version=.../ingest_date=.../batch_id=.../payload/`、`health-processing`、`health-raw`、`health-processed`、`run_manifest.json`、`filename_policy`、`etl.person_id_map`、Airflow Job Request、批次审计事件与发布状态，均是**本项目明确制定的工程契约**。它们用于可追溯、幂等与跨源扩展，不能描述成医疗协会规定的通用目录标准。

**落地先后顺序：** 先完成 Synthea `person` 路径迁移、通用 source registry/manifest、Canonical schema/DQ；第二步用**合成 FHIR R4 NDJSON**及相应测试 contract 证明“不同文件名与协议 → 同一 Canonical patient”；待具备医院授权与真实协议后，才考虑对接真实 EHR/Epic API。

---

### 一句话总结

**遵循医疗行业的实际传输/内容标准 + 平台统一接入契约（不强迫统一文件名） → Landing 保留原文 → 运行级 Processing → Source Adapter → DQ Gate → Canonical Raw → 可选身份关联 → Product Mapper → Product Gate → Processed → Stage/UPSERT → OMOP CDM；Airflow 负责串联与恢复，Audit/Recon 贯穿整个流程。**

> **后续代码开发默认以本规范的 V2 目标目录和职责边界为依据；若发现冲突，先更新架构决策和契约，再修改实现。**
