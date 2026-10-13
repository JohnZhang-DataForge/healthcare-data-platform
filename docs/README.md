# Healthcare Data Platform — Agent START HERE（当前有效文档）

> **2026-10-13 架构决议（最高优先级；覆盖本文历史 Airflow generate_publish NEXT）：Synthea 独立 Producer / Airflow 仅按时读取 S3 verified Manifest，完全解耦。** **不是**由 Airflow 向 Synthea 传随机 Seed/人口/州，也**不是** Airflow 运行/重试时重新生成数据。用户要求三套各自独立的 Kubernetes Job/Pod、业务代码/镜像（NEW_ONLY、EXISTING_ONLY、MIXED），只先开发 **NEW_ONLY**（人数随机 1～100，随机州、Seed、当次日期）；Synthea 在 worker01 / dw-synthea 使用待验证的**专用 LocalPath 磁盘/PVC**保存自身恢复状态，发布后 SeaweedFS verified Manifest 为数据交换接口。**已批准设计，尚未部署新 Pod/PVC/DAG、未生成新批次或写库。** 下一步只执行 [NEW_ONLY 实施 NEXT](tasks/TASK-004-INDEPENDENT-GENERATOR-NEW-ONLY-NEXT-v1.0.zh-CN.md)，完整设计见 [独立 Generator & Airflow S3 Consumer 架构 v1.0](architecture/TASK-004-INDEPENDENT-SYNTHEA-GENERATORS-AND-AIRFLOW-CONSUMER-v1.0.zh-CN.md)。历史 STEP03E 的四任务 DAG 和旧 CDM 计划原样保留为验收证据，绝不当作新架构已实现；**TASK004 IN PROGRESS、TASK005 ON HOLD**。


> **2026-10-13 最新技术排查：Synthea Seed / Reference Date Source ID 冲突根因已通过真实 READ-ONLY AUDIT 验证。** 见 [根因验收文档](tasks/TASK-004-STEP04F-SYNTHEA-SEED-REFERENCE-DATE-ROOTCAUSE-READONLY-CLOSEOUT.md) 和 [Self-Runner Run 38447127571](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38447127571)。两批 23 人的 seed/clinician_seed 均为 `20261012`，唯一不同的生成入参是 reference_date（20261012→20261013）；原始 23/23 Patient Id 完全重合，23/23 BIRTHDATE 恰好 +1 天；OMOP 只在 23 人的 `birth_datetime` / `day_of_birth` 存在漂移。**新 NEXT = 明确跨批次 Seed/Source ID 与 batch replay 固定 Reference Date 策略；不是重新调查、不是新批次运行。Person Writer 继续 BLOCKED，不允许 COMMIT；TASK005 ON HOLD。**下文旧 NEXT 段落保留为历史说明。


> **2026-10-13 最新进度：STEP04F Person Source-ID READONLY AUDIT = PASS。** [实时证据 Closeout](tasks/TASK-004-STEP04F-PERSON-SOURCE-ID-READONLY-RECONCILIATION-CLOSEOUT.md)：Self-Runner [Run 38435544614](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38435544614) SUCCESS；新批次 23 个 Source ID 全部存在于 mapping、相同 Person=0、不同 Person=23、新 Person=0、dangling=0；失败批次 ledger/stage/commit=0/0/0。Self-Runner [PR #69](https://github.com/JohnZhang-DataForge/Self-Runner/pull/69) 已合并。**目前唯一 NEXT = 下一轮审查 Synthea Seed / Reference Date 与 Source ID 批次隔离策略（仍需单独授权）；禁止 Writer COMMIT、禁止开始 TASK005。**下文旧“修复只读审计”和 STEP04A NEXT 均为历史记录。

> **2026-10-13 当前状态更新：先读 [TASK004 最新 Agent 交接](tasks/TASK-004-AGENT-HANDOFF-CURRENT-2026-10-13.zh-CN.md)。** 新 Synthea 全流程已 PASS（Person 23/Visit 3588），新批次 Person Writer 因 EXISTING_TARGET_DRIFT 正确拒绝；最新只读审计 Run 38434861465 因 Python 模块路径错误 FAILURE。**唯一 NEXT = 修复只读审计并得出 Source ID overlap 汇总；本文后面旧“STEP04A NEXT”已过时，不是新 Agent 的开工点。**


> **CURRENT / 2026-10-12 EDT（2026-10-13 UTC 审计）**。本目录是新 Agent 的唯一文档入口。历史资料移入 `docs/archive/YYYY-MM-DD[-topic]/`，**不要将 Archive 的 NEXT / Candidate / Pilot 状态当成当前状态**。

## 按顺序阅读

1. [当前 TASK 状态与下一步](tasks/TASK-STATUS.md)：当前主线真实完成什么、下一步是什么。
2. [TASK004 Person/Visit OMOP 入库与同批次幂等实施计划](tasks/TASK-004-OMOP-CDM-INTEGRATION-AND-IDEMPOTENCY-PLAN-v1.0.zh-CN.md)：**当前唯一 NEXT = STEP04A READ ONLY**，提供 Agent 可直接开工的步骤、风险、验收矩阵和 DB 安全门槛。
3. [TASK004 MVP 历史 Final Closeout](tasks/TASK-004-FINAL-CLOSEOUT.md)：真实 DAG/Runner 验收、三轮只读集群审计、关闭边界与未执行项。
4. [TASK005 Condition 开发方案 v1.0](tasks/TASK-005-CONDITION-DEVELOPMENT-PLAN-v1.0.zh-CN.md)：下一业务任务的设计基线、Processing/DB 分段授权与 STEP00 唯一开工入口。
5. [STEP03E End-to-End Acceptance](tasks/TASK-004-AIRFLOW-STEP03E-END-TO-END-CLOSEOUT.md)：Synthea→Landing→Person/Visit→Reconcile；本次正式验收。
6. [TASK004 Airflow Processing Orchestration Mainline Closeout](tasks/TASK-004-AIRFLOW-PROCESSING-ORCHESTRATION-MAINLINE-CLOSEOUT.md)：GitHub → git-sync → Airflow → Person/Visit → Reconcile 正式主线验收。
7. [TASK004 Batch Reconciliation Mainline Closeout](tasks/TASK-004-BATCH-RECONCILIATION-MAINLINE-CLOSEOUT.md)：Reconciliation 正式主线验收证据。
8. [正式双仓库开发操作手册](development/PLATFORM-DEVELOPMENT-OPERATIONS-v1.0.zh-CN.md)：Healthcare feature PR → exact SHA → Self-Runner / ARC → PASS → Merge → post-merge validation → Checkpoint。
9. [Agent 开发 Skill](skill/SKILL-cn.md)：一步一验、canonical source、数据安全、Git 与文档治理。
10. [通用开发经验](runbooks/development-lessons-cn.md) 与 [TASK004 专项经验](runbooks/development-lessons-task004-cn.md)。
11. [当前总架构（中文）](architecture/Healthcare-Data-Platform-Architecture-and-Implementation.v4.zh-CN.md) / [English](architecture/Healthcare-Data-Platform-Architecture-and-Implementation.v4.en.md)。
12. [文档生命周期规范](development/DOCUMENT-LIFECYCLE-AND-ARCHIVE-v1.0.zh-CN.md) / [历史归档](archive/README.md)。

## 当前主线状态

**TASK004 overall status = IN PROGRESS（完整 OMOP 入库闭环）**。原 STEP03E Processing MVP 仍 COMPLETE/FROZEN，历史人工只读集群审计见 [`TASK-004-FINAL-CLOSEOUT.md`](tasks/TASK-004-FINAL-CLOSEOUT.md)；但 **Airflow 同批次 Person + Visit PostgreSQL CDM 入库、数据库对账与同批次幂等重放尚未完成**。当前唯一 NEXT 是 [TASK004 STEP04A READ-ONLY PRE-FLIGHT](tasks/TASK-004-OMOP-CDM-INTEGRATION-AND-IDEMPOTENCY-PLAN-v1.0.zh-CN.md)。TASK005 Condition ON HOLD。

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

## TASK004 当前完整流程新定义（后续执行请先看这里）

- 用户正式完成标准：Synthea → verified Landing → Person/Visit Processing → **PostgreSQL OMOP Person/Visit 入库** → 独立数据库 Reconciliation；**相同 batch_id/manifest SHA replay、失败恢复逻辑上幂等**。
- **TASK004 原 STEP03E 已验收，仅 Processing MVP CLOSED，不能当作完整 CDM 终验**。旧 DB 的 Person=113、Visit=5799 是独立历史数据，不能算此次 Airflow 23/3592 已入库。
- 新计划：[`TASK-004-OMOP-CDM-INTEGRATION-AND-IDEMPOTENCY-PLAN-v1.0.zh-CN.md`](tasks/TASK-004-OMOP-CDM-INTEGRATION-AND-IDEMPOTENCY-PLAN-v1.0.zh-CN.md)，STEP04A–04H，**只授权 STEP04A 只读盘点**。任何新的 PG/S3/K8s mutation 或 Live Run 必须另行明确批准；禁止原样重跑旧 TASK003 一次性加载脚本。
- **TASK005 Condition 设计保留但 ON HOLD**；直到 TASK004 CDM 入库与重放验收真正 PASS。

## 历史 STEP03E Processing MVP 验收证据与新目标衔接

**真实 Airflow 业务链已 PASS。** Generate → Landing verified → Person (23) / Visit (3592) → Reconcile：Airflow run `task004-step03e-38324111846` 四个 Task 和 DAG 都 success。原始 GitHub workflow 因后置 XCom 取证返回 failure；独立 post-success Run `38326695107` 已 PASS。

STEP03E **当时验收的 Healthcare 源码 SHA**：`d0731df6ce09953e45e0458cd7bd85f0ce4fb60c`。当前 `main` 可以继续前进，新 Agent 须实时查询 GitHub HEAD，不能把此历史 SHA 当成今天的 `main`。

Self-Runner PR #38 已合并到 main（`6f72c05ad8eb1a0abeb19f3cff9e89ac698cff87`），post-merge 只读 Run `38328600074` 已 PASS；Self-Runner PR #39 的历史只读 SHA gate 修复亦已合并，post-merge Run `38329852476` = SUCCESS。本 STEP03E 收尾已包含 Self-Runner 正式验证与文档归档；TASK004 Final Audit 又确认 Airflow Metadata、git-sync 源码、成功运行资源清理及 `dw-seaweedfs` S3 健康，**在原限定 Processing MVP 范围内历史关闭**，见 [MVP Final Closeout](tasks/TASK-004-FINAL-CLOSEOUT.md)。**Phase E 的第一实体已确定为 TASK005 Condition，设计与分步验收方案已形成；实施尚未开始**。历史讨论当时将 TASK005 STEP00 视为 NEXT，**已被当前 TASK004 CDM 计划取代**；现在 TASK005 ON HOLD，不授权自行生成 batch、写 Processing 或写 PostgreSQL。**不要重做已经成功的上游业务链，也不要自动重跑会写入新的数据的 Live 验证。** 下一步按当前 TASK-STATUS 和 TASK004 CDM 计划的 STEP04A 只读预检执行。

## 冲突优先级

- 当前业务进度：`docs/tasks/TASK-STATUS.md`。
- **当前 TASK004 真实剩余工作与唯一 NEXT**：`docs/tasks/TASK-004-OMOP-CDM-INTEGRATION-AND-IDEMPOTENCY-PLAN-v1.0.zh-CN.md`。
- TASK004 原限定 Processing MVP 验收及历史边界：`docs/tasks/TASK-004-FINAL-CLOSEOUT.md`。
- TASK005 Condition 受控开发设计（**ON HOLD，不是当前 NEXT**）：`docs/tasks/TASK-005-CONDITION-DEVELOPMENT-PLAN-v1.0.zh-CN.md`。
- 最新 STEP03E 全链验收：`docs/tasks/TASK-004-AIRFLOW-STEP03E-END-TO-END-CLOSEOUT.md`。
- 历史 STEP02 Airflow Processing 验收：`docs/tasks/TASK-004-AIRFLOW-PROCESSING-ORCHESTRATION-MAINLINE-CLOSEOUT.md`。
- 当前 Reconciliation 验收：`docs/tasks/TASK-004-BATCH-RECONCILIATION-MAINLINE-CLOSEOUT.md`。
- 开发工作流：当前 Operations。
- 业务语义与冻结边界：Contract / 已验收主线 Checkpoint。
- 历史状态：Archive / historical Closeout / GitHub Actions。
- TASK001–TASK003 整体冻结；TASK004 Synthea / Landing / Resolver / Control Runtime / Person / Visit / Reconciliation / STEP02 Processing 均为冻结基线；STEP03E End-to-End 业务验收 PASS，CI 正式收尾单独记录；TASK004 既定 Processing MVP **COMPLETE / CLOSED / FROZEN**；**TASK004 按新明确目标的整体 CDM 入库/幂等闭环仍 IN PROGRESS**。
- 新 STEP 默认直接维护 Git canonical source；历史 generator-owned 文件修复仍必须同步 Generator。
