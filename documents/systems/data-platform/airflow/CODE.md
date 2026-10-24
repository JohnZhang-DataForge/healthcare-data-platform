---
status: active
scope: airflow-source-code-map
last_verified: 2026-10-24
source_sha: 460069e37d3ac38ec2f240f3105d023799340785
---

# Airflow — CODE / 源码导航

> **唯一 Airflow 组件源码地图**。本文件只说明源码位置、职责、入口及依赖，不重复维护业务 CURRENT/NEXT 或独立运维手册。组件职责见 [README.md](README.md)；运行安全边界见 [Safe Operations](../../../engineering/operations/SAFE-OPERATIONS.md)。本清单按上述 Source SHA 的 Git 树核对，**不是当前 Kubernetes 运行态探针**。

## 主链路：正式 Consumer、发现与辅助模块

| 源文件（直接链接） | 作用 / 使用范围 |
| --- | --- |
| [`new_only_omop_consumer.py`](../../../../local-data-platform/airflow/dags/new_only_omop_consumer.py) | 经 Person/Visit E2E 验收的手工 NEW_ONLY Consumer DAG；串联 READY 选择、只读 Claim、Spark、对账和受控 Writer。Portal P2 在既有 DAG 外层使用 Provider 的 `enable_lineage(DAG(...))`，仅增加可观测 opt-in，不改 DAG/Task ID、XCom 或 Writer Gate；新业务 Run 及 Transport 生效仍待 Live 读回 |
| [`new_only_omop_routing.py`](../../../../local-data-platform/airflow/dags/new_only_omop_routing.py) | 纯 Batch/Manifest 校验及 fail-closed 路由；完成批次走 `already_completed_no_replay` |
| [`new_only_omop_writer_handoff.py`](../../../../local-data-platform/airflow/dags/new_only_omop_writer_handoff.py) | Spark 结果与 Writer 之间的不可变交接校验；自身不授权 COMMIT |
| [`landing_batch_discovery.py`](../../../../local-data-platform/airflow/dags/landing_batch_discovery.py) | 独立、周期性 S3 Landing Discovery DAG；扫描不等于自动业务提交 |
| [`landing_spark_processing.py`](../../../../local-data-platform/airflow/dags/landing_spark_processing.py) | Landing/Spark opt-in 选择 Gate、校验及 KPO 工厂；辅助模块而非独立 DAG |

## Legacy / 兼容性源码（不可因文件名而删除）

| 源文件（直接链接） | 作用 / 使用范围 |
| --- | --- |
| [`task004_cdm_materialization_plan.py`](../../../../local-data-platform/airflow/dags/task004_cdm_materialization_plan.py) | 受约束的动态 CDM 批次 Plan 与标识校验 |
| [`task004_cdm_preflight_contract.py`](../../../../local-data-platform/airflow/dags/task004_cdm_preflight_contract.py) | Airflow → CDM Handoff 的只读前置合同校验 |
| [`task004_cdm_dynamic_source.py`](../../../../local-data-platform/airflow/dags/task004_cdm_dynamic_source.py) | 从已验证 S3 Processing Parquet 读取动态批次数据 |
| [`task004_cdm_dynamic_adapters.py`](../../../../local-data-platform/airflow/dags/task004_cdm_dynamic_adapters.py) | Person/Visit Canonical → OMOP 行适配、映射及校验 |
| [`task004_cdm_dynamic_pg_writer.py`](../../../../local-data-platform/airflow/dags/task004_cdm_dynamic_pg_writer.py) | PG 事务 SQL 渲染；不同 Writer 路径具有严格授权限制 |
| [`task004_cdm_postgres_readonly.py`](../../../../local-data-platform/airflow/dags/task004_cdm_postgres_readonly.py) | 只读 PostgreSQL / CDM 查询及权限验证 |
| [`task004_cdm_postgres_rollback_executor.py`](../../../../local-data-platform/airflow/dags/task004_cdm_postgres_rollback_executor.py) | 受控 PostgreSQL Rollback-only 验证执行器 |
| [`task004_processing_pipeline.py`](../../../../local-data-platform/airflow/dags/task004_processing_pipeline.py) | 历史 Processing-first DAG；保留其证据与依赖兼容 |

## 历史 TASK004 Airflow 只读核验（源码位于 apps）

| 实际源码文件 | 作用及使用边界 |
| --- | --- |
| [`step04a_inspect_airflow_log_lineage.py`](../../../../local-data-platform/apps/task004/step04a_inspect_airflow_log_lineage.py) | 历史 Airflow DagRun 日志血缘只读检查 |
| [`step04a_xcom_uri_readonly.py`](../../../../local-data-platform/apps/task004/step04a_xcom_uri_readonly.py) | 历史 Airflow XCom Processing URI 只读核验 |

## 平台探针

| 源文件（直接链接） | 作用 / 使用范围 |
| --- | --- |
| [`platform_portal_openlineage_probe.py`](../../../../local-data-platform/airflow/dags/platform_portal_openlineage_probe.py) | opt-in Airflow OpenLineage A3 Probe，不执行 S3/Spark/OMOP 业务 |
| [`airflow_smoke_test.py`](../../../../local-data-platform/airflow/dags/airflow_smoke_test.py) | 独立 Airflow 基础部署 Smoke DAG，非业务消费链路 |

## 相关测试、Contract 与构建入口

- **NEW_ONLY 真正 Provider Macro Jinja 渲染（离线）**：[OpenLineage task parent macro test](../../../../local-data-platform/tests/airflow/test_portal_openlineage_parent_macros.py) 在 Airflow 3.2.2 pinned 容器内直接调用已安装 OpenLineage Provider 的真实宏函数（离线容器不冒称运行态插件注册），并对 `spark_patient` / `spark_encounter` / `spark_reconcile` 的 KPO `env_vars` 做 Strict Jinja 渲染；核对 Namespace、Task Job Name、真实 UUID、3 个不同 Task Run ID。复用原有 [DagBag CI](../../../../.github/workflows/local-dp-airflow-dagbag-parse.yml)，网络关闭且无数据库、DagRun、Pod 或 Writer 写操作。**本测试仍不证明现网 Airflow Scheduler/GitSync 及新镜像已发布**。


- **Portal P2 OpenLineage selective/负向边界**：[Opt-in contract tests](../../../../local-data-platform/tests/landing_discovery/test_new_only_openlineage_opt_in.py)（纯离线 AST，不触发 DagRun；核对现有 14 个 Task ID、A3 Probe、Discovery 默认未 opt-in）。
- **DAG / 路由**：[Consumer tests](../../../../local-data-platform/tests/landing_discovery/test_new_only_omop_airflow_consumer.py)、[Writer branch tests](../../../../local-data-platform/tests/landing_discovery/test_new_only_airflow_writer_branch.py)、[Discovery DAG contract](../../../../local-data-platform/tests/landing_discovery/test_airflow_dag_contract.py)。
- **Processing / Handoff**：[Spark processing gate](../../../../local-data-platform/tests/landing_discovery/test_spark_processing_gate.py)、[Airflow handoff](../../../../local-data-platform/tests/task004/test_step04f_airflow_handoff.py)、[Writer runtime](../../../../local-data-platform/tests/omop_writer/test_new_only_airflow_writer_runtime.py)。
- **契约**：[NEW_ONLY Batch identity](../../../../local-data-platform/contracts/synthea/producer-batch-identity-v1.json)、[Writer identity](../../../../local-data-platform/contracts/omop-writer/writer-batch-identity-v1.json)。
- **镜像依赖**：[Writer Dockerfile](../../../../local-data-platform/images/new-only-omop-writer/Dockerfile)、[Legacy 重构约束](../../../engineering/development/LEGACY-CODE-REFACTOR-PLAN.md)。历史 `task004_cdm_*.py` 的 Docker COPY、Import 和数据库标识仍需兼容；开发镜像使用 :latest，运行证据记录实际 Pod imageID/Digest；README 整理不改变它们。

## 历史控制面镜像（Airflow 调度及旧 TASK004）

| 源文件（直接链接） | 用途与运行边界 |
| --- | --- |
| [`Dockerfile`](../../../../local-data-platform/images/task004-runtime/Dockerfile) | 历史 Airflow/Spark 控制面容器：kubectl、生成/处理脚本与跨 namespace 编排，不是 Spark 执行器 |
| [`entrypoint.sh`](../../../../local-data-platform/images/task004-runtime/entrypoint.sh) | 历史控制面 CLI：resolve / generate-publish / person / visit / reconcile；调用固定旧脚本 |

## 历史控制面与跨 Namespace RBAC

| 源文件（直接链接） | 用途与运行边界 |
| --- | --- |
| [`airflow-task004-control-runtime-rbac.yaml`](../../../../local-data-platform/kubernetes/manifests/task004/airflow-task004-control-runtime-rbac.yaml) | 历史 dw-spark Airflow Pod Launcher Role/Binding：跨 namespace Scheduler Pod 权限 |
| [`control-runtime-rbac.yaml`](../../../../local-data-platform/kubernetes/manifests/task004/control-runtime-rbac.yaml) | 历史 dw-spark 控制面 ServiceAccount/Role/Binding：SparkApplication、ConfigMap、Pods 权限 |
| [`control-runtime-synthea-rbac.yaml`](../../../../local-data-platform/kubernetes/manifests/task004/control-runtime-synthea-rbac.yaml) | 历史控制面跨 dw-synthea 的 Job/ConfigMap/Secret RBAC；不等于当前授权 |

**RBAC 安全**：这些 Role/Binding 是旧控制面真实权限声明，包括 Pod 执行、SparkApplication/ConfigMap 变更和跨 `dw-synthea` Secret 读取。不能作为新 Agent 的默认运行授权，也不能仅凭文件存在断言当前集群已部署。修改 RBAC 或重放历史 Job 必须单独审查权限、现网 Namespace、会话冲突与部署窗口。

## 历史 Shell / 脚本导航（由 airflow 组件负责）

> 本清单是历史 Step Shell 的**代码索引，不是按顺序执行的 Runbook**。这些文件可能使用固定 Git SHA/Batch ID、操作 S3/PG/K8s、修改仓库源码或生成本地报告；任何执行须先读脚本全文并核对 [Safe Operations](../../../engineering/operations/SAFE-OPERATIONS.md)。新脚本必须按组件/能力命名，不能新增 `taskNNN` 路径。

## 历史 task004（2 个入口）

| 真实源文件 | 主要职责与执行风险 |
| --- | --- |
| [`05b-prepare-person-visit-runtime-interface.sh`](../../../../local-data-platform/scripts/task004/05b-prepare-person-visit-runtime-interface.sh) | [PREPARE / may write] 历史 TASK004 prepare person visit runtime interface 脚本；可能生成/覆盖仓库源码或报告，先检查目标路径 |
| [`06a-prepare-unified-runtime-image.sh`](../../../../local-data-platform/scripts/task004/06a-prepare-unified-runtime-image.sh) | [PREPARE / may write] 历史 TASK004 prepare unified runtime image 脚本；可能生成/覆盖仓库源码或报告，先检查目标路径 |

## 只读部署来源核验

| 真实源文件 | 主要职责与执行风险 |
| --- | --- |
| [`read-only-gitsync-spark-provenance.sh`](../../../../local-data-platform/scripts/quality/read-only-gitsync-spark-provenance.sh) | [CHECK / read-only opt-in] 只读采集 Airflow Pod DAG 挂载和指定 Spark ConfigMap；核对 Git 中单个 Python 源文件 SHA256。需显式 Kubernetes context 和最小只读权限，不自动执行，不核验运行中 GitSync checkout SHA；原始证据敏感，不提交仓库 |

## CODE.md 同步规则（本组件）

**新增、删除、移动或重命名本组件负责的 `airflow/`、`apps/`、`images/`、`kubernetes/`、`scripts/` 下的源文件，必须在同一个 PR 同步修改本 CODE.md**，并检查现有相对链接、测试入口和真实依赖。调整现有文件的职责、入口或重要依赖时也要同步更新；普通内部实现变更可核对后确认地图无需修改。

CI 的 [Component Code Naming](../../../../.github/workflows/code-component-naming-check.yml) 使用 [Code Map Sync Guard](../../../../.github/quality/scripts/check_component_code_map.py) 对 Airflow 文件增删/改名执行最小检查，且校验这里列出的 `airflow/dags/*.py` 文件清单与实际源码一致。现在 `apps/` 的源代码由 Airflow、Synthea、Landing、OMOP 四份 CODE.md 分别拥有，并通过同一个 CI 自动检查；其它尚未建立 CODE.md 的目录不宣称覆盖。

**运行限制**：DAG/Smoke 代码存在不等于允许运行。已完成 Batch 不能随意重放；Writer UNKNOWN 需先只读核实 Claim/Stage/Checkpoint。参见 [组件说明](README.md) 和 [最终 E2E 历史验收](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md)。
