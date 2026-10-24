---
status: historical
scope: legacy-docs-historical-snapshot
last_verified: 2026-10-16
snapshot_sha: 49936b51d4beadc69383e931efc3e72d2f0db47e
---

# Legacy `docs/` — Git 历史快照（已从 Main 清理）

**删除的只是 Main 上的旧目录，不是历史证据。** 原 `docs/` 在 Main 的最后完整快照包含 **111 个 Git Tracked 文件**（约 **1,006,300 bytes**），全部可通过 GitHub 的固定 Commit 浏览：

- **[浏览完整旧 docs 快照](https://github.com/JohnZhang-DataForge/healthcare-data-platform/tree/49936b51d4beadc69383e931efc3e72d2f0db47e/docs)**
- **[TASK004 NEW_ONLY 最终真实 E2E 验收](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md)** — PG COMMIT、独立读回、完成批次 SKIP。
- **[Condition STEP00 旧方案](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-005-CONDITION-DEVELOPMENT-PLAN-v1.0.zh-CN.md)** — 设计和历史计划，非当前授权。
- **[Portal Spark A4 Smoke 验收](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/A4-SPARK-OPENLINEAGE-REAL-SMOKE-2026-10-14.zh-CN.md)** — 独立 Spark 完成、原 Workflow FAIL、后续只读核验。
- **[Azure/Fabric Terraform Plan-only 证据](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/azure-fabric/AZURE-ONELAKE-INFRA-PLAN-ONLY-2026-10-15.md)** — Plan PASS，不是 Apply。
- **[旧开发经验与故障记录](https://github.com/JohnZhang-DataForge/healthcare-data-platform/tree/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/runbooks)** — 按原始日期保留。

- **[旧 `SKILL-cn.md` 完整原文](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/skill/SKILL-cn.md)** — 仅供历史查证；原 [PR #202 的 35 章审计](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/664dfed06a206ff20822a118c8f04771a307452b/documents/engineering/migration/LEGACY-SKILL-COVERAGE-AUDIT.md) 已存 Git 历史，不维护为当前 Agent 规则。

**永久链接规则**：若历史文件路径为 `docs/xxx/file.md`，使用

```text
https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/xxx/file.md
```

目录链接使用 `/tree/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/xxx/`；只应阅读/审计，**不从该历史树复制过时 `CURRENT/NEXT`、`scripts/taskNNN` 和旧 Warehouse-first 指令到新代码或 OpenSpec**。

## 当前权威入口

- [AGENTS.md](../../../AGENTS.md) → [documents/README.md](../../README.md) → [PROJECT-STATUS](../status/PROJECT-STATUS.md)
- 新代码按 [Component-first Naming](../development/CODE-ORGANIZATION-AND-NAMING.md)；共享运行按 [Session Coordination](../development/SESSION-COORDINATION.md)。
- `documents/` 保留稳定的架构、组件、运维、安全和决策；**不要重新创建 `docs/` 或 `docs/archive/`**。
- [OpenSpec Readiness](OPENSPEC-READINESS.md)：当时的旧 PR #164 修订要求属于历史准备事项，当前 OpenSpec 已初始化且正式接入 Main Required CI，不是需要再次初始化的待办。

**Git 历史保存策略与长期取舍**：快照 Commit `49936b51d4beadc69383e931efc3e72d2f0db47e` 是当时 Main 的祖先，删除当前目录不会删除 Git 的祖先提交。仓库被永久删除、历史被特殊重写或访问权限改变则另当别论。若将来需要独立归档，可再迁移到用户已有的 Healthcare-Specs 仓库；本次不对另一仓库做复制/写入。
