# Healthcare Data Platform — 当前 TASK 状态与下一步（2026-10-12 EDT，更新 TASK004 OMOP 完整闭环验收范围）

> **2026-10-13 新增权威状态：READONLY Person Source ID Reconciliation 已 PASS（STEP04F DB 写入仍 BLOCKED）**。[验收记录](TASK-004-STEP04F-PERSON-SOURCE-ID-READONLY-RECONCILIATION-CLOSEOUT.md) / [Self-Runner Run 38435544614](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38435544614) ：固定新批次 Person 23，Source ID 已存在 23（完全一致 0，内容不同 23），全新 0，dangling map 0；数据库 Person 136 / Visit 9391；失败批次 Ledger/Stage/Commit 0/0/0；`DATABASE_MUTATION=NO`。审计路径修复、Self-Runner PR #69 已合并。**唯一 NEXT = 独立规划/验证 Source ID + Seed/Reference Date 隔离语义，不开始新的批次，不执行 Writer COMMIT，TASK005 ON HOLD。**以下旧 STEP04A/04B/只读审计 NEXT 均为历史阶段说明。

> **2026-10-13 当前权威 NEXT / 见 [TASK004 最新交接](TASK-004-AGENT-HANDOFF-CURRENT-2026-10-13.zh-CN.md)：** 固定批次 STEP04C/D/E 已完成；STEP04F S3/CDM Runtime reader+rollback writer 已构建实测，新 Airflow Synthea Batch `task004-airflow-task004-step03e-38431103586` Processing PASS（Person=23，Visit=3588），但新 Person 入库测试 `BLOCKED:EXISTING_TARGET_DRIFT`，不允许 COMMIT。最新只读 Source ID 审计 Run `38434861465` 为 FAILURE（`ModuleNotFoundError: task004_cdm_materialization_plan`），Self-Runner feature `feature/task004-person-readonly-audit-20261013` 尚未合并。**唯一 NEXT = 修复该测试 Job PYTHONPATH，真实只读查 23 人的 existing/changed/new/dangling 数量与失败批次 DB residual；不重新跑 Synthea、不得绕过漂移保护。**本文件后面遗留 STEP04A/04B NEXT 是过期阶段说明，以最新交接为准。TASK005 仍 ON HOLD。


> **CURRENT STATUS / MAINLINE AUTHORITY**。本文件描述唯一正式业务主线当前状态。历史 Candidate / Pilot / Closeout 只说明当时事实，不能覆盖本文件。

## 已验证 / 下一步

| 范围 | 当前主线状态 | 当前动作 |
|---|---|---|
| TASK001 | 历史冻结 Landing / batch 基线 | 不重跑、不改冻结文件 |
| TASK002 | Person V2 历史回归与冻结基线 | 不擅自修改 |
| TASK003 | **COMPLETE / CLOSED** | 只读参考实现 |
| **TASK004 — overall（完整闭环）** | **IN PROGRESS** | **STEP04A CLOSED; STEP04B OFFLINE REPLAY CONTRACT BASELINE PASS (15/15), NEXT: controlled mapping/loader implementation subject to separate DB write authorization**；正式开发计划见 [Person/Visit CDM + Idempotency Plan](TASK-004-OMOP-CDM-INTEGRATION-AND-IDEMPOTENCY-PLAN-v1.0.zh-CN.md) |
| TASK004 — Processing MVP（既有验收） | **COMPLETE / CLOSED / FROZEN** | 保持历史业务/Runner PASS，见 [MVP Closeout](TASK-004-FINAL-CLOSEOUT.md) |
| TASK004 — CDM Person/Visit Materialization | **STEP04C/D DB LOAD + STEP04E JOINT RECONCILIATION PASS** | 固定 batch Person 23、Visit 3592 已分别真实写入 PostgreSQL，Person 136 / Visit 9391，重复加载不新增，Visit FK 缺失 0。证据见 [Person Closeout](TASK-004-STEP04C-PERSON-DB-COMMIT-CLOSEOUT.md)、[Visit Closeout](TASK-004-STEP04D-VISIT-DB-COMMIT-CLOSEOUT.md) 与 [Joint DB Closeout](TASK-004-STEP04E-JOINT-DB-RECONCILIATION-CLOSEOUT.md)；STEP04F Airflow DB 编排为 NEXT |
| TASK004 — STEP04F Airflow Dynamic CDM Plan | **6-TASK DAG PARSE PASS / DB AUTO LOAD PENDING** | 已在 reconcile→cdm_load_preflight 后接入 cdm_materialization_plan，动态批次 URI/Manifest 指纹、来源漂移检查 PASS；真实 Airflow scheduler DagBag 解析 SUCCESS；无新 DAG Run 或数据库写入。见 [STEP04F Dynamic Plan Closeout](TASK-004-STEP04F-DYNAMIC-BATCH-PLAN-CLOSEOUT.md) |
| TASK004 — STEP04F Dynamic PostgreSQL Writer | **REAL POSTGRESQL ROLLBACK PASS / COMMIT DISABLED** | 动态批次 Person/Visit 事务 SQL 已在真实 PG 进行联合 ROLLBACK 演练，并独立确认无数据遗留；Airflow 自动写库、镜像和新批次 COMMIT 仍待做。见 [STEP04F Dynamic PG Writer](TASK-004-STEP04F-DYNAMIC-PG-WRITER-ROLLBACK.md) |
| TASK004 — 同批次 Airflow replay/retry 幂等性 | **PERSON + VISIT DB REPLAY PASS / FULL DAG NOT VERIFIED** | STEP04C/D 同 batch Person 与 Visit 各自数据库重放已实测不增加记录；跨批次并发、未知提交恢复、整条 Airflow DAG 重放仍未验证 |
| TASK004 — Synthea | **PASS** | frozen baseline |
| TASK004 — Resolver / Control | **PASS** | frozen baseline |
| TASK004 — Person | **PASS** | frozen baseline |
| TASK004 — Visit | **PASS** | frozen baseline |
| TASK004 — Batch Reconciliation | **PASS / MAINLINE ACCEPTED** | frozen baseline；正式证据见 Mainline Closeout |
| TASK004 — Airflow STEP02 Processing orchestration | **PASS / HISTORICAL MAINLINE ACCEPTED** | frozen baseline |
| **TASK004 — Airflow STEP03E end-to-end** | **PASS / BUSINESS + SELF-RUNNER MAINLINE ACCEPTED** | frozen STEP03E baseline，Final Audit PASS；旧 Live 新批次未重跑 |
| **TASK005 — Condition (Phase E)** | **ON HOLD / DESIGN BASELINE ONLY** | 等 TASK004 Person + Visit 同 batch CDM 入库和重放验收完成后再解锁 STEP00 |
| Azure/Fabric/dbt/MLflow 等 | 后续分阶段设计 | 不阻塞已完成的 Airflow MVP |

**TASK004 overall status = IN PROGRESS（按用户明确的完整流程完成标准）。** 既有 Synthea → verified Landing → Person/Visit Processing → Reconcile 的 **MVP COMPLETE / FROZEN**、历史真实验收未被推翻；但 **OMOP Person/Visit 同批次入库 + 数据库级对账 + Airflow 重放幂等** 尚未完成。权威 NEXT = [`TASK-004-OMOP-CDM-INTEGRATION-AND-IDEMPOTENCY-PLAN-v1.0.zh-CN.md`](TASK-004-OMOP-CDM-INTEGRATION-AND-IDEMPOTENCY-PLAN-v1.0.zh-CN.md) 的 **STEP04B CODE / TEST ONLY**；STEP04A 实际只读调查已经验收，见 [STEP04A Final Closeout](TASK-004-STEP04A-READONLY-FINAL-CLOSEOUT.md)，但写库前 batch isolation 仍 BLOCKED。过去 [`TASK-004-FINAL-CLOSEOUT.md`](TASK-004-FINAL-CLOSEOUT.md) 仅证明原限定 Processing MVP，属历史里程碑。TASK005 暂缓。

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

## TASK004 原限定 Processing MVP Final Audit & Closure（历史里程碑，2026-10-13 UTC）

- runner01 分别执行 STEP01、STEP02、Final Storage Check 的只读审计：四节点 Ready、历史 DAG/四 Task success、成功 run Synthea Job 和 Control Pod residual=NO、Airflow 当前 DAG GitSync 源码 SHA256 与 GitHub main 一致。
- S3 正确 namespace 是 `dw-seaweedfs`，四个 Pod 全部 1/1 Running，S3 EndpointSlice 存在。早期失败运行的历史 Job/Pod 不等同于成功运行的残留，不擅自删除。
- Self-Runner [PR #39](https://github.com/JohnZhang-DataForge/Self-Runner/pull/39) 已修复历史只读固定 SHA 检查，post-merge [Run 38329852476](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38329852476) SUCCESS；**修复后 Live mutating 新批次回归未执行**。
- PostgreSQL `omop` 历史状态：Person=113、Visit=5799、Condition=0；STEP03E 的 23/3592 是 Processing，**数据库新批次写入不属于 TASK004 验收范围**。
- 当时限定的 Processing MVP 范围、非阻塞项、证据：[`TASK-004-FINAL-CLOSEOUT.md`](TASK-004-FINAL-CLOSEOUT.md)。**本条是历史关闭证据，当前 TASK004 扩展目标及 NEXT 已由上方状态表与新增 CDM 计划取代**。

## TASK004 OMOP Person/Visit + Replay 新增完成标准（当前 NEXT）

- 用户最终目标：一个批次从 Airflow 触发 Synthea → verified Landing → Person/Visit Processing → **Person CDM 入库 → Visit CDM 入库 → 独立数据库对账**，同一 batch 重放/部分失败恢复**不产生重复数据或重分配稳定 ID**。
- **唯一当前授权 STEP：STEP04A 只读数据库与真实输入调查**；STEP04B 为逻辑/契约设计。后续任何 PG/S3/K8s mutation 或新的 Airflow Live Run 均需单独明确授权。
- 入库顺序与动态业务键：Person Mapping + CDM commit/readback → Visit Mapping + CDM commit/readback → batch-scoped final database reconciliation。**不能原样复用历史追加写入共享 etl.person_stage 和 TASK003 冻结的 5799 行脚本。**
- 正式执行契约、PR 结构、失败重试/同 batch replay 与 A1–A11 验收矩阵详见 [`TASK-004-OMOP-CDM-INTEGRATION-AND-IDEMPOTENCY-PLAN-v1.0.zh-CN.md`](TASK-004-OMOP-CDM-INTEGRATION-AND-IDEMPOTENCY-PLAN-v1.0.zh-CN.md)。
- 当前状态：TASK004 Processing MVP PASS/FROZEN；CDM loop NOT IMPLEMENTED；replay idempotency NOT VERIFIED；**TASK004 overall IN PROGRESS；TASK005 ON HOLD**。

## TASK005 Condition 设计基线与历史 NEXT（当前 ON HOLD）

- 业务实体：Synthea v3.3.0 `conditions.csv` → `condition_occurrence`；七列表头 `START, STOP, PATIENT, ENCOUNTER, SYSTEM, CODE, DESCRIPTION`，**没有 Id**，必须证明可重复且保留重复事件的唯一 occurrence key。
- 设计文档：`TASK-005-CONDITION-DEVELOPMENT-PLAN-v1.0.zh-CN.md`（STEP00–06）。
- **当前状态：ON HOLD**。原 STEP00 Condition 只读 preflight 属 TASK005 将来解锁后的下一步，**不是此刻可启动的工作**。先完成 TASK004 STEP04A–04H 的完整入库与重放闭环；Condition 设计计划仍保留。
- Processing Candidate 与 PostgreSQL `cdm.condition_occurrence` materialization 必须分别验收；OMOP mapping 的源码 code 不得当成 `concept_id`；修复后的 STEP03E Live Workflow 不得未经授权自动重跑。
- Condition 当前不开发、不部署、不写库；待 TASK004 完成正式 DB 闭环后才按 STEP00 的小范围 PR + exact-SHA Runner 开工。

## 下一位 Agent 如何开始（唯一当前主线）

1. 读取 `../README.md`、本状态表、**TASK004 OMOP CDM Integration & Idempotency Plan**、STEP03E 历史真实 Closeout、TASK003 Final Closeout、Operations、Skill 和 Lessons。
2. 实时核对 Healthcare / Self-Runner main SHA，确认 TASK004 已验收 Processing MVP 不动；旧 MVP 的 CLOSEOUT 属 **历史限定范围**，不代表本次数据库终验。
3. 只进入 **TASK004 STEP04A**：固定一个只读 verified batch，盘点真实 Postgres DDL、既有 ID mapping 和 Processing 结构，提交 read-only 预检源码/报告 PR，绑定 exact SHA Self-Runner 验证，写证据。
4. 不得运行旧的 TASK003 数据库一次性脚本，不得直接读取共享 Person Stage 当作新批次，禁止无批准触发新 Airflow/Synthea、Postgres DML/DDL、S3/集群写入。
5. STEP04A PASS 或 BLOCKED 后更新状态并再决定 STEP04B；**TASK005 Condition ON HOLD**。

## 冻结与安全

- TASK001–TASK003：task-level frozen。
- TASK004 既有 Processing MVP frozen baseline：Synthea / Landing / Resolver / Control Runtime / Person / Visit / Batch Reconciliation / STEP02 Processing / STEP03E；Self-Runner PR #38/#39 与 Final Audit 验收 PASS。**新增 OMOP 入库/幂等性扩展是未完成工作**，不得改写旧验收。
- TASK004 整体（新定义的完整闭环）：**IN PROGRESS**；新批次 PostgreSQL Person + Visit 入库、数据库对账及同 batch replay 未通过前不允许 CLOSED。TASK005 **ON HOLD**。
- 不把 DAG parse、render-only 或单个 operator 构造成功冒充真实 Airflow orchestration PASS。
- 历史文档原文归档，不追溯改写。

## 相关文档

- `TASK-004-OMOP-CDM-INTEGRATION-AND-IDEMPOTENCY-PLAN-v1.0.zh-CN.md` — **当前 TASK004 开发权威计划 / NEXT STEP04A**
- `TASK-004-FINAL-CLOSEOUT.md` — 原限定 Processing MVP 历史验收（仍然有效，但不能充当 CDM 终验）
- `TASK-005-CONDITION-DEVELOPMENT-PLAN-v1.0.zh-CN.md` — Condition 已设计，**ON HOLD**（当前不是 NEXT）

- `TASK-004-PHASE9-CLOSEOUT.md`
- `TASK-004-AIRFLOW-PROCESSING-ORCHESTRATION-MAINLINE-CLOSEOUT.md`
- `TASK-004-BATCH-RECONCILIATION-MAINLINE-CLOSEOUT.md`
- `../archive/2026-10-12-mainline-reconciliation-acceptance/tasks/TASK-004-BATCH-RECONCILIATION-CANDIDATE-STATUS.md`
- `../archive/2026-10-12/tasks/TASK-004-BATCH-RECONCILIATION-CLOSEOUT-V9-TEST-PERIOD.md`
