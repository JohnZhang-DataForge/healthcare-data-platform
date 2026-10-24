---
status: active
scope: portal-spark-openlineage
last_verified: 2026-10-24
source_sha: ad39ed608c699ea3f30b74bd4bc331733d462e99
---

# Spark OpenLineage — A4 隔离 Smoke

> **2026-10-24 P4 实际业务上线读回（覆盖下方“尚未运行业务”历史备注）**：[真实 NEW_ONLY Spark-only 验收 #40125211881](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40125211881) 中三个 Spark 业务 Task 成功，真实 KPO Container `imageID` 与新 `:latest` Digest 一致。Marquez **业务 Spark 子 Job**（非顶层应用 Job）已取得 Person/Visit 各 1 S3 Landing Input + 1 S3 Processing Output [#40125843864](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40125843864)；Reconcile 的两条输入也存在，但对应 Child Runs 仍处于 RUNNING [#40125995864](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40125995864)。**尚不能宣称 P4 完整终态通过；Writer COMMIT、PG17 和 SKIP 尚未执行。** [真实业务验收细节与 Run IDs](../../../../openspec/changes/complete-platform-portal-lineage-integration/evidence/PORTAL-P4-REAL-NEWONLY-PERSON-VISIT-RECONCILE-20261024.md)。


> **2026-10-24 P4 NEW_ONLY 真实业务模板现已打包发布（不是 E2E）**：[P4 单镜像 GHCR Release #40123946926](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/40123946926) 对现有 `landing-processing-v2` 单一子镜像 Clean Build、三个 Listener 镜像内 Smoke、`:latest` Digest 读回均 PASS。新镜像 `sha256:f735f6088efad7f0f0b6f2a4d2540ecfa5195925cda719cfc0c17c5e78a21f37`；旧 Digest/回退标签已记录。P4 Person/Visit/Reconcile **实际 NEW_ONLY DagRun/Pod/Marquez 业务 Dataset 仍待验证**。详见 [P4 Release Evidence](../../../../openspec/changes/complete-platform-portal-lineage-integration/evidence/PORTAL-P4-BUSINESS-IMAGE-LATEST-RELEASE-20261024.md)。


**职责**：使用专属、隔离的 SparkApplication 和真实 Listener 发送 OpenLineage 事件到 Marquez；不是 Person/Visit 业务 ETL，不读取/修改 OMOP PostgreSQL、S3 生产批次、Writer Claim/Secret。实际源码与离线测试见 [CODE.md](CODE.md)。

## 独立静态源码及运行边界

- `render.py` 仅离线读取 `probe.py`、`input.csv` 与 `sparkapplication.yaml.tpl`，为唯一 Token 生成 ConfigMap + 本次独占的 1Gi `local-path` PVC + SparkApplication YAML，**不连接 Kubernetes、不执行 Apply**。
- P3 更新后的 `probe.py` 使用 3 行 CSV 做读取与分组统计；ConfigMap 只读挂载输入，Driver/Executor 将 Parquet 真正写到其专属 PVC，并再次通过 Spark 读回验证（2 行）。不写 S3/OMOP。**尚未有实机 Spark/Marquez Run 证明新的输出血缘被成功采集**；旧 A4 没有实际输出的历史测试仍不可冒充。
- 模板设定 `dw-spark`、`spark:3.5.7-python3`、`spark-job` ServiceAccount，Spark Operator API `v1beta2`，单个 executor、`restartPolicy Never`；仅 per-job 配置 `io.openlineage:openlineage-spark_2.12:1.47.1` 和 `io.openlineage.spark.agent.OpenLineageSparkListener`。Scala binary、JAR 可访问性及真实环境兼容须在**另行授权 Live 操作前**核实，不把候选坐标说成生产全局配置。
- P3 增加 `spark.openlineage.appName=portal-a4-<run-token>` 作为 `unknown` Job 关联的候选改进；是否解决必须通过真实 Run+Dataset 读回，不在离线阶段宣称修复。
- Marquez 目标为 `http://marquez.dw-marquez.svc.cluster.local/api/v1/lineage`；OpenLineage Namespace `healthcare-platform-spark-probe`，不伪造 Airflow parent run、业务关联或人工 POST JSON。

> **最新 P3 独立 Live 验收（2026-10-24）**：[Run #40120840326](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40120840326) 真实 Spark COMPLETED、3 行 CSV 聚合、PVC 上 Parquet 写出再读回 2 行、Marquez **非 unknown** 具体 Job + COMPLETED Run + 1 Input + 1 Output DatasetVersion，均 PASS。旧 A4 `unknown` / 0 Output 的历史结果仍保留，不能推断根因在单独一个配置；本次**未运行实际 OMOP Person/Visit/S3**。完整 [P2/P3 实机 evidence](../../../../openspec/changes/complete-platform-portal-lineage-integration/evidence/PORTAL-P2-P3-ISOLATED-LIVE-VERIFICATION-20261024.md)。

## A4 的真实验收与限制

**2026-10-14 历史结果**：隔离 SparkApplication **COMPLETED**、3 行 CSV 聚合成功、Marquez 收到带 Spark facets 的真实 COMPLETED Run。**初始 Workflow 38628542127 的整体结论仍为 FAILURE**；后续受控只读 Run 38629607225 等验证部分结果成功。`portal_a4_a438628542127` 应用 Job 的 `latestRun` 仍为空，完成 Run 出现在 `unknown` Job，`inputDatasetVersions=0` / `outputDatasetVersions=0`。Job/Run 关联与真实 Dataset I/O 的根因尚未确认，不允许声称完整业务血缘通过。

[固定 A4 Closeout](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/A4-SPARK-OPENLINEAGE-REAL-SMOKE-2026-10-14.zh-CN.md) · [原失败 Run](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38628542127) · [只读核验 Run](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38629607225)。

## 静态检查与安全门禁

离线开发依赖 `requirements-static.txt` 的 PyYAML 和 `tests/test_static.py`；静态检查验证 Token、生成 YAML、镜像/资源限制、Listener 属性和 Probe 逻辑，不触发集群。历史 README 中的 `TASK1_STATIC=PASS` / `A4_LIVE=NOT_RUN` 表示**任务 1 刚完成时的时点**；后续已有独立 Live Smoke，因此不应再将这两个时间点混为一谈。

再次执行真实 Smoke、创建 PVC/写测试 Parquet、修改 Operator/JAR、调度新 Pod 或清理 Job 必须遵守 [Session Coordination](../../../engineering/development/SESSION-COORDINATION.md) 与 [Safe Operations](../../../engineering/operations/SAFE-OPERATIONS.md)。未来 Person/Visit 集成方案**尚未批准**，不通过本次文档迁移落地。

[CODE](CODE.md) · [系统 README](../README.md) · [Marquez](../marquez/README.md)。

### P3 新版隔离输出与清理边界

- 生成资源：`portal-a4-<token>` SparkApplication、`portal-a4-<token>-source` ConfigMap、`portal-a4-<token>-output` PVC；全部仅用于隔离测试。两个 Pod 均在 `workload=platform`，共用单节点 `ReadWriteOnce` PVC；需在 Live 之前确认 Operator 挂载支持、存储卷权限、空闲资源和 JAR 下载。
- 输出 `file:///opt/spark/portal-a4-output/<token>/summary.parquet`；`errorifexists` 确保不覆盖。测试 PVC 后续只允许针对**已确认本次 token**的资源清理，不会清理已有业务 S3/PG。
- 实验的输入和输出 Dataset 边仍是待证事实；如文件 URI 被 OpenLineage 过滤，应保留原始日志与 Marquez GET 结果，不能通过人工 POST 假事件凑数。
