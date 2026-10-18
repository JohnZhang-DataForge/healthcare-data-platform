---
status: active
scope: code-organization-and-naming
last_verified: 2026-10-16
source_sha: 2c85b485381a72425506829fd321d93b164a231d
---

# Component-first 源代码组织与命名规范

**对所有 Agent 强制执行，自本规范进入 Main 起适用于新增代码。**

## 一、唯一规则

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

## 四、执行与验收

- 在创建新文件之前，Agent 先说明它属于哪个组件、负责什么功能；使用**功能名**组织路径、公共函数、DAG ID、镜像和新测试。
- [CI 命名检查](../../../.github/workflows/code-component-naming-check.yml) 用 [Python 检查器](../../../.github/quality/scripts/check_new_code_names.py) 对 PR 的**新增源码路径**拒绝 `taskNNN` / `stepNNN`；**不追溯阻断既有文件**。函数/变量、文本内部新名字由 Reviewer/Agent 依据本规范复核。
- 任务号允许出现在 PR、OpenSpec Change 的开发追踪、日志、历史证据。新正式脚本和测试**不允许**继续放入新建的 `scripts/taskNNN/` 或 `tests/taskNNN/`。
- 保持已验收 DAG ID、镜像 Digest、老数据库表/函数 `etl.task004_*`、Batch Identity；涉及兼容变更必须独立设计版本、回退、单测和必要的 Runtime 验收，不自行重放冻结 Batch。
- 对代码的真正迁移先制作依赖列表，再按模块逐 PR 执行。文档重建与代码重命名**不等于**获得运行 K8s/PG/Azure 的授权。
