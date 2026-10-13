# Healthcare Data Platform — Agent START HERE（当前有效文档）

> **CURRENT / 2026-10-12**。本目录是新 Agent 的唯一文档入口。历史资料移入 `docs/archive/YYYY-MM-DD[-topic]/`，**不要将 Archive 的 NEXT / Candidate / Pilot 状态当成当前状态**。

## 按顺序阅读

1. [当前 TASK 状态与下一步](tasks/TASK-STATUS.md)：当前主线真实完成什么、下一步是什么。
2. [STEP03E End-to-End Acceptance](tasks/TASK-004-AIRFLOW-STEP03E-END-TO-END-CLOSEOUT.md)：Synthea→Landing→Person/Visit→Reconcile；本次正式验收。
3. [TASK004 Airflow Processing Orchestration Mainline Closeout](tasks/TASK-004-AIRFLOW-PROCESSING-ORCHESTRATION-MAINLINE-CLOSEOUT.md)：GitHub → git-sync → Airflow → Person/Visit → Reconcile 正式主线验收。
4. [TASK004 Batch Reconciliation Mainline Closeout](tasks/TASK-004-BATCH-RECONCILIATION-MAINLINE-CLOSEOUT.md)：Reconciliation 正式主线验收证据。
5. [正式双仓库开发操作手册](development/PLATFORM-DEVELOPMENT-OPERATIONS-v1.0.zh-CN.md)：Healthcare feature PR → exact SHA → Self-Runner / ARC → PASS → Merge → post-merge validation → Checkpoint。
6. [Agent 开发 Skill](skill/SKILL-cn.md)：一步一验、canonical source、数据安全、Git 与文档治理。
7. [通用开发经验](runbooks/development-lessons-cn.md) 与 [TASK004 专项经验](runbooks/development-lessons-task004-cn.md)。
8. [当前总架构（中文）](architecture/Healthcare-Data-Platform-Architecture-and-Implementation.v4.zh-CN.md) / [English](architecture/Healthcare-Data-Platform-Architecture-and-Implementation.v4.en.md)。
9. [文档生命周期规范](development/DOCUMENT-LIFECYCLE-AND-ARCHIVE-v1.0.zh-CN.md) / [历史归档](archive/README.md)。

## 当前主线状态

**TASK004 overall status = IN PROGRESS。**

```text
Synthea generation          PASS
Landing publication         PASS
Generic lineage resolver    PASS
Control runtime             PASS
Standalone Person           PASS
Standalone Visit            PASS
Batch Reconciliation        PASS / MAINLINE ACCEPTED
Airflow Processing           PASS / MAINLINE ACCEPTED
Airflow upstream ingestion   PASS / STEP03E BUSINESS ACCEPTED
Self-Runner STEP03E finalization   PENDING FINAL CI/MERGE
```

以下是历史 STEP02 Processing 正式主线验收（STEP03E 新结果见上方新增 Closeout）：

~~~text
Healthcare main = 5e043b8f00d89a01b72ae6264f35903ceff93de9
DAG = task004_processing_pipeline
Airflow = 3.2.2
Kubernetes provider = 10.17.1

Self-Runner live Run = 38311805385
Artifact = 11775098927
Digest = sha256:570901ce456778457fecc3a1c718ea88aa9ea9dafe8281028e917b3f678cf0ed

Person    success
Visit     success
Reconcile success
DAG run   success

Successful SparkApplication residual = NO
Successful control Pod residual       = NO
PostgreSQL mutation                    = NO
~~~

Post-merge git-sync exact source、default unpaused 和 runtime unpaused 均已再次验证 PASS。

Batch Reconciliation 已完成正式主线验收：

```text
Healthcare PR #24
tested PR HEAD = ee16f5265b0ebb8c30e7e65ec665215613956e77
Healthcare merge/main = 91d96f436e7697d70025cc1c9a045ecfb20f41b1

Self-Runner pre-merge Run  = 38287060452
Self-Runner post-merge Run = 38287401518
Self-Runner PR #31 merge   = 8ab26784cd0229cce96989e3691c122049e3c23a
```

两个真实 Spark reconciliation 都 PASS；20 Patient、2459 Encounter、0 orphan；Processing/PostgreSQL 均无 mutation；成功临时 K8s 资源独立确认已清理。

测试期 Candidate Status 已按文档治理规则原文归档，不再是 current 状态。

## 当前开发目标：STEP03E 收尾（不是再次开发 upstream ingestion）

**真实 Airflow 业务链已 PASS。** Generate → Landing verified → Person (23) / Visit (3592) → Reconcile：Airflow run `task004-step03e-38324111846` 四个 Task 和 DAG 都 success。原始 GitHub workflow 因后置 XCom 取证返回 failure；独立 post-success Run `38326695107` 已 PASS。

Healthcare main：`d0731df6ce09953e45e0458cd7bd85f0ce4fb60c`。

当前只剩 Self-Runner PR #38 的正式代码整理、最终 CI 验证、merge、post-merge checkpoint，以及 STEP03E 文档一致性修复。**不要重做已经成功的上游业务链，也不要自动重跑会写入新的数据的 Live 验证。** 下一业务阶段未在本次收尾中确定。

## 冲突优先级

- 当前业务进度：`docs/tasks/TASK-STATUS.md`。
- 最新 STEP03E 全链验收：`docs/tasks/TASK-004-AIRFLOW-STEP03E-END-TO-END-CLOSEOUT.md`。
- 历史 STEP02 Airflow Processing 验收：`docs/tasks/TASK-004-AIRFLOW-PROCESSING-ORCHESTRATION-MAINLINE-CLOSEOUT.md`。
- 当前 Reconciliation 验收：`docs/tasks/TASK-004-BATCH-RECONCILIATION-MAINLINE-CLOSEOUT.md`。
- 开发工作流：当前 Operations。
- 业务语义与冻结边界：Contract / 已验收主线 Checkpoint。
- 历史状态：Archive / historical Closeout / GitHub Actions。
- TASK001–TASK003 整体冻结；TASK004 Synthea / Landing / Resolver / Control Runtime / Person / Visit / Reconciliation / STEP02 Processing 均为冻结基线；STEP03E End-to-End 业务验收 PASS，CI 正式收尾单独记录；TASK004 整体仍 IN PROGRESS。
- 新 STEP 默认直接维护 Git canonical source；历史 generator-owned 文件修复仍必须同步 Generator。
