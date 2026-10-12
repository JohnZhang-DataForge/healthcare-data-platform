# Healthcare 文档治理首批归档 — 2026-10-12

> **ARCHIVED / HISTORICAL**。本目录保存当时文档原文；其操作说明、`NEXT`、`NOT_DEPLOYED`、Pilot 状态不代表当前事实。当前开发入口：[../../README.md](../../README.md)。

## 1. 归档原因

V8/V9 已验证跨仓库固定 SHA、GitHub Policy、ARC/Kubernetes/Spark 真运行与合并前后验证。旧 GitOps 迁移草案、Runner Pilot、过期交接/状态记录容易误导新 Agent。当前执行以 [正式开发手册](../../development/PLATFORM-DEVELOPMENT-OPERATIONS-v1.0.zh-CN.md) 为准；最新业务状态以 [TASK-STATUS](../../tasks/TASK-STATUS.md) 为准。

## 2. 归档来源

- Repository: `JohnZhang-DataForge/healthcare-data-platform`
- Archive Date: `2026-10-12`
- Source main baseline: `f39abdc45b52cae8e872b5609c65945f5affb843`
- Work branch: `docs/cleanup-current-and-archive-20261012`
- Archive PR / merge SHA: 在本次 PR 合并后，以 GitHub PR 和 commit 记录为准；本文件不预填尚未发生的 SHA。

## 3. 逐文件归档清单

| 原路径（均位于 docs/ 下） | 新路径（均位于本目录下） | 原因/替代入口 |
|---|---|---|
| `migration/HEALTHCARE-GITOPS-MIGRATION-v1.0-zh-CN.md` | `migration/HEALTHCARE-GITOPS-MIGRATION-v1.0-zh-CN.md` | 初期候选方案 → 正式 Operations |
| `migration/HEALTHCARE-GITOPS-MIGRATION-v1.1-zh-CN.md` | `migration/HEALTHCARE-GITOPS-MIGRATION-v1.1-zh-CN.md` | M2 设计稿，状态已过时 → 正式 Operations |
| `migration/M1-CROSS-REPO-READONLY-BASELINE-2026-10-12.zh-CN.md` | `migration/M1-CROSS-REPO-READONLY-BASELINE-2026-10-12.zh-CN.md` | 历史基线审计 → V8/V9 证据 |
| `runbooks/GITHUB-SELF-HOSTED-RUNNER-DEVELOPMENT-V2.zh-CN.md` | `runbooks/GITHUB-SELF-HOSTED-RUNNER-DEVELOPMENT-V2.zh-CN.md` | Pilot 流程被跨仓库模式替代 → 正式 Operations |
| `handoffs/TASK-003-COMPLETION-HANDOFF.md` | `handoffs/TASK-003-COMPLETION-HANDOFF.md` | 旧交接 → TASK003 Final Closeout |
| `handoffs/TASK-004-PHASE10-AFTER-PERSON.md` | `handoffs/TASK-004-PHASE10-AFTER-PERSON.md` | Visit 尚未完成时的快照 → TASK004 Closeout + TASK-STATUS |
| `tasks/TASK-004-PROGRESS-CHECKPOINT-AFTER-PERSON.md` | `tasks/TASK-004-PROGRESS-CHECKPOINT-AFTER-PERSON.md` | 旧 Person 阶段状态 → TASK004 Closeout + TASK-STATUS |
| `tasks/TASK-004-BATCH-RECONCILIATION-PILOT.md` | `tasks/TASK-004-BATCH-RECONCILIATION-PILOT.md` | Runtime 尚未验收时的草稿 → TASK004 Batch Reconciliation Closeout |
| `runbooks/TASK-003-DEVELOPMENT-LESSONS.md` | `runbooks/TASK-003-DEVELOPMENT-LESSONS.md` | 通用经验已在当前 development-lessons-cn.md 中汇总 |
| `runbooks/DEVELOPMENT-LESSONS-STEP04.md` | `runbooks/DEVELOPMENT-LESSONS-STEP04.md` | STEP04 复盘已由当前 General Lessons + STEP04 专项 Lessons 覆盖 |
| `handoffs/HANDOFF-2026-10-09-STEP04.md` | `handoffs/HANDOFF-2026-10-09-STEP04.md` | 旧交接，当前 TASK003 已完整 Closeout |

所有移动文件的正文应逐字与原文相同，保留当时事实；本次更新的现行 Skill、Lessons、Index 另行列为 UPDATE。

## 4. 保留在当前 main 的资料（KEEP / DEFER）

- **KEEP**：`docs/BASELINE.md`、正式开发/归档规范、`docs/skill/SKILL-cn.md`、当前通用和 TASK 专项 Lessons、TASK003 Final Closeout、TASK004 Phase9/Batch Recon Closeout、Contract/冻结记录、`docs/task003/` 的细粒度验收、V4 中英文架构、TASK003 Blueprint。
- **DEFER**：`docs/architecture/Healthcare-ETL-Hybrid-Fabric-ML-Design.zh-CN.v2.1.md`，虽然 V4 是当前总架构，但 v2.1 包含 Azure/Fabric/ML 的独立详细设计；在独有内容纳入现行架构前不贸然归档。
- **KEEP（历史步骤证据）**：`docs/tasks/TASK-003-STEP04-*.md`、`STEP05*.md` 等为具体 Contract/运行证据，不能按“旧”字批量删除。

## 5. 已提炼的当前有效经验

- 现行通用 Lessons：Shell stdin/退出码、`grep -F`、S3 空列表、manifest-last、Run 恢复、幂等、PG Identity/Sequence/COMMIT uncertainty、独立 readback、镜像权限/身份、失败资源保留。
- TASK004 专项 Lessons：Batch/Run 区分、Synthea generator 参数不等于事实、Landing 状态机、控制面/数据面、Airflow 最后编排的业务顺序；**旧 Visit NEXT 已更新为已验证 PASS**。
- Skill：区分旧 Generator 维护与新 GitHub canonical source 直接开发，当前跨仓库 Self-Runner 是正式执行入口。
- TASK-STATUS：为最新 PASS/NEXT 提供唯一索引，旧 Checkpoint 原文不改。

## 6. 引用与验证

- 归档文件正文内容不改；旧 STEP04 Closeout 中的两个原始链接将只更新**文档路径**指向本批次归档（不修改业务验收结果）。
- 当前文档如需引用旧历史，请使用 `docs/archive/2026-10-12/...` 路径。
- 验收必须核对每个归档文件原始/新内容相同、所有原路径已移除、当前入口有效、当前状态没有旧 `NEXT` 误导、变更仅限 `docs/`、没有业务/Workflow/运行环境修改。
