---
status: active
scope: architecture-design-index
last_verified: 2026-10-31
source_sha: 7060cbb673ea9bcea1de9311f58c1a4145316b35
---

# 架构与设计索引

本目录只保留**仍有独立价值**的决策、实施计划和必要的历史风险/验收依据。设计合并不代表代码已部署或云端资源通过验收。新开发 Agent 应先阅读当前权威 ADR，不应把早期 Draft 或被替代的实现目录当作指令。

## Healthcare / Fabric：当前有效开发依据

- **[Fabric Notebook + Pipeline + Environment + Shared Engine 最终 ADR](FABRIC-NATIVE-NOTEBOOK-PIPELINE-ENVIRONMENT-ADR-20261031.md)**：Fabric Git Item 目录、真正的 PySpark Notebook、Pipeline 编排、唯一 Shared Wheel 及 Environment Publish。
- **[Fabric Bronze → Canonical Silver → OMOP Gold 业务 ADR](FABRIC-MEDALLION-CANONICAL-ADR-20261030.md)**：数据契约、来源与批次版本、审批/重跑、Warehouse Gold 事务候选和 E2E 闸门。
- **[Fabric FHIR 实战目录与文件级实施计划](FABRIC-FHIR-PRACTICAL-SOURCE-LAYOUT.md)**：已有 Local/Trial 源码对照、目标文件、OneLake Catalog 与分期开发步骤。
- [Fabric Terraform Workspace-scoped 架构](FABRIC-TERRAFORM-ENVIRONMENT-ARCHITECTURE.md)：仍有效的 IaC 目标和 State 保护；实际变更以 [对应 OpenSpec](../../../openspec/changes/organize-fabric-terraform-by-workspace/tasks.md) 和真实 State 为准。
- [FHIR R4 / HL7 v2 多来源 MVP](FHIR-HL7-MULTISOURCE-MVP-DESIGN.md)：医院模拟来源和合成患者交叉身份的已确认设计，实施状态与 Fabric FHIR 入库独立。

## 其他当前组件与工程设计

- [Local Portal MVP 收尾与延后追踪](LOCAL-PORTAL-MVP-CLOSEOUT-AND-DEFERRED-FOLLOWUPS.md)
- [OpenLineage Spark A4 unknown Job 法证](OPENLINEAGE-SPARK-A4-UNKNOWN-JOB-FORENSICS.md)
- [OpenLineage Spark RDD Action 生命周期决策](OPENLINEAGE-SPARK-RDD-ACTION-LIFECYCLE-DECISION.md)
- [Data Platform V2 源码目录迁移设计](DATA-PLATFORM-V2-MIGRATION-DESIGN.md)
- [OpenSpec 接入和治理设计](OPENSPEC-ADOPTION-DESIGN.md)

## 历史参考，不是当前开发规范

- [Healthcare V2 多来源/双 Portal 早期路线](HEALTHCARE-V2-MULTISOURCE-FABRIC-ROADMAP-DESIGN.md)：有未来方向，但旧实施顺序不得覆盖新 ADR。
- [Fabric 多环境旧重建架构](FABRIC-MULTI-ENVIRONMENT-REBUILD-DESIGN.md) 与 [旧部署基线](FABRIC-CURRENT-DEPLOYMENT-BASELINE.md)：**SUPERSEDED**，只因账号、旧 State/Storage 和风险分析仍有追溯价值暂留；不能照此重建新环境。

2026-10-31 已从 Main **移除两份已被正式 ADR 替代的 FHIR 草稿**，不再创建第二个 `archive/` 副本。历史快照统一见 [PR #533](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/533) 或 [Medallion ADR 的固定 Git 版本链接](FABRIC-MEDALLION-CANONICAL-ADR-20261030.md#6-历史来源与决策追溯)。

其他权威入口：[当前总体架构](../SYSTEM-OVERVIEW.md)、[已批准决策](../decisions/README.md)、[系统组件文档](../../systems/data-platform/README.md)、[Agent 开发规则](../../engineering/development/AGENT-RULES.md)。
