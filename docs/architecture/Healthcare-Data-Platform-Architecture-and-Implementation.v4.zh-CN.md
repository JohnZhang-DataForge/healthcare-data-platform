# Healthcare Data Platform — Architecture & Implementation Baseline V4

> **版本：V4.0 — Consolidated Runtime & Orchestration Baseline**
> **更新日期：2026-10-10**
> **状态：当前权威总设计（Authoritative Master Design）**
> **仓库：** `JohnZhang-DataForge/healthcare-data-platform`
> **适用环境：** Kubernetes + SeaweedFS(S3) + Airflow + Spark Operator/PySpark + PostgreSQL 17 / OMOP CDM 5.4.3 + GitHub
> **后续扩展：** Azure Blob/ADLS Gen2、Microsoft Fabric、dbt-fabric、MLflow、Mirth/HL7、FHIR、GitHub Actions、Argo CD

---

## 0. 文档定位与版本关系

本文件从 2026-10-10 起作为项目的**总设计与实施基线**。

它合并并取代以下两份文档作为“后续开发首先阅读的主设计”：

1. `Emory-Healthcare-Data-Platform-Architecture.v3.md`
   - 2026-10-05；
   - 重点是三节点 Kubernetes 基础设施、SeaweedFS、Airflow、Spark、PostgreSQL/OMOP、Mirth 等组件职责；
   - 适合作为基础设施架构历史基线。
2. `Healthcare-Batch-ETL-Hybrid-Fabric-ML-Implementation-Design.zh-CN.v2.1.md`
   - 2026-10-08；
   - 重点是 Batch-first、Canonical/Processed、OMOP、Airflow 整批编排、Azure/Fabric/ML 的实施基线；
   - 内容日期比 V3 更新，但版本号属于另一条实施设计线。

因此，不能简单理解为“V3 一定比 V2.1 新”。V4 将两条设计线合并。

历史文档继续保留，不删除，用于追溯设计演化。

---

## 1. V4 核心决策摘要

后续开发以本节为优先原则。

1. **先让平台真正运行起来。** 当前优先级从“继续逐张做 OMOP 表”调整为“先把已完成的 Person + Visit 封装为可由 Airflow 编排的 Kubernetes 工作负载，并用新生成的 Synthea batch 真正跑通”。
2. **Synthea 也成为平台工作负载。** 使用独立 `synthea-generator` image/Kubernetes Job，根据参数生成一批 synthetic patients 及其关联 encounter/condition/procedure/medication/observation，并发布到 Landing。
3. **调试阶段以 `population_size=20/50` 为主。** `population_size` 表示 patient 数量，不代表所有 CSV 的行数。先使用固定 seed 保证可重复，再引入随机 population/seed。
4. **数据产生也是 DAG 的一部分。** Airflow 第一版主线从 `Generate Synthea → Landing → Person → Visit → Reconcile` 开始，而不是从人工准备好的 CSV 开始。
5. **建立两个主要项目 image。** 第一阶段：`healthcare-data-platform-synthea` 和 `healthcare-data-platform-runtime`。Spark transformation 暂时可继续使用已验证 Spark image；后续再构建项目专属 Spark image。
6. **TASK-003 是 Reference Implementation。** 后续 `condition_occurrence`、`procedure_occurrence`、`drug_exposure`、`measurement`、`observation` 复用其架构，不复制其代码量。
7. **从 Condition 开始抽取通用框架。** Raw publish、Processed publish、ID mapping、materialization、reconciliation、evidence/hash 等逻辑逐步转为共享 Python 模块/通用 runner。
8. **运行时事实优先于文档。** 只有真实运行证据才能把能力从 `PLANNED` 改为 `VERIFIED`。
9. **不对已冻结 batch 盲目重跑。** 已提交的 Person/Visit baseline 只用于 read-only verification；新的 Airflow 执行使用新 batch。
10. **文档、经验和开发方法纳入正式工程资产。** 主设计中英双版；`docs/runbooks/development-lessons.md` 聚合经验；每个关键步骤保留 `development-lessons-taskNNN-stepXX.md`；项目开发规则维护在 `docs/skill/SKILL.md`。

---

## 2. 当前平台拓扑与节点职责

| 节点 | 标签/角色 | 当前职责 | 主要组件 |
|---|---|---|---|
| `master01` | control-plane | Kubernetes 管理入口 | Kubernetes control plane、kubectl、Helm |
| `worker01` | `workload=storage` | Data Lake / Landing | SeaweedFS Master/Filer/Volume/S3、本地持久化 |
| `worker02` | `workload=platform` | Orchestration / Compute | Airflow 3.2.2、Spark Operator 2.5.2、动态 Driver/Executor |
| `worker03` | compute / relational | OMOP relational serving | PostgreSQL 17、OMOP DB、Airflow metadata DB |
| `runner01` | control / CI runner | 开发、验证、后续 CI/self-hosted runner | Git、kubectl、开发脚本 |

原则：

- master01 不承载主要数据工作负载；
- storage、orchestration/compute、relational serving 分离；
- Spark 使用 SparkApplication 动态 Pod，不部署常驻 standalone master/worker；
- runner01 逐步从“手工执行主机”转为 control/CI runner。

---

## 3. 存储与数据库

### 3.1 StorageClass

- `local-path`：普通实验组件；
- `seaweed-local`：worker01，SeaweedFS；
- `postgres-local`：worker03，PostgreSQL；
- 关键数据类 StorageClass 使用 Retain 时，PV/PVC 删除必须人工确认实际数据状态。

### 3.2 SeaweedFS

SeaweedFS 是本地 S3-compatible Data Lake / Landing Zone。

当前逻辑 bucket：

```text
health-landing
health-processing
health-raw
health-processed
health-archive
postgres-backup
```

职责：

```text
Landing     = 源批次原始文件与 manifest
Processing  = run 级临时 workspace / DQ / rejects
Raw         = 已通过 Canonical Gate 的 Canonical Parquet
Processed   = 已通过产品/OMOP Gate 的目标数据集
Archive     = 历史/归档辅助区
Backup      = PostgreSQL backup
```

### 3.3 PostgreSQL / OMOP

PostgreSQL 17 运行于 worker03。

主要数据库：

```text
omop
  ├── cdm.*
  └── etl.*

airflow
  └── Airflow metadata
```

OMOP 是标准化医疗研究数据模型，不是编排器或计算引擎。

---

## 4. Namespace 与平台组件

| Namespace | 作用 |
|---|---|
| `dw-seaweedfs` | SeaweedFS / S3 |
| `dw-postgre` | PostgreSQL / OMOP |
| `dw-airflow` | Airflow |
| `dw-spark` | Spark Operator / SparkApplication |
| future `data-warehouse` | ClickHouse 等分析服务 |
| future `streaming` | Kafka/streaming，仅在明确需要时加入 |

职责边界：

```text
SeaweedFS = Data Lake / Object Storage
Airflow   = Orchestration
Spark     = Compute / Transformation
Postgres  = Relational Serving
OMOP      = Healthcare Standard Data Model
Mirth     = HL7 Interface Engine (future)
Fabric    = Managed analytics/ML platform (future)
```

---

## 5. 当前已验证状态（2026-10-10）

| 能力 | 状态 |
|---|---|
| Kubernetes 三 worker + control-plane | VERIFIED |
| SeaweedFS S3 + authenticated access | VERIFIED |
| PostgreSQL 17 persistence | VERIFIED |
| OMOP CDM 5.4.3 + vocabulary | VERIFIED |
| Airflow 3.2.2 / GitSync / UI / LocalExecutor | VERIFIED |
| Spark Operator 2.5.2 / Spark 3.5.7 / Driver+Executor lifecycle | VERIFIED |
| TASK-001 whole-batch Landing | VERIFIED |
| TASK-002 Person V2 | VERIFIED (`cdm.person=113`) |
| TASK-003 Encounter → Visit | VERIFIED |
| TASK-003 Processed Visit rows | 5799 |
| Visit stable ID mappings | 5799 |
| Visit ID range | 2..5800 |
| `cdm.visit_occurrence` | 5799 rows |
| Visit sequence | `5800|true` |
| TASK-003 implementation checkpoint | `373439c323c82388f559538204b1ba6348916fa0` |
| Full healthcare Batch DAG | PLANNED / NEXT |
| Synthea Generator Kubernetes Job | PLANNED / NEXT |
| Project runtime image | PLANNED / NEXT |
| Condition/Procedure/Drug/Measurement/Observation | PLANNED |
| Azure/Fabric/ML | PLANNED |
| Mirth/FHIR/HL7 | PLANNED |

TASK-003 已建立第一套完整参考模式：

```text
source
  ↓
canonical
  ↓
Raw
  ↓
Processed
  ↓
stable surrogate IDs
  ↓
OMOP CDM
  ↓
independent verification
```

---

## 6. Synthea Batch 目标与剩余 OMOP 核心表

一次 Synthea export 是一个 batch，不是 18 个独立 batch。

核心转换范围：

| Source | Canonical | OMOP target | 当前状态 |
|---|---|---|---|
| `patients.csv` | patient | `person` | VERIFIED |
| `encounters.csv` | encounter | `visit_occurrence` | VERIFIED |
| `conditions.csv` | condition | `condition_occurrence` | NEXT |
| `procedures.csv` | procedure | `procedure_occurrence` | PLANNED |
| `medications.csv` | medication | `drug_exposure` | PLANNED |
| `observations.csv` | observation | `measurement` + `observation` | PLANNED |

因此当前还剩 **4 个 source domain、5 张核心 OMOP target table**。

其余 Synthea 文件仍必须进入 batch manifest 和 intake verification，但本阶段可以明确标记 `DEFERRED`，不伪装成已完成 OMOP 映射。

---

## 7. V4 新主线：Synthea Generator 也是 Kubernetes Workload

### 7.1 目标

将数据生成纳入平台，而不是依赖手工准备 CSV。

```text
Airflow DAG
    |
    v
Synthea Generator Job
    |
    v
Generated Synthea CSV batch
    |
    v
Landing Publisher
    |
    v
SeaweedFS health-landing
    |
    v
Batch Intake Gate
    |
    v
Person → Visit → Reconcile
```

### 7.2 Synthea Generator Image

建议 image：

```text
healthcare-data-platform-synthea:<git-sha>
```

输入参数第一版：

```text
population_size=20|50
seed=<fixed debug seed>
state=Georgia
city=Atlanta
source_version=v3.3.0
export_csv=true
```

`population_size=50` 表示生成 50 个 synthetic patients；关联 encounters、conditions、procedures、medications、observations 数量由 Synthea 纵向病程决定，不等于 50 行。

第一阶段使用固定 seed：

```text
same parameters + same seed
→ reproducible source batch
```

系统稳定后再支持：

- random seed；
- configurable population range；
- geography/scenario config；
- FHIR export；
- controlled incremental test data。

### 7.3 Landing Publication

Generator 或紧随其后的 Landing Publisher 必须完成：

1. 生成 CSV；
2. 验证预期文件集合；
3. 验证文件非空/header；
4. 计算 SHA256；
5. 生成 batch_id；
6. 上传 `payload/csv/*`；
7. 发布 manifest **LAST**；
8. 输出 `batch_id` 与 `manifest_uri` 给 Airflow。

推荐输出：

```text
SYNTHEA_GENERATION=PASS
POPULATION_SIZE=50
LANDING_PUBLICATION=PASS
BATCH_ID=...
MANIFEST_URI=s3://...
```

---

## 8. Batch Identity 与 Pipeline Run Identity

不要混淆数据身份和处理身份。

```text
batch_id
= 这一批输入数据是谁

pipeline_run_id
= 这一次是谁处理它
```

同一个 immutable batch 可以有多个验证/处理 run。

建议：

```text
batch_id=synthea-20261010-pop50-seed10001
pipeline_run_id=synthea-omop-20261010T210000Z-<suffix>
```

已冻结 batch 不通过新 DAG 做盲写式重跑；需要演示/回归时要么 read-only verify，要么生成新 batch。

---

## 9. Container Image 策略

### 9.1 第一阶段两个项目 image

#### A. `healthcare-data-platform-synthea`

负责：

- Java/Synthea runtime；
- parameterized synthetic population generation；
- batch output preparation；
- 可选择包含 Landing publisher，或由 runtime image 接管 publication。

#### B. `healthcare-data-platform-runtime`

负责：

- Python utilities；
- contracts；
- batch/manifest validation；
- DQ；
- mapping/control utilities；
- ID reconciliation/allocation；
- database loading/materialization utilities；
- final reconciliation；
- shared evidence/hash logic。

### 9.2 Spark Image

短期：继续使用已验证 Spark 3.5.7 image + 当前代码分发机制。

中期：构建：

```text
healthcare-data-platform-spark:<git-sha>
```

包含：

- stable Spark/Python runtime；
- `spark/apps/*`；
- shared libraries；
- JDBC/S3A/JAR dependencies；
- exact version metadata。

部署最终优先使用 immutable digest。

### 9.3 不进入 image 的内容

禁止 bake：

- S3 keys；
- PostgreSQL passwords；
- GitHub token；
- Azure credentials；
- kubeconfig；
- batch_id/run_id；
- environment-specific endpoint。

这些通过 Kubernetes Secret / Config / runtime parameters 注入。

---

## 10. 第一版 Airflow 可运行 DAG

目标 DAG（MVP）：

```text
Generate Synthea Batch
        |
        v
Publish / Verify Landing
        |
        v
Process Person
        |
        v
Verify Person
        |
        v
Process Encounter / Visit
        |
        v
Verify Visit
        |
        v
Batch Reconcile
        |
        v
CORE_PARTIAL_COMPLETE
```

第一版重点不是把 5 张剩余表全部接上，而是证明：

- Airflow 能提交真正 Kubernetes workload；
- source generation 在集群内完成；
- 新 batch 自动进入 Landing；
- Person/Visit 可以处理新 batch；
- 每个 task 有可观察 PASS/FAIL；
- DAG 最终给出 reconciliation。

后续扩展：

```text
                         ┌─ Condition ──────────┐
                         |
Generate → Person → Visit ┼─ Procedure ──────────┼→ Reconcile
                         |
                         ├─ Drug ───────────────┤
                         |
                         └─ Measurement/Obs ────┘
```

---

## 11. Airflow 参数与依赖原则

建议 DAG 参数：

```text
population_size
seed
state
city
source_version
batch_id (optional if generate_new_batch=true)
pipeline_run_id
canonical_version
product_version=5.4.3
generate_new_batch=true|false
```

原则：

- DAG 不硬编码 113/5799 或固定历史 run；
- task 之间只传 lightweight identity/URI/status，不传大文件；
- Raw 层可在依赖允许时并行；
- OMOP 依赖按 `person → visit → clinical facts`；
- failure 不允许最终 COMPLETE；
- 已成功 immutable artifacts 保留用于恢复；
- CLI runner 保留作为调试/回归接口。

---

## 12. TASK-003 之后的开发策略

TASK-003 是 Reference Implementation，不是后续每张表都复制同样代码量的模板。

### 12.1 下一张表：Condition

Condition 的双重目标：

1. 完成 `condition_occurrence`；
2. 同时提取 TASK-003 中可复用 framework。

Entity-specific 内容主要是：

```text
source contract
business key
concept mapping
target columns
FK rules
DQ rules
```

Generic 内容应抽取：

```text
canonical publish
processed planning/publication
reservation/write intent/permit
evidence/hash
ID reconciliation/allocation
CDM staging/materialization
post-commit reconciliation
```

### 12.2 Procedure 目标

到 Procedure 时应尽量成为 configuration-driven implementation。

如果 Procedure 仍需要复制数千行新的 Bash，说明通用抽象不足。

### 12.3 Drug / Observation

- `drug_exposure`：重点在 medication vocabulary/domain mapping；
- `observations.csv`：最复杂，需要按语义路由 `measurement` vs `observation`，并处理 value/type/unit/concept/domain。

---

## 13. 数据层与发布边界

### 13.1 Landing

原始 batch，不覆盖。

```text
s3://health-landing/source=synthea/source_version=<v>/ingest_date=<UTC>/batch_id=<B>/
  manifest.json
  payload/csv/*.csv
```

manifest LAST。

### 13.2 Processing

run 级 workspace：

```text
s3://health-processing/source=synthea/batch_id=<B>/run_id=<R>/...
```

不是下游正式消费层。

### 13.3 Canonical Raw

```text
s3://health-raw/canonical_version=v1/entity=<entity>/source=synthea/.../run_id=<R>/
  data/
  dq/result.json
  manifest.json
```

只有 APPROVED manifest 指向的数据可下游消费。

### 13.4 Processed

按目标数据集组织，支持 immutable run 与精确 lineage。

### 13.5 CDM

最终关系型权威数据。

---

## 14. DQ / Idempotency / Reconciliation 标准

每层必须有实际验收，不以 exit code 0 代替数据正确性。

### 14.1 Dataset 基础证据

- row count；
- unique business key count；
- contract version；
- source lineage；
- SHA256/fingerprint；
- required-field violations；
- FK violations；
- domain/concept checks。

### 14.2 Mutation 标准

重大 mutation 使用：

```text
read-only preflight
  ↓
mutation contract
  ↓
rehearsal where practical
  ↓
one controlled execution
  ↓
independent reconciliation
  ↓
canonical freeze
```

未知 commit 状态：**禁止 blind retry**，必须重新建立 read-only session，从 persistent state reconciliation。

### 14.3 ID 标准

- stable ID 不要求 gapless；
- sequence gap 可以合法存在；
- same business key → same stable ID；
- 不自动 rewind sequence。

---

## 15. Runtime 与 Git 边界

Git：

```text
canonical source
contracts
tests
manifests
docs
SQL
permanent scripts
```

不进 Git：

```text
runtime/
raw healthcare files
Parquet outputs
credentials
kubeconfig
temp_shell/
local.env
```

一句话：

> Git 说明系统如何工作；runtime 说明某次运行发生了什么。

---

## 16. Git / CI / Delivery Roadmap

短期：

```text
local development
→ tests
→ Git checkpoint
→ Airflow GitSync / manifests
```

下一阶段：

```text
Git commit
  ↓
unit + contract tests
  ↓
build image
  ↓
security scan
  ↓
push GHCR
  ↓
record immutable digest
  ↓
Airflow/Kubernetes execute
```

未来再加入 Argo CD/GitOps，不阻塞当前 runtime MVP。

---

## 17. Azure / Fabric / ML 阶段 II

阶段 II 不阻塞本地 Batch MVP。

目标：

1. S3 + Azure Blob/ADLS Gen2 双目标 Landing 验证；
2. PostgreSQL OMOP 仍是本地 CDM authority；
3. 选定 OMOP tables 批/增量复制到 Azure/OneLake Delta；
4. Fabric Lakehouse/Notebook；
5. dbt-fabric Gold models；
6. Fabric Warehouse SQL serving；
7. MLflow batch feature/score lifecycle。

Azure/Fabric 成功必须有真实运行证据，不能因为设计存在就在简历/文档中写成 VERIFIED。

---

## 18. FHIR / HL7 / Mirth 阶段

当前 Synthea CSV Batch 主线稳定后再扩展。

推荐：

```text
HL7 v2 / MLLP
  ↓
Mirth Connect
  ↓
Landing
  ↓
Airflow
  ↓
Spark
  ↓
Canonical / OMOP
```

FHIR R4：

```text
FHIR Patient/Encounter/Condition/Observation
  ↓
source-specific adapter
  ↓
同一 Canonical / OMOP 主线
```

Adapter 与 Mapper 解耦保证不同 source 可以复用 OMOP transformation framework。

---

## 19. 文档治理

### 19.1 主设计

权威设计提供中英双版：

```text
docs/architecture/Healthcare-Data-Platform-Architecture-and-Implementation.v4.zh-CN.md
docs/architecture/Healthcare-Data-Platform-Architecture-and-Implementation.v4.en.md
```

历史 V3/V2.1 保留，不删除。

### 19.2 Development Lessons

聚合文档：

```text
docs/runbooks/development-lessons.md
```

每个重要步骤保留独立源文档：

```text
docs/runbooks/development-lessons-taskNNN-stepXX.md
```

周期性把可泛化经验整理进 `development-lessons.md`，但**不删除** step-specific lessons。

### 19.3 Project Skill

```text
docs/skill/SKILL.md
```

持续记录：

- 开发流程；
- shell 交付规范；
- PASS/freeze 规则；
- mutation/recovery 规则；
- Git/doc 规范；
- lessons consolidation 规则；
- 新形成且已经验证的开发习惯。

---

## 20. 当前优先 Roadmap

### Phase A — Documentation & Git Baseline

- 整理 V4 中英主设计；
- 建立 `development-lessons.md`；
- 规范 step lessons 命名；
- 更新 `docs/skill/SKILL.md`；
- Git checkpoint。

### Phase B — Synthea Runtime

- build `healthcare-data-platform-synthea` image；
- Kubernetes Job 参数化生成 20/50 patients；
- 自动 publish immutable Landing batch；
- verify manifest/checksum。

### Phase C — Runtime Image

- build `healthcare-data-platform-runtime`；
- 封装 validation/DQ/ID/materialization/reconciliation 工具；
- 保留 CLI 调试接口。

### Phase D — Airflow Person + Visit MVP

- Airflow DAG 编排 Synthea generation；
- Landing intake；
- Person pipeline；
- Visit pipeline；
- final reconcile；
- 使用**新 batch**真实写入并验收。

### Phase E — Clinical Facts

按顺序：

```text
Condition
→ Procedure
→ Drug
→ Measurement / Observation
```

Condition 阶段同步做 shared framework extraction。

### Phase F — Hybrid / Healthcare Integration

- Azure/Fabric/ML；
- Mirth/HL7；
- FHIR；
- CI/CD/GitOps；
- ATLAS/WebAPI / dbt / research workflows。

---

## 21. 最终架构目标

平台最终不是“安装了很多产品”，而是提供一条可解释、可验证、可重放、可扩展的数据工程链路：

```text
Synthetic / Healthcare Sources
        ↓
Kubernetes Source Jobs / Interfaces
        ↓
Immutable Landing Batch
        ↓
Airflow Orchestration
        ↓
Spark / Runtime Jobs
        ↓
Canonical Raw
        ↓
OMOP Processed
        ↓
Stable IDs + Transactional CDM
        ↓
Reconciliation / Evidence
        ↓
Analytics / Fabric / Research / ML
```

**V4 的短期成功标准：不是先把所有表做完，而是先把这条链真正运行起来。**
