---
status: active
scope: portal-spark-openlineage
last_verified: 2026-10-18
source_sha: ad39ed608c699ea3f30b74bd4bc331733d462e99
---

# Spark OpenLineage — A4 隔离 Smoke

**职责**：使用专属、隔离的 SparkApplication 和真实 Listener 发送 OpenLineage 事件到 Marquez；不是 Person/Visit 业务 ETL，不读取/修改 OMOP PostgreSQL、S3 生产批次、Writer Claim/Secret。实际源码与离线测试见 [CODE.md](CODE.md)。

## 独立静态源码及运行边界

- `render.py` 仅离线读取 `probe.py`、`input.csv` 与 `sparkapplication.yaml.tpl`，为唯一 Token 生成 ConfigMap + SparkApplication YAML，**不连接 Kubernetes、不执行 Apply**。
- `probe.py` 使用 3 行 CSV 做读取与分组统计；ConfigMap 通过只读挂载供 Driver/Executor 使用，未写入真实 Parquet/S3，因此**不能宣称输出 Dataset 血缘通过**。
- 模板设定 `dw-spark`、`spark:3.5.7-python3`、`spark-job` ServiceAccount，Spark Operator API `v1beta2`，单个 executor、`restartPolicy Never`；仅 per-job 配置 `io.openlineage:openlineage-spark_2.12:1.47.1` 和 `io.openlineage.spark.agent.OpenLineageSparkListener`。Scala binary、JAR 可访问性及真实环境兼容须在**另行授权 Live 操作前**核实，不把候选坐标说成生产全局配置。
- Marquez 目标为 `http://marquez.dw-marquez.svc.cluster.local/api/v1/lineage`；OpenLineage Namespace `healthcare-platform-spark-probe`，不伪造 Airflow parent run、业务关联或人工 POST JSON。

## A4 的真实验收与限制

**2026-10-14 历史结果**：隔离 SparkApplication **COMPLETED**、3 行 CSV 聚合成功、Marquez 收到带 Spark facets 的真实 COMPLETED Run。**初始 Workflow 38628542127 的整体结论仍为 FAILURE**；后续受控只读 Run 38629607225 等验证部分结果成功。`portal_a4_a438628542127` 应用 Job 的 `latestRun` 仍为空，完成 Run 出现在 `unknown` Job，`inputDatasetVersions=0` / `outputDatasetVersions=0`。Job/Run 关联与真实 Dataset I/O 的根因尚未确认，不允许声称完整业务血缘通过。

[固定 A4 Closeout](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/A4-SPARK-OPENLINEAGE-REAL-SMOKE-2026-10-14.zh-CN.md) · [原失败 Run](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38628542127) · [只读核验 Run](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38629607225)。

## 静态检查与安全门禁

离线开发依赖 `requirements-static.txt` 的 PyYAML 和 `tests/test_static.py`；静态检查验证 Token、生成 YAML、镜像/资源限制、Listener 属性和 Probe 逻辑，不触发集群。历史 README 中的 `TASK1_STATIC=PASS` / `A4_LIVE=NOT_RUN` 表示**任务 1 刚完成时的时点**；后续已有独立 Live Smoke，因此不应再将这两个时间点混为一谈。

再次执行真实 Smoke、添加 S3/Parquet Dataset、修改 Operator/JAR、调度新 Pod 或清理 Job 必须遵守 [Session Coordination](../../../engineering/development/SESSION-COORDINATION.md) 与 [Safe Operations](../../../engineering/operations/SAFE-OPERATIONS.md)。未来 Person/Visit 集成方案**尚未批准**，不通过本次文档迁移落地。

[CODE](CODE.md) · [系统 README](../README.md) · [Marquez](../marquez/README.md)。
