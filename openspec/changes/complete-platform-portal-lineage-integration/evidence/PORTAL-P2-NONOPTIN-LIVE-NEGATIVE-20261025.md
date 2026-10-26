# P2 3.3 — 非 opt-in Airflow Smoke DAG 真实负向事件验收（2026-10-25）

> **范围：** 选择已存在、只调用 `BashOperator` 打印消息的 `airflow_smoke_test.check_airflow`，**不运行** `landing_batch_discovery`（S3/PG）或任何 `new_only_omop_consumer` 业务 Task/Writer。原始测试 Workflows 是 **Self-Runner 临时分支**的单次 Push 入口，不能未经审查合并为 Main 的常驻自动执行器。

## 版本与证据

- Healthcare 源固定 `7f4c21c76c6484f4d2ec5694e84aefe03ab9ea6a`（含 [PR #498](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/498) 已通过 CI 的**所有 Airflow DAG 源码 AST 全目录选择性 opt-in 负向合同**）。
- Self-Runner 运行开始时 Main `4396ef902267eabfc946fe6a428e4a6f24e0faae`；一次性测试分支 `test/portal-p2-nonoptin-airflow-negative-20261025`，`portal-p2-nonoptin-negative-once.yml` 原始提交 `2d15f24aa9782a69189c3c64885437506a907453`。
- [原现场 Preflight + 一次 DagRun #40247000949](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40247000949)：安全静态测试、受控 kubeconfig、活动 Spark/Airflow、Scheduler+dag-processor GitSync smoke DAG SHA、实际 Scheduler SELECTIVE/非 opted-in DagBag 全部通过前置步骤，随后仅操作 `airflow_smoke_test`。
- [独立只读 GET/DB Run #40247126516](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40247126516) **SUCCESS**；[原始 Artifact #12619320666](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40247126516/artifacts/12619320666)，由**另一个** GitHub Runner Job 通过 in-cluster ServiceAccount 只读对照，不触发 DAG、不修改暂停、不向 Marquez POST 事件。

## 真实业务以外的最小 DAG 运行

- 固定测试 DAG：`airflow_smoke_test`，固定唯一 Task：`check_airflow`，BashOperator 仅打印 hostname/date/文字。源码 `local-data-platform/airflow/dags/airflow_smoke_test.py` 本身未新增、修改或重新发布。
- 实际新 DagRun ID：`portal-p2-nonoptin-gh-40247000949`。
- 独立 Run #40247126516 确认 Airflow `DagRun.state=success`；原 TaskInstance `{'check_airflow': 'success'}`。原有 `landing_batch_discovery`、Legacy DAG 和 NEW_ONLY Consumer 均未被本次触发。
- Marquez 只读验证时段开始：`2026-10-25T23:56:51Z`（测试 Workflow 创建时点，**早于**真实触发）；GET `healthcare-platform-airflow` namespace 的实际 Job 清单，无 `airflow_smoke_test`、`airflow_smoke_test.check_airflow` 或新 `unknown` 相关 Job/Run。独立 Reader 的 `P2_NONOPTED_EXISTING_JOB_NAMES=[]`、`P2_NO_NEW_NONOPTIN_OR_UNKNOWN_MARQUEZ_EVENTS=PASS` 均通过。
- 这是一项真实 **LIVE NEGATIVE**：**同一个非 opt-in DAG 真正执行成功，但实际 Marquez 未收到其身份下的 Task Event**。它与 P2 已通过的 **NEW_ONLY 正向** [#40126168286](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40126168286)（真实 10 个 opt-in DAG/Task Job + Run）以及 Main AST 所有 DAG 的负向合同形成正反证据。

## 清理/归档前必要 Gate

- **原 #40247000949 完整 Run 终态及 Original Paused 状态恢复：待独立最终读回确认**。该 Run 的结果轮询表达式可能存在格式问题，不能用原 Job 的 Pipeline 结论替代上方独立核验，也不因此二次触发 Smoke。待确认 Always Restore/Artifact 后把实际结果补在这里。
- 非 opt-in DAG 的 Live Negative 仅实际触发了这一个**无业务** Smoke；其他真正的 S3/PG DAG 只进行了已合并源码 AST 负向覆盖，**没有运行它们**。因此不能声称“所有 DAG 均经过 Live 负向执行”。
- 此测试没有业务 Batch/Manifest、Synthea、SparkApplication 或 Writer COMMIT；不推断 PG17 计数变化，也不修改既有 RDD START-only 的设计 A 限制。
- PR/Status 完成前，应核对原 DAG pause 的恢复是否确实发生且不影响现有其他 Session；任何不确定事项保持 OPEN，不凭文档将其抹除。
