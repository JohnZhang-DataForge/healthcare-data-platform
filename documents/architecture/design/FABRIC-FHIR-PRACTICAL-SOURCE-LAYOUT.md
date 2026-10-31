---
status: adopted-file-level-implementation-plan
scope: fhir-intake-bronze-canonical-silver-and-future-omop-gold
verified_main_sha: 95b0d561833088ecceb2b6874fcfce4f298868df
proposal_branch: feature/fabric-fhir-blob-ingestion-design-20261027
verified_at: 2026-10-31
runtime_status: no-new-runtime-or-business-code
---

# Fabric FHIR — 可直接实施的源码、原生 Item、OneLake 目录和开发切片

> **2026-10-31 最终开发依据：** [Fabric-native ADR](FABRIC-NATIVE-NOTEBOOK-PIPELINE-ENVIRONMENT-ADR-20261031.md)。旧两只 Wheel 和独立 Fabric IO/runtime 方案已作废，本文的目录清单按下面最终版本执行；尚未创建任何实际 Native Items 或业务源码。 这份文档补充 [Shared Engine 代码归属规范](../../engineering/development/SHARED-DATA-ENGINE-STRUCTURE-AND-OWNERSHIP.md) 和 [Medallion 数据架构 ADR](FABRIC-MEDALLION-CANONICAL-ADR-20261030.md)。长期领域归属与业务数据语义由前两者决定；**本文只负责把它们落到实际路径、现有代码可提取点、OneLake Catalog 和交付顺序**。

## 1. 已核实的实际目录与不可破坏的现状

- 本计划的初始源码静态核查基线为 `95b0d561833088ecceb2b6874fcfce4f298868df`，随后**最终架构已通过 PR #533 合并 main（2026-10-31，merge SHA `7060cbb673ea9bcea1de9311f58c1a4145316b35`）**。该 SHA 是历史证据而非永久最新 Main；所有新业务代码必须从实施当天的最新 main 建分支并重新核对相关源码和 Contract。
- `local-data-platform/spark/apps/person/synthea_patient_adapter.py`、`visit/synthea_encounter_adapter.py` 同时耦合 Spark Job、S3/Manifest、处理与验证；`person/map_canonical_patient_to_omop.py` 还会从 PostgreSQL JDBC 读取映射。不能整文件复制到 Shared；必须先抽纯 DataFrame 函数。
- `local-data-platform/spark/apps/visit/map_encounter_to_visit_candidate.py` 是现有仅 DataFrame 输入/输出的独立映射逻辑，适合**优先做有行为对照的提炼**；现有 Patient/Encounter Contract 保持 `local-data-platform/spark/contracts/canonical/` 唯一权威，不在本规划中创建第二套。
- `azure-fabric/workspaces/healthcare-omop/notebooks/ingestion/.gitkeep` 和 `pipelines/.gitkeep` 目前只是占位；`azure-fabric/workspaces/johnzhang-test/` 已有 Git 原生 Notebook/Pipeline 的 `.platform` 和 `notebook-content.py` / `pipeline-content.json` 实例，可作为**格式参考**，不得复制其 logicalId 以创建新业务 Item。
- `azure-fabric/deployment/trial_smoke_publisher.py` 以严格固定 Workspace/Item 清单发布 `johnzhang-test` Smoke；不能直接用于正式 `healthcare-omop`，不能通过简单改常量覆盖它。
- Terraform 现有两套历史/过渡路径：`azure-fabric/infra-terraform/components/`（旧组件根）与 `fabric-workspace/healthcare-omop/{workspace,onelake}/`、`shared-infra/{storage,connection}/`（Workspace-Scoped）。后一组新根已有真正 `main.tf`/State 依赖。**本轮不搬任何 Terraform 文件，实际 Apply 前需核实哪个 State/Workflow 拥有当前 Workspace、Connection 和 Lakehouse**。
- `azure-fabric/infra-terraform/modules/onelake/main.tf` 创建配置含 `configuration.enable_schemas = true`；但此**源码**不保证当前现存 Lakehouse 已启用 Schema。当前 `healthcare-omop/onelake/terraform.tfvars` 提议 `lh_omop_analytics`，所有 Notebook 实际 Lakehouse ID/名称必须从 Live Catalog + 已批准 State 独立读回，不能只按文件名推断。

### 真实现有链接

- [Local source and contracts](../../../local-data-platform/spark/apps/) · [Local Contract authority](../../../local-data-platform/spark/contracts/canonical/)
- [Trial native Notebook example](../../../azure-fabric/workspaces/johnzhang-test/notebooks/nb_trial_smoke.Notebook/) · [Trial native Pipeline example](../../../azure-fabric/workspaces/johnzhang-test/pipelines/pl_trial_smoke.DataPipeline/)
- [Trial-only publisher](../../../azure-fabric/deployment/trial_smoke_publisher.py) · [Lakehouse Terraform module](../../../azure-fabric/infra-terraform/modules/onelake/main.tf)
- [Existing Fabric CODE map](../../systems/azure-fabric/CODE.md) · [Shared Engine CODE map](../../systems/data-platform/shared-engine/CODE.md)

## 2. 第一批真正要写的 Python 项目：共享业务计算

**将来新增（本轮只设计）**。不建和数据库、云 SDK、Filesystem 绑定的共享单体，也不复制 Local 旧 CLI：

~~~text
shared-data-engine/
├── AGENTS.md                              # 已有
├── pyproject.toml                         # [P1] healthcare-data-engine wheel
├── src/healthcare_data_engine/
│   ├── __init__.py                        # [P1] 对外版本/API
│   ├── models/
│   │   ├── batch_context.py              # [P1] source + processing + publication identity
│   │   └── source_identity.py             # [P1] source_system / hospital/feed namespace
│   ├── adapters/
│   │   └── fhir_r4/
│   │       ├── bundle.py                  # [P1] Bundle/individual Resource → normalized items
│   │       ├── references.py              # [P1] fullUrl/urn:uuid/relative refs
│   │       ├── patient.py                 # [P1] FHIR Patient → Canonical Patient DF
│   │       └── encounter.py               # [P1] FHIR Encounter → Canonical Encounter DF
│   ├── canonical/
│   │   └── validation.py                  # [P1] pinned contracts / allowed clinical semantics
│   ├── quality/
│   │   └── result.py                      # [P1] ACCEPT / QUARANTINE / REJECT + metrics
│   ├── mapping/
│   │   └── omop/
│   │       ├── person.py                  # [P3] extracted pure mapping only
│   │       ├── visit_occurrence.py        # [P3] reuse Local pure visit function
│   │       └── concepts.py                # [P3] versioned terminology mappings
│   ├── identity/
│   │   └── mapping_plan.py                # [P3] no writes / source-aware keys
│   └── reconciliation/
│       └── person_visit.py                # [P3] pure counts/PK/FK audit
└── tests/
    ├── fixtures/fhir_r4/                 # [P1] synthetic good/bad + references
    ├── unit/                             # [P1] parser, Canonical, error classification
    ├── contract/                         # [P1] pinned Local Patient/Encounter v1
    └── cross_runtime/                    # [P2] Local Spark vs Fabric runtime evidence
~~~

**禁止现在提前建空的 `csv/`、`hl7_v2/`、`observation/`、`condition/` 或新的 `contracts/` 复制目录**：等该实体的真实功能和测试进入 PR 时再新增，现阶段只有 FHIR Patient/Encounter。共享包只接受已验证原始内容/解码后的输入或 DataFrame 和显式 Contract/Profile/ID Map 快照；不负责下载 Blob 或写 Delta。发布 wheel 时使用固定版本、精确 hash 与兼容性测试，不能使用可变 Latest。

共享 API 候选（**先于代码冻结函数签名、可小幅迭代，但不能让调用端自造 Schema**）：

~~~python
parse_fhir_resources(raw_objects, source_context) -> ParsedResources
normalize_fhir_patient(resources, canonical_contract, context) -> TransformResult
normalize_fhir_encounter(resources, canonical_contract, context) -> TransformResult
map_patient_to_person(approved_patient_df, concept_snapshot, identity_plan, context) -> TransformResult
map_encounter_to_visit(approved_encounter_df, approved_person_map_df, mapping_profile, context) -> TransformResult
~~~

`TransformResult` 至少携带 rows DataFrame / rejects / metrics / contract+code version；既不提交表也不创建 Spark Session。真实资源缺字段必须 Quarantine 或另批准 Canonical v2，不造生日/race/Encounter end date。

## 3. Fabric Native Item 目录及真正的 Spark 执行

~~~text
azure-fabric/
├── workspaces/
│   ├── healthcare-omop/                        # Git Folder ↔ real Fabric Workspace
│   │   ├── notebooks/ingestion/
│   │   │   └── nb_fhir_ingest.Notebook/
│   │   │       ├── .platform                  # generated by Fabric
│   │   │       └── notebook-content.py        # actual Spark ETL, not empty launcher
│   │   ├── pipelines/
│   │   │   └── pl_fhir_ingest.DataPipeline/
│   │   │       ├── .platform
│   │   │       └── pipeline-content.json      # dependencies/retry/Notebook Activity
│   │   └── environments/
│   │       └── env_healthcare.Environment/     # actual exported Environment Item
│   └── johnzhang-test/                        # existing Smoke, leave as-is
├── infra-terraform/                           # existing modules/state, no move
├── deployment/                                # existing Trial publisher, no re-purpose
└── openlineage/                               # existing integration
~~~

The exact selected Fabric Workspace Git folder is `azure-fabric/workspaces/healthcare-omop/`; the chosen `notebooks/`, `pipelines/`, `environments/` directories must mirror actual Fabric UI folders. These names are our convention. Native `.platform` IDs/Environment files come from real Fabric export (not Trial IDs).

- **Fabric Pipeline**: cross-step orchestration, Notebook Activity, scheduling/parameters/retry/failure handling.
- **Fabric Notebook**: meaningful, visible Spark steps for Manifest/hash checks, native Shortcut/Copy/source read, Bronze evidence, Shared FHIR/Canonical/DQ transform, Spark/Delta Silver/quarantine write, independent two-table readback/approval and structured returned status.
- **Shared Engine**: one installable wheel under `shared-data-engine/`. Environment installs a fixed version from CI artifact, explicitly Publish and read back effective version. Shared Python source is not mapped to Environment; don't use session `%pip install` as release.
- **No speculative I/O package**: prior `azure-fabric/ingestion/`, `runtime/`, `libraries/healthcare-fabric-io/` and `healthcare_fabric` wheel are superseded. Native Fabric I/O first. If complex repeated platform code emerges, open an independent reviewed Change before extracting minimal reusable helpers.
- **Gold**: Warehouse T-SQL Writer POC (not yet implemented), cross-table transaction/readback and ownership still to prove.


## 4. 另外一套真实目录：Fabric Lakehouse 数据，不是 Git

**仅为将来 Lakehouse 实例的目标逻辑 Catalog；当前没创建这些 Table、Schema、Shortcut。** 优先复用现有真正已获授权的 Lakehouse。先核实真实 Item GUID、`enableSchemas` 与 Terraform State；`lh_omop_analytics` 是 repo 配置中候选名字，不能凭它假设线上已经存在。

~~~text
Fabric Workspace: healthcare-omop
  OneLake Lakehouse: <LIVE VERIFIED LAKEHOUSE ID>
    Files/
      bronze/landing/                   # shortcut to verified Blob immutable objects
      bronze/frozen/                    # ONLY if Copy/retention mandatory
    Tables/
      bronze.ingest_receipt             # one verified object/batch receipt
      silver.canonical_patient          # approved Canonical Patient Delta
      silver.canonical_encounter        # approved Canonical Encounter Delta
      quarantine.fhir_resource          # failed source resources/reasons
      ops.silver_approval               # batch + processing/version approvals
      ops.ingest_run                    # lifecycle, hash/count, error status
      candidate.omop_person             # [Gold phase only] Candidate, NOT COMMITTED
      candidate.omop_visit_occurrence   # [Gold phase only]
~~~

使用 schema-qualified 表名，避免将所有表落入 `dbo`。当前 Terraform 源码启用了 schemas，但真实现存 Lakehouse 状态 **HOLD until readback**；若当前 Item 不支持 schemas，**不得默默改为大量带前缀的第二套正式表名**，先补一条建表/兼容决策，避免以后再大迁移。Lakehouse Files 不能作为 Git 源码目录；不得把真实 Batch、样本患者信息或运行产物提交到仓库。

**Silver 批次与数据版本：** Local Contract 的真实 PK 是 Patient(`source_system,source_record_id`) 与 Encounter(`source_system,source_encounter_id`)，并已有 `source_batch_id`、`processing_run_id` 等字段。MVP NEW_ONLY 要保持同版本重复执行无二次 INSERT；多实体 Silver 只有两个表都完成读回和 FK/DQ 后才在 `ops.silver_approval` 发出批准记录。未来同 Source Batch 不同 mapper/contract SHA 产生新 Processing Version 时，不能复用这些 PK 盲目 append 覆盖；必须先选择**独立 staging/version 表 + approved view/指针**或明确按来源覆盖的 Delta 策略，再上 Update。Gold 只读取明确批准的 Silver 版本，不扫“所有当前 Delta 文件”。

**Warehouse Gold（未来 POC）**：`staging.person_candidate`、`staging.visit_candidate` → 在 Warehouse 内短 T-SQL transaction 维护 `cdm.person`、`cdm.visit_occurrence`、`etl.identity_map`、`etl.batch_ledger`。上述 Schema 名称是候选，第一版 POC 需先确认现有 OMOP CDM DDL/ID 语义。跨 Lakehouse→Warehouse 传输不参与该事务，Warehouse PK/FK/UNIQUE NOT ENFORCED 须独立验证。

## 5. 确切的代码→模块映射及复用动作

| Existing file | 新 API 目标 | 允许的动作 |
| --- | --- | --- |
| `local-data-platform/spark/apps/visit/map_encounter_to_visit_candidate.py` | shared `mapping/omop/visit_occurrence.py` | 先提炼纯函数，冻结输入+输出测试，Local 旧导入不变 |
| `local-data-platform/spark/apps/person/map_canonical_patient_to_omop.py` | shared `mapping/omop/person.py` | **只提 DataFrame mapping**，JDBC/PG credentials 留 Local |
| `local-data-platform/spark/apps/person/synthea_patient_adapter.py` | shared `adapters/csv/patient.py`（未来） | 只提 CSV→Canonical 语义，S3 Manifest/CLI/Spark Session 留 Local |
| `local-data-platform/spark/apps/visit/synthea_encounter_adapter.py` | shared `adapters/csv/encounter.py`（未来） | 只提 Entity 规则，input/output URI 和 Job 留 Local |
| `local-data-platform/spark/common/canonical_gate.py` | shared `canonical/validation.py` | 提可配置 Contract/DQ，不提 S3/K8s 调度 |
| `local-data-platform/spark/contracts/canonical/*.json` | **当前仍留原处** | exact SHA/hash pin；单独 Contract Migration PR 后才可换 owner |
| `azure-fabric/deployment/trial_smoke_publisher.py` | 保留试验工具 | 新业务发布做受控新入口，而不是扩大现有硬编码 Smoke 安全面 |
| `azure-fabric/infra-terraform/modules/onelake/main.tf` | 保留 IaC | 只核验 Live State/ID/schema；不为新 ETL 另造同名 Lakehouse |

## 6. 第一轮最小真正开发的交付列表

| PR/Phase | 交付源码/验证 | 未完成条件 |
| --- | --- | --- |
| **P0 预检/静态门槛** | 确认 Main/feature SHA 与冲突、Contract File SHA；扩展 `.github/quality/scripts/` 的 Shared/Fabric CODE-map & forbidden import 检查；在 `documents/systems/data-platform/shared-engine/CODE.md` 和 Fabric Notebook/Pipeline/Environment CODE map 登记单一 owner | 未通过静态/负向测试不写业务代码 |
| **P1 Shared offline FHIR** | Shared `pyproject.toml` + FHIR Bundle/Reference/Patient/Encounter + Canonical validation + synthetic fixtures + pytest；纯 DataFrame 结果含 Quarantine/Error；Wheel Build+Install+Import Test | 不要求 Blob/Fabric Live 权限；不能复制 Local 生产批次 |
| **P2 Fabric I/O offline** | Notebook 内 Manifest/hash、Bronze、Spark/Delta Silver/quarantine/readback 代码，Native Item schema/CI 测试；准确 Source/Processing version | 无需运行 Azure/Fabric；新的 Blob Live 操作独立授权 |
| **P3 Controlled Fabric Runtime** | 修复旧三轮 HOLD 的 Notebook definition/exitValue；核实 Workspace/Lakehouse GUID、schema/Shortcut RBAC；发布唯一 Shared Wheel、Environment Publish/Readback；发布原生 Notebook/Pipeline，5–10 → 100 Patient/Encounter Silver Readback | 未通过新授权/环境/成本 Gate 不执行 |
| **P4 Gold candidate + transaction POC** | 提炼 Local OMOP Mapper、ID Snapshot、Candidate 与 Reconciliation；再评估 Warehouse Writer、事务/并发/Unknown ACK/跨表 readback | 无 Warehouse TX 证据不得宣布 Gold COMMITTED |
| **P5 后续独立工作** | CSV / HL7 v2 / Observation / PG OMOP Snapshot / dbt | 不得因目录已经预留而自动实现 |

## 7. 强制目录与部署验收门槛

- **New code naming**: 禁止 taskNNN/stepNNN、按日期/医院复制整条 ETL；每个 source/entity 以功能命名。每个业务 Python Package 只有一个 import namespace，独立 `src` 布局。
- **Ownership**: Shared 只能引用 Python/PySpark/Contract & explicit snapshot，绝不 import Azure/Fabric/Local runtime、调用联网或持久写入。Fabric Notebook → shared 是单向 import；Notebook 必须可见执行真实 Spark ETL，不复制 Mapper。
- **Contract**: 所有临床字段和 ID/概念匹配有明确来源语义和缺失/quarantine，不因 FHIR optional 强行填假数据。已批准 Contract 不偷偷放宽。
- **CI**: 同 PR 更新唯一 CODE.md，命名/文档链接/OpenSpec/CODE-map/禁止 import/重复源测试通过；现行 CODE-map 对新根覆盖尚未实测，不许标记“自动保护已完成”。
- **Artifact**: 记录 shared wheel version+SHA、Fabric Environment Published Library List 和 Notebook/Pipeline Git HEAD/logicalId/actual Item readback。禁止使用浮动版本/不同代码的 Run 假冒验收。
- **Operations**: 不静默创建或覆盖 Warehouse/Workspace/Shortcut/State，不对现有 Local Writer/Blob Publisher 部署/回放；用户在各 Gate 明确授权才运行 Fabric/PG/K8s/Azure。
- **MVP success**: 从确切 Blob Manifest/Object hash → Intake Gate → Bronze Evidence → Silver Delta 两表 approved batch（PK/FK/row reconcile、quarantine、重跑 SKIP）及新会话独立读回，再进入 OMOP/Gold 实机 POC。

## 8. Source reference for native Fabric rules

- Fabric Git Item folders and .platform metadata: https://learn.microsoft.com/en-us/fabric/cicd/git-integration/source-code-format
- Notebook notebook-content.py and generated environment/lakehouse references: https://learn.microsoft.com/en-us/fabric/data-engineering/notebook-source-control-deployment
- Environment wheel publish requires separate Publish: https://learn.microsoft.com/en-us/fabric/data-engineering/environment-git-and-deployment-pipeline
- Environment custom wheel libraries: https://learn.microsoft.com/en-us/fabric/data-engineering/environment-manage-library
- Lakehouse schema enableSchemas and namespace: https://learn.microsoft.com/en-us/fabric/data-engineering/lakehouse-schemas
