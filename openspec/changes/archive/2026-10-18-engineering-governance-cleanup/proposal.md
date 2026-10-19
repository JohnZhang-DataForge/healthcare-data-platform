# Proposal

## Why

OpenSpec Change Gate 已通过真实 Ruleset [#25365902](https://github.com/JohnZhang-DataForge/healthcare-data-platform/rules/25365902) 与正反 PR #233/#234 验证，但 `documents/engineering/` 和 `documents/README.md` 仍将 2026-10-16/18 的 G0–G7 Bootstrap 计划作为当前实施任务来源；部分页面还声称 G5 未开始、本地业务源码未迁移、Current Changes 仍为空。重叠的 Engineering 执行计划与 Active OpenSpec Changes 将误导新 Session。

## What Changes

- 明确单一职责：`AGENTS.md` 为 AI 入口；`documents/` 持有长期架构/组件/运维/开发规范，`PROJECT-STATUS.md` 只汇总跨项目当前状态；`openspec/changes/` 唯一管理每项实质性变更的 Proposal/Design/Tasks/验收；`openspec/specs/` 仅放经采用且可验证的行为要求；GitHub PR/Run/源码记录事实。
- 审计 Engineering 19 个 Markdown 的权威边界；保留永久规则、技术地图和历史证据，不删除固定 SHA 的审计材料。
- 将旧 `OPENSPEC-IMPLEMENTATION-PLAN.md` 和文档迁移状态降为**历史 Bootstrap/迁移记录**，不再继续作为 G5/G6 当前 Tasks；保留原始 G0–G4、PR、Run、失败、计划与实际偏差。
- 将尚未开始的 Legacy Task 命名代码重构 R2–R5 作为**独立待审批实施**的 OpenSpec Change，不偷并到已存在的物理路径迁移 Change；旧计划保留历史静态清单并清楚标注源路径为迁移前快照。
- 修正 README、Agent 入口、OpenSpec config、治理规则、跨项目状态中的过时 CURRENT，链接到真实两个 Active Changes 和正式 Ruleset；不冒充 Runtime 已迁移验收。
- 用受信任 OpenSpec Change Gate、官方 Strict Validation 和文档链接 CI 检查真实 PR；将合并/验收证据写入本 Tasks；完成后单独归档。

## Capabilities

### New Capabilities

无运行能力。这里只治理文档职责、历史溯源和后续需求来源，不引入可观察的新业务系统功能。

### Modified Capabilities

无。本 Change 是 docs-only 治理，不改变既有 OpenSpec/Ruleset 行为，不增加 PR 检查脚本；采用 `skip_specs: true`，不凭空新建 Current Specs。

## Impact

只改 `documents/`、`AGENTS.md`、`openspec/config.yaml` 和新的 `openspec/changes/` 管理文档。**不改或执行**代码、Actions、DAG、Docker、K8s、Spark、PG、S3、Azure/TF、数据回放。不能将旧审计日期的结果当作最新运行 PASS。
