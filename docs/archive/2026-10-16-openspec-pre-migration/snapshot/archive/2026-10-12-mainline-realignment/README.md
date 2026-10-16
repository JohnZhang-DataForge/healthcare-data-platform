# TASK004 Mainline Realignment — Archive Snapshot 2026-10-12

> **ARCHIVED / HISTORICAL SNAPSHOT**。本批次保存 TASK004 主线纠偏前的 current 文档原文，仅用于追溯；当前开发状态请从 `docs/README.md` 开始。

## 1. 归档原因

2026-10-12 对 TASK004 主线边界进行纠偏：

- V8 Visit 被接受为对既有主线代码的真实 runtime validation；
- V9 Batch Reconciliation 的运行证据继续有效，但测试期新增业务实现被降级为 candidate；
- 当前 NEXT 改为 Mainline Reconciliation Candidate Review，而不是 Airflow。

这是当前权威文档的重大语义调整，因此按 Documentation Lifecycle 规则保存修改前快照。

## 2. 来源基线

```text
Repository = JohnZhang-DataForge/healthcare-data-platform
Source main before realignment = 3ff07a76e99630818ffbcbf9777e18d07a26f197
Realignment PR = #21
Realignment merge SHA = 4a08c623dca52d7d43abe0290d989753033ee2ae
Archive snapshot PR = #22
Archive snapshot merge SHA = 03388449f7dbbde2e54ac0ed18fb30dec931da58
```

## 3. 归档映射

| 修改前 current 路径 | 本批次归档路径 |
|---|---|
| `docs/README.md` | `docs/archive/2026-10-12-mainline-realignment/current/README.md` |
| `docs/BASELINE.md` | `docs/archive/2026-10-12-mainline-realignment/current/BASELINE.md` |
| `docs/tasks/TASK-STATUS.md` | `docs/archive/2026-10-12-mainline-realignment/tasks/TASK-STATUS.md` |
| `docs/development/PLATFORM-DEVELOPMENT-OPERATIONS-v1.0.zh-CN.md` | `docs/archive/2026-10-12-mainline-realignment/development/PLATFORM-DEVELOPMENT-OPERATIONS-v1.0.zh-CN.md` |
| `docs/skill/SKILL-cn.md` | `docs/archive/2026-10-12-mainline-realignment/skill/SKILL-cn.md` |
| `docs/runbooks/README.md` | `docs/archive/2026-10-12-mainline-realignment/runbooks/README.md` |

另外，V9 reconciliation closeout 已在 PR #21 中原文移动到：

```text
docs/archive/2026-10-12/tasks/TASK-004-BATCH-RECONCILIATION-CLOSEOUT-V9-TEST-PERIOD.md
```

其 Git blob 与移动前一致。

## 4. 当前替代权威

```text
docs/README.md
docs/tasks/TASK-STATUS.md
docs/tasks/TASK-004-BATCH-RECONCILIATION-CANDIDATE-STATUS.md
docs/development/PLATFORM-DEVELOPMENT-OPERATIONS-v1.0.zh-CN.md
docs/skill/SKILL-cn.md
```

## 5. 阅读警告

本目录是历史快照。不得把其中的：

```text
Batch Reconciliation = PASS
Airflow = NEXT
```

重新当成当前主线状态。

当前状态只服从 current TASK-STATUS 和 Candidate Status。
