# TASK004 — Airflow NEW_ONLY Consumer 第一阶段：已入库批次安全跳过，真实 DAG Run 证据及后续交接

> **2026-10-14 EDT。** 新 `new_only_omop_consumer` 已在 Healthcare `main` [PR #126](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/126) 合并，GitSync 真实 Scheduler SHA 完全一致，真实 DagBag 已解析。最终 Self-Runner [Run 38559222216](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38559222216) 中新 DAG 实际 DagRun `state=success`，已完成批次分支的 TaskInstance 状态校验通过、真实 PG 前后完全不变；**但整个 Self-Runner job 的 conclusion 是 failure**，因为验收脚本错误地要求 BranchPythonOperator 的 XCom return_value 等于分支名，而实际读到 None。严格区分「真实 Airflow DagRun success」和「Self-Runner 全部附加断言 PASS」：后者**尚未完成**。按照最多三轮修复的要求，本 Session 停止重试；下一 Session 优先修复验收脚本，不重写业务 DAG、不重跑 Spark。

## 1. 本轮已经实装的代码（Healthcare Main）

- `airflow/dags/new_only_omop_consumer.py`：新的 **schedule=None、paused upon creation、max_active_runs=1** 独立手工入口，不变更现有 `landing_batch_discovery` 的历史语义。
- `airflow/dags/new_only_omop_routing.py`：纯函数对真实 S3 Discovery READY Manifest XCom、明确的 `dag_run.conf` Batch+SHA+URI、v2 NEW_ONLY、18 files、无截断、只读身份进行精确检查。
- 新 DAG 任务链：`scan_ready_manifests → select_verified_new_only_batch → inspect_claim_readonly → route_new_only_status → already_completed_no_replay | unclaimed_batch_hold`。
- `inspect_claim_readonly` KPO 在 worker02 使用固定原 CDM runtime 镜像和专用 `landing_claim_worker` 登录，仅在 PostgreSQL `READ ONLY` transaction SELECT Claim/Writer Ledger 身份、状态，不授予 CDM 写入。
- 对已经 `COMPLETED` 的真实 `synthea-new-only-gh-38497355290` 返回 `already_completed_no_replay`；完全没有调用 Spark、Writer 或 PostgreSQL Claim INSERT。若选择未 Claim 的新 Batch，仅到 `unclaimed_batch_hold`，**尚未连接实际新 Batch 的 Claim→Spark→Writer**。
- `tests/landing_discovery/test_new_only_omop_airflow_consumer.py` 包括 COMPLETED、ABSENT、Manifest drift、角色只读、手工配置、运行模式等 fail-closed case。
- 首轮 SHA 固定 Self-Runner [38557168598](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38557168598) **SUCCESS**：Landing Discovery 46 tests、历史 STEP04F handoff 6 tests，共 52 tests；DAG Python compile PASS。

## 2. 真实 Kubernetes + Airflow 调度验证

Runner 使用 Healthcare 合并 Main SHA `956ccbc2f73f2b2dfda335511db8df5ff6d4ca29`，真实 `dw-airflow` Scheduler 文件字节 SHA 精确一致。

最终 [Run 38559222216](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38559222216) 的可证实日志：

```text
NEW_ONLY_AIRFLOW_REAL_PG_BASELINE=PASS
AIRFLOW_NEW_ONLY_GITSYNC_EXACT_MAIN=PASS
AIRFLOW_NEW_ONLY_REAL_DAGBAG=PASS
AIRFLOW_NEW_ONLY_NO_SPARK_OR_CLAIM=PASS
AIRFLOW_NEW_ONLY_TEMPORARY_MANUAL_UNPAUSE=PASS
AIRFLOW_NEW_ONLY_REAL_DAGRUN_SUBMITTED=PASS
AIRFLOW_NEW_ONLY_REAL_DAGRUN_STATE=success
# 后续验收脚本：AssertionError: None （分支任务 XCom return_value）
AIRFLOW_NEW_ONLY_REAL_PG_NO_MUTATION=PASS
AIRFLOW_AUTO_CLAIM=NO
SPARK_RERUN=NO
BUSINESS_COMMIT=NO
S3_READY_MUTATION=NO
```

- DAG 起初 `is_paused_upon_creation=True`，直接 CLI trigger 会进入 `queued`，因此最终 Run 在仅人工执行的 `schedule=None` DAG 上临时 `airflow dags unpause`，并在脚本 `trap EXIT` 恢复 `pause`。**这不是打开自动 Claim；该 DAG 本身没有 Claim/Writer 实际执行器，也没有 schedule。**
- 最终 DagRun 达到 **success**。后续独立 Airflow TaskInstance 校验依次检查五个主路径任务 `state=success` 与 `unclaimed_batch_hold=skipped`，随后才在 `assert branch==... ` 遇到 `AssertionError: None`；说明 **TaskInstance 状态断言未触发错误**，但 BranchPythonOperator 的 XCom return_value 不应被当成可靠的分支结果。下一轮应检查 task instance states 与 DB immutable status，而不是将 BranchOperator 的 XCom 当必备值；这样不会重新执行已完成批次的 Writer。
- 正式 PostgreSQL Person **137**、Visit **10203**、Person Map **137**、Visit Map **10203**、Claim **1**（NEW_ONLY 目标 COMPLETED **1**）、Stage **813**、VERIFIED checkpoints **2**。这八项与测试开始前一致，实际 `diff -u` PASS。业务 Source Batch 无重复插入。

## 3. 连续三轮修复与停止条件

1. [Run 38557391802](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38557391802) — Runner `kubectl` 安装后仅写 GITHUB_PATH 而未加到**本步** PATH；在 PG preflight 之前失败，无业务操作。修复。
2. [Run 38557452287](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38557452287) — 正确 GitSync/真实 DagBag，但 Runner 内的 pinned Discovery image suffix 写错；业务 DAG image 正确。修复。
3. [Run 38557565322](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38557565322) — 真实 DagBag PASS、CLI DagRun created，但默认 paused 导致 state=queued；全程 PG 无变更。随后将最终一次**受控手工临时 unpause + EXIT 恢复 pause**写入 Runner workflow。
4. [Run 38559222216](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38559222216) — 临时 unpause 后实际 Airflow DagRun 成功、TaskInstance 分支状态断言通过、PG before/after 完全一致。**Job 最终失败仅由 BranchPythonOperator 缺少预期的 XCom return_value**；不应把这个失败等同于数据库业务失败。**本轮到此停止，不继续无限修复测试。**

说明：这里的第三次修复针对暂停态，Run 38559222216 是修复后的真实试验；虽然功能达成主要目标，验收脚本未全绿，因此按用户规则 STOP 并记录。

## 4. 下一轮最小收尾和主线

1. **只调整 Self-Runner 分支** `feature/task004-airflow-new-only-router-20261014` 下 `.github/workflows/task004-airflow-new-only-consumer-route.yml`：不再强制 `branch = ti.xcom_pull('route_new_only_status')` 等于分支名；信任 Airflow TaskInstance 已确认的 `already_completed_no_replay=success`、`unclaimed_batch_hold=skipped`，并可检验 `claim_status=COMPLETED`；避免改动完成批次业务 DAG 或 S3/PG。
2. 做一次 Runner 真实 `Airflow DagRun` 绿灯验收并合并 Self-Runner PR（本轮 Runner 分支因最终 run 失败尚未合并 Main）。另需确认最后 `pause` 恢复确实完成；不能当作 schedule 开启。
3. **然后**扩展同一 NEW_ONLY DAG 的 `unclaimed_batch_hold` 为**受控单批 Claim + Spark + Writer 接口**。但在 Portal/TASK004 Spark 冲突人工协调完成、明确指向**新 S3 READY**、Writer 用最小权限登录并具备多事务 Ticket 交接策略之前，不直接启用 Claim，不重跑已完成 Batch。
4. 双 Writer 并发/复杂 lease auto recovery 仍是 FUTURE ENHANCEMENT，不作为 Demo TASK004 blocker。TASK004 IN PROGRESS，TASK005 ON HOLD，Portal A4 HOLD。

**注意**：本阶段主要完成 Airflow 入口、真实完工批次安全跳过的部署/运行；没有新批次自动 Claim、Spark 或 Writer COMMIT。既有 Person137/Visit10203 坚持不变。
