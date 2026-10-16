---
status: reviewed
scope: openspec-migration-preparation
last_verified: 2026-10-16
source_sha: d1962f79e1c7337c372de1aebfaaec87dfc7d1c8
---

# OpenSpec 迁移准备 — STEP08/STEP09 Gate

> **STEP08 终审完成后的准备清单，不是 OpenSpec 初始化记录。** 正式采用 OpenSpec 管后续变更与 Agent 接力的方向已确认，但已核验的 Main 仍**没有 `openspec/`**；没有运行 OpenSpec CLI/npm，也没有为此触发业务或云端 Workflow。[最终文档权威终审](FINAL-DOCUMENTATION-AUDIT.md)。

## 1. 最小职责分配

| 系统 | 负责 | 不负责 |
| --- | --- | --- |
| [`documents/`](../README.md) | 稳定架构、组件、运维、命名/安全、历史决策 | 不为每个任务/Session 存一份 CURRENT 文档 |
| `openspec/specs/`（未来） | **实际行为的**可验证需求 / 验收场景 | 不将 Azure/Portal 规划写成已上线功能 |
| `openspec/changes/`（未来） | Proposal / Design / Delta Specs / Tasks / 验证与归档 | 不当作分布式运行锁或业务 COMMIT 证据 |
| GitHub PR/Issue + Self-Runner | 多分支代码审查、准确 SHA、Run/Artifacts | 不能仅凭 CI SUCCESS 宣称 PG/Delta 实际验收 |
| [Session Coordination](../development/SESSION-COORDINATION.md) | 共享 Spark/Airflow/PG/K8s/Azure 的人工协调与前置 Gate | 不提供完整自动 Agent 调度或无条件并发锁 |

## 2. 旧 OpenSpec Bootstrap PR 的冲突

检查时 [PR #164](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/164) **仍 OPEN、未合并**，HEAD `b694de91c575a62868c7c04367d25774d5f09d73`。它已有 `openspec/config.yaml` 的早期候选和旧 `docs/development/OPENSPEC-ADOPTION-PLAN.md`，但：
- 早期配置将 `docs/README.md`、`docs/tasks/TASK-STATUS.md` 和旧 `PLATFORM-DEVELOPMENT-OPERATIONS` 视作当前入口，**和 STEP01–07 的新 `documents/` 权威冲突**。
- 原 PR 自述尚未执行 OpenSpec CLI 安装、初始化/校验的成功验证，**不能直接当已验证配置合并**。
- PR 基于旧 Main，不能不审 Diff 就复用。STEP09 前先决定更新旧 PR 或关闭/以新 PR 替换，**STEP07 不擅自处理 PR #164**。

## 3. 未来首批 Specs 的候选（现在不新建）

- `synthea-new-only-producer`：真实 NEW_ONLY 固定 Request/Batch、生成、校验和 READY 发布；不宣称 UPDATE_ONLY/MIX_DATA。
- `landing-batch-consumer`：已验收 Manifest 身份、读取/Claim Gate、手工新批次和完成批次 SKIP；不宣称自动业务 COMMIT。
- `omop-person-visit-ingestion`：已验收 Spark Person/Visit、原子 Writer、独立 PG 读回和幂等。
- `platform-lineage-observability`：Marquez + Airflow A3 真实事件 + Spark A4 独立 Smoke 的**分项现状**；真实 Spark Dataset 业务血缘作为未来 Change。
- `azure-omop-analytics`：Azure/Fabric 目标架构、现有 IaC/Plan 的**当前事实**；Exporter/Notebook/OneLake 业务加载应是未来 Change，不得写成现行已验收 Behavior。

## 4. STEP08 最终文档审核 Gate（PR #174 合并后 COMPLETE）

1. 检查根 `README.md`、`AGENTS.md`、新 `documents/` 及仍被引用的旧 `docs/`：入口是否把旧 `TASK-STATUS` 误标为 Current；修正权威导航，**不批量改写历史验收**。
2. 校验全部当前 Markdown 相对链接、当前项目状态是否唯一、COMPLETE 与真实证据一致；保留版本/SHA/适用范围。
3. 确认新代码组件/功能命名规则持续生效；旧 Task-named Runtime 不要因文档搬迁被 Rename。
4. 确认 `docs/archive/` 没有被重建，原 Private Healthcare-Specs Archive 只作历史参考。

## 5. STEP09 正式采用时的 Gate

1. 从**当时最新 Main** 审核旧 PR #164 的变更，更新/取代其过时的 config 上下文；不直接合并旧参考入口。
2. 在适合的受控静态执行环境中查核**当时官方支持的 OpenSpec CLI 版本和命令**，运行 Init/Validate 并记录 Tool Version、Source SHA、输出；不能因为文件存在就说「CLI PASS」。
3. 仅添加必需 `openspec/`、配置和最小可验证 Baseline；不复制全部 `documents/`，不重放 TASK004 或修改 K8s/Azure。
4. 选择一个小型**获批** Change 测试新 Session 接力与 Verify/Archive；Task 勾选不能代替 PR 合并与独立业务读回。
5. OpenSpec 与 Self-Runner 是不同层：OpenSpec 不自动抢占任务或管理共享 Runtime；任何实际运行仍按安全规则单独授权。

**STEP08 只完成文档审查与权威切换，STEP09 仍未初始化。** 下一阶段从最新 Main 更新或替代旧 PR #164，并记录真实 CLI Init/Validate、配置 Schema 与版本证据，再开展第一个受控 Change。
