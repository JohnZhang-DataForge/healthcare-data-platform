---
status: draft
scope: architecture-design-index
last_verified: 2026-10-17
source_sha: 664dfed06a206ff20822a118c8f04771a307452b
---

# 架构设计讨论稿

本目录存放**待审核的架构设计和迁移方案**。它们不代表已经部署的功能，也不取代已批准的架构决策或项目唯一当前状态。

- [Data Platform V2：仓库迁移与模块化重构设计](DATA-PLATFORM-V2-MIGRATION-DESIGN.md)：四个顶层模块、本地组件划分、Task004 兼容重命名、公共能力提取、实施阶段、测试和回滚。
- [OpenSpec 接入与开发治理设计](OPENSPEC-ADOPTION-DESIGN.md)：同仓 OpenSpec、Documents/Specs/Changes 权威边界、官方标准流程、Agent 接力、STEP09 实施 Gate（编写时为未初始化的讨论稿；此后 G0–G4 已实施，G5 首个业务 Change 未开始，最新状态以 [实施计划](../../engineering/migration/OPENSPEC-IMPLEMENTATION-PLAN.md) 为准）。

- [Healthcare V2：双平台、多数据源与公开展示路线](HEALTHCARE-V2-MULTISOURCE-FABRIC-ROADMAP-DESIGN.md)：暂停 Condition，保留 Local OMOP，PG/FHIR/HL7 三条独立 Fabric 输入、双 Portal 可公开只读展示及 OpenSpec→目录迁移→云端 E2E 实施顺序（讨论稿）。

其他权威入口：[当前总体架构](../SYSTEM-OVERVIEW.md)、[已批准的架构决策](../decisions/README.md)、[Data Platform 组件文档](../../systems/data-platform/README.md)、[Agent 开发规则](../../engineering/development/AGENT-RULES.md)。
