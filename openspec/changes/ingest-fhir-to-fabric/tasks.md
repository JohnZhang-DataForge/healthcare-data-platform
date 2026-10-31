# Tasks

> **Architecture decision 2026-10-30 complete; implementation NOT authorized.** 详细权威设计：[ADR](../../../documents/architecture/design/FABRIC-MEDALLION-CANONICAL-ADR-20261030.md)。完成文档不等于运行时验收。

## 1. Architecture decisions

- [x] 1.1 2026-10-27 已核查 Local NEW_ONLY 真实 DAG、Canonical/OMOP Contract、Publisher v1 Manifest 和 Fabric 旧 POC 状态（静态）。
- [x] 1.2 形成独立 Draft PR #533、两份 Fabric/Local 对照架构初稿，不合并 Main。
- [x] 1.3 2026-10-30 讨论确认 Bronze raw / Silver Canonical Delta / Gold OMOP 业务分层。
- [x] 1.4 确定 Source + Entity Adapter 插件化；Silver 后共用 OMOP Mapper、DQ、Identity、Reconciliation；Local 引擎逐步抽到 shared-data-engine，现有运行代码不动。
- [x] 1.5 明确 PySpark 优先、dbt MVP 暂缓；Gold Warehouse T-SQL 事务首选 POC、全 Delta visibility 备选，均非既有已验收成果。
- [x] 1.6 同步权威 ADR、原两份初稿的历史声明和 OpenSpec proposal/design/tasks。
- [x] 1.9 2026-10-30 用户确认采用独立 `shared-data-engine` Python Package 的目录规则、唯一源码归属、依赖方向和渐进 Local 迁移策略；建立仓库根/Scoped AGENTS 规则、组件 README/CODE 与专门开发规范；同步更新旧“禁止重复 src”对独立 Wheel 的例外。**此项仅代表规范落地，不代表已创建业务包或 CI 自动拦截。**
- [x] 1.11 从 Main 真实源码核对 Local Mapper 与 JDBC 耦合、Terraform Existing Workspace/OneLake、Trial Git Native Items/硬编码 Publisher；制定 Shared/Fabric 两只 Wheel 的精确源码文件名、OneLake schema/table/approval 目录、Environment Publish/Readback、P0–P5 交付顺序与禁止迁移清单（**仅文档提案，所有业务实现与运行仍未开始**）。
- [ ] 1.10 首个真实 Python Source PR 前扩展 CODE-map 静态所有权及 shared→platform 禁止 import 检查、配套正负向单元测试；验证冻结 Local Contract 单一权威和跨版本 package pin 后再允许业务代码提交。
- [ ] 1.7 通过实机/成本验证后，最终敲定 Shortcut/Copy、Warehouse/Delta Writer、ID namespace、Canonical v2 和 Update 政策，完善正式 delta spec/测试及 CODE 导航。
- [ ] 1.8 用户审查并决定是否合并此设计 PR；任何未来实施需要单独授权。

## 2. Future implementation (not authorized)

- [ ] G0：只读校验 Manifest 原始字节/对象 SHA/ETag、真实 FHIR Profile、Blob Shortcut RBAC/保留策略。
- [ ] G1：冻结 synthetic FHIR fixtures；离线 Bundle/ref/Patient/Encounter、Contract/Quarantine/缺失/重复/冲突负向测试。
- [ ] G2：独立解决三次 Trial Notebook Create/GetDefinition LRO/exitValue HOLD；得到新授权后才进行免费受控的真实结果 SHA Smoke。
- [ ] G3：5–10 新 synthetic Patient → Intake + Bronze raw/ref + receipt，按 Source Batch/Processing Version 验证 replay SKIP 和漂移 HOLD。
- [ ] G4：100 新 synthetic Patient/Encounter → managed Silver canonical_patient/encounter Delta；PK/FK/DQ/来源/hash/readback、quarantine、approved 证据。
- [ ] G5：Shared Silver→OMOP Person/Visit Candidate + Concept/Identity/row reconcile，证明相同输入/版本结果稳定。
- [ ] G6：Warehouse staging + Person/Visit/IdentityMap/Ledger T-SQL 单事务（首选）故障、回滚、并发、未知 ACK、NOT ENFORCED 约束/读回；不能用时重新评审 Delta visibility。
- [ ] G7：正式受控 Pipeline E2E、实际 Lineage、Compute/Cost/CI-CD/Runtime 兼容及清理证据。
- [ ] G8：HL7/CSV Fabric Adapter、PG OMOP Snapshot、dbt、Canonical v2 等未来各自单独 Change。

## 3. Explicit non-goals / safety

本轮只提交 Git 设计文档。**不合并 main；不触发 Fabric/Azure/Blob/K8s/PostgreSQL 写入；不变更 Warehouse/Notebook/Pipeline/Connection/Terraform/paid capacity；不改 Local 或发布器生产实现。** Warehouse 跨表事务能力不代表跨系统事务；未通过实机 Gate 不得标记 Gold COMMITTED。
