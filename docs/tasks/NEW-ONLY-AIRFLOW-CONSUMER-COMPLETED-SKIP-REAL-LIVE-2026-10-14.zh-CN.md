# TASK004 — NEW_ONLY Airflow Consumer：真实已完成批次安全跳过 LIVE PASS

> **2026-10-14 EDT — 本轮正式 CLOSEOUT。** [Self-Runner Run 38560309400](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38560309400) **全 Job SUCCESS**；Self-Runner [PR #102](https://github.com/JohnZhang-DataForge/Self-Runner/pull/102) 已合并 `main`（SHA `459ea965aa89a4aea8948ef07854080fcd81fd3f`）。Healthcare 新 Airflow DAG/纯路由代码来自 [PR #126](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/126)，早已合并 `main`。已在真实运行中确认：完成的 NEW_ONLY v2 Batch 被安全跳过，**没有重跑 Spark、不会第二次 Writer COMMIT、不重复 Claim**。TASK004 尚未完整自动入库，保持 IN PROGRESS / TASK005 ON HOLD。

## 最终真实证据

- GitHub Self-Hosted Runner 固定 Healthcare `main` SHA `956ccbc2f73f2b2dfda335511db8df5ff6d4ca29`；46 个 Landing 回归 + 6 个 TASK004 handoff 回归 **52/52 PASS**。
- Kubernetes `dw-airflow` Scheduler 的 GitSync `new_only_omop_consumer.py` + `new_only_omop_routing.py` **字节 SHA 与 GitHub main 一致**；实际 Airflow 3 DagBag 加载、完整 Task 图与 `schedule=None` / `paused upon creation` 校验成功。
- 新 DAG 默认 paused；Self-Runner 在严格受控手工测试中**临时 unpause**，CLI 提交 exact identity `synthea-new-only-gh-38497355290` / Manifest SHA `dfb5d30e83c6a9b35b3a723137a5f3ab67649ad94ef1801e2bae3ef42fe5fa80`，**真实 DagRun state=success**。
- 真实 TaskInstance 和 XCom 验收：`scan_ready_manifests` / `select_verified_new_only_batch` / `inspect_claim_readonly` / `route_new_only_status` / `already_completed_no_replay` 全部 `success`，`unclaimed_batch_hold=skipped`；PG `landing_claim_worker` 以只读事务报告真实 Claim `COMPLETED`，已完成 Batch 正确走安全跳过分支。
- Self-Runner 的 BranchPythonOperator XCom 断言问题已经在 PR #102 修复。不可假设 BranchOperator 必然持久化 `return_value`；实际选定的下游 **TaskInstance 状态** 是验收标准。
- 实测结束时独立查询 Airflow metadata：`TASK004_NEW_ONLY_DAG_REPAUSED=PASS`，DAG 已恢复暂停；**仍无定时触发，也未启用自动 Claim**。

```text
TASK004_NEW_ONLY_AIRFLOW_ROUTING_REGRESSIONS=PASS
NEW_ONLY_AIRFLOW_REAL_PG_BASELINE=PASS
AIRFLOW_NEW_ONLY_GITSYNC_EXACT_MAIN=PASS
AIRFLOW_NEW_ONLY_REAL_DAGBAG=PASS
AIRFLOW_NEW_ONLY_NO_SPARK_OR_CLAIM=PASS
AIRFLOW_NEW_ONLY_TEMPORARY_MANUAL_UNPAUSE=PASS
AIRFLOW_NEW_ONLY_REAL_DAGRUN_SUBMITTED=PASS
AIRFLOW_NEW_ONLY_REAL_DAGRUN_STATE=success
AIRFLOW_REAL_S3_COMPLETED_SKIP_ROUTED=PASS
AIRFLOW_REAL_NEW_ONLY_CLAIM_READONLY=PASS
AIRFLOW_REAL_UNCLAIMED_PATH_NOT_TRIGGERED=PASS
AIRFLOW_NEW_ONLY_REAL_PG_NO_MUTATION=PASS
TASK004_NEW_ONLY_DAG_REPAUSED=PASS
SPARK_RERUN=NO
AIRFLOW_AUTO_CLAIM=NO
BUSINESS_COMMIT=NO
S3_READY_MUTATION=NO
```

### PostgreSQL 独立持久化前后检查

| 实体 | Before | After |
|---|---:|---:|
| `cdm.person` | 137 | 137 |
| `cdm.visit_occurrence` | 10203 | 10203 |
| `etl.person_id_map` | 137 | 137 |
| `etl.visit_occurrence_id_map` | 10203 | 10203 |
| `etl.landing_batch_ledger` | 1 | 1 |
| 目标批次 Claim `COMPLETED` | 1 | 1 |
| 目标 Batch Stage | 813 | 813 |
| 目标 2 个 VERIFIED checkpoints | 2 | 2 |

实际两次独立 PG `READ ONLY` Session 输出 `diff -u` 一致，未产生新 business mutation。

## 技术边界与下一步（主线优先）

1. **已完成并验收：** 独立 NEW_ONLY Airflow 手工入站、真实 S3 Discovery/完整 Manifest XCom、最小权限 Claim 状态查询、`COMPLETED` 安全跳过。历史 Airflow `landing_batch_discovery` 和已有 Spark、Writer 均未被更改。
2. **尚未实现：** `unclaimed_batch_hold` 仍是空 `EmptyOperator`；未实际 Claim 新的 READY Batch；也没有从新 DAG 编排 Spark + Person/Visit PostgreSQL Writer COMMIT。因此**本轮不能宣称完整 Airflow 自动入库完成**。
3. **下一轮开发原则：** 先定义受控单批 `Claim ticket` 与 Writer 完成状态的传递合同，保留 manifest SHA/URI + Owner 48hex + Attempt + Lease fencing，确保不能先 Claim 而无可用 Writer；接入需要使用真正全新、源键不冲突的 v2 READY Batch。**禁止拿已完成 `synthea-new-only-gh-38497355290` 重做 COMMIT**。
4. **跨 Session 冲突人工协调：** Portal A4 仍 HOLD。任何 SparkApplication、Spark live processing、Airflow DAG 共用部署变更前，必须提醒检查其他 Session 是否正在修改 Spark/Airflow，防止共用 Runner/集群资源冲突。非 Spark 的纯 Python/合同/文档工作可以并行准备。
5. 双 Writer 并发压测、复杂 lease recovery / unknown COMMIT Recovery 为 `FUTURE ENHANCEMENT`，不阻断 Demo 主线，但正常单 Writer 原子 COMMIT/Source ID 防撞/同 Batch 重复跳过必须可靠。

**旧文档** [上一轮验收失败交接](NEW-ONLY-AIRFLOW-CONSUMER-REAL-COMPLETED-SKIP-HANDOFF-2026-10-14.zh-CN.md) 的 `Runner PR #102 draft/未合并` 和 `Branch XCom 断言尚未修复` **现在都已过时**，仅供历史追溯。本 Closeout 为当前版本。
