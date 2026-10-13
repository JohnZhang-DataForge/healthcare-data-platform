# Healthcare Data Platform — Agent START HERE（当前有效文档）

> **CURRENT / 2026-10-12 EDT（2026-10-13 UTC 审计）**。本目录是新 Agent 的唯一文档入口。历史资料移入 `docs/archive/YYYY-MM-DD[-topic]/`，**不要将 Archive 的 NEXT / Candidate / Pilot 状态当成当前状态**。

## 按顺序阅读

1. [当前 TASK 状态与下一步](tasks/TASK-STATUS.md)：当前主线真实完成什么、下一步是什么。
2. [TASK004 Final Closeout](tasks/TASK-004-FINAL-CLOSEOUT.md)：真实 DAG/Runner 验收、三轮只读集群审计、关闭边界与未执行项。
3. [TASK005 Condition 开发方案 v1.0](tasks/TASK-005-CONDITION-DEVELOPMENT-PLAN-v1.0.zh-CN.md)：下一业务任务的设计基线、Processing/DB 分段授权与 STEP00 唯一开工入口。
4. [STEP03E End-to-End Acceptance](tasks/TASK-004-AIRFLOW-STEP03E-END-TO-END-CLOSEOUT.md)：Synthea→Landing→Person/Visit→Reconcile；本次正式验收。
5. [TASK004 Airflow Processing Orchestration Mainline Closeout](tasks/TASK-004-AIRFLOW-PROCESSING-ORCHESTRATION-MAINLINE-CLOSEOUT.md)：GitHub → git-sync → Airflow → Person/Visit → Reconcile 正式主线验收。
6. [TASK004 Batch Reconciliation Mainline Closeout](tasks/TASK-004-BATCH-RECONCILIATION-MAINLINE-CLOSEOUT.md)：Reconciliation 正式主线验收证据。
7. [正式双仓库开发操作手册](development/PLATFORM-DEVELOPMENT-OPERATIONS-v1.0.zh-CN.md)：Healthcare feature PR → exact SHA → Self-Runner / ARC → PASS → Merge → post-merge validation → Checkpoint。
8. [Agent 开发 Skill](skill/SKILL-cn.md)：一步一验、canonical source、数据安全、Git 与文档治理。
9. [通用开发经验](runbooks/development-lessons-cn.md) 与 [TASK004 专项经验](runbooks/development-lessons-task004-cn.md)。
10. [当前总架构（中文）](architecture/Healthcare-Data-Platform-Architecture-and-Implementation.v4.zh-CN.md) / [English](architecture/Healthcare-Data-Platform-Architecture-and-Implementation.v4.en.md)。
11. [文档生命周期规范](development/DOCUMENT-LIFECYCLE-AND-ARCHIVE-v1.0.zh-CN.md) / [历史归档](archive/README.md)。

## 当前主线状态

**TASK004 overall status = COMPLETE / CLOSED / FROZEN。** 最终人工只读集群审计与证据见 [`TASK-004-FINAL-CLOSEOUT.md`](tasks/TASK-004-FINAL-CLOSEOUT.md)。

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
Self-Runner STEP03E validation   PASS / MAINLINE MERGED
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

## 当前正式状态与下一业务阶段入口

**真实 Airflow 业务链已 PASS。** Generate → Landing verified → Person (23) / Visit (3592) → Reconcile：Airflow run `task004-step03e-38324111846` 四个 Task 和 DAG 都 success。原始 GitHub workflow 因后置 XCom 取证返回 failure；独立 post-success Run `38326695107` 已 PASS。

STEP03E **当时验收的 Healthcare 源码 SHA**：`d0731df6ce09953e45e0458cd7bd85f0ce4fb60c`。当前 `main` 可以继续前进，新 Agent 须实时查询 GitHub HEAD，不能把此历史 SHA 当成今天的 `main`。

Self-Runner PR #38 已合并到 main（`6f72c05ad8eb1a0abeb19f3cff9e89ac698cff87`），post-merge 只读 Run `38328600074` 已 PASS；Self-Runner PR #39 的历史只读 SHA gate 修复亦已合并，post-merge Run `38329852476` = SUCCESS。本 STEP03E 收尾已包含 Self-Runner 正式验证与文档归档；TASK004 Final Audit 又确认 Airflow Metadata、git-sync 源码、成功运行资源清理及 `dw-seaweedfs` S3 健康，正式关闭，见 [Final Closeout](tasks/TASK-004-FINAL-CLOSEOUT.md)。**Phase E 的第一实体已确定为 TASK005 Condition，设计与分步验收方案已形成；实施尚未开始**。当前 NEXT 仅是 TASK005 STEP00 的只读预检，不授权自行生成 batch、写 Processing 或写 PostgreSQL。**不要重做已经成功的上游业务链，也不要自动重跑会写入新的数据的 Live 验证。** 下一阶段具体步骤请以 TASK005 Condition 正式计划和 TASK-STATUS 为准。

## 冲突优先级

- 当前业务进度：`docs/tasks/TASK-STATUS.md`。
- TASK004 全任务正式验收及已知边界：`docs/tasks/TASK-004-FINAL-CLOSEOUT.md`。
- TASK005 Condition 受控开发设计与唯一 NEXT：`docs/tasks/TASK-005-CONDITION-DEVELOPMENT-PLAN-v1.0.zh-CN.md`。
- 最新 STEP03E 全链验收：`docs/tasks/TASK-004-AIRFLOW-STEP03E-END-TO-END-CLOSEOUT.md`。
- 历史 STEP02 Airflow Processing 验收：`docs/tasks/TASK-004-AIRFLOW-PROCESSING-ORCHESTRATION-MAINLINE-CLOSEOUT.md`。
- 当前 Reconciliation 验收：`docs/tasks/TASK-004-BATCH-RECONCILIATION-MAINLINE-CLOSEOUT.md`。
- 开发工作流：当前 Operations。
- 业务语义与冻结边界：Contract / 已验收主线 Checkpoint。
- 历史状态：Archive / historical Closeout / GitHub Actions。
- TASK001–TASK003 整体冻结；TASK004 Synthea / Landing / Resolver / Control Runtime / Person / Visit / Reconciliation / STEP02 Processing 均为冻结基线；STEP03E End-to-End 业务验收 PASS，CI 正式收尾单独记录；TASK004 整体在既定 Processing-first Airflow MVP 范围内已 **COMPLETE / CLOSED / FROZEN**（数据库新批次入库不在范围内）。
- 新 STEP 默认直接维护 Git canonical source；历史 generator-owned 文件修复仍必须同步 Generator。
