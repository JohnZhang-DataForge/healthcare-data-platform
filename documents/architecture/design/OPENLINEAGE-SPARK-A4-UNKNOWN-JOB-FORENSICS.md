---
status: reviewed
scope: platform-portal-a4-historical-openlineage-spark-job-identity-forensics
last_verified: 2026-10-25
source_sha: aa63022ce1f9716a6b91520b7cafc16ba3b42875
evidence:
  - https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38628542127
  - https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38629607225
  - https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40249499652
  - https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/432
---

# A4 历史故障法证：OpenLineage Spark 1.47.1 的 `unknown` Job 与 Dataset 观测边界

> **结论类别：已证实的历史现象 + 官方固定版本源码机制 + 尚待证明的事件级归因。不是用户批准的运行时修复，也不是正式认定 OpenLineage 上游存在某个未确认 Bug。** 所有调查仅用历史 GitHub 日志/PR、公开 1.47.1 / Spark 3.5.7 标签源码和一次内网 Marquez GET-only；没有创建 SparkApplication、重启 Airflow、改写 Marquez/PG/S3、发布镜像或补造事件。关联 [OpenSpec 4.1](../../../openspec/changes/complete-platform-portal-lineage-integration/tasks.md)，与已批准的 [RDD START-only 方案 A](OPENLINEAGE-SPARK-RDD-ACTION-LIFECYCLE-DECISION.md) **是两个独立问题**。

## 1. 旧运行的事实与直接失败点

| 条目 | 原始证据与判定 |
| --- | --- |
| 当时 Spark | `spark:3.5.7-python3`、`openlineage-spark_2.12:1.47.1`，命名空间 `healthcare-platform-spark-probe`；`SparkSession.builder.appName("portal-a4-" + run_token)`，但**未设置** `spark.openlineage.appName` |
| [原始 #38628542127](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38628542127) | `A4_ACTUAL_SPARK_STATE=COMPLETED` 与 `PORTAL_A4_SPARK_READONLY_AGGREGATION=PASS`。Driver 在停止阶段记载 `EventEmitter: Emitting lineage completed successfully with run id: 01a13c02-6d9c-7684-913d-f64966d76110`。此 Log 信息只表示 emitter 调用完成，**本身未携带事件 Job Name/JSON/eventType** |
| 旧验证器直接失败点 | 只按期望的 `portal_a4_a438628542127` Job 查询 `COMPLETED` Run，最终 `AssertionError: MARQUEZ_SPARK_RUN_NOT_FOUND`。原 Workflow **FAILURE** 原样保存 |
| [独立 Marquez #38629607225](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38629607225) | 预期 Application Job `latestRun=False`、仅有 `jobType` Facet、Job 级 0 I/O；实际 `unknown` Job `latestRun=True`，对应同一 `01a13c02-6d9c-7684-913d-f64966d76110`，Run `state=COMPLETED`，`inputDatasetVersions=0`、`outputDatasetVersions=0`、Run Facets `environment-properties` / `processing_engine` / `spark_properties` |
| [PR #432](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/432) 前后 | 旧 Probe 只 CSV read→`count()`→GroupBy→`collect()`；没有 Parquet/S3/PG 或其他持久输出，**0 Output 是源码语义的预期**。新版**同时**增加了 `spark.openlineage.appName`、PVC、Parquet Write/Readback，并取得真实 P3 正向 Job/Run/I/O；**非单变量 A/B** |
| 旧 Driver Fabric8 异常 | `spark.stop()` 阶段出现 `DELETE /namespaces/dw-spark/persistentvolumeclaims` 权限/客户端异常，**发生于上述 emitter 日志附近**；它与事件命名丢失的直接因果关系**没有证据**，不作为本次修改 RBAC 的理由 |

## 2. OpenLineage 1.47.1 固定标签：为什么可能叫 `unknown`

直接审读官方标签 [OpenLineage/OpenLineage 1.47.1](https://github.com/OpenLineage/OpenLineage/tree/1.47.1) 的 Java 源码，**不是基于未来最新版推断旧版本**：

1. [`ApplicationJobNameResolver.java`](https://github.com/OpenLineage/OpenLineage/blob/1.47.1/integration/spark/shared/src/main/java/io/openlineage/spark/api/naming/ApplicationJobNameResolver.java)：按顺序选择 `OpenLineageAppNameApplicationJobNameProvider`（显式 override）→ AWS Glue Provider → `SparkApplicationNameApplicationJobNameProvider`。
2. [`OpenLineageAppNameApplicationJobNameProvider.java`](https://github.com/OpenLineage/OpenLineage/blob/1.47.1/integration/spark/shared/src/main/java/io/openlineage/spark/api/naming/OpenLineageAppNameApplicationJobNameProvider.java)：只有 `getOverriddenAppName()!=null` 时才明确使用 `spark.openlineage.appName`。旧 A4 未设置此值。
3. [`SparkApplicationNameApplicationJobNameProvider.java`](https://github.com/OpenLineage/OpenLineage/blob/1.47.1/integration/spark/shared/src/main/java/io/openlineage/spark/api/naming/SparkApplicationNameApplicationJobNameProvider.java)：当 `OpenLineageContext.getSparkContext()` 存在且 `sparkContext.appName()` 非空时使用真实应用名称；**如果没有有效 SparkContext/name，就显式回退常量 `DEFAULT_JOB_NAME="unknown"`**。官方 [`SparkApplicationNameApplicationJobNameProviderTest.java`](https://github.com/OpenLineage/OpenLineage/blob/1.47.1/integration/spark/shared/src/test/java/io/openlineage/spark/api/naming/SparkApplicationNameApplicationJobNameProviderTest.java) 确切断言 `Optional.empty()`、`null`、空白 appName → `unknown`，正常 appName → 真实名称。
4. [`JobNameBuilder.java`](https://github.com/OpenLineage/OpenLineage/blob/1.47.1/integration/spark/shared/src/main/java/io/openlineage/spark/api/naming/JobNameBuilder.java)：Application/Action 命名都可走上述 Resolver（Action 另外追加执行节点/表名）。**“没有显式 openlineage.appName”不等于必定是 unknown**；在有有效 SparkContext 的情况下仍能使用 `spark.app.name`。
5. [`OpenLineageSparkListener.java`](https://github.com/OpenLineage/OpenLineage/blob/1.47.1/integration/spark/app/src/main/java/io/openlineage/spark/agent/OpenLineageSparkListener.java)：`onApplicationStart` 与 `onApplicationEnd` **分别**调用 `getSparkApplicationExecutionContext()`；它从默认 SparkSession 或 `SparkContext.getActive()` 取得当前 SparkContext，允许向 `ContextFactory.createSparkApplicationExecutionContext(null)` 传入空值。
6. [`ContextFactory.java`](https://github.com/OpenLineage/OpenLineage/blob/1.47.1/integration/spark/app/src/main/java/io/openlineage/spark/agent/lifecycle/ContextFactory.java) 在构造 **每个** Application Execution Context 时，使用当时提供的 `sparkContext` 生成新的 `OpenLineageContext`，然后调用 `JobNameBuilder.buildApplicationName`。因此**同一应用不同事件如果构造上下文时拿到的 SparkContext 不同，Job 名理论上可以不同**，特别是没有显式 `spark.openlineage.appName` 时。
7. [`SparkApplicationExecutionContext.java`](https://github.com/OpenLineage/OpenLineage/blob/1.47.1/integration/spark/app/src/main/java/io/openlineage/spark/agent/lifecycle/SparkApplicationExecutionContext.java) 的 Application START 和 COMPLETE 复用同一个 `applicationUuid`，但每次分别调用 Job Name Builder；其 Job Facet `jobType=APPLICATION`。这提供了一条**源码机制层面可解释**的路径：若某事件能获取 SparkContext、另一个拿不到，可在 Marquez 看到同一应用相关的预期 Job 和 `unknown` Job。
8. **关键反证约束**：[Apache Spark 3.5.7 的 `SparkContext.scala`](https://github.com/apache/spark/blob/v3.5.7/core/src/main/scala/org/apache/spark/SparkContext.scala) 在 `stop()` 中先 `postApplicationEnd()` / `listenerBus.stop()`，后 `clearActiveContext()`。因此**不能仅因为旧驱动调用 `spark.stop()` 就断言 Application END 一定取不到 SparkContext**。真正失效的上下文读取时点/具体事件类型仍未保存在历史可见日志中。

**解释等级：`unknown` 是上游源码明确支持的 fallback，可信度高；“旧 A4 某次事件为何没取得有效 SparkContext”未获得完整 Event JSON 或 DEBUG Trace，仍为待证假设。** 新版显式 `spark.openlineage.appName` 可以避开**这个具体 fallback 路径**，不等于单变量证明旧失败的全部因果。

## 3. Application 与物理 Dataset：为什么 `0 I/O` 不能一概判断丢采集

- 上游 [`SparkApplicationExecutionContext.java`](https://github.com/OpenLineage/OpenLineage/blob/1.47.1/integration/spark/app/src/main/java/io/openlineage/spark/agent/lifecycle/SparkApplicationExecutionContext.java) 在 Application START/COMPLETE 发出 Application 级 Run（`JobType=APPLICATION`），并不等于 DataFrame SQL/RDD Action 子 Job 的物理输入输出。
- [`OpenLineageRunEventBuilder.java`](https://github.com/OpenLineage/OpenLineage/blob/1.47.1/integration/spark/shared/src/main/java/io/openlineage/spark/agent/lifecycle/OpenLineageRunEventBuilder.java) 依据 Execution Context 可见的逻辑计划/RDD 节点发现 Dataset。某个**Application 级** Run 的 `inputDatasetVersions=0` 不意味着整个 Spark Application 没有任何 CSV Input；应查询相应 SQL/RDD **子 Job 和其精确 Run**。
- 原始 readback **只查询**预期 Application Job 与一个 `unknown` Run，没有完整遍历旧执行期间所有 SQL/RDD Job/Run。因此：
  - 旧 Probe **确实没有持久 Output Writer**，所以没有持久 Output Dataset 是预期的；
  - 旧查询显示 `unknown` Run 的 **0 Input/Output** 是事实，却**不能证明**所有 SQL/RDD 子 Run 均没有 CSV Input；
  - 旧 `unknown` Run 的具体 `jobType` Facet、事件原始 Job Payload 未被 2026-10-14 的短摘要完整保存，不能从 Run Facet 名称反推它必定属于 Application END。
- 此处与现有正式 P4/P5 经验一致：业务数据边在底层 Spark Action Job；Application 自身即使未显示 Dataset，也必须用完整 Namespace + Job Name + Run ID 反向审计子 Job。参见 [RDD 方案 A 决策](OPENLINEAGE-SPARK-RDD-ACTION-LIFECYCLE-DECISION.md) 和 [P6 固定 Batch UI 证据](../../../openspec/changes/complete-platform-portal-lineage-integration/evidence/PORTAL-P6-LAN-BROWSER-HOMEPAGE-20261025.md)。

## 4. 原 Marquez 在线数据重取：独立 GET 只读成功、目标均 404

2026-10-26 00:28 UTC 执行**独立** [Self-Runner #40249499652](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40249499652)（**SUCCESS**，[Artifact #12620242185](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40249499652/artifacts/12620242185)）。唯一动作：从已有 Runner 内网对原 Namespace `healthcare-platform-spark-probe` 发送 **HTTP GET**，精确查询 `portal_a4_a438628542127` Job、`unknown` Job、以及 `01a13c02-6d9c-7684-913d-f64966d76110` Run；无 `kubectl`、PG、POST 或资源创建。

三个查询均返回 **HTTP 404**。这仅能证明**当前原 API 路径不可读**；不能据此判断旧 Marquez 数据为何不见、2026-10-14 独立查询当时是否真实、是否曾有清理或 Retention 机制，亦不能重新获取旧完整 Run Event JSON。**#40249499652 的 Workflow 成功只表示有界 GET 成功执行，不代表历史记录找到了**。

## 5. 设计建议与不做什么

1. **所有新 Spark 集成明确指定稳定业务身份**：在 Spark conf 同时明确 `spark.openlineage.namespace`、`spark.openlineage.appName`；由 orchestrator 调用时还传递真实 `parentJobNamespace` / `parentJobName` / `parentRunId`，并通过 GET 校验精确值。注意命名不等于事件终态或真实 I/O。
2. **Producer 的功能要求与观察要求分开**：如果演示需要 Output Dataset，就必须进行**真实、受控、可独立读回的持久写出**；单纯读 CSV / `count` / `collect` 并不创造 Output；绝不通过 POST 假事件补图。
3. **三层门槛不可混同**：Spark/Application `COMPLETED`、OpenLineage Job/Run/DatasetVersion、PG17 Writer durable COMMIT 是不同的验证面。FHIR/HL7 Producer 后续进入 Spark/Fabric 时同样需要保留输入/输出 DatasetVersion 与 ParentRun 的契约和真实读回。
4. **避免不必要重做**：当前 P5/P6 真实 Person/Visit/Reconcile/Writer 及官方 Marquez Web 已按方案 A 验收。**不为了退休的 A4 Probe** 重新构建 8 镜像、覆盖现有 Dataset/Batch、修改 Marquez 事件、升级 Listener 或扩大 K8s PVC 删除权限。
5. **4.1 状态**：调查已把 `unknown` 具体上游 fallback 与旧 Probe 0 Output 原因定位到固定源码；但**历史确切事件类型/SparkContext 可用性和旧 0 Input 的端到端唯一原因尚未证实**。如 4.1 仍要求“唯一根因”标准，保持 **OPEN**。用户/维护者可选择不进行新 A/B，把它作为**有界历史法证未决项**独立跟踪并明确影响仅限已退休 Probe；整项 OpenSpec 是否归档必须经单独 Change Gate 审查。
6. 仅在真正需要旧版本的单变量归因时才考虑单独 A/B：固定 1.47.1 Spark JAR/3.5.7、相同 CSV 读写/Exec、Namespace、transport，只改变 `spark.openlineage.appName`。既然旧 Marquez 记录现在 404，任何新 A/B 只能证明**可重复的机制行为**，不可能倒流还原 2026-10-14 的具体事件 Payload。A/B 实验有运行资源风险，必须另行批准隔离安全 Gate，不能从本文直接执行。

## 6. 核销结论

**已证实**：旧 Spark 成功、验证器只按错位 Job 身份找 Run、原 `unknown` 已存完成 Run、旧 Probe 无持久写出、官方 1.47.1 有精确 `unknown` fallback、后续 P3 显式命名/持久写出正向成功、旧 Marquez 指定记录当前 404。

**高度可信但不是唯一确定**：生命周期事件在无显式 `openlineage.appName` 时的 SparkContext/name 可用性差异导致 `unknown` 和预期 Application Job 分裂。

**仍缺的历史证据**：原 `unknown` Job 的完整 `jobType` / Raw Run Event JSON，准确失名事件时点/原因，旧 CSV Input Dataset 是否存在于其它 SQL/RDD 子 Job，原历史 Job 无法在线读取的具体清理原因。

因此：**证据已足够防止当前与未来重复踩坑；尚不足以诚实地把唯一根因 OpenSpec 4.1 勾成完成，也不自动授权 7.3 Archive。**
