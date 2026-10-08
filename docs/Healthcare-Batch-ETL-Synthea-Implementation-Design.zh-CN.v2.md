# Healthcare Data Platform — Synthea Batch ETL 设计与开发基线

> **文档版本：V2.0（Batch MVP）**  
> **日期：2026-10-07**  
> **状态：正式开发设计基线；目标 V2 尚未部署**  
> **项目仓库：** `JohnZhang-DataForge/healthcare-data-platform`  
> **适用环境：** Kubernetes + SeaweedFS（S3 API）+ Spark Operator/PySpark + Airflow + PostgreSQL 17 / OMOP CDM 5.4.3
>
> **唯一主目标：** 用 **Synthea v3.3.0 一次生成的整批 18 个 CSV**，建设、验证并自动编排一条可重复运行的 **Batch → Canonical → OMOP CDM** 数据流水线。本文刻意不展开其他数据源接入、实时处理或完整企业平台建设。

---

## 0. 决策摘要（后续开发以本节为准）

1. **一个交付批次（batch）包含多个文件。** 同一次 Synthea 导出产生的 18 个 CSV 属于同一个 `batch_id`。平台先完整接收、登记、校验整个批次，再对具体数据集分配任务，不能把 `patients.csv` 当成整个批次。
2. **整个批次的所有文件都要有处理结论；不要求每个 CSV 对应一个 OMOP 表。** 本轮对 18 个文件做清单、完整性、格式和基础质量检查。优先转换主要临床实体；其余文件明确记录为 `DEFERRED`（本阶段暂不映射），绝不能把“核心表处理完成”描述为“18 个文件全部完成 OMOP 映射”。
3. **开发范围以 Synthea CSV 批处理为准。** 本次不实现 HL7 消息接收、FHIR 外部接口、流式处理、跨院身份识别、加密文件解密或通用来源注册服务。架构保留适度的参数化空间，但不为假设功能增加实际开发任务。
4. **文件目录先统一，再继续增加业务表。** 采用 `Landing → Processing（临时）→ Canonical Raw → OMOP Processed → Stage → CDM`。旧 S3 key 和既有 `person` 数据先保留；迁移验收前不删除。
5. **Source Adapter 与 OMOP Mapper 解耦。** Synthea Adapter 只负责读取源 CSV 并生成我们定义的 Canonical 实体；OMOP Mapper 只读 Canonical 数据和稳定 ID/概念映射，不依赖源 CSV 文件名与字段名。
6. **Airflow 按 `batch_id` 统筹整批执行。** 一个 batch 触发一个批处理 DAG Run；Raw 作业可以并行，OMOP 作业按 `person → visit → 临床事实表` 的依赖执行；最后给出清晰的批次状态与对账结果。
7. **先交付可演示的闭环。** 基础文件清单、DQ、幂等、失败停止与批次汇总是必须项；复杂路由、不可篡改账本、MPI、通用 UI 暂不做。

### 0.1 此版本怎样才算完成

**Batch MVP 完成（`CORE_COMPLETE`）：**

- 18 个输入 CSV 都已登记、传入 Landing、校验 checksum/header/基本质量，并获得明确处理状态。
- 核心数据从 **同一个 batch** 转换成 Canonical Parquet，再生成并加载 `cdm.person`、`cdm.visit_occurrence`、`cdm.condition_occurrence`、`cdm.procedure_occurrence`、`cdm.drug_exposure`，以及由 `observations.csv` 派生的 `cdm.measurement` 和适用的 `cdm.observation`。
- 所有加载都有 DQ 与批次对账、stable ID/FK 检查、失败阻断与重跑验证。
- Airflow 可以从一个 batch manifest 启动整个流程，并完成状态汇总。
- 其余文件（如 claims/payers 等）没有被默默丢弃，必须在清单中标明 `DEFERRED` 与理由。**`CORE_COMPLETE` 不等于全部 Synthea 18 个数据集都做了完整 OMOP ETL。**

> 若将来为全部适用文件补齐 OMOP 处理，再定义更严格的 `FULL_COMPLETE`；本次交付**不以此为目标**。

---

## 1. 当前已验证基线（不是未来规划）

| 组件/能力 | 当前情况 |
|---|---|
| Kubernetes | `master01` 控制平面；`worker01` storage；`worker02` platform；`worker03` compute；`runner01` 管理部署 |
| SeaweedFS | 已建 `health-landing`、`health-raw`、`health-processed`、`health-archive`、`postgres-backup`；S3 访问验证通过 |
| Airflow | 3.2.2，已部署、GitSync 和 smoke DAG 成功；**尚未编排完整 Healthcare Batch** |
| Spark Operator | 2.5.2；PySpark 3.5.7，S3A/JDBC 能工作 |
| PostgreSQL | 17；`omop` DB，`cdm` schema，OMOP CDM 5.4.3，词表已加载 |
| Synthea | 固定 v3.3.0、seed=20261005、population=100、Atlanta, Georgia；导出 18 个 CSV |
| `person` 端到端 | Landing → typed Raw Parquet → OMOP-ready Parquet → `etl.person_stage` → `cdm.person` **已通过** |
| Person 验收 | `cdm.person=113`、stable ID=113、stage/CDM diff=0；重复执行后仍为 113 |
| V2 目录及 Batch DAG | **设计中，尚未改动现有运行环境** |

**现有代码应当作为回归基准保存**：`/data/spark/phase3c/03`、`04`、`05`、`07`、`10`、`11`、`12` 等已经验证的脚本与 PySpark 程序。改造采用新分支和新配置，先跑通再切换。

---

## 2. Synthea 一次交付的对象：18 个 CSV

一次固定 seed 的 Synthea 导出属于**一个 Source Batch**，不是 18 个独立、互不相关的 batch。

已生成的文件清单（**以下行数为当前实验数据，不应硬编码到生产参数**）：

| Synthea CSV | 当前已知行数 | 本轮 Batch MVP 用途 |
|---|---:|---|
| `patients.csv` | 113 | Canonical patient → `cdm.person`（已实现，迁移 V2） |
| `encounters.csv` | 5,799 | Canonical encounter → `cdm.visit_occurrence` |
| `conditions.csv` | 4,152 | Canonical condition → `cdm.condition_occurrence` |
| `procedures.csv` | 16,994 | Canonical procedure → `cdm.procedure_occurrence` |
| `medications.csv` | 5,467 | Canonical medication → `cdm.drug_exposure`；需验证药品术语映射 |
| `observations.csv` | 76,588 | Canonical observation → 根据语义拆分 `cdm.measurement` / `cdm.observation` |
| `allergies.csv` | 待运行时统计 | 完整接收与基础验证；OMOP 映射本轮 `DEFERRED` |
| `careplans.csv` | 待运行时统计 | 完整接收与基础验证；后续再评估映射 |
| `claims.csv` | 待运行时统计 | 完整接收与基础验证；不假定直接对应标准 OMOP 临床表 |
| `claims_transactions.csv` | 待运行时统计 | 完整接收与基础验证；本轮暂不映射 |
| `devices.csv` | 待运行时统计 | 完整接收与基础验证；后续可评估 `device_exposure` |
| `imaging_studies.csv` | 待运行时统计 | 完整接收与基础验证；需另定影像资料模型 |
| `immunizations.csv` | 待运行时统计 | 完整接收与基础验证；后续评估适用 OMOP 域 |
| `organizations.csv` | 待运行时统计 | 保留机构参考数据；本轮可用于关联检查，暂不强制构建 `care_site` |
| `payers.csv` | 待运行时统计 | 保留保险方参考数据；本轮暂不映射 |
| `payer_transitions.csv` | 待运行时统计 | 完整接收与基础验证；本轮暂不映射 |
| `providers.csv` | 待运行时统计 | 保留医生参考数据；本轮可用于关联检查，暂不强制构建 `provider` |
| `supplies.csv` | 待运行时统计 | 完整接收与基础验证；本轮暂不映射 |

**处理口径：** 18/18 完整性验收是输入批次目标；上述 6 个核心 CSV（可产生 7 个或更多目标数据集）是本轮业务转换目标。其余文件必须出现在 batch summary 中，显示 `VALIDATED/DEFERRED` 及原因。**不允许在未处理时打上 `MAPPED`/`SUCCEEDED`。**

### 2.1 数据依赖关系

```text
patients.csv ─────────────→ person_id_map ────────────→ cdm.person
                                                       │
encounters.csv ───────────→ visit_occurrence_id_map ──→ cdm.visit_occurrence
              (引用 person_id_map)                       │
                 ┌───────────────────────────────────────┴───────────────┐
                 ↓                  ↓                  ↓                 ↓
conditions.csv ─→ condition_occurrence    procedures.csv ─→ procedure_occurrence
medications.csv ─→ drug_exposure          observations.csv ─→ measurement / observation
```

后四类记录至少需要正确关联已有的 `person_id`，有源 encounter 引用时还要验证与 `visit_occurrence_id` 的匹配。实际约束与是否允许空引用，以对应 OMOP 表定义及各域 mapping contract 为准。

---

## 3. 目标架构：简洁的 Batch 数据流

```mermaid
flowchart TD
  G[Generate Synthea v3.3.0 CSV x18] --> U[Upload entire batch]
  U --> L[Landing payload + batch manifest]
  L --> V{Whole-batch verification}
  V -->|FAIL| F[Stop batch; record failure]
  V -->|PASS| P[Processing workspace / run_id]
  P --> A[Parallel Synthea dataset adapters]
  A --> Q{Canonical DQ per dataset}
  Q -->|FAIL| F
  Q -->|PASS| R[Canonical Raw Parquet]
  R --> I[Stable Person and Visit IDs]
  I --> M[OMOP domain transformations]
  M --> D{OMOP DQ}
  D -->|FAIL| F
  D -->|PASS| O[Processed OMOP Parquet]
  O --> S[JDBC stage]
  S --> C[Transactional CDM UPSERT]
  C --> X[Reconciliation + batch summary]
  X --> Y[CORE_COMPLETE / FAILED]
```

| 层或组件 | 输入 | 核心职责 | 输出 |
|---|---|---|---|
| **Landing** | 整批 Synthea CSV | 原样入湖、checksum、完整文件清单、批次元数据 | 18 个 CSV + `manifest.json` |
| **Processing** | Landing 数据 + run 参数 | 执行临时空间；暂存待验证 Parquet / DQ 结果 | run 工作文件，非正式数据 |
| **Synthea Adapter** | Source CSV | Schema、类型、字段语义、源键、基础业务校验 | Canonical datasets |
| **Canonical Gate** | Adapter 输出 | 按字段、主键、引用、行数检查；失败不发布 | `PASS` 后的 Raw 发布许可 |
| **Canonical Raw** | 合格的 Canonical datasets | 稳定、可复用的内部实体契约，保留批次来源 | Parquet |
| **OMOP Mapper** | Canonical + 稳定键 + 术语词表 | 生成 OMOP person/visit/clinical facts | OMOP-ready Parquet |
| **Product Gate** | OMOP-ready | 字段、概念、FK、唯一性、关系检查 | 合格的 Processed 产品 |
| **PostgreSQL stage/CDM** | OMOP-ready | JDBC Stage + 事务 UPSERT | `cdm.*` |
| **Airflow** | 一个 batch manifest | 编排依赖、并行、失败停止、重试、状态汇总 | 一次 Batch DAG Run |
| **Recon** | 全阶段计数/状态 | 各阶段按 dataset 对账，给出可解释的结果 | 控制表 + Batch Summary |

> `health-raw` 在本项目中明确表示**已标准化的 Canonical Raw**，不是未处理的原始文件；原始文件只在 Landing 的 `payload/` 中保留。

---

## 4. S3 目录与命名规范（本次冻结）

### 4.1 Bucket 清单

| Bucket | 本轮职责 |
|---|---|
| `health-landing` | 源批次原始 CSV + 清单；保留源文件原始文件名 |
| `health-processing` | **本轮新增**；run 级临时数据、DQ/错误输出；严格控制清理 |
| `health-raw` | 已通过 Canonical DQ 的实体 Parquet |
| `health-processed` | 已通过 OMOP DQ 的目标表 Parquet |
| `health-archive` | 当前保留作日志/历史归档，不建设独立 Journal 系统 |
| `postgres-backup` | PostgreSQL 备份，独立于 ETL 数据路径 |

不强制同时创建新服务或新数据库；`health-processing` 只是一个新的 S3 bucket。`manifest`、状态及控制表尽量保持精简。

### 4.2 Landing：以整个 Batch 为单位

```text
s3://health-landing/
└── source=synthea/
    └── source_version=v3.3.0/
        └── ingest_date=2026-10-07/
            └── batch_id=synthea-20261005-pop100-atlanta/
                ├── manifest.json
                └── payload/
                    └── csv/
                        ├── patients.csv
                        ├── encounters.csv
                        ├── conditions.csv
                        ├── procedures.csv
                        ├── medications.csv
                        ├── observations.csv
                        └── ...其他 12 个 CSV
```

- 外壳 `source/source_version/ingest_date/batch_id` 属于平台约定；payload 保留 Synthea 实际导出布局。
- `ingest_date` 是**首次成功接收的 UTC 日期**，不是业务日期；重跑不更改。
- `batch_id` 唯一标识该批次输入；同 `batch_id` 重传且 checksum 相同 → 去重；相同 ID、不同字节 → 报冲突，不静默覆盖。
- Synthea 的 `seed=20261005`、`population=100`、`city=Atlanta` 放在 manifest 元数据中，不再作为通用目录层级。
- **本轮 Synthea 合同**明确预期 18 个 CSV，包含预期文件名；这个限制是针对本次固定 exporter 的输入协议，**不是要求所有数据源永远按该文件名上传**。

### 4.3 Processing：运行工作区，不当最终数据读取

```text
s3://health-processing/
└── source=synthea/
    └── batch_id=synthea-20261005-pop100-atlanta/
        └── run_id=<safe_run_id>/
            ├── batch_validation.json
            └── entity=patient/
                ├── work/data/part-*.parquet
                ├── dq/result.json
                └── rejects/                      # 本轮可只有错误摘要
            └── entity=encounter/
                ├── work/data/part-*.parquet
                └── dq/result.json
            └── ...
```

- 临时输出写入 Processing，DQ PASS 才发布到 Raw；失败写错误摘要并阻止依赖任务。
- 不要求第一版实现逐记录隔离/自动补数/复杂状态机。对合成数据，首版采用**严重校验失败即中止该数据集，且阻断下游关联表**。
- 工作区保留至少本次调试所需的日志/结果，再根据运行状态安全清理，不清理 Landing 输入。

### 4.4 Canonical Raw：实体优先，batch 可追溯

```text
s3://health-raw/
└── canonical_version=v1/
    └── entity=patient/
        └── source=synthea/
            └── batch_id=synthea-20261005-pop100-atlanta/
                └── run_id=<safe_run_id>/
                    ├── manifest.json
                    └── data/
                        ├── part-00000-....snappy.parquet
                        └── _SUCCESS
```

其他 core entities 同样布局：`entity=encounter`、`condition`、`procedure`、`medication`、`observation`。

- `canonical_version` 是内部 schema 版本，**不是** Synthea 版本，也不是 OMOP 版本。
- Schema 使用版本化 Contract（字段类型、可空性、源 ID、编码体系、时间语义）；同一实体的所有批次遵守相同 Contract。
- 新 `run_id` 保留重新处理产物，不覆盖历史 run；**下游必须只读控制表所批准的输入 run URI**，不能扫描所有 run 造成重复。
- 数据读取必须指向 `.../data/`，不把上一层 `manifest.json` 混进 Parquet 读取。
- 即使当前只接入 Synthea，也保留 `source=synthea` 的 lineage。

### 4.5 OMOP Processed：按目标表组织

```text
s3://health-processed/
└── product=omop/
    └── product_version=5.4.3/
        └── dataset=person/
            └── batch_id=synthea-20261005-pop100-atlanta/
                └── run_id=<safe_run_id>/
                    ├── manifest.json
                    └── data/
                        ├── part-00000-....snappy.parquet
                        └── _SUCCESS
```

不同目标表使用：`dataset=visit_occurrence`、`condition_occurrence`、`procedure_occurrence`、`drug_exposure`、`measurement`、`observation`。

- 本轮 Processing/Raw/Processed 可以引用同一逻辑 `run_id`，但对象路径中的 entity/dataset 隔离各任务输出；Spark task 的内部 attempt 不能误当为新业务 batch。
- OMOP-ready 数据列和类型按现有 PostgreSQL OMOP CDM 5.4.3 表定义生成；`manifest` 记录 mapping 版本、源 batch、输入 Raw 路径、输出行数、DQ 状态。
- **发布控制是状态，不是目录存在性**：读取 `.../data/` 前必须确认该 run 已批准。`_SUCCESS` 只能证明写入完成，不能证明 DQ PASS。

### 4.6 命名与时间语义

| 字段 | 意义 | 本例 |
|---|---|---|
| `batch_id` | 一次逻辑数据交付，同批 18 文件共享 | `synthea-20261005-pop100-atlanta` |
| `run_id` | 一次 ETL 执行及其输出；重跑应新建 | `manual-20261007T201500Z-001`（示例） |
| `source_version` | Synthea exporter/输入合同版本 | `v3.3.0`（本 lab 简化） |
| `canonical_version` | 我们的内部实体模型版本 | `v1` |
| `product_version` | OMOP CDM 目标 Schema 版本 | `5.4.3` |
| `ingest_date` | 第一次接收时间的 UTC 日期 | `2026-10-07`（示例） |
| 业务事件时间 | encounter/procedure 实际发生日期 | 从 CSV 字段解析，不从目录获取 |

所有日期/ID 实际执行时都由参数/manifest 传入，**严禁把示例日期、行数或路径直接硬编码到可复用的 Spark job**。

---

## 5. 最小批次契约与控制状态

### 5.1 Landing manifest（一个 Batch 一个）

**下面仅展示少量文件项。真实 manifest 必须包含 18 个文件的完整列表与计算出的 SHA256；示例中的 checksum 占位符不可直接用于程序。**

```json
{
  "manifest_version": "1.0",
  "source": "synthea",
  "source_version": "v3.3.0",
  "batch_id": "synthea-20261005-pop100-atlanta",
  "ingested_at": "2026-10-07T20:00:00Z",
  "payload_format": "csv",
  "expected_file_count": 18,
  "source_parameters": {
    "seed": 20261005,
    "population": 100,
    "state": "Georgia",
    "city": "Atlanta"
  },
  "files": [
    {
      "path": "payload/csv/patients.csv",
      "dataset": "patients",
      "sha256": "<actual_sha256_required>",
      "row_count": 113
    },
    {
      "path": "payload/csv/encounters.csv",
      "dataset": "encounters",
      "sha256": "<actual_sha256_required>",
      "row_count": 5799
    }
  ]
}
```

**正式执行的附加规则：** `files` 清单应是全部 18 项，`len(files)==expected_file_count==18`。禁止只看到示例的两项就判断整个 batch 完整。接入程序还必须验证文件实际存在、校验和一致、header 与固定 Synthea exporter schema 一致，且每个文件的行数来自实际读取而非猜测。`SOURCE_INFO.txt` 和原生源说明文件可以原样随 payload 保留，但不计入 18 个 CSV 的数据文件数。

### 5.2 两个层级的状态

**Batch 状态：** `RECEIVED → VALIDATED → RUNNING → CORE_COMPLETE`，或 `FAILED`。本轮没有复杂 `ON_HOLD` 流程。发现格式/外键/概念映射硬错误时标记 `FAILED` 并保留错误原因；修复后新的 run 引用同一 batch 重试。

**Dataset 状态：**

| 状态 | 含义 |
|---|---|
| `VALIDATED` | 文件已检查完整、符合 source contract |
| `RAW_PUBLISHED` | Canonical 数据 DQ PASS 并获得发布许可 |
| `CDM_LOADED` | 对应 OMOP 产品验证并成功落库，对账通过 |
| `DEFERRED` | 文件已验证但本轮没有 OMOP mapping，保留原因与后续计划 |
| `FAILED` | 当前 dataset 的处理或验证失败，记录失败阶段及错误摘要 |

**Batch `CORE_COMPLETE` 的判定必须同时满足**：18/18 输入 VALIDATED；core 业务数据集及其派生 OMOP 数据集完成 CDM_LOADED；其他数据集均为明确的 DEFERRED（而不是缺失状态）；所有必需对账 PASS。

### 5.3 控制表（最小可实现）

建议在 PostgreSQL `etl` schema 新增（实际 DDL 在对应开发阶段编写和测试）：

- `etl.batch_run`：`batch_id, run_id, source, landing_manifest_uri, status, started_at, finished_at, error_summary`。
- `etl.dataset_run`：`batch_id, run_id, dataset, input_uri, raw_uri, processed_uri, status, input_rows, accepted_rows, rejected_rows, loaded_rows, dq_status, error_summary`。
- 现有 `etl.person_id_map` 保留；新增 `etl.visit_occurrence_id_map`，键作用域包含 `source_system` + 源 encounter UUID。

对于文件清单，以 S3 Landing manifest 为准；PostgreSQL 控制表只保存状态、引用、计数，不重复写 18 个源文件全文。

---

## 6. 完整文件流转示例：一个 Synthea Batch，多个最终目标

### 6.1 一次生成与交付

```text
runner01:/data/spark/phase3c/source/synthea/csv/
  patients.csv         113 records
  encounters.csv      5799 records
  conditions.csv      4152 records
  procedures.csv     16994 records
  medications.csv     5467 records
  observations.csv   76588 records
  ...其余 12 个 CSV
           │
           │ upload whole delivery; verify all 18 checksums
           ▼
s3://health-landing/source=synthea/source_version=v3.3.0/
    ingest_date=2026-10-07/batch_id=synthea-20261005-pop100-atlanta/
      manifest.json
      payload/csv/patients.csv
      payload/csv/encounters.csv
      payload/csv/conditions.csv
      ... 18 files total
```

**注意：** 这是一个 batch，不能仅因先做了 `person` 就宣称该批完成；要等依赖的其他 core datasets 落库后才能 `CORE_COMPLETE`。

### 6.2 Landing → Processing → Canonical Raw

Airflow 解析一个 manifest，按 `dataset` 分发 Synthea Adapter 任务（没有必然需要的外键时可并行）：

```text
Landing payload/csv/patients.csv
    ↓ synthea_patient_adapter.py
health-processing/.../run_id=R/entity=patient/work/data/*.parquet
    ↓ validate canonical patient, then publish
health-raw/canonical_version=v1/entity=patient/source=synthea/
    batch_id=B/run_id=R/data/*.parquet

Landing payload/csv/encounters.csv
    ↓ synthea_encounter_adapter.py
health-processing/.../run_id=R/entity=encounter/work/data/*.parquet
    ↓ validate canonical encounter, then publish
health-raw/canonical_version=v1/entity=encounter/source=synthea/
    batch_id=B/run_id=R/data/*.parquet

... parallelize conditions/procedures/medications/observations similarly
```

这里 **Adapter 做 Source-specific 的格式与字段转换**，产物是内部 Canonical，不包含 OMOP domain 业务映射。Canonical v1 字段清单应单独存放在 `spark/contracts/canonical/` 并由测试检查，避免与旧的 Synthea-specific Raw 混淆。

**示意 Patient 行变化（取自当前合成源样例）：**

```text
CSV:  Id=84f0e055-7375-86f3-a3f6-89176737678e
      BIRTHDATE="2018-02-28", GENDER="M", RACE="white", ETHNICITY="nonhispanic"
      ↓ Synthea Adapter
Canonical patient v1:
      source_record_id="84f0e055-7375-86f3-a3f6-89176737678e"
      birth_date=DATE(2018-02-28)
      gender_code="M", race_code="white", ethnicity_code="nonhispanic"
      source_system="synthea", source_batch_id=B
```

### 6.3 Canonical → OMOP Processed → CDM

```text
Canonical patient         + etl.person_id_map       + demographic concepts
       ↓ OMOP person mapper
Processed dataset=person/run_id=R/data/*.parquet
       ↓ PySpark JDBC stage → transactional SQL UPSERT
cdm.person

Canonical encounter       + person_id_map + visit_id_map + Visit concepts
       ↓ OMOP visit mapper
Processed dataset=visit_occurrence/run_id=R/data/*.parquet
       ↓ Stage → UPSERT
cdm.visit_occurrence

Canonical condition / procedure / medication / observation
       + stable person_id / visit_occurrence_id
       + domain-specific vocabulary mapping
       ↓ OMOP mappers
Processed dataset=condition_occurrence / procedure_occurrence /
                  drug_exposure / measurement / observation
       ↓ Stages → UPSERT
cdm.<target domain tables>
```

以 Patient 示例说明 **OMOP 不复制整个 CSV**：

```text
Canonical:
  birth_date=2018-02-28, gender_code=M,
  race_code=white, ethnicity_code=nonhispanic
    ↓ map-person-omop.py
OMOP person:
  person_id=<existing stable integer, query from etl.person_id_map>
  year_of_birth=2018, month_of_birth=2, day_of_birth=28
  gender_concept_id=8507
  race_concept_id=8527
  ethnicity_concept_id=38003564
  person_source_value="84f0e055-7375-86f3-a3f6-89176737678e"
```

`person_id` 不编造具体整数；由当前数据库 stable mapping 查得。姓名、SSN、详细地址、收入等**不因存在于源文件就自动写入 `cdm.person`**。现有映射中的人口学 concept 已通过数据库验证；Visit、Condition、Drug 等概念必须分别 discovery/验证，不能照搬未核实的概念 ID。

### 6.4 同一批次的处理统计（区分已验证与目标）

| 数据集 | Landing 输入 | Canonical | OMOP 数据集 | 当前落地状态 |
|---|---:|---|---|---|
| patients | 113 | patient | person | ✅ 当前旧路径 113 行已通过；V2 待迁移 |
| encounters | 5,799 | encounter | visit_occurrence | 设计目标，未落库 |
| conditions | 4,152 | condition | condition_occurrence | 设计目标，未落库 |
| procedures | 16,994 | procedure | procedure_occurrence | 设计目标，未落库 |
| medications | 5,467 | medication | drug_exposure | 设计目标，未落库 |
| observations | 76,588 | observation | measurement / observation | 设计目标，未落库；分流数量待确定 |
| 其余 12 个文件 | 运行时统计 | 本轮不承诺 Canonical 落地 | `DEFERRED` | 仍必须完成源文件验收与状态记录 |

**绝不预设 OMOP 输出行数与源行数相等**：映射过滤、拆分、术语未匹配和粒度变化都可能影响数量。Recon 要求明确解释 `source_count → accepted + rejected/deferred` 和各 OMOP dataset 的映射计数，而非一刀切 1:1。

---

## 7. PySpark、SQL 与 Airflow 的程序边界

### 7.1 每一类程序负责什么

| 程序类别 | 示例 | 输入→输出 | 是否复用 |
|---|---|---|---|
| **Batch intake** | `register_synthea_batch.py` | 整批目录→manifest、checksum 与控制状态 | 整个 batch 共用，不按 CSV 复制 |
| **Source Adapter** | `synthea_patient_adapter.py`、`synthea_encounter_adapter.py` | Synthea CSV→Canonical Parquet | 公共 CSV/I/O/DQ 封装 + entity-specific 字段规范 |
| **Canonical DQ** | `validate_canonical.py --entity patient` | Canonical 输出→PASS/FAIL | 公共引擎 + entity contracts |
| **Stable keys** | `prepare_person_ids`、`prepare_visit_ids` | 源身份→稳定整数映射 | ID 逻辑可复用，键作用域各自明确 |
| **OMOP Mapper** | `person.py`、`visit_occurrence.py`、`condition_occurrence.py` | Canonical→OMOP-ready Parquet | I/O/lookup 可复用，医疗域映射独立 |
| **OMOP DQ** | `validate_omop.py --dataset person` | OMOP-ready→PASS/FAIL | 通用 required/FK/uniqueness + domain rules |
| **DB loader** | `load_cdm.py --dataset person` | OMOP-ready Parquet→PostgreSQL `etl.*_stage` | 尽量共用 JDBC loader，表配置不同 |
| **DB UPSERT** | `sql/upsert/person.sql` | Stage→`cdm.*` | 事务模板复用，冲突键和更新列按表定义 |
| **Recon** | `reconcile_batch.py` | 各层行数/状态/外键→batch summary | 公共运行组件 |
| **Airflow DAG** | `synthea_batch_omop.py` | 读取 manifest、提交作业、处理依赖和结果 | 一个 Batch DAG，而不是 18 套 DAG |

*一个 Synthea source 文件也可能产生多个 OMOP dataset（observations），所以不能依赖“文件名 = OMOP 表名”的一对一假设。*

### 7.2 当前已经写好的 Person 脚本怎样处理

| 旧脚本/程序 | 本轮动作 |
|---|---|
| `03-upload-synthea-landing.sh` | 改为一次性登记/上传完整 Batch，生成 V2 manifest |
| `04-ingest-patients-raw.sh` / `apps/ingest-patients-raw.py` | 保留作为 Synthea Adapter 的可用起点；修改字段契约与 V2 输入输出 URI |
| `05-validate-patients-raw.sh` | 改为 Canonical DQ 与发布 gate 的首个实例 |
| `07-prepare-person-etl.sh` | 保留稳定 person ID 设计和已分配的 113 个 ID，不重置映射 |
| `10-map-person-omop.sh` / `apps/map-person-omop.py` | 调整为读取 Canonical v1；保留验证过的 OMOP 业务逻辑 |
| `11-validate-omop-person.sh` | 调整到 Processed V2 URI，仍验证术语与 stable ID |
| `12-load-person-cdm.sh` | 保留经过重跑验证的 Stage + UPSERT；把路径和批次控制参数化 |

**Git 纪律：** 在 `feature/batch-v2-foundation` 等分支开发，脚本和配置通过 PR 合并到 `main`；Airflow GitSync 仍从 `main` 读取正式 DAG。避免直接改动 vendor/Synthea 源码或旧的已验证部署产物。

---

## 8. Airflow：一次 DAG Run 编排完整 Batch

### 8.1 目标 DAG 拓扑（不是现在已经存在）

```mermaid
flowchart TD
  A[Read and verify batch manifest] --> B[Validate all 18 CSV + checksums]
  B --> C[Register batch run]
  C --> D1[Adapter: patients]
  C --> D2[Adapter: encounters]
  C --> D3[Adapter: conditions]
  C --> D4[Adapter: procedures]
  C --> D5[Adapter: medications]
  C --> D6[Adapter: observations]
  D1 --> Q1[Canonical DQ/Publish patient]
  D2 --> Q2[Canonical DQ/Publish encounter]
  D3 --> Q3[Canonical DQ/Publish condition]
  D4 --> Q4[Canonical DQ/Publish procedure]
  D5 --> Q5[Canonical DQ/Publish medication]
  D6 --> Q6[Canonical DQ/Publish observation]
  Q1 --> P[Stable person IDs + OMOP person]
  P --> V[OMOP visit occurrence]
  Q2 --> V
  V --> T1[condition_occurrence]
  V --> T2[procedure_occurrence]
  V --> T3[drug_exposure]
  V --> T4[measurement / observation]
  Q3 --> T1
  Q4 --> T2
  Q5 --> T3
  Q6 --> T4
  T1 --> Z[Batch reconcile]
  T2 --> Z
  T3 --> Z
  T4 --> Z
  Z --> E[CORE_COMPLETE]
```

图中每个 OMOP node 逻辑上包含：stable ID lookup → PySpark mapping → OMOP DQ → JDBC Stage → SQL UPSERT → dataset recon。早期为了便于调试，仍可分成多个独立任务；不强行封装为一个不可观察的大脚本。

### 8.2 Airflow DAG 强制参数

```text
batch_id
landing_manifest_uri
source=synthea
source_version=v3.3.0
run_id (pipeline run identity)
canonical_version=v1
product_version=5.4.3
```

- DAG 从 manifest 读取输入路径/行数/校验和，**不硬编码文件路径、固定日期或 113**。
- `max_active_runs=1` 用于**首版单批次串行保护**，因为现有 `etl.person_stage` 采用 TRUNCATE + 写入；在需要并发批次之前再升级为 run-scoped stage 或显式 DB 锁。
- Raw 各 Adapter 可以并行，但依赖 CDM 的顺序由 Airflow 显式约束。
- 一项核心任务失败时，不允许调用最终 `CORE_COMPLETE`；已成功的其他实体产物可保留以供重试，但不能绕过 DQ/发布控制。
- CLI 手工 `.sh` 执行方式仍保留，作为 Airflow 故障排查与回归工具。
- Airflow 的 Spark Operator 提交方式和监控策略需基于已部署的 Spark Operator 验证后选择；不在设计稿里声称尚未写好的 operator 已经可用。

---

## 9. 质量、幂等与对账：本轮必须做的最小集合

### 9.1 三个 gate

1. **Batch intake gate：** 预期 18/18 CSV 都存在、单文件 SHA256 一致、文件非空、表头匹配 Synthea v3.3.0 版本契约；基础源 ID/FK 健康检查。
2. **Canonical gate：** 输出 Schema/type、必填字段、source record ID 唯一性（若该实体定义唯一）、时间有效性、source patient/encounter 引用；通过后才能发布 Raw。
3. **OMOP gate：** 目标列类型、NOT NULL、standard concept、主键唯一、稳定 person/visit ID、必要外键/域匹配；通过后才能批准 Processed 并加载。

### 9.2 Idempotency 与状态边界

- Landing `batch_id` 与 checksum 决定接收去重；源文件不可被后续重跑覆盖。
- Raw 和 Processed 使用单独 run 前缀；每次重跑产生新的 run，原 run 保留。
- `etl.person_id_map` 目前已证明同批重跑不重新分配 person ID；`visit_occurrence_id_map` 采用相同思想。
- JDBC 写 PostgreSQL `etl.<dataset>_stage`；事务性 `INSERT ... ON CONFLICT DO UPDATE`（或经验证的等效实现）写入 `cdm.*`。**严禁直接 append 到 CDM 表。**
- 现有共享 Stage 仅在首版单 DAG Run 顺序执行时安全；并发改造之前必须有互斥保护。
- 若一个 batch 重跑，验收应验证 CDM 不出现重复 person/visit/clinical events；对于更新已有行也必须保证关系一致。

### 9.3 Recon 示例

```text
BATCH: synthea-20261005-pop100-atlanta

Intake:                 18 / 18 CSV validated
Patient:                113 source → 113 canonical → 113 person loaded
Encounter:            5,799 source → ... canonical → ... visit loaded
Condition:            4,152 source → ... canonical → ... condition loaded
Procedure:           16,994 source → ... canonical → ... procedure loaded
Medication:           5,467 source → ... canonical → ... drug loaded
Observation:         76,588 source → ... canonical
                                   → measurement N + observation M + unmapped K
Other 12 files:            validated / DEFERRED, reason recorded

Final: CORE_COMPLETE only if required gates and per-domain recon PASS
```

`...`、`N/M/K` 是**必须在执行中填入的实际结果**，不是预期断言；一条输入可以拆成多个目标输出，也可能因明确规则被拒绝或暂缓。

---

## 10. Git 仓库与代码组织（最小够用，不做过度框架）

```text
healthcare-data-platform/
├── airflow/
│   └── dags/
│       └── synthea_batch_omop.py
├── spark/
│   ├── common/
│   │   ├── io.py
│   │   ├── contracts.py
│   │   ├── dq.py
│   │   └── jdbc.py
│   ├── adapters/synthea/
│   │   ├── patient.py
│   │   ├── encounter.py
│   │   ├── condition.py
│   │   ├── procedure.py
│   │   ├── medication.py
│   │   └── observation.py
│   ├── products/omop/
│   │   ├── person.py
│   │   ├── visit_occurrence.py
│   │   ├── condition_occurrence.py
│   │   ├── procedure_occurrence.py
│   │   ├── drug_exposure.py
│   │   ├── measurement.py
│   │   └── observation.py
│   ├── contracts/
│   │   ├── sources/synthea/v3.3.0/
│   │   ├── canonical/v1/
│   │   └── omop/5.4.3/
│   └── mappings/omop/
├── sql/
│   ├── etl_control/
│   ├── stage/
│   └── upsert/
├── infrastructure/
├── docs/
│   ├── architecture/
│   └── runbooks/
└── .github/workflows/
```

这是**建议的目标目录**，不表示仓库里已经存在这些文件。不要为了目录漂亮预先生成几十个空脚本；按实现顺序逐个加入。当前 `/data/spark/phase3c` 已验证脚本保留为可执行回归资产，再逐步纳入 Git。

---

## 11. 实施任务与交付顺序（集中力量做 Batch MVP）

| 阶段 | 本轮要实际完成的事 | 验收与交付 |
|---|---|---|
| **A. Freeze + Baseline** | 固定本文件；保存 Person 旧实现、Synthea 原始样例和旧路径；建 feature branch | 老流程可回归，旧数据未删 |
| **B. Whole-batch Intake** | 为 18 CSV 建清单、校验和、行数/header 验证；按 V2 Landing 路径一次性上传；建 `health-processing` bucket | 18/18 registered & verified；manifest 与实际 S3 一致 |
| **C. Person V2 Regression** | 建 Canonical patient v1；迁移现有 03/04/05/10/11/12 的输入输出 URI；加入最小 DQ 状态 | 新 V2 路径上仍然 `cdm.person=113`，stable IDs、stage diff、重跑无重复 |
| **D. Visit** | Encounters adapter、visit stable IDs、Visit concept discovery、OMOP mapper、DQ、Stage/UPSERT | `visit_occurrence` 批次落库、Person FK 与重跑校验通过 |
| **E. Other clinical domains** | Condition、Procedure、Drug、Observation/Measurement 的 adapter + mapper + DQ + load | 主要 core tables 全部完成；合法 FK/concept；所有未映射记录有理由 |
| **F. Airflow Batch DAG** | 一次 DAG Run 接受整个 batch、并行 adapter、依赖 CDM、失败停止及重跑 | 手工和 Airflow 两条执行方式输出一致；失败不会误标成功 |
| **G. Recon + Closure** | `etl.batch_run` / `etl.dataset_run`、Batch Summary、端到端回归、GitHub 文档 | 18 个 CSV 状态完整；所有 core domain recon 通过；`CORE_COMPLETE` |

**执行纪律：** 每个阶段只交付并验证一个可执行增量；先新脚本+日志跑绿，再继续下一步。遇到新的 mapping 问题时先做 discovery，不凭推测填 OMOP Concept IDs。每次 Git 修改走 feature branch → PR → merge，不直接把未经验证的 DAG 推到 `main`。

### 11.1 本次明确不开发

- HL7 实时接口、FHIR 外部 API、医院 Epic 接口。
- 跨来源患者匹配（MPI）、复杂流式窗口/重放。
- 大而全的 Routing 状态机、企业级不可变 Journal 服务、独立监控平台、UI 管理后台。
- 全部 18 CSV 的完整 OMOP 映射；非核心文件保留、登记、标记 deferred。
- 一开始就升级到并发多 batch、多租户生产级处理。首版 `max_active_runs=1`。

这些能力不妨碍将来扩展，但**不得阻碍本轮 Batch MVP 交付**。

---

## 12. 开发验收 Checklist

- [ ] V2 S3 三层目录及 processing 工作区已建，旧 S3/Person 数据仍可访问。
- [ ] 单一 Synthea `batch_id` 的 18 个 CSV 全部入 Landing；每个文件校验和、header、基础行数可核对。
- [ ] Landing manifest 完整；含 18 个文件项和真实 SHA256；batch 重传去重/冲突检查有效。
- [ ] Processing 新 run 隔离，不覆盖已发布旧数据。
- [ ] Canonical patient/encounter/condition/procedure/medication/observation 都有可测试的 Schema Contract 和源适配器。
- [ ] Raw/Processed 只在 DQ PASS 后批准，失败不能被下游当成成功读取。
- [ ] Person V2 回归：113 行、同一 stable IDs、stage/CDM diff 0；重跑后仍正确。
- [ ] Visit 与各临床核心表完成 OMOP 概念/主外键及重跑验证。
- [ ] Observation 能解释每条源记录最终属于 measurement、observation 或哪类明确处理结论。
- [ ] 18 个输入 CSV 都有明确 `VALIDATED` 结果及后续 `CDM_LOADED/DEFERRED/FAILED` 处理状态。
- [ ] Airflow 单个 Batch DAG Run 能串联全部必需任务，依赖、失败阻断和重试符合预期。
- [ ] Dataset/Batch Recon 通过；最终批次状态只有在所有本轮核心产物都通过时才是 `CORE_COMPLETE`。
- [ ] 全部代码、mapping、contracts、部署步骤和示例报告进 Git；真实密码/密钥/患者数据不入 Git。

---

## 13. 已知技术风险与防返工约束

1. **当前 Raw 还不是完全来源无关的 Canonical。** 迁移 `person` 时必须显式批准 Canonical v1 字段类型，而不是仅改 S3 目录名字。
2. **部分现有 person OMOP concept mapping 直接写死在 PySpark。** 本轮可以先保留已验证的映射规则作为 regression baseline；在抽公共组件时升级为版本化 mapping 文件与 join，但不能推迟 Visit/核心表交付。
3. **Vocabulary 映射是医疗域最大的不确定性之一。** Synthea `CODE` 可能需要 SNOMED CT、RxNorm 或其他 vocabulary 对应；不能简单把源 `CODE` 当 OMOP `concept_id`，也不能把 unmapped 强行设置为貌似有效的标准 concept。未知情况要保留源值并出具 mapping coverage 报告。
4. **S3 批量写不是原子事务。** 写到 run 级临时路径，DQ PASS 后登记 `approved/published` 状态；下游只用批准 URI。先实现控制表与 gate，不建设额外发布服务。
5. **PostgreSQL Stage 并发问题。** 当前 `TRUNCATE stage` 在并发时危险；首版 Airflow 仅允许一个活动 batch run，若扩容必须先引入隔离 Stage/锁，不允许悄悄修改并发参数。
6. **结果不可按 18 CSV = 18 OMOP 表来验收。** 需要按 Source Contract → Canonical Entity → OMOP Domain 的映射关系审核，支持一个文件拆成多张表或多个源合一张表。
7. **不要以固定 100 作为 patient 行数。** 此次 Synthea seed=20261005、population=100 的输出有 113 个 patient 记录；所有断言应读取 manifest/实际行数，测试夹具可明确断言 113。
8. **合成数据也要演练安全。** 用户/数据库密码走 Kubernetes Secret；日志和 S3 路径不要输出 SSN、姓名等记录内容；工作区可清理而 Landing 保留原输入。

---

## 14. 这份文档的最终定位

这是一份**可实际开始编码的批处理开发基线**，不是未来所有 Healthcare 系统的终极架构，也不是别的公司的内部流程复制版。

**我们这次集中实现：**

```text
Synthea v3.3.0 / one batch / 18 CSV files
         ↓ 18/18 manifest + integrity validation
S3 Landing (immutable payload)
         ↓ dataset adapters + per-run processing
Canonical Raw (6 core clinical datasets)
         ↓ stable person / visit IDs + OMOP mappings
OMOP Processed (person, visit, condition, procedure, drug, measurement/observation)
         ↓ JDBC stage + transactional UPSERT
PostgreSQL OMOP CDM
         ↓ batch reconciliation
Airflow batch DAG → CORE_COMPLETE
```

> **开发下一步固定为阶段 B：Whole-batch Intake & V2 Landing。** 完成整批 18 个 CSV 的 `manifest.json`、checksum 验证和新 Landing 路径，再做 Person V2 回归，之后直接推进 Visit 及其他核心临床表。原架构中的非批处理能力不在本轮开发计划内。
