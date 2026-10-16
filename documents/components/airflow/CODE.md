---
status: active
scope: airflow-source-code-map
last_verified: 2026-10-16
source_sha: badd7b400212ca7302f9ccd216c074359720d5a9
---

# Airflow — CODE / 源码导航

> **唯一 Airflow 组件源码地图**。本文件只说明源码位置、职责、入口及依赖，不重复维护业务 CURRENT/NEXT 或独立运维手册。组件职责见 [README.md](README.md)；运行安全边界见 [Safe Operations](../../operations/SAFE-OPERATIONS.md)。本清单按上述 Source SHA 的 Git 树核对，**不是当前 Kubernetes 运行态探针**。

## 主链路：正式 Consumer、发现与辅助模块

| 源文件（直接链接） | 作用 / 使用范围 |
| --- | --- |
| [`new_only_omop_consumer.py`](../../../airflow/dags/new_only_omop_consumer.py) | 经 Person/Visit E2E 验收的手工 NEW_ONLY Consumer DAG；串联 READY 选择、只读 Claim、Spark、对账和受控 Writer |
| [`new_only_omop_routing.py`](../../../airflow/dags/new_only_omop_routing.py) | 纯 Batch/Manifest 校验及 fail-closed 路由；完成批次走 `already_completed_no_replay` |
| [`new_only_omop_writer_handoff.py`](../../../airflow/dags/new_only_omop_writer_handoff.py) | Spark 结果与 Writer 之间的不可变交接校验；自身不授权 COMMIT |
| [`landing_batch_discovery.py`](../../../airflow/dags/landing_batch_discovery.py) | 独立、周期性 S3 Landing Discovery DAG；扫描不等于自动业务提交 |
| [`landing_spark_processing.py`](../../../airflow/dags/landing_spark_processing.py) | Landing/Spark opt-in 选择 Gate、校验及 KPO 工厂；辅助模块而非独立 DAG |

## Legacy / 兼容性源码（不可因文件名而删除）

| 源文件（直接链接） | 作用 / 使用范围 |
| --- | --- |
| [`task004_cdm_materialization_plan.py`](../../../airflow/dags/task004_cdm_materialization_plan.py) | 受约束的动态 CDM 批次 Plan 与标识校验 |
| [`task004_cdm_preflight_contract.py`](../../../airflow/dags/task004_cdm_preflight_contract.py) | Airflow → CDM Handoff 的只读前置合同校验 |
| [`task004_cdm_dynamic_source.py`](../../../airflow/dags/task004_cdm_dynamic_source.py) | 从已验证 S3 Processing Parquet 读取动态批次数据 |
| [`task004_cdm_dynamic_adapters.py`](../../../airflow/dags/task004_cdm_dynamic_adapters.py) | Person/Visit Canonical → OMOP 行适配、映射及校验 |
| [`task004_cdm_dynamic_pg_writer.py`](../../../airflow/dags/task004_cdm_dynamic_pg_writer.py) | PG 事务 SQL 渲染；不同 Writer 路径具有严格授权限制 |
| [`task004_cdm_postgres_readonly.py`](../../../airflow/dags/task004_cdm_postgres_readonly.py) | 只读 PostgreSQL / CDM 查询及权限验证 |
| [`task004_cdm_postgres_rollback_executor.py`](../../../airflow/dags/task004_cdm_postgres_rollback_executor.py) | 受控 PostgreSQL Rollback-only 验证执行器 |
| [`task004_processing_pipeline.py`](../../../airflow/dags/task004_processing_pipeline.py) | 历史 Processing-first DAG；保留其证据与依赖兼容 |

## 历史 TASK004 Airflow 只读核验（源码位于 apps）

| 实际源码文件 | 作用及使用边界 |
| --- | --- |
| [`step04a_inspect_airflow_log_lineage.py`](../../../apps/task004/step04a_inspect_airflow_log_lineage.py) | 历史 Airflow DagRun 日志血缘只读检查 |
| [`step04a_xcom_uri_readonly.py`](../../../apps/task004/step04a_xcom_uri_readonly.py) | 历史 Airflow XCom Processing URI 只读核验 |

## 平台探针

| 源文件（直接链接） | 作用 / 使用范围 |
| --- | --- |
| [`platform_portal_openlineage_probe.py`](../../../airflow/dags/platform_portal_openlineage_probe.py) | opt-in Airflow OpenLineage A3 Probe，不执行 S3/Spark/OMOP 业务 |
| [`airflow_smoke_test.py`](../../../airflow/dags/airflow_smoke_test.py) | 独立 Airflow 基础部署 Smoke DAG，非业务消费链路 |

## 相关测试、Contract 与构建入口

- **DAG / 路由**：[Consumer tests](../../../tests/landing_discovery/test_new_only_omop_airflow_consumer.py)、[Writer branch tests](../../../tests/landing_discovery/test_new_only_airflow_writer_branch.py)、[Discovery DAG contract](../../../tests/landing_discovery/test_airflow_dag_contract.py)。
- **Processing / Handoff**：[Spark processing gate](../../../tests/landing_discovery/test_spark_processing_gate.py)、[Airflow handoff](../../../tests/task004/test_step04f_airflow_handoff.py)、[Writer runtime](../../../tests/omop_writer/test_new_only_airflow_writer_runtime.py)。
- **契约**：[NEW_ONLY Batch identity](../../../contracts/synthea/producer-batch-identity-v1.json)、[Writer identity](../../../contracts/omop-writer/writer-batch-identity-v1.json)。
- **镜像依赖**：[Writer Dockerfile](../../../images/new-only-omop-writer/Dockerfile)、[Legacy 重构约束](../LEGACY-CODE-REFACTOR-PLAN.md)。历史 `task004_cdm_*.py` 的 Docker COPY、Import、镜像 Digest/数据库标识均需要迁移评审；README 整理不改变它们。

## CODE.md 同步规则（本组件）

**新增、删除或移动 `airflow/` 下的源文件，必须在同一个 PR 同步修改本 CODE.md**，并检查现有相对链接、测试入口和真实依赖。调整现有文件的职责、入口或重要依赖时也要同步更新；普通内部实现变更可核对后确认地图无需修改。

CI 的 [Component Code Naming](../../../.github/workflows/code-component-naming-check.yml) 使用 [Code Map Sync Guard](../../../scripts/quality/check_component_code_map.py) 对 Airflow 文件增删/改名执行最小检查，且校验这里列出的 `airflow/dags/*.py` 文件清单与实际源码一致。现在 `apps/` 的源代码由 Airflow、Synthea、Landing、OMOP 四份 CODE.md 分别拥有，并通过同一个 CI 自动检查；其它尚未建立 CODE.md 的目录不宣称覆盖。

**运行限制**：DAG/Smoke 代码存在不等于允许运行。已完成 Batch 不能随意重放；Writer UNKNOWN 需先只读核实 Claim/Stage/Checkpoint。参见 [组件说明](README.md) 和 [最终 E2E 历史验收](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md)。
