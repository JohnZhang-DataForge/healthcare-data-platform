# A4 — Standalone Spark → OpenLineage → Marquez (STATIC SOURCE + ONE REAL SMOKE DONE)

**任务 1 源码起点是静态交付；2026-10-14 后来已进行一次独立真实 Spark Smoke（Spark/CSV 成功，Marquez 真 Run 回读 PASS，App Job↔Run 命名和 Dataset facets 仍未完成）**。详见 [A4 实测 Closeout](../../../docs/platform-portal/A4-SPARK-OPENLINEAGE-REAL-SMOKE-2026-10-14.zh-CN.md)。 先阅读 [Portal 人工协调规则](../../../docs/platform-portal/SESSION-COORDINATION-POLICY.zh-CN.md)：用户确认另一个 TASK004 Session 仍在处理最后 DB COMMIT/Secret。**在用户明确暂停共享集群工作且实时只读检查通过之前，不得触发 Runner/Kubernetes/SparkApplication**。

## 结构与隔离

- sparkapplication.yaml.tpl — SparkApplication v1beta2，镜像沿用已有 spark:3.5.7-python3，仅为这个独立 Job 安装 OpenLineage Listener。CR Namespace dw-spark（已有 Operator watch/ServiceAccount 的已知命名空间），名称每次使用唯一 portal-a4-<run-token>。
- probe.py + input.csv — 完全独立的 3 行 CSV Spark 读和聚合测试。CSV 通过每次生成的 ConfigMap 安装到 Driver/Executor **相同只读目录**。不使用 TASK004 的 Python、S3、Claim、Writer、PostgreSQL 或业务 Secret；没有真实输出 Parquet，因此不报告成功 output lineage。
- render.py — **离线**生成 ConfigMap + SparkApplication 双 YAML，不含 kubectl/客户端操作，也不自动 apply/trigger。使用严格 DNS token，防止覆盖另一轮名字。
- tests/test_static.py — 纯 Python/PyYAML 静态测试，无 Spark、集群、网络、Secret。

**现有运行环境推断（非 A4 Live 证明）**：Spark 3.5.7，worker02/workload=platform，Spark Operator API sparkoperator.k8s.io/v1beta2，dw-spark/spark-job。使用 Scala 2.12 的 **候选** OpenLineage Maven 坐标 io.openlineage:openlineage-spark_2.12:1.47.1；选择 1.47.1 是与现有 Airflow 端 openlineage-python 版本接近，**不是证明 Spark JVM Scala 版本/JAR 可加载，也不是跨组件必须同版本**。A4 Live 先只读确认 Spark 镜像 Scala binary、Maven 依赖解析/Java 兼容。若不符，只改 Portal 专属文件，绝不更改共享 Spark Operator 或 TASK004 镜像。

真实 HTTP Collector：内部 ClusterIP http://marquez.dw-marquez.svc.cluster.local + /api/v1/lineage，namespace healthcare-platform-spark-probe。**不会增加 Airflow parent ID 或伪造关联边**。

## 任务 1：仅本地静态执行（不会使用 Self-Runner）

从仓库根目录（需要 Python3）：

    python -m pip install -r platform-portal/openlineage/spark/requirements-static.txt
    python -m unittest discover -s platform-portal/openlineage/spark/tests -p 'test_*.py' -v
    python platform-portal/openlineage/spark/render.py --run-token probe01 > /tmp/portal-a4-probe01.yaml

注意最后一行**只写本地 YAML 文件**，没有创建 Kubernetes 资源；这里**不包含** kubectl apply 或任何触发示例，避免误操作。模板中的包版本、Core/Memory 只是待 Live 验证的固定候选。

## 任务 2：真实 Smoke 已执行；后续再次运行仍须人工协调

在用户明确确认 TASK004 的共享 Spark/Airflow 修改、部署、测试**已暂停且没有未完成 Job**后，才可：
1. 用受控的只读查询检查现存 SparkApplication、Driver/Executor、Airflow DagRun/TaskInstance、最新 GitHub Actions，确认 worker02 可用，Operator watch dw-spark；确认镜像 Spark/Scala 版本、Agent Maven JAR 可达、Marquez 服务健康。
2. 根据 exact Main SHA 渲染 uniquely named ConfigMap + SparkApplication；Review 后通过受控 Self-Runner 一次性 deploy，仅启动这个独立 Application（driver 1 CPU/1Gi、executor 1 CPU/1Gi，1 executor，restartPolicy Never，不触发 Airflow）。
3. 验证 SparkApplication COMPLETED、Spark 数据读取/分组实际结果、Marquez 内新增 **真实** Spark Job 和其 Run START/COMPLETE。API GET 必须按本次 token 查 Job/Run，不能使用旧 Run 或手工 POST JSON 冒充。
4. 若需要 **真实输出 Parquet/S3 数据集血缘**，须在另一次授权的单独子阶段设计 Portal 专属 scratch bucket/prefix、限定写权限以及读取回验；**本独立只读 CSV 探针只验收真实 Job/Run + 尽力读入 dataset facet，不承诺已经生成 output Dataset**。
5. 验收后撤销本次 ConfigMap/SparkApplication；先审查 Operator/Driver 清理策略，不动 TASK004 或已有 PVC。保留真实 Run ID/Job/Marquez API 证据。

## 版本与公开依据

- OpenLineage Spark Listener per-job 配置： https://openlineage.io/docs/integrations/spark/configuration/usage/
- OpenLineage Spark Maven 坐标/安装： https://openlineage.io/docs/integrations/spark/installation/
- HTTP Transport endpoint： https://openlineage.io/docs/integrations/spark/configuration/transport/
- 现有 TASK004 成功 Spark Handoff： [2026-10-14 真实验收](../../../docs/tasks/NEW-ONLY-AIRFLOW-SPARK-FRESH-70-11487-LIVE-HANDOFF-2026-10-14.zh-CN.md)。

## 成功判断

TASK1_STATIC=PASS：Python 语法、render YAML 结构、隔离门槛、ConfigMap 完整性、Spark 资源限制经 CI 静态测试；**A4_LIVE=NOT_RUN**。不改变运行中的 Spark/DB/Marquez。
