# 历史开发经验 / Runbooks 索引

> **STEP08 权威切换（2026-10-16）：历史开发经验索引。** 当前运维安全和检查规范以 [Operations](../../documents/operations/README.md)、[Safe Operations](../../documents/operations/SAFE-OPERATIONS.md)、[Agent Rules](../../documents/development/AGENT-RULES.md) 为准；本页下方 TASK004 Airflow NEXT、按 TASK 编号新增脚本等属于历史做法，不能作为当前执行指令。


> **新 Agent**：先读 [通用开发经验](development-lessons-cn.md)，再按当前 TASK 阅读必要的专项经验。历史 Pilot/过时迁移方案见 [归档索引](https://github.com/JohnZhang-DataForge/Healthcare-Specs/tree/main/archive)。

| 文档 | 何时阅读 |
|---|---|
| [development-lessons-cn.md](development-lessons-cn.md) | 每个新 TASK：Shell、S3、PostgreSQL、幂等、恢复、K8s、镜像、Git 的跨任务经验 |
| [development-lessons-task003-step04-cn.md](development-lessons-task003-step04-cn.md) | Raw/S3 发布、manifest、幂等重放和原始故障细节 |
| [development-lessons-task003-step06-cn.md](development-lessons-task003-step06-cn.md) | OMOP CDM、Sequence、事务不确定性、ID allocation |
| [development-lessons-task004-cn.md](development-lessons-task004-cn.md) | TASK004 Generator、Landing、Control runtime、Spark、Reconciliation，以及进入 Airflow 前后的专项经验 |

历史 Lessons 只记录发生时的背景；**当前 TASK 进度以 [PROJECT-STATUS](../../documents/status/PROJECT-STATUS.md) 为准**；旧 [TASK-STATUS](../tasks/TASK-STATUS.md) 保留阶段性历史。

TASK004 历史阶段快照（非当前）：

```text
Standalone Person      = PASS
Standalone Visit       = PASS
Batch Reconciliation   = PASS / MAINLINE ACCEPTED
Airflow                = NEXT / NOT YET VERIFIED
```

正式 Reconciliation 证据见：

```text
../tasks/TASK-004-BATCH-RECONCILIATION-MAINLINE-CLOSEOUT.md
```

历史 Candidate / V9 test-period evidence 已归档。

历史依赖 Generator 的修复必须同步 Generator，但**新 STEP 默认直接维护 GitHub 中的 canonical source**。
