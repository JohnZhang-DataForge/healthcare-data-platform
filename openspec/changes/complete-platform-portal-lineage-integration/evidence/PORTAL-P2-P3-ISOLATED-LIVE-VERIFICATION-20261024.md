# Portal P2/P3 — 2026-10-24 当前真实 Airflow 与 Spark 隔离血缘验收

> **已验证**：Airflow Scheduler 配置 + GitSync SHA256、两任务真实 A3 Probe Event、P3 隔离 Spark 真 Parquet I/O 与 Marquez 实际 Job/Run + 1 Input / 1 Output DatasetVersion。**未验证**：真实 `new_only_omop_consumer` 业务 DagRun 的 Task lineage、Person/Visit/Reconcile 实际 S3 Parquet、跨 Airflow→Spark parent 关系、Writer COMMIT / PG17 readback；不得宣称 P4/P5 E2E PASS。

## 1. 不变输入及执行方式

- Healthcare 只读/业务 DAG 源码校验使用精确 Main `bcb18bc93e0372e4e78aa373c83768a143ab4b0d`；此前 P2 Airflow 代码由 [PR #416](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/416) Main `7c192414fcdca99278421c003d1d135dac6a3968` 引入，P3 隔离 Parquet 源由 [PR #432](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/432) Main `e297709dc8e8964e1dec90f2874087616a1cc371` 引入。
- Self-Runner 正式手动测试入口为 [P2 runtime readonly](https://github.com/JohnZhang-DataForge/Self-Runner/actions/workflows/portal-p2-airflow-runtime-readonly.yml) 与 [P3 Spark Live](https://github.com/JohnZhang-DataForge/Self-Runner/actions/workflows/portal-a4-live-smoke.yml)。当前 GitHub 连接无直接 workflow_dispatch 写动作，故用户明确批准后，使用**仅在独立特定测试分支 push 本次文件时触发**的一次性受限 Workflow 执行；没有更改 Main 工作流为自动运行，没有触发正式业务 Writer 或 GHCR `:latest`。
- Runner 使用已有 ServiceAccount 的临时 kubeconfig **tokenFile**，不复制凭证；所有测试先核对共享运行环境。这里记录分支触发是真实操作，不将 PR CI PASS 冒充 Live。
- 当时 P2 只读环境中 Kubernetes `dw-airflow` 的 Scheduler、DAG Processor、API Server、Triggerer 为 Ready；未观察到常驻 `worker` 容器。数据可重生成，但仍保留其他 Session 资源边界。

## 2. P2 — 生效配置与源码读回

| 实际 Run / 来源 | 结果及确切边界 |
| --- | --- |
| [#40120573116](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40120573116) | **FAILURE（检查器要求 API Server 也启用 selective）**。实际上 API Server 报 `BLOCKED:SELECTIVE_DISABLED`；不能由此推断 Scheduler 失败。 |
| [#40120678131](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40120678131) | **SUCCESS／全角色实际 inventory**：Airflow `3.2.2`、Provider `2.17.0`；Scheduler 的 `SELECTIVE=True`、`DISABLE_SOURCE_CODE=True`、Namespace `healthcare-platform-airflow`、Marquez private HTTP transport 均 PASS；DAG Processor、API Server、Triggerer 未配置上述选项。 |
| 源码/GitSync | Scheduler 与 DAG Processor 上的 `new_only_omop_consumer.py` SHA256 均为 `b455c115f6b5468c698a2e9ce2c13cf37412e368742dcd654ee8a81eb8621144`，与本次 Healthcare 源码一致；Scheduler 当时 Airflow 活跃 TaskInstance `0`；Marquez Private HTTP GET PASS。API Server 中无可定位的该源码，不等于 GitSync 无效。 |
| [Self-Runner PR #249](https://github.com/JohnZhang-DataForge/Self-Runner/pull/249) | 持久修复手动 P2 runtime preflight：Scheduler 必须通过，但其他非必需执行角色仅据实报告，`verify-source` 核验可见源码。Main `9397c317dcd56d4b781465055d32bd012ac569c8`，PR 静态 CI PASS。 |

**结论：** 当前共享 Scheduler 可采集到选择性血缘、P2 业务 DAG 已由 GitSync 装载；Task 的具体执行进程采集设置仍需以真实 NEW_ONLY Run 观察，不能把 API/Triggerer 未配置自动当成缺陷，也不应把 Scheduler PASS 当全部 Worker PASS。

## 3. P2 — 真实 Airflow Provider → Marquez 最小新事件

- [Self-Runner Run **#40121352170**](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40121352170)，job `120953366872`：**Workflow SUCCESS，且真实 DAG/Task PASS**。
- 固定 DAG `platform_portal_openlineage_probe`（`schedule=None`，仅 `observe_runtime`、`confirm_runtime` 两项无业务 PythonOperator），手工触发 Run ID `portal-ol-40121352170`。
- `A3_GITSYNC_EXACT_SOURCE=PASS`、`A3_DAGBAG_OPT_IN_ONLY=PASS`、`A3_REAL_DAGRUN_SUCCESS=PASS`、`A3_REAL_TWO_TASK_INSTANCES=SUCCESS`。
- 真正 Marquez API 读回 Namespace `healthcare-platform-airflow` 下至少三个 Job：`platform_portal_openlineage_probe`、`platform_portal_openlineage_probe.observe_runtime`、`platform_portal_openlineage_probe.confirm_runtime`，`A3_MARQUEZ_RECEIVED_AIRFLOW_PROVIDER_EVENTS=PASS`。
- 执行前 `P2_SPARK_BUSY=[]`、`P2_AIRFLOW_ACTIVE_TASKS=0`；未触发 NEW_ONLY、Spark 或 Writer，没有业务 S3/PG17 写入。**此测试验证 A3 Provider 真实事件，不等于 NEW_ONLY 的 14 Task 血缘都验证通过。**

## 4. P3 — 真正 Spark input/output Dataset 与 Job/Run 关联

- [Self-Runner Run **#40120840326**](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40120840326)：**Workflow static 和 live 都 SUCCESS**；Live job `120951859316`。
- 独立 SparkApplication 使用 3 行 synthetic ConfigMap CSV、每次唯一 1Gi `local-path` RWO PVC，Spark 实际写出聚合 Parquet 并再次读回。实际日志 `A4_ACTUAL_SPARK_STATE=COMPLETED`、`PORTAL_A4_SPARK_READONLY_AGGREGATION=PASS`、`PORTAL_P3_SPARK_PARQUET_PVC_READBACK=PASS`。
- 真正 Marquez namespace `healthcare-platform-spark-probe` 查询得到**非 unknown** 的 Job `portal_a4_a440120840326.adaptive_spark_plan.a440120840326_summary_parquet`，真实完成 Run `01a16f2d-0a34-7d81-b0f4-b07ffc3d6261`。
- Marquez 真实 API 返回：`P3_INPUT_DATASET_VERSIONS=1` 与 `P3_OUTPUT_DATASET_VERSIONS=1`；`P3_REAL_SPARK_DATASET_LINEAGE=PASS`。证明**隔离 Spark 的真实输入与输出 I/O Dataset 边有效**，未证明 OMOP 真实 S3 路径或 Airflow parent facet 关联。
- 本次 `P3_SUCCESSFUL_TEST_PVC_CLEANUP_ATTEMPTED=YES`，代表执行了只针对本次 token 的 PVC 清理命令，但**本轮未作独立 PVC=NotFound 读回**；不扩大为持久卷独立清空证明。
- 旧 [A4 失败 Run #38628542127](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38628542127) 的 `unknown` Job 和 0 Output 仍是历史事实。新 Probe 同时加入了实际 Parquet 写出和 `spark.openlineage.appName`；正向 Live 已解决**新案例**的名称与 Dataset 关联，但未做对照试验确认旧 `unknown` 的单独根因，也不覆盖原 FAILURE。

## 5. 当前 Go / Hold 与下一阶段

**GO：** P3 单独 Spark Listener + Marquez Job/Run + Dataset 双向边具备 Live 正向证据；P2 Scheduler Provider + A3 Probe 真实事件及 GitSync source 具备 Live 证据。可以按 P4 计划实施 Person/Visit/Reconcile 真实 SparkApplication 模板最小 Listener 接入；只在 Docker 包确实变化时按已定义的手工 `publish-latest` 更新受影响镜像。

**HOLD：** P2 `new_only_omop_consumer` 的真实业务 DagRun OpenLineage Job/Run；P4 三个业务 Spark Job 的正确 S3 Dataset 边、Airflow↔Spark parent 关系及 Writer 状态；P5 新 Batch 原子 COMMIT、PG17 独立 Readback、同批 SKIP/PG 零变化。不能人工 POST 伪造 lineage。

本 evidence 是 2026-10-24 **事件层**验收；未重新单独执行 PG14 metadata exact COUNT 或 Data Platform PG17 业务数据写入读回，不将 Marquez API Job/Run 读回扩展为 PG14 表级独立证据。
