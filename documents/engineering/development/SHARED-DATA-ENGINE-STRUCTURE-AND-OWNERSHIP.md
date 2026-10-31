---
status: approved-directory-policy-implementation-pending
decision_date: 2026-10-31
scope: shared-data-engine-and-fabric-ownership
authority: code-structure-and-agent-rules
runtime: none
---

# Shared Data Engine — 目录结构、唯一代码归属及 Agent 开发规范

> **2026-10-31 最终实施规则：** [Fabric-native Notebook/Pipeline/Environment ADR](../../architecture/design/FABRIC-NATIVE-NOTEBOOK-PIPELINE-ENVIRONMENT-ADR-20261031.md) 优先于本文件任何早期 I/O Wheel 设计。此规则只代表开发依据，不代表 Fabric 已部署。
>
> 数据业务架构参考 [Fabric Bronze → Canonical Silver → OMOP Gold ADR](../../architecture/design/FABRIC-MEDALLION-CANONICAL-ADR-20261030.md)；通用命名、安全和审批仍以仓库根 [AGENTS.md](../../../AGENTS.md)、[CODE Organization](CODE-ORGANIZATION-AND-NAMING.md) 和 [OpenSpec lifecycle](OPENSPEC-DEVELOPMENT-LIFECYCLE.md) 为准。本文只约束目录和依赖归属，不代替 Contract 或运行时验收事实。

## 1. 唯一责任边界

| Owner | 实际角色 | 禁止 |
| --- | --- | --- |
| `shared-data-engine/src/healthcare_data_engine/` | 本期唯一新 Python Wheel；FHIR/CSV/HL7 Source/Entity Adapter、Canonical、OMOP Candidate/DQ/Identity Plan/Reconciliation | Azure/OneLake/S3/PG/Delta 物理 I/O，Pipeline/Airflow |
| `local-data-platform/` | 已有 Spark/Airflow/SeaweedFS/PG 运行环境；逐模块测试后才改用 Shared | 大规模移动旧代码/合同、复制新的核心 Mapper |
| `azure-fabric/workspaces/healthcare-omop/notebooks/` | 实际 Fabric Notebook PySpark 应用：Spark 读取、转换调用、DQ、Delta、读回 | 复制 Shared 算法、只提供空启动壳 |
| `azure-fabric/workspaces/healthcare-omop/pipelines/` | Fabric 原生工作流：依赖/参数/失败分支/重试/调度 | 另建 Python Airflow-like 调度层 |
| `azure-fabric/workspaces/healthcare-omop/environments/` | Fabric 原生 Environment Item：安装并 Publish 固定版本 Shared Wheel | 直接放入 Shared 可编辑 Python 源码，双发布者竞争 |
| `azure-fabric/infra-terraform/` | 已有 Infrastructure Terraform Modules/State | 同时写 native Notebook/Pipeline/Environment Item |
| `azure-fabric/deployment/`, `openlineage/` | 现有发布脚本和 Lineage 能力，路径保留 | 随意扩大 Trial Smoke 发布范围 |

## 2. 真实目录规划（未创建的 Native Items 仅为目标）

~~~text
healthcare-data-platform/
├── shared-data-engine/
│   ├── AGENTS.md                              # exists
│   ├── pyproject.toml                         # one future Wheel
│   ├── src/healthcare_data_engine/
│   │   ├── adapters/fhir_r4/
│   │   ├── canonical/
│   │   ├── mapping/omop/
│   │   ├── identity/
│   │   ├── quality/
│   │   └── reconciliation/
│   └── tests/
├── local-data-platform/                       # unchanged
└── azure-fabric/
    ├── workspaces/
    │   ├── healthcare-omop/
    │   │   ├── notebooks/ingestion/nb_fhir_ingest.Notebook/
    │   │   ├── pipelines/pl_fhir_ingest.DataPipeline/
    │   │   └── environments/env_healthcare.Environment/
    │   └── johnzhang-test/                    # existing Smoke
    ├── infra-terraform/                       # existing
    ├── deployment/                            # existing
    └── openlineage/                           # existing
~~~

`azure-fabric/workspaces/healthcare-omop/` is the chosen Fabric Git Folder root. The `notebooks/`, `pipelines/`, `environments/` subfolders **must correspond to actual Fabric UI folders**, but the names are our project convention, not Microsoft-mandated. Native Item definitions (`.platform`, Notebook content, Pipeline JSON) must come from actual Fabric exports, not manually invented identifiers. No `shared-data-engine/` Python source under native Environment; Environment consumes the **built, versioned, hash-pinned shared wheel**. One selected release writer + Environment Publish + Notebook version readback.

## 3. 业务功能落点与依赖方向

- Shared Engine owns only pure business normalization/candidate mapping, contracts/DQ/identity/reconciliation. Existing Canonical/OMOP Contracts remain `local-data-platform/spark/contracts/` single manual authority until an independently approved move; pin exact SHA and hash.
- Fabric Pipeline owns orchestrated Notebook invocations, retries and dependencies. Fabric Notebook owns the single Spark app's actual visible steps, importing Shared for FHIR Patient+Encounter normalization and using native Spark APIs to read/write OneLake/Delta.
- Shortcut/Copy are Fabric-native options requiring actual RBAC/byte/retention POC, not excuses to skip source Manifest SHA256 validation. Silver readback/PK/FK/Quarantine/Approval remain mandatory; no unconditional append.
- **No new second wheel**: earlier `azure-fabric/ingestion/`, `azure-fabric/runtime/`, and `azure-fabric/libraries/healthcare-fabric-io/` proposals are superseded. No Fabric-specific import allowed inside Shared. If future genuine repeated platform code warrants extraction, use a separately reviewed OpenSpec Change.
- Actual `local-data-platform` code/DAG IDs and current Terraform State remain unchanged until distinct tested migration/release. Native Git Items must be managed through one Fabric Git owner, not Terraform in parallel.


## 5. 路径、版本和测试标准

- **命名**：新源码按组件+业务能力命名，snake_case 文件、PascalCase 类型；禁止新增 taskNNN/stepNNN、v2_final、misc、utils2；禁止按医院/时间/开发任务号创建顶层目录。业务版本在 Contract/Mapping Profile/包版本中体现，不通过复制目录代替升级。
- **固定 package namespace**：`healthcare_data_engine` 只对应 `shared-data-engine/src/healthcare_data_engine/`；不再建立第二只 Fabric I/O wheel。建议 PEP 621 + `pyproject.toml` 的共享 wheel，Local/Fabric 安装**经过测试的指定版本/哈希**，不使用浮动 `latest`、共享工作目录 PYTHONPATH 作为长期集成接口。
- **Contract Source of Truth**：当前 Local Contract 原位不动，包构建/测试读固定 hash 的确切版本。未来有明确影响矩阵、回滚和双端测试后，再用单独 PR 迁移权威 Contract，不在同一个 PR 同时修改 Schema 和移动运行代码。
- **测试归属**：Shared 函数及失败/幂等/缺字段测试在 `shared-data-engine/tests/`；Fabric I/O 和 Warehouse SQL 的 mock/静态测试分别在 Fabric 自己的 `tests/`；真实 Trial/Local 接口测试额外提供 frozen synthetic fixtures 及跨 Spark 版本比较。禁止真实患者数据/Secret 进入 Git。
- **Data identity**：Source Batch（hospital/feed/request/manifest SHA）、Processing Version（adapter/contract/map/code SHA）、Publication ID（approved commit）的数据模型在 shared；状态的物理持久化由各平台独占。不同医院身份不得按姓名/生日自动合并。
- **Schema edge case**：Local Canonical v1 的非空约束不一定适用于真实 FHIR；只允许匹配 profile 的合成 MVP，缺字段 quarantine 或经独立审批推出 v2；不得默填生日、种族、Encounter 结束时间。
- **发布**：Local Spark 3.5.7 与 Fabric Runtime 2.0 有版本差异；两边固定共享包版本且独立测试、独立部署，不得 Fabric 变更自动升级 Local。新的真实 File/Item ID 必须从系统生成而非硬编码猜测。
- **不可迁移**：现有 Local DAG ID、Git 路径、镜像/ConfigMap、PostgreSQL 业务合同与已发布批次不做命名清理；以后任何提取以“旧版本照常运行 → 新实现等价测试 → 显式调用切换 → 独立验收 → 有条件清理”为顺序。

## 5A. Fabric 实战源码与数据落地补充

**在开发具体 Python 源文件、Fabric Native Item、Environment、OneLake Table 或 Warehouse SQL 前，必须按 [实战文件级实施计划](../../architecture/design/FABRIC-FHIR-PRACTICAL-SOURCE-LAYOUT.md) 检查：真实旧文件可提取部分、唯一 Shared Wheel 的构建/发布、Live Lakehouse schema 与准确 ID、Silver batch approval/版本策略、Native .platform logicalId、SQL Gold Writer 单一权属。** 该实施计划不能覆盖本文的永久唯一 owner 和禁止依赖规则；与现有已部署事实不一致则 HOLD 并更新计划，禁止盲目创建第二套。

## 6. Agent 的强制执行顺序

开发 Agent **在新增/改动任何共享/Local/Fabric 数据转换源文件之前**：

1. 读取根 `AGENTS.md`、本规则、`shared-data-engine/AGENTS.md`（只要涉及 shared）、对应模块 `README.md/CODE.md`，并核对当前 `main` / PR 的完整 SHA 与真实源码。
2. 在当前 OpenSpec Change 中先列明 **业务职责、目标 owner 路径、允许依赖、公开 API、Contract SHA、测试/回滚计划**；没有唯一归属或发现两个实现时标记 HOLD，不自行复制新实现。
3. 首先新增**薄的必要文件**和 contract/unit/negative/replay 测试，不建立未来所有实体/医院的空脚手架，不以大规模移动旧代码作为第一步。
4. 同一 PR 更新唯一组件 CODE.md 和必要 README/ADR/OpenSpec tasks；文件/部署不越界。Fabric Native Item 文件应与 `fabric-cicd` 唯一权属一致，不交 Terraform 与 fabric-cicd 双重管理。
5. 应运行现有命名、OpenSpec、DOC-link、CODE-map 检查。**目前旧 CODE-map 只覆盖已列明的 Local/部分 Fabric 原生路径，对新 shared/Fabric Native Notebook/Pipeline/Environment/warehouse 并非自动覆盖**；新增源码前必须扩展静态校验的路径归属、依赖边界和重复实现负向测试。没有 CI 证据不能声称 Agent 路径边界已有自动保护。
6. 真实 Blob/Fabric/K8s/PG 操作必须逐项授权并核验资源/费用/并行任务；PR 合并与静态测试不代表业务运行成功。

## 7. 本轮落地状态（避免 Agent 错认）

- **已定版**：唯一 Shared Wheel、Fabric NB/PL 必选、Environment 安装发布、原生 Spark I/O、Contract 唯一权威、CODE map、渐进迁移策略。
- **已建立**：`shared-data-engine/AGENTS.md` 的 scoped Agent 指令和文档 Code Ownership 入口。
- **尚未建立**：`pyproject.toml`、任意 `src/*.py`、Wheel 构建、Contract 复制/迁移、Native Notebook、Warehouse Gold Writer、Delta/Shortcut 云端资源。
- **独立未来 Gate**：按原 PR 的 OpenSpec tasks 分阶段建设自动静态边界检查、Shared Python 包、合同与 Spark 跨版本测试；不能把本轮文件夹治理视为业务功能 PASS。
