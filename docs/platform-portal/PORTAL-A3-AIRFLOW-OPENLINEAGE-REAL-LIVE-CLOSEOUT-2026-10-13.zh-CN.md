# Platform Portal A3 — Airflow OpenLineage → Marquez 真实闭环验收

**日期**：2026-10-13 EDT / 2026-10-14 UTC  
**阶段**：路线 A / A3；**最终状态**：**REAL LIVE PASS**（独立 Portal DAG/Task/Run，不含 TASK004 业务数据血缘）。  
**当前 NEXT**：A4 隔离 Spark Operator/OpenLineage Agent 验证；随后按 TASK004 真实成功证据逐步整合，不需要提前开放 Writer/Claim。

## 1. 固定运行架构

- Airflow **3.2.2**（`dw-airflow`）；Provider **`apache-airflow-providers-openlineage=2.17.0`**，OpenLineage Python **1.47.1** 已安装；无需重建 Airflow 镜像。
- Marquez **0.51.1**（`dw-marquez`），API `marquez.dw-marquez.svc.cluster.local` / **ClusterIP**；PostgreSQL14 `dw-postgre14` 独立元数据数据库，未新建或操作 OMOP PostgreSQL17。
- Airflow Scheduler 使用配置 `AIRFLOW__OPENLINEAGE__TRANSPORT={"type":"http","url":"http://marquez.dw-marquez.svc.cluster.local","endpoint":"api/v1/lineage"}`、`NAMESPACE=healthcare-platform-airflow`、`SELECTIVE_ENABLE=True`、`DISABLE_SOURCE_CODE=True`。实际更新 Shared Scheduler 前确认 Airflow 活跃/排队 TaskInstance **0**；只改变 `dw-airflow-scheduler` 部署的环境变量并做一次受控滚动，不修改 TASK004 DAG/OMOP/Writer。
- 唯一 opt-in DAG：`airflow/dags/platform_portal_openlineage_probe.py`，`schedule=None`、两个无业务数据的 PythonOperator：`observe_runtime` 和 `confirm_runtime`；原生 Provider 根据 `enable_lineage()` 自动产生事件。**没有手写/POST 伪装的 OpenLineage JSON**，也不证明真实的 Synthea → OMOP 数据集边。

## 2. 真实证据与 Run 的区分

| GitHub Self-Runner | 实际动作 | 验收 |
|---|---|---|
| [38501427974](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38501427974) | 只读 Airflow 组件 / Provider / private API preflight | **SUCCESS**；HTTP 200，`SELECTIVE_ENABLE` helper 已安装，原来 transport 未配置 |
| [38501866970](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38501866970) | 固定源码静态与真实 Airflow runtime import | **SUCCESS**；opt-in DAG 导入/语法 Gate PASS，无业务任务触发 |
| [38502006416](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38502006416) | 首次 Shared Scheduler 配置 | **Workflow FAILED**：`kubectl set env` 已使旧 Pod 退出，脚本随后错误选择正在终止的旧 Pod；Main PR #111 已修复 Pod 选择。不能把这一轮当成通过 |
| [38502637283](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38502637283) | 原 DAGRun 排队的只读诊断 | **SUCCESS / READONLY**；DAG 文件存在、Transport 正确但 DAGRun queued；TaskInstance 尚未执行 |
| [38502759492](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38502759492) | 仅解暂停 `platform_portal_openlineage_probe` | **SUCCESS**；`A3_PORTAL_DAG_INITIAL_STATUS=PAUSED`，`A3_PORTAL_DAG_UNPAUSED=PASS`；TASK004 DAG 不改 |
| [38502227961](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38502227961) | 真实 A3 全链路 DAGRun，运行时经历 opt-in DAG unpause | **SUCCESS**；真实 Airflow Run `portal-ol-38502227961` 完成，两个 TaskInstance `success`，Marquez Job 列表出现 DAG 和两个 Task |
| [38502283003](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38502283003) | **无 Scheduler 重启**的第二次独立验证 | **SUCCESS**；`A3_SHARED_SCHEDULER_ROLLOUT_THIS_RUN=NO`，真实 Run `portal-ol-38502283003`，两个 Task `success`，Marquez Job 读回 PASS |
| [38502899963](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38502899963) | Marquez Task Job `/runs` API 只读回读 | **SUCCESS**；两种 Task 各 1 个 `COMPLETED` Run（在第二次 DAGRun 完成之前的时间点） |
| [38502940358](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38502940358) | 最终 Marquez Job/Run 只读回读 | **SUCCESS**；两种 Task 各 **2 条** `COMPLETED` Run，`startedAt`/ `endedAt` 存在；`A3_BOTH_TASKS_ACTUAL_MARQUEZ_RUN_STATES=PASS` |

**确证的命名空间和 Job：**

- OpenLineage Namespace：`healthcare-platform-airflow`。
- Marquez DAG Job：`platform_portal_openlineage_probe`。
- Marquez Task Job：`platform_portal_openlineage_probe.observe_runtime`、`platform_portal_openlineage_probe.confirm_runtime`。
- 两次真实 Airflow Run：`portal-ol-38502227961` / `portal-ol-38502283003`；两个任务分别 success。
- 最终 [Run 38502940358](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38502940358) 读回：两个 Marquez Task Job 各 **2 条 COMPLETED Run**。记录属于真实 Provider 事件，而非人工伪造生产数据。

## 3. 代码、边界与遗留工作

本轮代码已在 Healthcare Main（PR #110 添加 opt-in DAG 和受控配置脚本，PR #111 修复滚动 Pod 选择），路径：

- `airflow/dags/platform_portal_openlineage_probe.py`
- `platform-portal/openlineage/airflow/configure-scheduler.sh`
- `platform-portal/openlineage/airflow/verify-real-events.sh`
- `platform-portal/openlineage/airflow/README.md`

**当前只完成 Airflow 的真实运行血缘**。不能误报为 Spark/S3/Parquet/OMOP Writer 已接入，不能把前期 Writer Drift Gate / ROLLBACK 解释为 COMMIT。TASK004 继续其独立数据工程开发；TASK005 不启动。

**运维注意**：本轮通过 `kubectl set env` 对现有 Airflow Scheduler Deployment 做临时受控配置，并通过实际 Pod 配置读回 PASS。未来如果重新执行 Airflow Helm upgrade，可能由 Helm Values 覆盖这些环境变量，需按既有 Helm release 的准确 Values 将 `openlineage` transport/selective 设置**持久化纳入受控 Helm 配置**，再验证 restart/readback。直到该 Helm 配置持久化闭环完成，不将“配置永不漂移”标记为 PASS。

**安全边界**：A3 没有修改 PostgreSQL17/OMOP、S3 Manifest、TASK004 DAG、Spark App 或 Writer，也没有暴露 Marquez API 到公网。原生 Marquez Web 的 `30999` 仍是受控 LAN/VPN 入口，尚无路由器 NAT/防火墙和个人浏览器外部可访问性验收。

**NEXT A4**：独立 Spark Agent + 短时 SparkApplication 的真实输入/输出血缘（使用清晰标识的隔离测试数据集），只有 Task 和 Spark 真实运行完成后才关联；不得通过创建伪造 Synthea→OMOP 成功边来“补齐” Portal 图。
