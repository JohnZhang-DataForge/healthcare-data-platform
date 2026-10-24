---
status: active
scope: portal-airflow-openlineage-source-map
last_verified: 2026-10-24
source_sha: 460069e37d3ac38ec2f240f3105d023799340785
---

# Airflow OpenLineage — CODE / 源码导航

| 实际源码文件 | 功能、部署与安全边界 |
| --- | --- |
| [`airflow/dags/platform_portal_openlineage_probe.py`](../../../../local-data-platform/airflow/dags/platform_portal_openlineage_probe.py) | 真实 Airflow opt-in Probe DAG，`schedule=None`，2 个无业务数据任务；部署读取仍通过现有 Airflow DAG GitSync |
| [`new_only_omop_consumer.py`](../../../../local-data-platform/airflow/dags/new_only_omop_consumer.py) | **P2 业务侧显式 opt-in**：使用与 A3 一致的 `enable_lineage(DAG(...))`；14 个原 Task、路由和 Writer 许可不改。只在 Airflow `SELECTIVE_ENABLE=True`、实际执行组件具备 Provider/Transport 时发出真实事件；运行态尚未验收 |
| [`test_new_only_openlineage_opt_in.py`](../../../../local-data-platform/tests/landing_discovery/test_new_only_openlineage_opt_in.py) | 离线 AST 合同：DAG selective wrapper、14 Task ID、XCom/Writer Gate，以及 Discovery 默认不 opt-in 的负向检查 |
| [`configure-scheduler.sh`](../../../../platform-portal/openlineage/airflow/configure-scheduler.sh) | 有副作用：改共享 Scheduler 的 OpenLineage 环境变量、选择性采集并触发滚动更新 |
| [`verify-real-events.sh`](../../../../platform-portal/openlineage/airflow/verify-real-events.sh) | **真实 DAG Trigger**、Task 状态和 Marquez API 查询，不是离线单元测试 |

**源码所有权**：Probe DAG 属于 Airflow 的 DAG Source Root，也被 [Data Platform Airflow CODE](../../data-platform/airflow/CODE.md) 记录；这里记录 Portal 观测职责，不能复制真正的 Person/Visit ETL 到 Portal。A3 `configure-scheduler.sh` 仅修改 Scheduler；是否覆盖实际 Task 事件发送进程必须经 P2 只读检查证实。P2 单纯变更 DAG Git 文件不会自动修复集群配置，不能将 Provider 2.17.0 历史验收扩展为当前 Worker/Transport 运行证据。任何脚本执行都需要受控 Scheduler/Marquez 状态、精确 SHA/Run、授权和真实事件读回。

[组件 README](README.md) · [系统 CODE](../CODE.md) · [Marquez CODE](../marquez/CODE.md)。
