# Proposal

## Why

现有 Canonical-first 业务架构正确，但 Shared Wheel 0.1.3 的 OMOP Candidate 输出固定为 Person/Visit，`candidates.py` 的 Profile 固定要求人口学与 Visit 字段，Fabric F2 `identity_plan.py` 的 `KINDS` 仅包含 `PERSON`、`VISIT_OCCURRENCE`，Silver→OMOP Handoff/Approval 也固定 Patient/Encounter。若直接在这两个实体的基础上完成 Gold Writer，后续引入 Condition、Measurement、Observation、Drug 等目标表，会重复修改核心 Identity、Mapping、FK、Candidate 和发布/Replay 机制。

已证明的实际范围：Fabric G4 合成数据 Canonical Patient 100 / Encounter 5,918 的 Silver 物理读回；F0 CDM 5.4 Schema、F1 Vocabulary、F2 合成 SQL ROLLBACK 有独立证据。临床 Concept Profile、真实 Candidate Delta、稳定 ID 持久化、Gold COMMIT、完整 Pipeline E2E **尚未完成**。设计扩展必须与这些事实分离。

## What Changes

- 建立 **Multi-Entity** 公共契约：`EntityDefinition/Registry`、`MapperInput/EntityCandidate`、经审核的 `ConceptProfile`、`IdentityPlan/ReferenceResolver`、`DependencyGraph`、`PublicationGroup/Receipt`。
- 将「一个 Canonical 业务 Entity」与「一个或多个 OMOP 目标表」解耦；来源记录可确定性地派生多条不同业务角色的 OMOP 目标行，且具备稳定来源/派生身份。
- 固化 Snapshot → provisional ID plan → Candidate → Warehouse 单写入事务内重新校验 → Map/Allocator/Gold/Ledger COMMIT → 独立 SQL Readback 的正确顺序；预览/候选不构成 ID 预约或正式发布。
- 以 Person/Visit 作为向后兼容的首批实体；以独立后续 Condition 增量验证第三实体可接入，不在本轮设计 PR 创建空代码脚手架。
- 将公共业务规则归属唯一 `shared-data-engine` Wheel，平台 I/O/事务仍分别归 Local PG 与 Fabric Warehouse Writer；沿用已批准 Canonical-first / Native Item ADR 和现有真实目录。
- 分阶段 PR 与验收：先文档契约、再最小 Registry/API/回归、Identity/Concept/FK、真实 Fabric Candidate、Gold Writer、最后第三实体实验。相关 G5/F2/统一 E2E Change 继续作为实际业务验收的唯一任务来源；此 Change 仅跟踪公共能力落地，不重复标记实际 Gold PASS。

## Capabilities

### New Capabilities

- `shared-omop-multi-entity`: 平台中立、可测试、向后兼容的多实体 OMOP Candidate/Identity/Dependency/Publication 协作规范。

### Modified Capabilities

- 本 PR 只增加目标行为的 Delta Spec；不修改已验收的 Current Spec 或运行时。后续行为落地后再按 OpenSpec 生命周期同步 Current Specs。

## Impact

- **Git / owner：** 本阶段仅新增 `openspec/changes/extend-shared-omop-multi-entity/` 五个文档；后续源码归属 `shared-data-engine/src/healthcare_data_engine/`，新增测试归属 `.github/quality/tests/shared-data-engine/`，物理 Fabric Writer 归属 `azure-fabric/warehouse/omop-foundation/writer/`，组件说明在 `documents/`。
- **Compatibility：** `local-data-platform/spark/contracts/` 的 Patient/Encounter/Person/Visit 现有合同字节、已提交业务 ID、历史 G4 分区、正式 Wheel 0.1.3 及 Local DP 运行时全部保持原样，升级必须显式测试并独立发布。
- **Related active work：** `fabric-g5-approved-silver-omop-candidate`、`fabric-omop-foundation`、`fabric-fhir-omop-unified-e2e`；业务 Concept 复核与 Gold 实际运行不能凭本设计 PR 关单。
- **Cloud：** 本阶段零 Azure/Fabric/PG/S3/K8s/Capacity 读写、无 SQL DDL/DML、无真实患者数据。

## Non-goals

不一次性实现 CDM 5.4 全部表；不重新实现已冻结 FHIR/CSV 转换；不新增第二个 Shared Wheel、Fabric 专属 Mapper、独立 Pipeline 调度器或复杂通用 DSL；不推断真实患者跨医院身份；不自动猜测临床 Concept；不承诺跨事务组数据库级原子性；不在此 Change 擅自引入 dbt、UPDATE_ONLY/MIX_DATA 或执行云端写入。

## Rollback

设计 PR 可以直接 revert，无运行时影响。后续代码 PR 必须保留旧 Person/Visit API、双运行时等价回归和明确调用方切换/回退路径；任何 Gold 写入需独立运行授权与事务/读回证据。
