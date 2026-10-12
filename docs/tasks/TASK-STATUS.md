# Healthcare Data Platform — 当前 TASK 状态与下一步（2026-10-12）

> **CURRENT STATUS / MAINLINE AUTHORITY**。本文件描述唯一正式业务主线当前状态。历史 Candidate / Pilot / Closeout 只说明当时事实，不能覆盖本文件。

## 已验证 / 下一步

| 范围 | 当前主线状态 | 当前动作 |
|---|---|---|
| TASK001 | 历史冻结 Landing / batch 基线 | 不重跑、不改冻结文件 |
| TASK002 | Person V2 历史回归与冻结基线 | 不擅自修改 |
| TASK003 | **COMPLETE / CLOSED** | 只读参考实现 |
| TASK004 — Synthea | **PASS** | frozen baseline |
| TASK004 — Resolver / Control | **PASS** | frozen baseline |
| TASK004 — Person | **PASS** | frozen baseline |
| TASK004 — Visit | **PASS** | frozen baseline |
| TASK004 — Batch Reconciliation | **PASS / MAINLINE ACCEPTED** | frozen baseline；正式证据见 Mainline Closeout |
| **TASK004 — Airflow Processing orchestration** | **PASS / PROCESSING MAINLINE ACCEPTED** | **NEXT：将 Generate Synthea → Landing 接到现有 DAG 上游** |
| Azure/Fabric/dbt/MLflow 等 | 后续分阶段设计 | 不阻塞当前 Airflow MVP |

**TASK004 overall status = IN PROGRESS。**

## Airflow Processing orchestration 正式主线验收

当前正式 Processing DAG：

~~~text
GitHub main
→ git-sync
→ Airflow 3.2.2
→ Person + Visit (KubernetesPodOperator, parallel)
→ dynamic XCom
→ Reconcile
~~~

Healthcare：

~~~text
PR #26 merge/main = e99a68e8b24a3dee97ea38ce7dc426a63c6fb119
runtime image digest =
sha256:bf7f4611a9dcbd8bd79b420f80c5f97f4ec92e0dbd5ba8132cea4be59fdf57bf

PR #27 merge/main = f82a70e28038d87bb9e7e60670dfb0c39e928b0b
PR #28 merge/main = 5e043b8f00d89a01b72ae6264f35903ceff93de9
~~~

Self-Runner acceptance：

~~~text
Airflow parse             38309576088  PASS
KPO PodSpec dry-run       38309911048  PASS
scheduler RBAC            38311231070  PASS
control-runtime kubectl   38311402840  PASS
live orchestration        38311805385  PASS
DAG unpause               38312544761  PASS
post-merge git-sync       38313275171  PASS

Self-Runner PR #35
squash merge/main         a67a75c15e5c6385131b056c1af0d1aa8eb34077
~~~

Live evidence：

~~~text
AIRFLOW_GITSYNC_DAG_VISIBLE=YES
AIRFLOW_GITSYNC_EXACT_SOURCE_GATE=PASS
AIRFLOW_DAG_TRIGGER=PASS
TASK_STATE_PERSON=success
TASK_STATE_VISIT=success
TASK_STATE_RECONCILE=success
AIRFLOW_DAG_RUN=PASS
SUCCESSFUL_SPARKAPPLICATION_RESIDUAL=NO
SUCCESSFUL_CONTROL_POD_RESIDUAL=NO
POSTGRESQL_MUTATION=NO
TASK004_AIRFLOW_STEP02C_LIVE=PASS
RESULT=PASS
~~~

Live artifact：

~~~text
Artifact = 11775098927
Digest =
sha256:570901ce456778457fecc3a1c718ea88aa9ea9dafe8281028e917b3f678cf0ed
~~~

Post-merge authority：

~~~text
Healthcare main =
5e043b8f00d89a01b72ae6264f35903ceff93de9

LOCAL_DAG_SHA256 =
6269920737ca616194f6282994dca711dac98afabf7a4b4f992c01d84789ac1c

GITSYNC_DAG_SHA256 =
6269920737ca616194f6282994dca711dac98afabf7a4b4f992c01d84789ac1c

DAG_IS_PAUSED=false
~~~

正式 Closeout：

- TASK-004-AIRFLOW-PROCESSING-ORCHESTRATION-MAINLINE-CLOSEOUT.md

## Batch Reconciliation 正式主线验收

Candidate review 结论：

```text
REVIEW_DECISION=MODIFY_BEFORE_ACCEPTANCE
```

完成 canonical source 加固后：

```text
Healthcare PR #24
final tested PR HEAD = ee16f5265b0ebb8c30e7e65ec665215613956e77
merge/main SHA       = 91d96f436e7697d70025cc1c9a045ecfb20f41b1
```

Self-Runner：

```text
pre-merge exact PR HEAD Run = 38287060452  PASS
post-merge exact main Run   = 38287401518  PASS
Self-Runner PR #31 merge    = 8ab26784cd0229cce96989e3691c122049e3c23a
```

最终业务 evidence：

```text
PATIENT_ROWS=20
PATIENT_UNIQUE_IDS=20
ENCOUNTER_ROWS=2459
ENCOUNTER_UNIQUE_IDS=2459
REFERENCED_PATIENTS=20
ORPHAN_ENCOUNTERS=0
SOURCE_SYSTEM=synthea
SOURCE_VERSION=v3.3.0
SOURCE_BATCH_ID=task004-p20-first-landing-20261011
SOURCE_INGEST_DATE=2026-10-11
PROCESSING_MUTATION=NO
POSTGRESQL_MUTATION=NO
SUCCESSFUL_SPARKAPPLICATION_RESIDUAL=NO
SUCCESSFUL_CONFIGMAP_RESIDUAL=NO
SUCCESSFUL_DRIVER_POD_RESIDUAL=NO
RECONCILIATION_STATE_GATE=PASS
RESULT=PASS
```

Artifacts：

```text
pre-merge:
  Run      = 38287060452
  Artifact = 11763243392
  Digest   = sha256:171fb1d9bdfd6506ef150c8e37a529fb26a2f3225ebce9deba344ec057307292

post-merge:
  Run      = 38287401518
  Artifact = 11764107251
  Digest   = sha256:c0f72a2dc7c84bccfa96af344432241de0ab6ace8a69ae5c959e5bcf3ac2d1f7
```

两次早期失败均未进入业务 mutation：

- Run `38286850393`：Workflow YAML parse failure，jobs=0。
- Run `38286943030`：source test assertion failure；Spark execution skipped。

## 下一位 Agent 如何开始

1. 阅读 `../README.md`、本文件、Reconciliation Mainline Closeout、Operations、Skill、TASK004 Lessons。
2. 不重新开发 Person / Visit / Reconciliation，也不重新设计已经验收的 Airflow Processing DAG。
3. 当前唯一主线目标是把 Generate Synthea → Landing publish / validate 接到现有 DAG 上游。
4. 先检查 04c-run-synthea-generate-publish.sh、dw-synthea RBAC、Landing 输出 contract，以及如何把 manifest URI / SHA 动态交给现有 Person / Visit。
5. 使用正式流程：Healthcare feature PR → exact PR HEAD → Self-Runner fixed validation → real Airflow/K8s runtime → PASS → merge → 必要的 post-merge exact-main validation → checkpoint。

## 冻结与安全

- TASK001–TASK003：task-level frozen。
- TASK004 当前 frozen baseline：Synthea / Landing / Resolver / Control Runtime / Person / Visit / Batch Reconciliation / Airflow Processing orchestration。
- TASK004 整体：**IN PROGRESS**。
- 不把 DAG parse、render-only 或单个 operator 构造成功冒充真实 Airflow orchestration PASS。
- 历史文档原文归档，不追溯改写。

## 相关文档

- `TASK-004-PHASE9-CLOSEOUT.md`
- `TASK-004-AIRFLOW-PROCESSING-ORCHESTRATION-MAINLINE-CLOSEOUT.md`
- `TASK-004-BATCH-RECONCILIATION-MAINLINE-CLOSEOUT.md`
- `../archive/2026-10-12-mainline-reconciliation-acceptance/tasks/TASK-004-BATCH-RECONCILIATION-CANDIDATE-STATUS.md`
- `../archive/2026-10-12/tasks/TASK-004-BATCH-RECONCILIATION-CLOSEOUT-V9-TEST-PERIOD.md`
