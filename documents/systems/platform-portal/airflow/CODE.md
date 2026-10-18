---
status: active
scope: portal-airflow-openlineage-source-map
last_verified: 2026-10-18
source_sha: ad39ed608c699ea3f30b74bd4bc331733d462e99
---

# Airflow OpenLineage — CODE / 源码导航

| 实际源码文件 | 功能、部署与安全边界 |
| --- | --- |
| [`airflow/dags/platform_portal_openlineage_probe.py`](../../../../airflow/dags/platform_portal_openlineage_probe.py) | 真实 Airflow opt-in Probe DAG，`schedule=None`，2 个无业务数据任务；部署读取仍通过现有 Airflow DAG GitSync |
| [`configure-scheduler.sh`](../../../../platform-portal/openlineage/airflow/configure-scheduler.sh) | 有副作用：改共享 Scheduler 的 OpenLineage 环境变量、选择性采集并触发滚动更新 |
| [`verify-real-events.sh`](../../../../platform-portal/openlineage/airflow/verify-real-events.sh) | **真实 DAG Trigger**、Task 状态和 Marquez API 查询，不是离线单元测试 |

**源码所有权**：Probe DAG 属于 Airflow 的 DAG Source Root，也被 [Data Platform Airflow CODE](../../data-platform/airflow/CODE.md) 记录；这里记录 Portal 观测职责，不能复制真正的 Person/Visit ETL 到 Portal。任何脚本执行都需要受控 Scheduler/Marquez 状态、精确 SHA/Run、授权和真实事件读回。

[组件 README](README.md) · [系统 CODE](../CODE.md) · [Marquez CODE](../marquez/CODE.md)。
