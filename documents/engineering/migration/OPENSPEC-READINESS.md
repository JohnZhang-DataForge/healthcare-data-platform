---
status: reviewed
scope: openspec-migration-preparation
last_verified: 2026-10-16
source_sha: d1962f79e1c7337c372de1aebfaaec87dfc7d1c8
---

# OpenSpec 迁移准备 — STEP08/STEP09 Gate

**历史快照说明（2026-10-16/17，G0 开始之前）**：本页正文中的“未初始化”“未执行 CLI”等均仅描述当时的 Main，**不是当前状态**。截至 2026-10-18，G0–G4 已完成并合并；当前唯一状态请见 [G0–G7 实施计划](OPENSPEC-IMPLEMENTATION-PLAN.md) 与 [PROJECT-STATUS](../status/PROJECT-STATUS.md)。

> **STEP08 终审完成后的准备清单，不是 OpenSpec 初始化记录。** 正式采用 OpenSpec 管后续变更与 Agent 接力的方向已确认，但当时核验的 Main 仍**没有 `openspec/`**；当轮没有运行 OpenSpec CLI/npm，也没有为此触发业务或云端 Workflow。[最终文档权威终审](FINAL-DOCUMENTATION-AUDIT.md)。

**2026-10-17 状态补充**：旧 Bootstrap [PR #164](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/164) 已 **CLOSED / NOT MERGED**；替代方案请审阅 [OpenSpec 接入与开发治理设计讨论稿](../../architecture/design/OPENSPEC-ADOPTION-DESIGN.md)。该动作只关闭过时 PR，**不表示 G1 CLI 初始化或 STEP09 已完成**。

**目录调整提示**：旧 `docs/` 已进入 [Legacy Snapshot](LEGACY-DOCS-SNAPSHOT.md)，不在当前 Main。旧 PR #164 对 `docs/README.md`、`docs/tasks/TASK-STATUS.md` 的引用在目录删除后更不可能作为有效 OpenSpec `config.yaml` 上下文；正式采用前必须替换为现行 `documents/`。

## 1. 最小职责分配

| 系统 | 负责 | 不负责 |
| --- | --- | --- |
| [`documents/`](../../README.md) | 稳定架构、组件、运维、命名/安全、历史决策 | 不为每个任务/Session 存一份 CURRENT 文档 |
| `openspec/specs/`（未来） | **实际行为的**可验证需求 / 验收场景 | 不将 Azure/Portal 规划写成已上线功能 |
| `openspec/changes/`（未来） | Proposal / Design / Delta Specs / Tasks / 验证与归档 | 不当作分布式运行锁或业务 COMMIT 证据 |
| GitHub PR/Issue + Self-Runner | 多分支代码审查、准确 SHA、Run/Artifacts | 不能仅凭 CI SUCCESS 宣称 PG/Delta 实际验收 |
| [Session Coordination](../development/SESSION-COORDINATION.md) | 共享 Spark/Airflow/PG/K8s/Azure 的人工协调与前置 Gate | 不提供完整自动 Agent 调度或无条件并发锁 |

## 2. 旧 OpenSpec Bootstrap PR 的冲突

2026-10-16 检查时 [PR #164](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/164) **仍 OPEN、未合并**，HEAD `b694de91c575a62868c7c04367d25774d5f09d73`。它已有 `openspec/config.yaml` 的早期候选和旧 `docs/development/OPENSPEC-ADOPTION-PLAN.md`，但：
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

## 5. STEP09 G0–G7 开工门槛（实施前核查）

**唯一完整执行方案：**[OpenSpec G0–G7 实施计划](OPENSPEC-IMPLEMENTATION-PLAN.md)。本文只保留 Readiness 与历史证据边界；之前讨论稿中“G2 Bootstrap / G3 首个 Change”的编号**已废止**，不能与新 G0–G7 混用。

1. **G0**：每次开始执行都从最新 Main 记录真实 SHA，确认 PR #164 CLOSED/NOT MERGED、当前 CODE Map/命名 CI 及实际 Node/CLI 兼容性。旧 PR 配置不得继续使用。
2. **G1**：固定并记录安装的官方 CLI 版本，真实执行 Init；确认在仓库根目录生成 `openspec/`，不将预先写出的 Markdown 视为安装成功。
3. **G2**：验证默认 Schema 与最小 config，引用现行 `documents/`、`AGENTS.md`、项目状态及[命名规范](../development/CODE-ORGANIZATION-AND-NAMING.md)；不用一次生成所有 Current Specs。
4. **G3**：CI 真实覆盖 OpenSpec 校验与未来 `data-platform/` 路径。旧代码**纯移动**只能在固定源 SHA、明确旧新路径、Blob 一致性及新代码负向测试的保护下受限豁免；不能关闭整个命名 Gate。
5. **G4**：复用 GitHub PR、Actions、Self-Runner、三轮失败停止规则和已有 Session 协调；Task 完成不等于 PR Merge 或 PG/S3/Delta 独立读回完成。
6. **G5**：先审核一个 `relocate-local-data-platform` 的 Proposal/Design/Tasks，确认 CLI 是否支持纯 Refactor 的 `skip_specs: true`，**不要移动代码**。
7. **G6**：按组件分 PR 迁移，先验证 Import/DAG/Docker/GitSync/CI/CODE Map 路径兼容，再受控切换实际运行入口；原 DAG ID、Batch、SQL 持久化协议与 Writer Fencing 不变。Live 验证单独授权。
8. **G7**：按 Change 独立推进 Modularization、PG→Fabric、FHIR、HL7 v2、业务 Lineage 和静态只读 Showcase；Condition 后续业务暂缓，历史 Step00 只读准备状态保留。

**STEP08 当时的阶段结论（历史）**：那一轮尚无任何 G0–G7 CLI/CI/Runtime PASS、OpenSpec 尚未初始化。此结论已被后续 G0–G4 的真实 CLI/CI/PR 证据取代，**当前不得从 G0 重新初始化**；G5 尚未开始，其范围以 [正式计划](OPENSPEC-IMPLEMENTATION-PLAN.md) 为准。
