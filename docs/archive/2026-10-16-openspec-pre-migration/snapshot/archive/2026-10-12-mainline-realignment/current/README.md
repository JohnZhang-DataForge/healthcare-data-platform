# Healthcare Data Platform — Agent START HERE（当前有效文档）

> **CURRENT / 2026-10-12**。本目录是新 Agent 的唯一文档入口。历史资料移入 `docs/archive/YYYY-MM-DD/`，**不要将 Archive 的 NEXT/NOT_DEPLOYED/Pilot 当成当前状态**。

## 按顺序阅读（先读这些就可以开始）

1. [当前 TASK 状态与下一步](tasks/TASK-STATUS.md)：当前已完成什么、下一步 Airflow 需要做什么、对应验收 SHA/Run。
2. [正式双仓库开发操作手册](development/PLATFORM-DEVELOPMENT-OPERATIONS-v1.0.zh-CN.md)：Healthcare feature PR → Self-Runner 手工绑定 PR/SHA → ARC → PASS → Merge → Checkpoint。
3. [Agent 开发 Skill](skill/SKILL-cn.md)：一步一验、源码、Shell、Generator 边界、数据安全与 Git。
4. [通用开发经验](runbooks/development-lessons-cn.md)：已知坑、数据库与 Spark/Kubernetes 的恢复原则。
5. [专项经验导航](runbooks/README.md)：当前 TASK 所需的详细事故案例。
6. [当前总架构（中文）](architecture/Healthcare-Data-Platform-Architecture-and-Implementation.v4.zh-CN.md) / [English](architecture/Healthcare-Data-Platform-Architecture-and-Implementation.v4.en.md)：设计和未来 Roadmap；运行状态以 TASK-STATUS 为准。
7. [文档生命周期规范](development/DOCUMENT-LIFECYCLE-AND-ARCHIVE-v1.0.zh-CN.md) / [历史归档](archive/README.md)。

## 当前开发目标

**TASK004 下一步：Airflow orchestration**。Synthea / Landing / Resolver / standalone Person / standalone Visit / batch reconciliation 已验收；不要重做。先读 [TASK004 Reconciliation Closeout](tasks/TASK-004-BATCH-RECONCILIATION-CLOSEOUT.md)、[Phase9 Closeout](tasks/TASK-004-PHASE9-CLOSEOUT.md) 和实际源码、Contract，再从一个有界 Airflow STEP 开始。每次开发前重新查询两个仓库当前 `main` 与运行态。

## 冲突优先级

- 开发工作流：当前 Operations；业务语义与冻结边界：对应 Contract；进度：最新真实 Checkpoint/Closeout；历史背景：Archive。
- TASK001–TASK003 冻结资产不擅自改；新 STEP 默认直接维护 Git canonical source；依赖旧 Generator 的修复必须同步 Generator。
- **不要为了“更像生产 CI/CD”而延迟业务开发。** 只有真实 STEP 被阻塞时才最小调整 Self-Runner。
