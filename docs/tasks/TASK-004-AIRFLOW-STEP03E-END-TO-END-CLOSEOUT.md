# TASK004 Airflow STEP03E — Generate → Landing → Person/Visit → Reconcile

> **BUSINESS MAINLINE ACCEPTED / 2026-10-12 (America/New_York).**
> 本文新增 STEP03E 全链路验收，不覆盖也不追溯改写既有 STEP02 Processing Closeout。
> 本次证据由真实 Airflow DAG 状态、四个 Task 的成功日志、只读后置核验与仓库源码共同组成。
> 需要严格区分 **业务执行成功** 与 **原始 GitHub Actions workflow 成功**。

## 1. 验收结论和边界

| 验收项 | 状态 |
|---|---|
| DAG trigger + git-sync exact source | PASS（原始 live evidence） |
| Synthea Generate → Landing publish / manifest verify | PASS |
| Airflow generate_publish | success |
| Airflow person | success |
| Airflow visit | success |
| Airflow reconcile | success |
| Airflow DagRun | success |
| Person / Visit processing readback | PASS |
| 同 batch lineage / reconciliation | PASS |
| 成功运行的临时 Synthea Job / ConfigMap / Control Pod / SparkApplication 残留 | NO |
| Reconcile Processing mutation | NO |
| PostgreSQL mutation | NO（本次脚本不执行写入） |
| 原始 Self-Runner STEP03E GitHub workflow | **FAILURE**（DAG 成功后，后置 XCom 取证退出） |
| 独立 Self-Runner post-success 只读核验 | **PASS** |

该验收证明 STEP03E **业务链已真实跑通**；不声称原始 GitHub run 显示 SUCCESS，也不声称修订后的 mutating Live 验证脚本已经重新触发一个新的业务 batch。

TASK004 整体仍为 IN PROGRESS；后续 Azure/Fabric/dbt 等范围不包含在本次 Closeout 中。

## 2. 源码和运行契约

- Healthcare main commit: `d0731df6ce09953e45e0458cd7bd85f0ce4fb60c`。
- DAG: `airflow/dags/task004_processing_pipeline.py`；DAG ID = `task004_processing_pipeline`。
- Runtime image 固定 digest: `sha256:8d55a150e7fcd8ea9a1ed8e8c2c64d09bf4d19687822c0ec84857fdf429c05a7`。
- Airflow 3.2.2；Kubernetes provider 10.17.1（STEP02 已验证运行版本）。
- DAG 由 GitHub main 经 git-sync 同步。任务执行身份为 `dw-spark/task004-control-runtime`，Airflow Scheduler 跨 Namespace KPO RBAC 沿用已验收边界。
- 采用 `schedule=None`、`catchup=False`、`max_active_runs=1` 和 `is_paused_upon_creation=False`。
- `generate_publish` 的 reference / ingest date 来自 `dag_run.run_after`，支持手工 DAG run；run-scoped `BATCH_ID` 从 Airflow run_id 生成。
- `generate_publish` 写 XCom return.json，输出 batch_id、manifest_uri / manifest_sha256、source_version、ingest_date、verified_file_count 与 verified status。
- Person、Visit 并行消费上游 XCom；二者输出本次 Processing URI 和 canonical_rows；Reconcile 消费本次 Person/Visit 输出。
- 流程是 `generate_publish >> [person, visit] >> reconcile`；不使用 STEP02 的历史静态 manifest/Processing URI。

```text
Airflow trigger
      |
generate_publish (Synthea → S3 Landing → verify manifest)
      | XCom: batch_id, manifest_uri, manifest_sha256
    /   \
 Person  Visit
 23 rows 3592 rows
    \   /
   Reconcile
      |
     PASS
```

## 3. 主线变更

原已验收 STEP02 的 `TASK-004-AIRFLOW-PROCESSING-ORCHESTRATION-MAINLINE-CLOSEOUT.md` 保持历史真实性，不修改其当时的验收范围。

STEP03E 尾段修复均已进入 Healthcare main：

- [PR #33](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/33)：手工 Airflow run 日期从 `dag_run.run_after` 推导。
- [PR #34](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/34)：generate-publish report 路径改到 non-root control runtime 可写目录。
- [PR #35](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/35)：DAG pin 到 exact main runtime image。
- 最终 Healthcare main: `d0731df6ce09953e45e0458cd7bd85f0ce4fb60c`。

## 4. 真实 live 验收

- [Self-Runner Run 38324111846](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38324111846)
- Airflow run_id = `task004-step03e-38324111846`
- GitHub workflow conclusion = **failure**（后置 scheduler-context XCom 检查）；DAG 自身与全部四个 Task 为 `success`。
- 原始证据 artifact ID = `11780281601`（包含业务任务成功和后置退出位置）。

```text
DAG_RUN_STATE=success
TASK_STATE_GENERATE_PUBLISH=success
TASK_STATE_PERSON=success
TASK_STATE_VISIT=success
TASK_STATE_RECONCILE=success
```

本次新 Landing batch：

```text
SOURCE_VERSION=v3.3.0
INGEST_DATE=2026-10-12
GENERATED_BATCH_ID=task004-airflow-task004-step03e-38324111846
LANDING_STATUS=INTAKE_VERIFIED
VERIFIED_FILE_COUNT=18
MANIFEST_SHA256=ecc7cf3b75240e530f2cc96635b25e4eaf0794403e1b04d50d2248cd3aaa5cb1
s3://health-landing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-12/batch_id=task004-airflow-task004-step03e-38324111846/
```

下游验证：

```text
Person:
  batch_id=task004-airflow-task004-step03e-38324111846
  canonical_rows=23
  PROCESSING_READBACK=PASS
  RESULT=PASS
Visit:
  batch_id=task004-airflow-task004-step03e-38324111846
  canonical_rows=3592
  PROCESSING_READBACK=PASS
  RESULT=PASS
Reconcile:
  SOURCE_BATCH_ID=task004-airflow-task004-step03e-38324111846
  SOURCE_VERSION=v3.3.0
  SOURCE_INGEST_DATE=2026-10-12
  PROCESSING_MUTATION=NO
  RESULT=PASS
```

## 5. 独立 post-success 验证

[Self-Runner Run 38326695107](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38326695107) = **SUCCESS**。
该只读 workflow 重新检查了同一个、**已有**的 Airflow run，而不是重新生成 Synthea 数据。

```text
DAG_RUN_STATE=success
TASK_STATE_GENERATE_PUBLISH=success
TASK_STATE_PERSON=success
TASK_STATE_VISIT=success
TASK_STATE_RECONCILE=success
POSTSUCCESS_LOG_LINEAGE=PASS
SUCCESSFUL_SYNTHEA_JOB_RESIDUAL=NO
SUCCESSFUL_SYNTHEA_CONFIGMAP_RESIDUAL=NO
SUCCESSFUL_CONTROL_POD_RESIDUAL=NO
SUCCESSFUL_SPARKAPPLICATION_RESIDUAL=NO
POSTGRESQL_MUTATION=NO
TASK004_AIRFLOW_STEP03E_POSTSUCCESS=PASS
RESULT=PASS
```

后置核验使用 Airflow 实际 task logs 的业务 marker 和 DagRun / TaskInstance 状态，验证 Generate → Person/Visit → Reconcile 的同批次关系；它不是在 scheduler 内直接调用 Airflow 3 的 XCom API，因此日志 lineage PASS **不应标成 direct XCom API readback PASS**。

## 6. Self-Runner 正式化和后续开发限制

Self-Runner [PR #38](https://github.com/JohnZhang-DataForge/Self-Runner/pull/38) 用独立收尾分支重新整理原 STEP03E 的 31-commit 实验分支。选取正式 live / post-success workflow、固定 request、policy、source tests 和执行脚本；**不把** failure-probe、log-probe、xcom-api-probe、postsuccess-probe、diagnose 或一次性 trigger 作为主线正式文件。

正式 Self-Runner 合并证据：

```text
Self-Runner feature HEAD = 49da2267aed6eca73b2fa735d5145f3ee9427e51
Read-only pre-merge run = 38328528372  SUCCESS
Policy job             = SUCCESS
ARC verify job         = SUCCESS
Evidence artifact ID   = 11781352153
PR #38 squash/main     = 6f72c05ad8eb1a0abeb19f3cff9e89ac698cff87
Post-merge exact-main  = 38328600074  SUCCESS
Post-merge artifact ID = 11781762914
```

[Pre-merge Run 38328528372](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38328528372) 的 workflow conclusion 为 SUCCESS，原始 GitHub Run `38324111846` 的 FAILURE 历史保持不变。先前 `38328025745` 的读日志、验证步骤成功，但 artifact upload 卡住；不将这个整次 workflow 冒充 SUCCESS。

Mutating STEP03E Live workflow 已更改为显式 `workflow_dispatch`，不得通过普通 source push 意外创建新的 Landing/Processing 数据。修复后的 Live Shell 虽已在正式 CI 做 Shell 语法检查，但**没有重新执行一个新的业务 batch**；正式验收属于已有的原始成功 Airflow run + 只读日志核验。

[Post-merge exact-main Run 38328600074](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38328600074) = **SUCCESS**，Policy / ARC Verify 均成功，并已上传正式证据 Artifact。Self-Runner STEP03E 验证代码现为正式 mainline。

**文档收尾：**合并本 Healthcare 文档 PR；然后以此 Closeout 作为当前 Agent 权威资料。不得依据 STEP02 的旧 `Airflow upstream ingestion NEXT` 再重复开发 STEP03E，后续新业务阶段另行确认。

## 7. 关键注意事项

1. 不改写历史 STEP02 Closeout；本文件是新增、较新的 STEP03E 验收文档。
2. GitHub workflow `failure` 不能冒充 SUCCESS；但不能抹去 DAG 实际 `success` 和独立 post-success 的 PASS。
3. 不重跑相同 batch 当作普通的 CI retry；只有明确的新 live 验收任务才允许 Synthea / Landing / Processing mutation。
4. 业务结果的证据来自日志 + 只读集群查询，不代表 PostgreSQL 发生了写入，也不是 Fabric/dbt 全链验收。
5. 任何新 Agent 开工先读 `docs/README.md`、`docs/tasks/TASK-STATUS.md`、本文件、Operations 和 Skill，确认两仓库 main SHA、正式 STEP03E Workflow 与最后一次 CI 结果。
