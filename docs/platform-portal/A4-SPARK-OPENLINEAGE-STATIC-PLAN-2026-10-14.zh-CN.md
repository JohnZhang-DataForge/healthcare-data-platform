# Portal A4 — Spark OpenLineage Agent 静态开发交付与 Live Gate

## 0. TASK1 静态 CI 真实验证（**SUCCESS / 无共享 Runner**）

- [GitHub-hosted Static Run **38626855999**](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/38626855999)：**SUCCESS**，仅 `ubuntu-latest`，没有访问家中 Kubernetes / Self-Runner。
- Python3.11 `py_compile`：PASS；`unittest` **6/6 PASS**；PyYAML 离线 ConfigMap + SparkApplication 双 YAML Render：PASS。
- Runner 原始标志：`PORTAL_A4_GITHUB_HOSTED_OFFLINE_YAML_RENDER=PASS`、`PORTAL_A4_STATIC_TEST_SUITE=PASS`、`PORTAL_A4_REAL_SPARKAPPLICATION=NOT_RUN`、`PORTAL_A4_GITHUB_SELF_RUNNER=NOT_USED`、`PORTAL_A4_KUBERNETES_S3_OMOP_MUTATION=NO`。
- **结论**：TASK1 静态代码准备和结构测试闭环成功；Scala/JAR 与 JVM 的实际兼容、Spark Listener 发出的真正事件、Marquez Job/Run、S3 读写血缘尚未验收。A4 TASK2 LIVE = HOLD。

> **截至 2026-10-14 EDT：A4 TASK1 STAGED / STATIC ONLY；A4 TASK2 LIVE = HOLD。** 用户说 TASK004 Spark 已完成主要处理，但另一个 Session 目前卡在数据库 COMMIT 前的 Secret 创建；**不能根据“Spark 暂时不在运行”的推测直接执行 A4**。遵循 [多 Session 人工协调规则](./SESSION-COORDINATION-POLICY.zh-CN.md)。

## 1. 已有验证事实

- A2：Marquez 0.51.1 API/Web 实测 Ready，独立 dw-postgre14 上 PostgreSQL14 37 表，API Service 保持 ClusterIP；Web-only 30999。
- A3：Airflow 3.2.2 OpenLineage Provider 2.17.0 / Python 1.47.1 两次独立真实 DagRun；Marquez 两种 Task Job 各 2 条 COMPLETED Run（[真实 Closeout](./PORTAL-A3-AIRFLOW-OPENLINEAGE-REAL-LIVE-CLOSEOUT-2026-10-13.zh-CN.md)）。
- TASK004 Spark 运行真实环境（来自仓库 manifests 和 [TASK004 Live Closeout](../tasks/NEW-ONLY-AIRFLOW-SPARK-FRESH-70-11487-LIVE-HANDOFF-2026-10-14.zh-CN.md)）：Spark Operator CRD v1beta2、Spark 3.5.7 / spark:3.5.7-python3、dw-spark，worker02 标签 workload=platform，serviceAccount spark-job；Person 70 / Encounter 11,487 已有真实 Spark→Parquet 输出，但该事实**不能视为 Portal Spark OpenLineage 已配置**。

## 2. A4 TASK1 范围（不使用共享环境）

仅在 platform-portal/openlineage/spark 目录新增：
1. 每轮独立 sparkoperator.k8s.io/v1beta2 SparkApplication 模板，保留已有 image、Namespace/SA/nodeSelector，应用名 portal-a4-<token>。唯一新 Listener 为 io.openlineage.spark.agent.OpenLineageSparkListener，通过私有 Marquez API（http://marquez.dw-marquez.svc.cluster.local，/api/v1/lineage）。
2. OpenLineage 包固定 **候选** io.openlineage:openlineage-spark_2.12:1.47.1；Scala 2.12 / Agent JAR 与生产 Spark JVM 的兼容**未获 Live 验证**。使用特定 Job 的 spec.deps.packages 与 sparkConf，**不修改集群 Spark Operator 全局默认设置**。
3. ConfigMap 3 行独立 CSV + Python Spark 只读 aggregate 程序，通过 render.py 输出双 YAML；独立 namespace 只有 OpenLineage namespace；**Kubernetes namespace 仍用既有 dw-spark**（独立资源名/CSV），因为不确认 Operator 是否 watch 新 Namespace。
4. PyYAML 静态校验和纯 Python unit tests；允许 GitHub-hosted ubuntu-latest 静态 CI，**不允许 Self-Runner / Kubernetes 实际运行**。
5. 新 READMEs 与协调门槛；TASK004 文件/镜像、Airflow 业务 DAG、Writer、OMOP、S3 数据和现有 PG Secret 完全不改。

## 3. 风险与边界

**依赖/容器类：** 镜像 Spark 3.5.7 的 Scala binary 待实际确认；Agent JAR 通过 Ivy 初次下载可能受 DNS/外网/仓库镜像策略影响，这些属于 A4 实际验收前只读 preflight。不要因为依赖拉不下来就去重装 Spark Operator、更改现有业务镜像或给共享 Pod 注入全局 Jar。

**存储与血缘真实性：** 当前测试读取自身 ConfigMap CSV，执行真正的 Spark SQL 聚合，目的是验证 Spark Listener 的自动 START/COMPLETE Run 与尽力捕获只读输入；它不写 Parquet、不插 OMOP、不触发 TASK004，也不会自动关联 Airflow 的 Job。只有从 Marquez API 实际读到 Job/Run 才可标记 A4 LIVE PASS。S3/Parquet **输出** lineage 必须是将来另一次协调通过后的 Portal scratch dataset 真实 I/O 验证，严禁伪造 Source-to-OMOP 完成路径。

**运行影响：** 虽然资源名 portal-a4-* 独立，但任务实际运行仍占用 worker02、Spark Operator、network 和 Controller；需要与 TASK004 Session **人工串行**。不同 GitHub Actions 名称/Namespace 不是全局锁。

## 4. A4 TASK2 Live 验收前，Portal 必须主动问用户

> 我准备使用共享 Spark Operator 在 dw-spark/worker02 启动独立 SparkApplication portal-a4-<run-token>（driver 与 executor 各 1 CPU / 1Gi），向 dw-marquez 发送真实 OpenLineage 事件。**另一个 TASK004 Session 是否已暂停 Spark 和其他共享资源的修改、部署、测试？是否还有未完成的 Workflow / SparkApplication / Airflow DagRun，或即将开始的数据库 COMMIT 联调？** 若已暂停并释放此次共享执行窗口，请明确确认。确认后我仍先做只读的运行状态核验。

**未经确认 = HOLD。** TASK1 代码合并、或另一 Session 只说“卡在 Secret”，都不等于授权开始 TASK2。

## 5. 下一步

TASK1：Offline YAML render + 单元测试 PASS → PR 与 Main 合并 → 记录静态证据。**无 A4 Spark Live Run**。

TASK2：收到人工确认 → 实际只读 preflight → 只部署本次独立 A4 App/ConfigMap → Spark Run → Marquez Job/Run GET → 清理指定资源 → Closeout。无法验证时按项目规则最多尝试三轮，不占用 TASK004 的开发窗口。

源码入口：[A4 Spark 独立探针](../../platform-portal/openlineage/spark/README.md)。 
