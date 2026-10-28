# Proposal

## Why

现有合成 FHIR R4 Producer 已建立 Azure Blob 不可变对象/最后 Manifest 发布协议（真实 Blob 发布范围以 Publisher 的单独验收证据为准）。目前 Healthcare Fabric 仓库里尚无该来源的真实 Notebook/Pipeline 入库实现。需要先设计一条可复用 Local DP 已验收的 Manifest、Canonical、身份、事务保护、对账与血缘经验，同时减少 Airflow/K8s/PG 专用 Writer 的复杂度。

本轮用户要求**先形成架构初稿并在独立 Git 分支讨论，绝不合并 Main**。根据后续要求增加 [Local DP 数据流复盘与新 Fabric 代码结构](../../../documents/architecture/design/LOCAL-DP-TO-FABRIC-CODE-ARCHITECTURE-DRAFT.md)，避免误将单 Notebook 设计成大型单文件实现。

## What Changes

- 首次明确 FHIR R4 Blob → Fabric Data Pipeline → PySpark Notebook → Lakehouse Bronze/Silver → 候选 OMOP Person/Visit Delta 路线。
- 根据实际 Publisher Manifest 字段设计消费入口与字节/哈希/幂等协议，不创造不存在的 READY/cohort_id 字段。
- 对照 Local DP 的 Source Contract、source-key mapping、双表 Writer、fencing/reconciliation 和已知 OpenLineage 问题提出 Fabric 适配和优化。
- 分阶段定义 Source 验证、数据质量、Delta 跨表可见性保护、失败恢复与独立读回 Gate；明确待讨论选项与性能/成本/权限门槛。
- 本 Change 当前仅为 **design-only draft**。详细方案唯一权威文本见 [Fabric FHIR 初稿](../../../documents/architecture/design/FABRIC-FHIR-BLOB-INGESTION-DRAFT.md)；确认后才创建可执行 Item、Specs/Tests 和细化实施计划。

## Capabilities

### New Capabilities
- ingest-fhir-to-fabric（**目标候选；尚未实现**）：通过受控 Pipeline 以明确的不可变 Manifest 消费原始 FHIR Bundle，并得到可核验 OneLake Delta Patient/Encounter/OMOP 数据产品。

### Modified Capabilities
- 无：不改 Local Data Platform、Blob Publisher 和 Fabric 已有 Items 的行为。

## Impact

- 讨论稿：documents/architecture/design/FABRIC-FHIR-BLOB-INGESTION-DRAFT.md 及本 OpenSpec Change。
- 未来潜在范围：azure-fabric/workspaces/healthcare-omop/notebooks/ingestion/、pipelines/、独立解析/测试组件、documents/systems/azure-fabric/*/CODE.md。
- 本次无 Fabric/K8s/Azure Blob/PG 修改、无配置/密钥写入、无 runtime 或成本副作用；不同来源不做无证据患者合并。
- PG→Fabric OMOP 快照复制、HL7 v2、公开触发器、Fabric OpenLineage Blob Relay 均属于关联但**独立**的交付边界。
