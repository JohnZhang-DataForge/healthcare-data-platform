---
status: active
scope: architecture-decision-index
last_verified: 2026-10-16
source_sha: d1962f79e1c7337c372de1aebfaaec87dfc7d1c8
---

# Architecture Decisions — 长期架构决策索引

> **只记录已确认的长期决策、为什么采取它及当前边界。** 不重复维护任务进度/Session 日志；未来新变更通过 OpenSpec Change 记录 alternatives/design/tasks，长期架构的结果再更新此索引。

| ID | 已确认决定 | 理由和证据 / 尚未覆盖 |
| --- | --- | --- |
| **D-01** | **Synthea 独立 Producer，Airflow 只消费 SeaweedFS READY Batch** | 避免生成与重试耦合；NEW_ONLY Person/Visit [真实验收](../../docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md)。旧 Processing-first 为历史版本；UPDATE_ONLY / MIX_DATA 未实现 |
| **D-02** | **PostgreSQL OMOP 仍为本地权威，Writer 有事务/Claim/Fencing/幂等保护** | Spark 完成不等于 DB COMMIT；[OMOP Writer](../components/omop/README.md) 和数据库独立读回为验收 |
| **D-03** | **Portal 用 OpenLineage + Marquez 原生 Web + 独立 PostgreSQL14** | 避免自建可视化与修改 OMOP PG17；[Portal](../components/platform-portal/README.md) Marquez/A3/A4 分项有证据，但**真正业务 Spark 接入方式仍未选定** |
| **D-04** | **Azure 走 OneLake-first MVP：PG → Azure Blob → Fabric Data Pipeline → PySpark Notebook → Lakehouse** | 缩减旧 Warehouse-first/多层 ETL；[Azure](../components/azure-fabric/README.md) 三组件仅 Plan PASS、**无 Apply/业务 E2E** |
| **D-05** | **新代码按组件 + 功能命名，Task/Step 仅表示开发活动** | [强制规范与 CI](../development/CODE-ORGANIZATION-AND-NAMING.md) 已合并；旧 `task004` Runtime 兼容搬迁尚未实施 |
| **D-06** | **准备采用 OpenSpec 管 Change/Tasks/Agent 接力，GitHub 管 PR，Self-Runner 管真实执行** | 不再另建持续膨胀的 Handoff 体系；[迁移准备](../migration/OPENSPEC-READINESS.md) 已规划，但 `openspec/` **尚未进入 Main** |

**决策状态**：D-01/D-02 已在对应本地已验收范围实施；D-03 的 Portal 基础完成而真实业务 Spark 集成方案仍在讨论；D-04 是已批准架构但云端业务尚未实施；D-05 新代码规则生效，旧代码保持；D-06 是已接受方向而不是已启动的 OpenSpec。

若未来出现被新事实/方案替代的决策，在本索引修订该项及其依据，链接审批的 Change/PR；不把未批准建议写成正式 ADR，也不为每次 Session 创建记录。
