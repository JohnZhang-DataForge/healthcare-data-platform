# Healthcare Data Platform — Agent START HERE（当前有效文档）

> **CURRENT / 2026-10-12 / MAINLINE REALIGNED**。本目录是新 Agent 的唯一文档入口。历史资料移入 `docs/archive/YYYY-MM-DD/`，**不要将 Archive 的 NEXT/NOT_DEPLOYED/Pilot 当成当前状态**。

## 按顺序阅读（先读这些就可以开始）

1. [当前 TASK 状态与下一步](tasks/TASK-STATUS.md)：当前主线真实完成什么、哪些只是测试期 candidate、下一步正式开发什么。
2. [TASK004 Reconciliation Candidate Status](tasks/TASK-004-BATCH-RECONCILIATION-CANDIDATE-STATUS.md)：解释 V9 reconciliation 为什么保留代码和运行证据、但暂不作为主线正式验收。
3. [正式双仓库开发操作手册](development/PLATFORM-DEVELOPMENT-OPERATIONS-v1.0.zh-CN.md)：Healthcare feature PR → Self-Runner 手工绑定 PR/SHA → ARC → PASS → Merge → Checkpoint。
4. [Agent 开发 Skill](skill/SKILL-cn.md)：一步一验、canonical source、Shell、Generator 边界、数据安全与 Git。
5. [通用开发经验](runbooks/development-lessons-cn.md)：已知坑、数据库与 Spark/Kubernetes 的恢复原则。
6. [专项经验导航](runbooks/README.md)：当前 TASK 所需的详细事故案例与专项经验。
7. [当前总架构（中文）](architecture/Healthcare-Data-Platform-Architecture-and-Implementation.v4.zh-CN.md) / [English](architecture/Healthcare-Data-Platform-Architecture-and-Implementation.v4.en.md)：设计和未来 Roadmap；运行状态以 TASK-STATUS 为准。
8. [文档生命周期规范](development/DOCUMENT-LIFECYCLE-AND-ARCHIVE-v1.0.zh-CN.md) / [历史归档](archive/README.md)。

## 当前主线状态

**TASK004 overall status = IN PROGRESS。**

当前唯一业务开发主线是本仓库正式 TASK004 主线。测试 Self-Runner / ARC 开发流程期间产生的执行证据可以用于验证既有主线代码，但**测试期间新增的业务实现不能自动升级为主线已验收功能**。

```text
Synthea generation          PASS
Landing publication         PASS
Generic lineage resolver    PASS
Control runtime             PASS
Standalone Person           PASS
Standalone Visit            PASS
Batch Reconciliation        CANDIDATE / NOT MAINLINE ACCEPTED
Airflow orchestration       NOT YET
```

### Visit 为什么可以接受

Self-Runner V8 Run `38250467965` 真实执行既有 `scripts/task004/05e-run-visit-canonical.sh`。V8 绑定 Healthcare SHA `40f9c37a303b95330a503ba69b99e5fc7014aca6`；从原主线文档 checkpoint `5c8677e2c46bea6eda0576d4c63c2612f599ff1a` 到该 SHA 没有 Healthcare 业务代码变化，Visit runner Git blob 与当前 main 也一致。

因此 V8 是**对既有主线 Visit implementation 的真实 runtime validation**，不是新的业务开发。

### Reconciliation 为什么暂不接受

V9 期间新增了 Healthcare 业务实现：

```text
scripts/task004/05f-reconcile-person-visit.sh
spark/apps/task004/reconcile_person_visit.py
spark/manifests/task004/person-visit-reconciliation.yaml.tpl
tests/task004/test_person_visit_reconciliation_source.py
```

V9 的 PR、Actions Run 和 PASS 结果作为**真实历史证据**保留，但主线必须先 review / adopt / modify / revalidate 这组 candidate implementation，之后才能升级为 MAINLINE PASS。

## 当前开发目标

**TASK004 下一步：Mainline Batch Reconciliation review / acceptance。**

```text
review current reconciliation candidate
→ decide adopt / modify
→ use feature-PR + exact-SHA + Self-Runner flow
→ real reconciliation validation
→ mainline checkpoint
→ only then start Airflow orchestration
```

不要重新开发已经验证的 Visit；也不要直接跳到 Airflow。

## 冲突优先级

- 当前业务进度：`docs/tasks/TASK-STATUS.md`。
- 当前 reconciliation 地位：`docs/tasks/TASK-004-BATCH-RECONCILIATION-CANDIDATE-STATUS.md`。
- 开发工作流：当前 Operations。
- 业务语义与冻结边界：对应 Contract / 已验收主线 Checkpoint。
- 历史运行证据：Archive / 历史 Closeout / GitHub Actions。
- TASK001–TASK003 整体冻结；TASK004 **已验收阶段**冻结，TASK004 整体仍 IN PROGRESS。
- 新 STEP 默认直接维护 Git canonical source；依赖旧 Generator 的历史文件修复仍必须同步 Generator。
- **不要为了“更像生产 CI/CD”而延迟业务开发。** 只有真实 STEP 被阻塞时才最小调整 Self-Runner。
