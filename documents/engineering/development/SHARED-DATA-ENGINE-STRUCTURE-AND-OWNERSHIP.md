---
status: approved-directory-policy-implementation-pending
decision_date: 2026-10-30
scope: shared-data-engine-and-fabric-ownership
authority: code-structure-and-agent-rules
runtime: none
---

# Shared Data Engine — 目录结构、唯一代码归属及 Agent 开发规范

> **2026-10-30 用户已同意采用 `shared-data-engine/` 共享业务引擎架构。本文件是未来新增/修改相关源文件时的权威目录与所有权规则，不能把 Draft PR 文档误称为已经实施或 Main 已生效。**
>
> 数据业务架构参考 [Fabric Bronze → Canonical Silver → OMOP Gold ADR](../../architecture/design/FABRIC-MEDALLION-CANONICAL-ADR-20261030.md)；通用命名、安全和审批仍以仓库根 [AGENTS.md](../../../AGENTS.md)、[CODE Organization](CODE-ORGANIZATION-AND-NAMING.md) 和 [OpenSpec lifecycle](OPENSPEC-DEVELOPMENT-LIFECYCLE.md) 为准。本文只约束目录和依赖归属，不代替 Contract 或运行时验收事实。

## 1. 唯一三个执行/业务源码域

| Source root | 唯一归属 | 可以依赖 | 绝对不应该变成 |
| --- | --- | --- | --- |
| `shared-data-engine/` | 可版本化、可离线测试、跨平台的 **纯业务 DataFrame 转换**、跨来源 Canonical / OMOP 候选、Contract/DQ/Identity Plan/Reconciliation | PySpark DataFrame、标准 Python、版本化/冻结 Contract 和纯计算库 | Fabric SDK/Blob/OneLake、Airflow DAG、K8s、PG/Warehouse Writer、Secret、Notebook |
| `local-data-platform/` | **已存在**的 Producer、Airflow、K8s Spark、SeaweedFS/S3、PG Writer、镜像和运行环境；必要时引用固定版本 shared package | `shared-data-engine` 的对外 API（经回归测试后） | 第二个自行维护的 OMOP 映射核心；本次不移动或重命名现有路径 |
| `azure-fabric/` | Blob Intake、Shortcut/Copy、Lakehouse Delta Publisher、Warehouse Gold Writer、薄 Notebook/Pipeline、Terraform、运行部署与 Lineage 适配 | `shared-data-engine` 的对外 API（经 Fabric 实测后） | FHIR/HL7/CSV 业务 Mapper/Canonical 规则的另一份副本 |

`documents/` 是架构与系统文档，`openspec/` 是需求/任务门槛，`.github/` 是 CI 与发布工具。SQL Gold Writer 只能存在于平台侧，**不允许进入共享包**。

## 2. 稳定目标结构（仅是规划；不创建一堆空目录）

~~~text
healthcare-data-platform/
├── shared-data-engine/
│   ├── AGENTS.md                              # 已建立：本目录 Agent 硬规则
│   ├── pyproject.toml                         # 开发 Python wheel 时才创建
│   ├── src/healthcare_data_engine/             # 唯一 import namespace
│   │   ├── __init__.py
│   │   ├── models/
│   │   │   ├── batch_context.py               # SourceBatch / ProcessingVersion / Publication
│   │   │   └── source_identity.py
│   │   ├── adapters/
│   │   │   ├── fhir_r4/
│   │   │   │   ├── bundle.py
│   │   │   │   ├── patient.py
│   │   │   │   ├── encounter.py
│   │   │   │   └── references.py
│   │   │   ├── csv/                            # 按需移植，不先复制 Local
│   │   │   └── hl7_v2/                         # 未来独立 Change
│   │   ├── canonical/
│   │   │   ├── patient.py
│   │   │   ├── encounter.py
│   │   │   └── validation.py
│   │   ├── mapping/omop/
│   │   │   ├── person.py
│   │   │   ├── visit_occurrence.py
│   │   │   └── concepts.py
│   │   ├── identity/
│   │   │   ├── source_keys.py
│   │   │   └── mapping_plan.py
│   │   ├── quality/
│   │   │   ├── schema.py
│   │   │   ├── duplicates.py
│   │   │   └── referential_integrity.py
│   │   └── reconciliation/
│   │       ├── counts.py
│   │       └── consistency.py
│   └── tests/
│       ├── fixtures/                           # synthetic only; no PHI
│       ├── unit/
│       ├── contract/
│       └── cross_runtime/
├── local-data-platform/                        # 现有 runtime 目录原位保留
├── azure-fabric/
│   ├── ingestion/                              # 独立 Fabric adapter wheel
│   │   ├── pyproject.toml
│   │   ├── src/healthcare_fabric/
│   │   │   ├── intake/                         # Azure Blob Manifest/byte validation
│   │   │   ├── storage/                        # Files/Shortcut + Delta I/O
│   │   │   ├── publishing/                     # Bronze receipt / Silver approval
│   │   │   ├── orchestration/                  # Calls shared API / state transitions
│   │   │   └── monitoring/
│   │   └── tests/
│   ├── warehouse/                              # Gold SQL POC, when approved
│   │   ├── ddl/
│   │   ├── procedures/
│   │   └── tests/
│   ├── workspaces/healthcare-omop/
│   │   ├── notebooks/                          # Native *.Notebook/.platform
│   │   ├── pipelines/                          # Native *.DataPipeline/.platform
│   │   └── environments/                       # Native Fabric Environment when needed
│   ├── infra-terraform/                        # 现有 infra/state/module hierarchy
│   ├── deployment/                             # 已有 deployment tooling
│   └── openlineage/                            # 已有 runtime integration
├── documents/
├── openspec/
└── .github/
~~~

**注意：** `shared-data-engine/contracts/` 是正式转移 Contract 唯一权威后才允许使用的预留位置，**当前不应创建相同内容的复制文件**。当前 Canonical/OMOP Contract 仍以 `local-data-platform/spark/contracts/` 为源；共享包在正式切换前通过 **锁定 repo commit + 文件 hash 的构建/装载**使用它们。不能在构建或运行时偷读未经版本固定的 `main` 或动态 GitHub 文件。未来需要 Contract 打包到 wheel 时由锁定权威源生成包内副本，不允许手工维护两套定义。

## 3. 功能放置表：Agent 必须据此判断

| 新增内容 | 唯一正确位置 | 错误位置 |
| --- | --- | --- |
| FHIR Bundle / Patient / Encounter 解析与 Canonical 规范 | shared `adapters/fhir_r4/`；`canonical/` | Fabric Notebook、`azure-fabric/ingestion/` 的独立 Mapper |
| CSV / HL7 解析的可复用业务规则 | shared `adapters/csv/`、`adapters/hl7_v2/`（到实施阶段再创建） | 每个医院复制一整份 ETL |
| Canonical Patient / Encounter Schema 验证 | shared `canonical/`、`quality/` | Fabric storage/、Warehouse SQL Writer |
| Canonical → OMOP Person / Visit / Concepts | shared `mapping/omop/` | Local PG Writer、Fabric Notebook 或新的 source adapter |
| 医院命名空间、稳定 ID 规则、分配计划 | shared `identity/`，**只输出计划** | shared 里直接 UPDATE PG/Warehouse |
| 业务数据对账（count/PK/FK/Concept coverage） | shared `reconciliation/` + `quality/` | 每个平台重新维护一份业务规则 |
| Azure Blob SDK / Manifest byte reader / Shortcut | `azure-fabric/ingestion/intake/` 和 `storage/` | shared `adapters/fhir_r4/` |
| SeaweedFS/S3 SDK / K8s / Airflow | `local-data-platform/` 对应现有组件 | shared |
| Delta Silver 物理写入、Quarantine storage、Approval ledger | `azure-fabric/ingestion/storage/` / `publishing/` | shared |
| Warehouse T-SQL/PG single transaction commit | `azure-fabric/warehouse/` / `local-data-platform/apps/omop_writer/` | shared `mapping/`、shared `identity/` |
| Fabric Notebook/Pipeline 与 .platform | `azure-fabric/workspaces/<workspace>/` 原生 Item | shared / `azure-fabric/ingestion/src/` |
| Terraform/Connection/Workspace IaC | 现有 `azure-fabric/infra-terraform/` | shared / Notebook |
| 工程治理、CODE.md、OpenSpec、tests | `documents/`、`openspec/`、对应组件自己的 `tests/` | 在 source root 下维护第二份重复架构说明 |

## 4. 依赖方向与 public API（MUST）

~~~text
Local Airflow / Local Spark      Fabric Pipeline / thin Notebook
             |                                |
     local platform adapter          azure-fabric runtime adapter
             \                               /
               version-pinned shared wheel
                    |  pure DataFrame API
                    v
 source/entity adapter → canonical contract + quality
                                     |
                           approved canonical rows
                                     |
                         OMOP mapping + identity PLAN
                                     |
                            reconciliation result
                    (NO external writes)
~~~

- `shared` **绝不能 import** `healthcare_fabric`、Local 的 Airflow/runtime 代码、`azure.*`、`airflow`、`psycopg`、`fabric-cicd`、云认证/Secret 客户端或持久化 Writer。PySpark DataFrame 转换是允许的；传入 DataFrame/immutable config，返回 DataFrame + typed quality/plan/evidence；不在 import 阶段读取环境变量、文件/网络或启动 Spark Session。
- Source parser/adapter **不依赖** OMOP Writer；OMOP Mapper **不依赖** FHIR/HL7/CSV parser，仅读 Canonical/DataFrame + versioned mapping profile。Canonical contract 不是 Fabric-specific Schema。
- `azure-fabric/ingestion/` 可以 import `healthcare_data_engine`，但 **共享包不可反向 import 平台包**。平台层独占 I/O、身份认证、外部事务、run logs 和 side effects。
- 每个新增业务实体（`observation`、`condition`、`procedure`）只需扩展 source adapter、canonical contract、target mapper 与测试，**不得创建 `patient_pipeline_v2/`、`hospital_a_etl/` 或另一整套 shared core**。
- 需要外部查表（Concept terminology、Identity Map）时，由平台 Adapter 读取并作为**显式版本化快照 DataFrame/接口参数**输入共享算法；共享包不擅自查询生产数据库或调用外部 API。
- 不在共享包中写一般性 Blob Manifest 下载器，Blob 的协议/存储读取在平台层；只有脱离云平台依赖的 batch identity、manifest model/纯校验规则才能进入 shared。
- 所有插件接口与 contract 都要固定可测试的输入、输出、source profile、quarantine 语义和错误分类。不能凭“有相同列名”推定不同医院相同 clinical code。

## 5. 路径、版本和测试标准

- **命名**：新源码按组件+业务能力命名，snake_case 文件、PascalCase 类型；禁止新增 taskNNN/stepNNN、v2_final、misc、utils2；禁止按医院/时间/开发任务号创建顶层目录。业务版本在 Contract/Mapping Profile/包版本中体现，不通过复制目录代替升级。
- **固定 package namespace**：`healthcare_data_engine` 只对应 `shared-data-engine/src/healthcare_data_engine/`；`healthcare_fabric` 只对应 `azure-fabric/ingestion/src/healthcare_fabric/`。建议 PEP 621 + `pyproject.toml` 的各自 wheel，Local/Fabric 安装**经过测试的指定版本/哈希**，不使用浮动 `latest`、共享工作目录 PYTHONPATH 作为长期集成接口。
- **Contract Source of Truth**：当前 Local Contract 原位不动，包构建/测试读固定 hash 的确切版本。未来有明确影响矩阵、回滚和双端测试后，再用单独 PR 迁移权威 Contract，不在同一个 PR 同时修改 Schema 和移动运行代码。
- **测试归属**：Shared 函数及失败/幂等/缺字段测试在 `shared-data-engine/tests/`；Fabric I/O 和 Warehouse SQL 的 mock/静态测试分别在 Fabric 自己的 `tests/`；真实 Trial/Local 接口测试额外提供 frozen synthetic fixtures 及跨 Spark 版本比较。禁止真实患者数据/Secret 进入 Git。
- **Data identity**：Source Batch（hospital/feed/request/manifest SHA）、Processing Version（adapter/contract/map/code SHA）、Publication ID（approved commit）的数据模型在 shared；状态的物理持久化由各平台独占。不同医院身份不得按姓名/生日自动合并。
- **Schema edge case**：Local Canonical v1 的非空约束不一定适用于真实 FHIR；只允许匹配 profile 的合成 MVP，缺字段 quarantine 或经独立审批推出 v2；不得默填生日、种族、Encounter 结束时间。
- **发布**：Local Spark 3.5.7 与 Fabric Runtime 2.0 有版本差异；两边固定共享包版本且独立测试、独立部署，不得 Fabric 变更自动升级 Local。新的真实 File/Item ID 必须从系统生成而非硬编码猜测。
- **不可迁移**：现有 Local DAG ID、Git 路径、镜像/ConfigMap、PostgreSQL 业务合同与已发布批次不做命名清理；以后任何提取以“旧版本照常运行 → 新实现等价测试 → 显式调用切换 → 独立验收 → 有条件清理”为顺序。

## 5A. Fabric 实战源码与数据落地补充

**在开发具体 Python 源文件、Fabric Native Item、Environment、OneLake Table 或 Warehouse SQL 前，必须按 [实战文件级实施计划](../../architecture/design/FABRIC-FHIR-PRACTICAL-SOURCE-LAYOUT.md) 检查：真实旧文件可提取部分、两只 Wheel 的构建/发布、Live Lakehouse schema 与准确 ID、Silver batch approval/版本策略、Native .platform logicalId、SQL Gold Writer 单一权属。** 该实施计划不能覆盖本文的永久唯一 owner 和禁止依赖规则；与现有已部署事实不一致则 HOLD 并更新计划，禁止盲目创建第二套。

## 6. Agent 的强制执行顺序

开发 Agent **在新增/改动任何共享/Local/Fabric 数据转换源文件之前**：

1. 读取根 `AGENTS.md`、本规则、`shared-data-engine/AGENTS.md`（只要涉及 shared）、对应模块 `README.md/CODE.md`，并核对当前 `main` / PR 的完整 SHA 与真实源码。
2. 在当前 OpenSpec Change 中先列明 **业务职责、目标 owner 路径、允许依赖、公开 API、Contract SHA、测试/回滚计划**；没有唯一归属或发现两个实现时标记 HOLD，不自行复制新实现。
3. 首先新增**薄的必要文件**和 contract/unit/negative/replay 测试，不建立未来所有实体/医院的空脚手架，不以大规模移动旧代码作为第一步。
4. 同一 PR 更新唯一组件 CODE.md 和必要 README/ADR/OpenSpec tasks；文件/部署不越界。Fabric Native Item 文件应与 `fabric-cicd` 唯一权属一致，不交 Terraform 与 fabric-cicd 双重管理。
5. 应运行现有命名、OpenSpec、DOC-link、CODE-map 检查。**目前旧 CODE-map 只覆盖已列明的 Local/部分 Fabric 原生路径，对新 shared/ingestion/warehouse 并非自动覆盖**；新增源码前必须扩展静态校验的路径归属、依赖边界和重复实现负向测试。没有 CI 证据不能声称 Agent 路径边界已有自动保护。
6. 真实 Blob/Fabric/K8s/PG 操作必须逐项授权并核验资源/费用/并行任务；PR 合并与静态测试不代表业务运行成功。

## 7. 本轮落地状态（避免 Agent 错认）

- **已定版**：目录命名、公共 API/依赖边界、Contract 唯一权威策略、组件级 Code Ownership、渐进迁移策略。
- **已建立**：`shared-data-engine/AGENTS.md` 的 scoped Agent 指令和文档 Code Ownership 入口。
- **尚未建立**：`pyproject.toml`、任意 `src/*.py`、Wheel 构建、Contract 复制/迁移、Native Notebook、Warehouse Gold Writer、Delta/Shortcut 云端资源。
- **独立未来 Gate**：按原 PR 的 OpenSpec tasks 分阶段建设自动静态边界检查、Shared Python 包、合同与 Spark 跨版本测试；不能把本轮文件夹治理视为业务功能 PASS。
