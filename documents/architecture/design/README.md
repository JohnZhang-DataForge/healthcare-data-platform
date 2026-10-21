---
status: active
scope: architecture-design-index
last_verified: 2026-10-19
source_sha: f3b2d9e97d9afe4e7457a1d48fde9e655add47d7
---

# 架构设计讨论稿

- **[Fabric Terraform 按真实 Workspace/资源类型独立部署架构（最新有效目标）](FABRIC-TERRAFORM-ENVIRONMENT-ARCHITECTURE.md)**：`fabric-workspace/<name>/<type>/` 独立 Root/State，`shared-infra/` 同级，Modules 通用，Workspace ID 经 Remote State Output 获取；Notebook/Pipeline 完全由 `fabric-cicd` 管理。实施见 [当前 OpenSpec Change](../../../openspec/changes/organize-fabric-terraform-by-workspace/tasks.md)。

本目录集中导航**讨论稿与已确认但尚未实施的目标架构设计**。每份设计以自身 status 为准；任何目标设计都不代表已经部署或运行验收，也不取代系统实际源码、项目唯一状态与 OpenSpec Change。

- [Data Platform V2：仓库迁移与模块化重构设计](DATA-PLATFORM-V2-MIGRATION-DESIGN.md)：四个顶层模块、本地组件划分、Task004 兼容重命名、公共能力提取、实施阶段、测试和回滚。
- [OpenSpec 接入与开发治理设计](OPENSPEC-ADOPTION-DESIGN.md)：同仓 OpenSpec、Documents/Specs/Changes 权威边界、官方标准流程、Agent 接力、STEP09 实施 Gate（编写时为未初始化的讨论稿；此后 G0–G4 已实施，G5 首个业务 Change 未开始，最新状态以 [实施计划](../../engineering/migration/OPENSPEC-IMPLEMENTATION-PLAN.md) 为准）。

- [Healthcare V2：双平台、多数据源与公开展示路线](HEALTHCARE-V2-MULTISOURCE-FABRIC-ROADMAP-DESIGN.md)：暂停 Condition，保留 Local OMOP，PG/FHIR/HL7 三条独立 Fabric 输入、双 Portal 可公开只读展示及 OpenSpec→目录迁移→云端 E2E 实施顺序（讨论稿）。
- [FHIR R4 / HL7 v2 多来源 MVP 设计（已确认目标、未实施）](FHIR-HL7-MULTISOURCE-MVP-DESIGN.md)：共享 Synthea 合成群体、固定部分患者 Crosswalk、FHIR Bundle JSON、OIE 转 HL7 ADT、无 Kafka 的文件发布、Fabric Bronze/Silver 和最小验收门槛；实施需独立 OpenSpec Change。
- [Fabric 多环境可重建架构（已确认目标、未实施）](FABRIC-MULTI-ENVIRONMENT-REBUILD-DESIGN.md)：稳定的本地与 Blob、分环境 Terraform State/身份、Terraform 控制平面、GitHub Actions + fabric-cicd 发布、跨租户前置条件与一键受控部署验收；原生 Workspace GitHub Integration 不是 MVP 依赖。

其他权威入口：[当前总体架构](../SYSTEM-OVERVIEW.md)、[已批准的架构决策](../decisions/README.md)、[Data Platform 组件文档](../../systems/data-platform/README.md)、[Agent 开发规则](../../engineering/development/AGENT-RULES.md)。
