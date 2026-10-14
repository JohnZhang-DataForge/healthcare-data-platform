# Platform Portal A3 — Airflow OpenLineage Provider

> **CURRENT RESULT = REAL PASS**：Airflow [Run 38502227961](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38502227961) 真实独立 opt-in DAG success、2 TaskInstances success、Marquez 3 Job 名称；Marquez [Run 38502899963](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38502899963) 真正读回两条 COMPLETED Task Run。新 DAG 默认 Paused，已由 [Run 38502759492](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38502759492) 仅为 Portal DAG 解除暂停。详见 [正式 A3 Closeout](../../../docs/platform-portal/A3-AIRFLOW-OPENLINEAGE-REAL-LIVE-CLOSEOUT-2026-10-13.zh-CN.md)。下一步 A4 Spark Agent，独立于 TASK004。

## 实施范围

已有 Airflow 3.2.2、OpenLineage Provider 2.17.0，Marquez API 在 dw-marquez 内网可访问。

新文件：
- airflow/dags/platform_portal_openlineage_probe.py：仅 opt-in DAG，两个无业务数据的 PythonOperator，schedule=None，不执行 S3/Spark/OMOP/Writer
- platform-portal/openlineage/airflow/configure-scheduler.sh：修改 Scheduler OpenLineage 的 transport、namespace、selective_enable 和 disable_source_code；**检测到任何运行/排队任务就停止，不重启**
- platform-portal/openlineage/airflow/verify-real-events.sh：GitSync SHA、DagBag parse、触发独立 DAG、读回两项 TaskInstance success 和 Marquez 内实际 Job

Provider 配置使用 AIRFLOW__OPENLINEAGE__TRANSPORT，目标为 http://marquez.dw-marquez.svc.cluster.local 的 api/v1/lineage；Namespace 固定 healthcare-platform-airflow。设置 AIRFLOW__OPENLINEAGE__SELECTIVE_ENABLE=True，只有通过 enable_lineage 明确标注的 Portal DAG 会发送事件，其他业务 DAG 先不采集。

## 运行边界

这是一个真实 Airflow DAG/Task/Run 事件验证，而不是完整 Synthea → OMOP 血缘，也没有伪造 S3 数据集、COMMIT 或 Provider 事件。

**共享基础设施影响**：configure-scheduler.sh 仅修改 Airflow Scheduler Deployment 的 env 并滚动更新，不改 TASK004 DAG/Claim/Writer，且在任何活跃任务时拒绝操作。但依然会短暂滚动共享 Scheduler，需要在无执行任务的时间运行。这个改变属于受控过渡部署；未来应纳入现有 Airflow Helm values 并回归验证，避免 helm upgrade 回滚配置。

验收需出现真实 Runner Run ID、Airflow run ID、TaskInstance 状态和 Marquez 私有 API Job/Run 证据；不能将一次配置写入直接当作 A3 完成。数据库和 Kubernetes 的其他 Namespace 不可修改。
