# TASK004 — Airflow Writer 自动接线 Main 部署 + 已完成批次安全跳过真实验收

> **2026-10-14 EDT — LIVE PASS / 尚待第三个真正新批次自动 COMMIT。** [Self-Runner Run 38583147075](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38583147075) 全 Job **SUCCESS**；[Self-Runner PR #109](https://github.com/JohnZhang-DataForge/Self-Runner/pull/109) 已合并 Main。Healthcare [PR #136](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/136) 已合并 Main，真实 `dw-airflow` Scheduler GitSync 新 Writer DAG SHA 一致并完成正式 DagBag 解析。手工双开闸门模拟了第二批已 COMMITTED 的状态，实际 Airflow DAG Run 成功，并正确 SKIP 全部 Spark/Writer 任务。**本轮没有再 COMMIT PostgreSQL。**

## 正式上线到 Main 的内容

```text
new_only_omop_consumer (Airflow DAG, manual, schedule=None, paused)
    ↓
scan_ready_manifests             (real S3, immutable identity)
    ↓
select_verified_new_only_batch  (exact batch/manifest SHA/URI manual conf)
    ↓
inspect_claim_readonly          (real landing_claim_worker PG READ ONLY)
    ↓
route_new_only_status
     ├─ COMPLETED ─→ already_completed_no_replay  [LIVE PASS]
     ├─ ABSENT + no spark_processing ─→ unclaimed_batch_hold
     └─ ABSENT + spark_processing:true
          ↓
        spark_patient + spark_encounter → spark_reconcile
          ↓
        prepare_writer_handoff         (immutable XCom + digest, no Claim)
          ↓
        route_writer_authorization
          ├─ default no writer_commit ─→ writer_awaits_live_preflight
          └─ writer_commit:true (manual) ─→ execute_new_only_writer
                                        ↓
                                   writer_committed_verified
```

`execute_new_only_writer` 是真实 `KubernetesPodOperator`，基于冻结的新镜像
`ghcr.io/johnzhang-dataforge/healthcare-data-platform-new-only-omop-writer@sha256:dd0b0483ec01b05f1d072d65c9ab728b563cb063da0705564f3a03e23160fd6c`。

它的 Python runtime 真正执行：重新验证 Airflow Handoff→从 SeaweedFS S3 读取两种 Parquet→cdm_reader 真 PG 只读 Source ID/Claim/Stage/Checkpoint 检查→已 COMMITTED 时坚决 SKIP→对于 ABSENT 的新批次在独立 **部署级 Secret** 允许后才用已验证的 **Claim+Fencing(3)+Person/Visit+row reconciliation+COMPLETED+单 COMMIT**，再用新只读 PG session 复查；没有自动 retries，结果不确定只能 readback，不能无脑二次提交。

### 安全：writer_commit:true 不是无限制写入权限

1. Airflow `schedule=None`、默认 paused、`max_active_runs=1`、任务 `retries=0`；只能人工精确选择 NEW_ONLY READY Batch、Manifest SHA、Source URI。
2. 一次 DagRun 必须 `spark_processing:true` 和 `writer_commit:true` 同时存在；已完成批次在**首次真实 Claim SELECT** 之后跳过所有 Spark/Writer，连提交凭据都不会使用。
3. Writer Pod 再次验证 `TASK004_WRITER_AIRFLOW_COMMIT_SELECTION=YES`、`TASK004_WRITER_MODE=COMMIT`、`cdm_reader` 身份，以及额外、独立的 `task004-new-only-writer-commit` Kubernetes Secret 的 `enabled=YES` 和临时的 `omop_admin` credential。
4. **此时 Secret 仍不存在**，没有任何第三批 live COMMIT，本轮不曾存储管理员密码到 GitHub；两批旧业务数据保持不可修改。
5. 演示实现仍以 `omop_admin` SQL session + `SET LOCAL ROLE` 实现角色分离；其强权限必须严格限制在临时、人工监督的 Demo，不能声称已达到生产最小权限。

## 实际 live acceptance 结果

```text
AIRFLOW_NEW_ONLY_WRITER_GITSYNC_EXACT_MAIN=PASS
AIRFLOW_NEW_ONLY_WRITER_LIVE_DAGBAG=PASS
AIRFLOW_NEW_ONLY_WRITER_14_TASKS=PASS
AIRFLOW_WRITER_COMPLETED_SKIP_STATE=success
AIRFLOW_WRITER_COMPLETED_SKIP_NO_SPARK_OR_WRITER=PASS
AIRFLOW_WRITER_DAG_REPAUSED=PASS
AIRFLOW_WRITER_LIVE_PG_ZERO_CHANGE=PASS
SPARK_RERUN=NO
BUSINESS_COMMIT=NO
AUTO_CLAIM=NO
```

真实 Airflow CLI DagRun：
`task004-writer-completed-skip-38583147075`。
选定已经持久 `COMPLETED` 的第二批：
`synthea-new-only-gh-38489944582`，
Manifest SHA `be6806a520d74f5c57886f39086363003a432170c45e71828addedc39b4e1256`，**即使用户 Conf 同时包含 `spark_processing:true, writer_commit:true`**，所有 Spark Patient/Encounter/Reconcile、Handoff、Writer Branch、Writer KPO 均处于 `skipped`，不会触发任何业务重放。

在真实 PostgreSQL 独立 SELECT 中，Person **207**、Visit **21690**、Claim Ledger **2**，旧批 `synthea-new-only-gh-38497355290` 和第二批均 `COMPLETED` 各 1，前后全部不变。验收后实际 DAG 已恢复 paused。

## 当前 STATUS 和最后一项严格验收

**已完成：** 两批历史真实 COMMIT（首次 1/812，第二 70/11487）；Airflow 对真实新批次完成 Spark/Handoff；**Airflow Writer KPO 自动 COMMIT 执行器已经接到 DAG Main，容器/编排真正部署加载、完成批次 SKIP 实际 live 验收通过。**

**未完成：** 必须另外生成/选择一个**第三个真正新的、source-key 不冲突的 NEW_ONLY v2 S3 READY** 批次，受控配置临时 Writer Secret 后，以新 Airflow DagRun 一口气完成 Spark→Handoff→Writer→真实 OMOP COMMIT→独立新 Session Reconciliation，再次重复触发验证 `COMPLETED→SKIP`。只有这轮成功，TASK004 的核心端到端闭环才可正式标为 DONE，TASK005 才可以进入 READY。

如出现未知 DB COMMIT 结果、碰撞、Claim drift，不得不受控地重新执行 Writer 或手动“修补” Claim；优先独立 durable PG 查询。双 Writer 压测、复杂 lease recovery 继续 FUTURE ENHANCEMENT。
