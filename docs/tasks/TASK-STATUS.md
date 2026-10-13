# Healthcare Data Platform — 当前 TASK 状态与下一步（2026-10-12 EDT；2026-10-13 UTC 审计）

> **CURRENT STATUS / MAINLINE AUTHORITY**。本文件描述唯一正式业务主线当前状态。历史 Candidate / Pilot / Closeout 只说明当时事实，不能覆盖本文件。

## 已验证 / 下一步

| 范围 | 当前主线状态 | 当前动作 |
|---|---|---|
| TASK001 | 历史冻结 Landing / batch 基线 | 不重跑、不改冻结文件 |
| TASK002 | Person V2 历史回归与冻结基线 | 不擅自修改 |
| TASK003 | **COMPLETE / CLOSED** | 只读参考实现 |
| **TASK004 — overall** | **COMPLETE / CLOSED / FROZEN** | Processing-first Airflow MVP 已最终验收；见 [Final Closeout](TASK-004-FINAL-CLOSEOUT.md) |
| TASK004 — Synthea | **PASS** | frozen baseline |
| TASK004 — Resolver / Control | **PASS** | frozen baseline |
| TASK004 — Person | **PASS** | frozen baseline |
| TASK004 — Visit | **PASS** | frozen baseline |
| TASK004 — Batch Reconciliation | **PASS / MAINLINE ACCEPTED** | frozen baseline；正式证据见 Mainline Closeout |
| TASK004 — Airflow STEP02 Processing orchestration | **PASS / HISTORICAL MAINLINE ACCEPTED** | frozen baseline |
| **TASK004 — Airflow STEP03E end-to-end** | **PASS / BUSINESS + SELF-RUNNER MAINLINE ACCEPTED** | frozen STEP03E baseline，Final Audit PASS；旧 Live 新批次未重跑 |
| **TASK005 — Condition (Phase E)** | **DESIGN BASELINE / IMPLEMENTATION NOT STARTED** | **NEXT: STEP00 read-only Source/ID/FK/Vocabulary/DB preflight**；不授权业务数据 mutation |
| Azure/Fabric/dbt/MLflow 等 | 后续分阶段设计 | 不阻塞已完成的 Airflow MVP |

**TASK004 overall status = COMPLETE / CLOSED / FROZEN。** 该状态仅覆盖 Synthea → verified Landing → Person/Visit **Processing** → Reconcile 的 Airflow MVP；不宣称新批次 PostgreSQL OMOP 写入。最终只读审计见 [`TASK-004-FINAL-CLOSEOUT.md`](TASK-004-FINAL-CLOSEOUT.md)。

## 历史 STEP02 Airflow Processing orchestration 正式主线验收

以下是历史 STEP02 Processing DAG（STEP03E 的最新四 Task DAG 见新增 Closeout）：

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

## 最新 STEP03E 全链业务验收（2026-10-12）

STEP03E 业务验收时固定的 Healthcare 源码 SHA = `d0731df6ce09953e45e0458cd7bd85f0ce4fb60c`（**历史已验收 SHA，不是持续变化的当前 main**；新 Agent 先查当前 GitHub main）；DAG = `task004_processing_pipeline`，现已形成 `generate_publish >> [person, visit] >> reconcile`。

- Self-Runner live Run `38324111846`：**GitHub failure**（发生在 DAG 成功后的后置 XCom 取证）。Airflow DagRun 及 generate_publish、person、visit、reconcile 四个 Task 均为 **success**。
- 新 Landing batch = `task004-airflow-task004-step03e-38324111846`；source_version `v3.3.0`；ingest date `2026-10-12`；18 verified files；manifest SHA256 `ecc7cf3b75240e530f2cc96635b25e4eaf0794403e1b04d50d2248cd3aaa5cb1`。
- Person `23` canonical rows + Visit `3592` canonical rows，Processing readback 均 PASS；Reconcile 同 batch、同 version / ingest date，PASS。
- Self-Runner 独立 post-success Run `38326695107` = **SUCCESS**，真实 Airflow 日志 lineage 与 Synthea Job、ConfigMap、Control Pod、SparkApplication 成功后 residual 检查 PASS；无 PostgreSQL 写入。
- Self-Runner 正式验证代码收尾：[PR #38](https://github.com/JohnZhang-DataForge/Self-Runner/pull/38)。最终固定 PR HEAD `49da2267aed6eca73b2fa735d5145f3ee9427e51`；pre-merge Run `38328528372` = SUCCESS；PR #38 squash/main = `6f72c05ad8eb1a0abeb19f3cff9e89ac698cff87`；post-merge exact-main Run `38328600074` = SUCCESS，Artifact `11781762914`。`38328025745` 因上传流程卡住，不作为主线成功证据。

正式细节、源码身份、证据、限制：`TASK-004-AIRFLOW-STEP03E-END-TO-END-CLOSEOUT.md`。历史 STEP02 Closeout 仍有效，但它当时写的 `upstream ingestion NEXT` **已经过期**。

## TASK004 Final Audit & Closure（2026-10-13 UTC）

- runner01 分别执行 STEP01、STEP02、Final Storage Check 的只读审计：四节点 Ready、历史 DAG/四 Task success、成功 run Synthea Job 和 Control Pod residual=NO、Airflow 当前 DAG GitSync 源码 SHA256 与 GitHub main 一致。
- S3 正确 namespace 是 `dw-seaweedfs`，四个 Pod 全部 1/1 Running，S3 EndpointSlice 存在。早期失败运行的历史 Job/Pod 不等同于成功运行的残留，不擅自删除。
- Self-Runner [PR #39](https://github.com/JohnZhang-DataForge/Self-Runner/pull/39) 已修复历史只读固定 SHA 检查，post-merge [Run 38329852476](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38329852476) SUCCESS；**修复后 Live mutating 新批次回归未执行**。
- PostgreSQL `omop` 历史状态：Person=113、Visit=5799、Condition=0；STEP03E 的 23/3592 是 Processing，**数据库新批次写入不属于 TASK004 验收范围**。
- 完整范围、非阻塞项、证据：[`TASK-004-FINAL-CLOSEOUT.md`](TASK-004-FINAL-CLOSEOUT.md)。**TASK004 正式冻结，唯一当前 NEXT 为 TASK005 STEP00 read-only preflight**。

## TASK005 Condition 设计基线与当前 NEXT（尚未执行）

- 业务实体：Synthea v3.3.0 `conditions.csv` → `condition_occurrence`；七列表头 `START, STOP, PATIENT, ENCOUNTER, SYSTEM, CODE, DESCRIPTION`，**没有 Id**，必须证明可重复且保留重复事件的唯一 occurrence key。
- 设计文档：`TASK-005-CONDITION-DEVELOPMENT-PLAN-v1.0.zh-CN.md`（STEP00–06）。
- **当前唯一获授权工作**：STEP00 read-only 前置条件盘点，锁定 verified source batch/manifest/sha，核查行数/重复、Person/Visit 同 batch FK、实际 OMOP/vocabulary 和数据库 ID mapping。输出报告及代码契约设计；**没有任何 Source/Processing/PostgreSQL mutation 授权**。
- Processing Candidate 与 PostgreSQL `cdm.condition_occurrence` materialization 必须分别验收；OMOP mapping 的源码 code 不得当成 `concept_id`；修复后的 STEP03E Live Workflow 不得未经授权自动重跑。
- 下一 Agent 必须按 STEP00 的小范围 PR + exact-SHA Self-Runner 验证，失败不得越过关口。Condition 未 VERIFIED，也未开始部署。

## 下一位 Agent 如何开始

1. 先读 `../README.md`、本文件、TASK005 Condition 开发方案、最新 STEP03E End-to-End Closeout、Operations、Skill、TASK003 Blueprint、Lessons。
2. 核对 Healthcare / Self-Runner 的实际 main SHA（Self-Runner 接受时 main 为 `6f72c05ad8eb1a0abeb19f3cff9e89ac698cff87`）及正式 Closeout，避免被老 STEP02 的 NEXT 误导。
3. STEP03E Business + Self-Runner Validation **已完成主线验收**。下一实体已确定为 **TASK005 Condition**，正式设计见 `TASK-005-CONDITION-DEVELOPMENT-PLAN-v1.0.zh-CN.md`。**唯一当前 NEXT 是 STEP00 只读 preflight**（source contract/事件 key/Person-Visit FK/Vocabulary/真实 DB DDL），实施代码与实际数据写入尚未开始，绝不跳到 STEP01 或 PostgreSQL mutation。
4. 不重复部署或重跑已验收的 Person / Visit / Reconcile / Synthea → Landing；除非明确开立下一业务阶段，不进行新数据 mutation。
5. 后续范围另行决策；严格维持一次一个有边界的 STEP 和固定 SHA 验证。

## 冻结与安全

- TASK001–TASK003：task-level frozen。
- TASK004 整体 frozen baseline：Synthea / Landing / Resolver / Control Runtime / Person / Visit / Batch Reconciliation / STEP02 Processing / STEP03E；正式 Self-Runner PR #38/#39 与 Final Audit 验收 PASS，其他能力及未执行的 Live 回归按 Final Closeout 的明确边界保留。
- TASK004 整体：**COMPLETE / CLOSED / FROZEN**；不覆盖 PostgreSQL 新批次物化、Fabric/dbt 等后续阶段。
- 不把 DAG parse、render-only 或单个 operator 构造成功冒充真实 Airflow orchestration PASS。
- 历史文档原文归档，不追溯改写。

## 相关文档

- `TASK-004-FINAL-CLOSEOUT.md` — TASK004 当前最终状态唯一 Closeout
- `TASK-005-CONDITION-DEVELOPMENT-PLAN-v1.0.zh-CN.md` — 当前 NEXT / 条件实体正式设计基线（实施 NOT STARTED）

- `TASK-004-PHASE9-CLOSEOUT.md`
- `TASK-004-AIRFLOW-PROCESSING-ORCHESTRATION-MAINLINE-CLOSEOUT.md`
- `TASK-004-BATCH-RECONCILIATION-MAINLINE-CLOSEOUT.md`
- `../archive/2026-10-12-mainline-reconciliation-acceptance/tasks/TASK-004-BATCH-RECONCILIATION-CANDIDATE-STATUS.md`
- `../archive/2026-10-12/tasks/TASK-004-BATCH-RECONCILIATION-CLOSEOUT-V9-TEST-PERIOD.md`
