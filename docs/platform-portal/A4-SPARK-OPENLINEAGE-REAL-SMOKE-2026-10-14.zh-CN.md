# Portal A4 — 独立 Spark → OpenLineage → Marquez Smoke 实测总结

> **2026-10-14 EDT / UTC — BASIC SMOKE VERIFIED（原 Live Workflow FAIL + 后续只读证据 PASS）**。仅为独立 Portal 测试，**没有修改、重新执行或部署 TASK004 的任何 Spark/Airflow/Writer 代码或业务数据**。注意：Spark App Job 与完成的 Run 目前在 Marquez 中没有形成理想的同名关系，Dataset 输入输出血缘还未验收。

## 1. 实际执行范围与隔离

用户批准执行独立 smoke。使用已有 `dw-spark` / worker02 `workload=platform`、Spark Operator 与 `spark:3.5.7-python3`，不改 Operator 全局参数或 TASK004 的 SparkApplication。

- SparkApplication：`dw-spark/portal-a4-a438628542127`
- ConfigMap：`dw-spark/portal-a4-a438628542127-source`
- Python/CSV：`platform-portal/openlineage/spark/probe.py`、`input.csv`，内含 **3 行虚拟非业务数据**，通过只读 ConfigMap 挂载给 Driver/Executor。
- 自用资源：Driver 1 CPU/1Gi + Executor 1 CPU/1Gi × 1，`restartPolicy: Never`，运行结束删除自己的资源。
- 本 Job 的 OpenLineage Spark Listener：`io.openlineage.spark.agent.OpenLineageSparkListener`；固定候选已在此真实运行中成功加载的 `io.openlineage:openlineage-spark_2.12:1.47.1`；HTTP 地址 `http://marquez.dw-marquez.svc.cluster.local/api/v1/lineage`，Namespace `healthcare-platform-spark-probe`。
- 运行前检查：SparkApplication 活跃数 **0**、Spark Driver/Executor 活跃数 **0**、Airflow 活跃 TaskInstance **0**、Marquez private HTTP 200，全部 PASS。既有 TASK004 Writer/Claim/OMOP 未被访问、调用或修改。**Runner 流程并不具备自动保护另一个 Session 在检查之后立刻启动任务的全局互斥能力**；以后仍需用户人工协调。

## 2. 真实证据（区分整个 Workflow 结果与通过的局部验证）

| Self-Runner | 结果 | 实际证据 |
|---|---|---|
| [Run **38628542127**](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38628542127) | **Workflow FAILURE**（只在最终 Marquez API 名称匹配门槛失败） | `A4_SHARED_ENVIRONMENT_PREFLIGHT=PASS`、`A4_PORTAL_ISOLATED_CONFIGMAP_AND_SPARKAPPLICATION_CREATED=PASS`、`A4_ACTUAL_SPARK_STATE=COMPLETED`、`A4_REAL_SPARK_THREE_ROW_COMPUTATION=PASS`；测试程序打印 `PORTAL_A4_SPARK_READONLY_AGGREGATION=PASS`。原验收错误地按含 `-` 的 Job 名称查找 `COMPLETED` Run，最终 `AssertionError: MARQUEZ_SPARK_RUN_NOT_FOUND`，故不能将本 Run 整体标成 SUCCESS。 |
| [Run **38629218047**](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38629218047) | **SUCCESS / 全只读** | Marquez 确有 Namespace `healthcare-platform-spark-probe` 和 **2 个** Job：`portal_a4_a438628542127`、`unknown`。前者将应用名连字符标准化为下划线，导致原错误查询不匹配；后者含 1 条真实 `COMPLETED` Run。 |
| [Run **38629414644**](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38629414644) | **SUCCESS / 全只读** | GET 验证规范化的应用 Job `portal_a4_a438628542127` 和完成的 Run UUID `01a13c02-6d9c-7684-913d-f64966d76110`。该 Run 开始 `2026-10-14T20:02:27.550Z`，结束 `2026-10-14T20:02:54.236Z`；时间与真实 SparkApplication 执行吻合。 |
| [Run **38629607225**](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38629607225) | **SUCCESS / 全只读** | Spark 完成 Run 的 facets：`environment-properties`、`processing_engine`、`spark_properties`，状态 `COMPLETED`；`portal-a4-a438628542127` 残留 Pod **0**；应用/ConfigMap 已删除。 |

**重要的精确边界**：`portal_a4_a438628542127` 这个应用 Job 当前 `latestRun` 为空；完整 `COMPLETED` Run 位于 `unknown` Job 中，带真实 Spark 专属 facets。两者同属这次独立探针新建的 OpenLineage Namespace，但不能把这次结果说成“App Job 下完整 Run 一一关联已经正常”。下一阶段优先解决 Job 命名关联问题。

**未完成**：Spark SQL 的 CSV Source Dataset 没有形成可确认的输入数据集版本（`inputDatasetVersions=0`），`outputDatasetVersions=0`；本次故意没有写 Parquet/S3，因此 **未验证数据集 I/O 或 Airflow→Spark 完整血缘**。绝不能用此测试 Run 冒充 TASK004 的 Person/Visit 数据已写入 OMOP。

## 3. 修复脚本，不重复 Spark

Self-Runner [PR #110](https://github.com/JohnZhang-DataForge/Self-Runner/pull/110) 已合并：保留真实 Live/只读验收 Workflow 和历史失败证据；将下一次 Live 入口改为仅 `workflow_dispatch`（**不会因 Git push 再自动启动 Spark**），读回策略改为检查规范化应用 Job，再按本轮开始时间、Spark `processing_engine`/`spark_properties` facets 和 `COMPLETED` 状态检查真实 Run。

**该更新后的 Live Workflow 本轮未重新执行**；本次真实 Run 的最终证据来自上表的三个成功只读 GET 验收。不能把修复后的静态配置冒充已运行通过。今后每次实际 Dispatch 都仍要按 [人工并行协调规则](./SESSION-COORDINATION-POLICY.zh-CN.md) 先征得用户针对该次的放行，并再次核查 Spark/Airflow 没有活跃作业。

## 4. 状态与下一阶段

- **A4 Basic Smoke：Spark 3.5.7 + Agent Listener + Marquez 收到一条真实 COMPLETED Spark Run，已证实**。不是一个整体 SUCCESS 的单 Run 验收，而是首轮 Spark 通过 + 三轮实际只读证据串联。
- **A4 Job/Run naming / Dataset facets：INCOMPLETE**。改进 Listener/App Job 的 `unknown` 命名关联、独立只读 CSV 或隔离 scratch S3/Parquet Dataset 的自动 I/O lineage，必须另设有边界的阶段。
- **TASK004 完全独立**：没有改它的 Spark/Airflow/Writer 业务代码、镜像、S3 业务路径与 OMOP。Marquez PostgreSQL14 中真实产生本次 Portal 的**观测元数据写入**，这属于 Smoke 的预期效果。
- **共享运行已释放**：Portal 的 SparkApplication、ConfigMap 和同名前缀残留 Pod 均已实际读回清空，TASK004 可继续自己的 Secret / DB COMMIT 调试。
- A5 与 TASK004 的真实数据血缘联动仍在 HOLD，必须人工协调；Writer COMMIT 的真实性以 TASK004 自身验收为准，不受 Portal smoke 影响。
