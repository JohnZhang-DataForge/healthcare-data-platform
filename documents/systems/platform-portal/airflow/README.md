---
status: active
scope: portal-airflow-openlineage
last_verified: 2026-10-18
source_sha: ad39ed608c699ea3f30b74bd4bc331733d462e99
---

# Airflow OpenLineage — A3 真实事件探针

**职责**：向 Marquez 发送真实 Airflow DAG/Task/Run OpenLineage 事件，并验证 Provider 和 Marquez 读取；**不**处理 S3、Spark/OMOP Writer 或业务数据库写入。Portal Airflow 观测源码由 [CODE.md](CODE.md) 维护，业务 Airflow DAG/路由由 [Data Platform Airflow CODE](../../data-platform/airflow/CODE.md) 管理。

> **最新 P2 真实验证（2026-10-24）**：Scheduler 与 DAG Processor 上现有 NEW_ONLY DAG 的 GitSync SHA256 对上源码、Scheduler OpenLineage 2.17.0/Transport/Selective 配置 [#40120678131](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40120678131) PASS；真实运行两任务 `platform_portal_openlineage_probe`（DagRun `portal-ol-40121352170`）及其 Marquez DAG/Task Jobs [#40121352170](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40121352170) PASS。**仍待业务 `new_only_omop_consumer` 的真实 DagRun Job/Run 读回**；DAG Processor/API Server/Triggerer 配置不全，需按事件实际发送进程判定影响。完整 [P2/P3 evidence](../../../openspec/changes/complete-platform-portal-lineage-integration/evidence/PORTAL-P2-P3-ISOLATED-LIVE-VERIFICATION-20261024.md)。

## 历史实现与验收范围

- 既有 Airflow 3.2.2、OpenLineage Provider **2.17.0**；`airflow/dags/platform_portal_openlineage_probe.py` 是 opt-in、`schedule=None` 的两个轻量 PythonOperator 任务，**不属于业务数据生产 DAG**。
- A3 真正触发的 [Run 38502227961](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38502227961) 两个 TaskInstance SUCCESS；[Marquez 读回 Run 38502899963](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38502899963) 证实两条 COMPLETED Task Run；[Run 38502759492](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38502759492) 只针对 Portal DAG 解除 Pause。
- [A3 正式 Closeout](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/PORTAL-A3-AIRFLOW-OPENLINEAGE-REAL-LIVE-CLOSEOUT-2026-10-13.zh-CN.md) 是 **2026-10-13 的历史事实**，不证明所有业务 DAG 已安装 Provider 或当前 Event 持续正常。

## Scheduler 改动风险与后续限制

`configure-scheduler.sh` 使用 `AIRFLOW__OPENLINEAGE__TRANSPORT` 指向内部 `http://marquez.dw-marquez.svc.cluster.local/api/v1/lineage`；Namespace `healthcare-platform-airflow`，`SELECTIVE_ENABLE=True`、`DISABLE_SOURCE_CODE=True`。只对明确 `enable_lineage` 的 DAG 发送事件，**不默认接管所有业务 DAG**。

该脚本先检查是否有 Running/Queued 等任务，然后会执行 **`kubectl set env`、Scheduler Deployment 滚动更新**；这不是纯只读操作。未来 Helm Values 持久化仍需独立评估，避免 Helm upgrade 回滚手动改动；任何再次执行前需检查其他 Session 和共享 DAG/Task 实际状态，必须获得授权。

[Airflow CODE](CODE.md) · [Marquez](../marquez/README.md) · [系统 README](../README.md) · [Safe Operations](../../../engineering/operations/SAFE-OPERATIONS.md)。
