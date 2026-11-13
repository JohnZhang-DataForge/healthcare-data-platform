---
status: active
scope: code-organization-and-naming
last_verified: 2026-10-16
source_sha: 2c85b485381a72425506829fd321d93b164a231d
---

# Component-first 源代码组织与命名规范

**对所有 Agent 强制执行，自本规范进入 Main 起适用于新增代码。**

## 一、唯一规则

**不允许把任何项目开发阶段号作为新增业务源码、函数、类、字段、状态/错误码、协议 Schema、Workflow 名称。** 例如 G3/G4/G5、P1/P2/P3、F1/F2、B2/B4、taskNNN、stepNNN 均为开发进度代号，不是稳定业务名。应采用 bronze_ingestion、silver_publication、technical_admission、identity_snapshot、candidate_publication、gold_publication 等职责命名。FHIR R4、HL7 v2、OMOP CDM 5.4、Python Wheel 0.1.13 等真实标准与版本号不受此限制。历史已发布协议与旧代码只能受控兼容读取，不能作为新代码命名模板。

**新增的语义命名检查**：[`check_semantic_naming.py`](../../../.github/quality/scripts/check_semantic_naming.py) 对 PR Git diff 中新增源码路径和新增声明/部分外部契约进行静态检测，另有负向测试；已接入 `Component Code Naming` 非 Required 工作流，并新增独立默认分支可信读取的 [`Semantic Naming Trusted Source Gate`](../../../.github/workflows/semantic-naming-trusted.yml)（Job `require-semantic-source-names`）。但该新 Job 还**未列入 GitHub Ruleset Required Status Checks**，也未完成真实负向 PR 验收。检查器目前不覆盖所有动态生成字符串/语言，**也尚未进入可信 Required Gate**，因此不能将 advisory PASS 说成治理完成。现有受保护 checker 禁止普通 PR 直接改动，必须另行授权升级默认分支可信策略并通过 GitHub Ruleset 实际负向验收。

**Task / Step 用来管理开发过程，不能用来命名新增的正式业务代码。** Task/Step 编号只出现在 Issue/PR、规划、验收、OpenSpec tasks、运行记录、历史文件中。Python 模块、包、函数、类、DAG ID、SQL 文件、正式 Shell、镜像、K8s Manifest、Workflow、测试路径均必须**按照组件 + 业务能力 + 操作**命名。

现有 `task001`、`task003`、`task004` 文件、导入、数据库表、镜像与 Batch Contract **暂时原样保留**。禁止为了让目录好看而批量替换已经接受验收的接口；要按 [Legacy Refactor Plan](LEGACY-CODE-REFACTOR-PLAN.md) 逐模块改造并验证。

## 二、命名示例

| 分类 | 正确（新增代码） | 不允许 |
| --- | --- | --- |
| Python / 应用源码 | `apps/omop_writer/condition_writer.py` | `apps/task005/condition.py` |
| Spark | `spark/apps/condition/transform_condition.py` | `spark/apps/task005/step02.py` |
| Airflow DAG 与 ID | `condition_omop_consumer.py` / `condition_omop_consumer` | `task005_pipeline.py` / `task005_run` |
| SQL | `sql/omop/condition_occurrence_indexes.sql` | `sql/task005/step04.sql` |
| Docker Context | `images/omop-condition-writer/` | `images/task005-runtime/` |
| K8s 部署 | `kubernetes/manifests/condition/consumer-job.yaml.tpl` | `kubernetes/manifests/task005/` |
| 正式脚本 | `scripts/omop/verify_condition_fk.sh` | `scripts/task005/step00-check.sh` |
| Tests | `tests/omop_writer/test_condition_idempotency.py` | `tests/task005/test_step04.py` |
| Workflow | `condition-source-validation.yml` | `task005-validation.yml` |
| Contract | `contracts/omop/condition-writer-v1.json` | `contracts/task005/step02.json` |

Python 模块、函数为 `snake_case`；类为 `PascalCase`；DAG ID、K8s/镜像名遵循现有服务惯例，原则上使用可读的组件/功能名。禁止新增加 `utils2`、`latest_final`、`step04a`、`task004_*` 等以实现顺序代替语义的名字。协议真正需要版本时允许 `v1`、`v2`，但版本号不能伪装成 TASK 编号。

## 三、组件边界（避免复制 Java MVC）

```text
Contracts/Manifest
  → Synthea Producer / Landing
  → Airflow Orchestration (routing only)
  → Spark domain adapters / canonical / DQ / reconciliation
  → OMOP Writer / Ledger / Mapping / Transaction
  → PostgreSQL OMOP
Portal/OpenLineage = 横切观测
Azure Exporter/Fabric = 独立分析副本链路
```

保留原仓库的 `apps/`、`spark/`、`airflow/`、`sql/`、`images/`、`tests/` 路径；不另开重复的 `src/` 或 MVC 层。真正稳定的、跨业务域复用的逻辑才放入 `common/`；不要为每个新 TASK 复制一个完整 Writer 或 Manifest 校验模块。

### 2026-10-30：独立共享 Python 包的明确例外（新规则）

上述“不要另开重复 `src/`”**仅限制在现有 Local DP 各业务目录内创建第二套重复源码树**。用户已经确认采用跨平台共享引擎，当前只新建**一个**可安装 Python Package：`shared-data-engine/src/healthcare_data_engine/`，使用标准 `src` 布局；此前第二只 `azure-fabric/ingestion/src/healthcare_fabric/` Python Wheel 的方案已取消。现有 `local-data-platform/` 原路径不重构。

新增通用 FHIR/HL7/CSV Source + Entity Adapter、Canonical、OMOP Candidate Mapper、Quality、Identity Plan、Reconciliation，归 `shared-data-engine`；Blob/Delta/PG/Warehouse Writer、Airflow/K8s/Notebook/Pipeline/Secrets 则属于对应平台。Source-specific 的 Mapper 禁止另起平台内复制品。共享 DataFrame 函数不产生外部 I/O 和持久化副作用。详细路径与 Code Ownership 以 [Shared Data Engine 规范](SHARED-DATA-ENGINE-STRUCTURE-AND-OWNERSHIP.md) 为准；新业务代码进仓前应同时扩展 CODE-map CI，不能假定已有检查覆盖新顶层目录。


## 四、执行与验收

- 在创建新文件之前，Agent 先说明它属于哪个组件、负责什么功能；使用**功能名**组织路径、公共函数、DAG ID、镜像和新测试。
- [既有 Component Code Naming 检查](../../../.github/workflows/code-component-naming-check.yml) 与 [原检查器](../../../.github/quality/scripts/check_new_code_names.py) 在 PR 分支执行新增源码路径拒绝规则，保留原有历史兼容机制；**它不是 Required/可信执行的强制边界**。本次新增默认分支独立 [Trusted Component Source Structure Gate](../../../.github/workflows/component-source-structure-trusted.yml) 和 [可信策略脚本](../../../.github/quality/scripts/check_new_source_structure_trusted.py)：覆盖 Local DP、Fabric、Shared Engine、Portal、质量测试和 CI 文件，检查新增文件路径，也检查新增业务源码直接引用旧 Task Python 模块/旧源码路径。该新检查现已在 Ruleset #25365902 中作为第四项 **Required** 生效；真实非 Draft [PR #721](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/721) 返回 `mergeable_state=blocked`，可信 Job #127670719105 正确拒绝 `apps/task005` 新路径，PR 随后关闭且未合并。
- 任务号允许出现在 PR、OpenSpec Change 的开发追踪、日志、历史证据。新正式脚本和测试**不允许**继续放入新建的 `scripts/taskNNN/` 或 `tests/taskNNN/`。
- 保持已验收 DAG ID、镜像 Digest、老数据库表/函数 `etl.task004_*`、Batch Identity；涉及兼容变更必须独立设计版本、回退、单测和必要的 Runtime 验收，不自行重放冻结 Batch。
- 对代码的真正迁移先制作依赖列表，再按模块逐 PR 执行。文档重建与代码重命名**不等于**获得运行 K8s/PG/Azure 的授权。


2026-10-31 Fabric 项目最终规范：[Native Notebook/Pipeline/Environment ADR](../../architecture/design/FABRIC-NATIVE-NOTEBOOK-PIPELINE-ENVIRONMENT-ADR-20261031.md)。Fabric NB/PL 是必须的原生执行资源，Environment 管共享包构建产物；不额外创建 Fabric I/O/runtime 包。

## Fabric dbt 项目命名例外（2026-11-07）

正式 Fabric 主线 dbt Core 项目目标父目录是 `azure-fabric/dbt/`；首期 `hl7-canonical/`，内部 `name: hl7_canonical`。项目保持 `models/staging/`、`models/intermediate/`、`models/canonical/`、`macros/`、`tests/`、`seeds/`、`snapshots/`、`analyses/`、`profiles/` 等标准骨架，暂无实现时用 `.gitkeep`。原 Required Gate 的源码 `tests/` 禁令仍适用于所有其他业务目录，但**已通过 [PR #815](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/815) 精确批准 HL7 dbt 原生 singular `.sql` 和根 `tests/.gitkeep`**；真实 PR [#816](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/816) 正向 PASS、[#817](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/817) 负向 blocked，且 Ruleset 四项 Required 全部恢复。标准骨架现可在独立开发 PR 中创建。现有 HL7 SQL 仍在 Local DP，源目录迁移须单独验收；其他 FHIR/共享业务 Project 需 OpenSpec。详见 [Fabric dbt 规则](../../systems/azure-fabric/dbt/README.md)。

## 验收与实际保护状态（2026-11-05）

- [PR #715](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/715) 的可信命名检查已合并到 main，真实 [正向 PR #716](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/716) 为 PASS、[负向 PR #717](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/717) 为 FAIL；历史 223 个 Task 文件未改。
- **最终核查（2026-11-05 ET）：** GitHub Ruleset #25365902 Active，原三项 Required Checks 与第四个 `require-trusted-component-paths`（GitHub Actions integration `15368`）完整存在；[PR #721](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/721) 非 Draft、真实 `blocked`，旧三项 PASS、新 Trusted Gate FAIL（正确拒绝），已关闭未合并。新源码目录正式封板，历史 Task 路径继续按独立 OpenSpec Clean Slate 迁移，不可借此改动旧运行时。
