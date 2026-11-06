---
status: active
scope: azure-fabric-system-overview
last_verified: 2026-11-05
---

# Azure / Microsoft Fabric — Lakehouse and OMOP Analytics

Fabric analytics is separated from the Local PG17 transactional OMOP writer. The physical Warehouse is an existing Workspace item; never invent a synthetic native Warehouse Git folder. [Fabric CODE](CODE.md) is the source owner map.

## Current business architecture — canonical-first, not PG-export-only

**批准的业务架构**：[Medallion Canonical ADR](../../architecture/design/FABRIC-MEDALLION-CANONICAL-ADR-20261030.md)；**批准的执行架构**：[Fabric-native ADR](../../architecture/design/FABRIC-NATIVE-NOTEBOOK-PIPELINE-ENVIRONMENT-ADR-20261031.md)；**唯一共享业务 Owner**：[Shared Engine rules](../../engineering/development/SHARED-DATA-ENGINE-STRUCTURE-AND-OWNERSHIP.md)。

- **当前在开发的真实 FHIR 主线**：FHIR R4 Adapter → 同一份 Canonical Patient/Encounter v1 → 已验收 G4 Approved Silver Delta (100 Patient / 5,918 Encounter / quarantine 0) → Shared OMOP Candidate + 经审查的来源 Concept Profile + 稳定 INT ID → 受控 Fabric Warehouse Gold。Candidate Delta、正式临床 Profile、Warehouse Gold COMMIT/Replay 和 Pipeline E2E **尚未通过**，不得以 Silver Approval 或 Vocabulary lexical lookup 代替。
- **各来源先各自做适配，之后共享**：CSV/FHIR/HL7 格式、字段和来源代码差异留在 Source/Entity Adapter 与版本化 Mapping Profile；Canonical 之后以唯一 Shared Engine 为目标共用纯业务计算。现有 Local PG 生产链仍是 legacy Local 实现，尚未完全替换为同一 Wheel；不能把目标架构写成双平台运行事实。
- **另一条独立路线**：已经提交的 Local PG OMOP → read-only snapshot Exporter → Azure Blob → Fabric 分析副本；Exporter/跨平台复制 E2E **未实现**，不是 Fabric FHIR Intake 前置。Fabric Warehouse 真实存在且是 Workspace-only，不是 PG 的自动镜像。

## Ownership at a glance

| Work | Source and map |
| --- | --- |
| Native Notebook, Pipeline, Environment, Lakehouse | [Native Git Items](../../../azure-fabric/workspaces/healthcare-omop/) · [Notebook](notebooks/CODE.md) · [Pipeline](pipelines/CODE.md) · [Environment](environments/CODE.md) |
| Warehouse SQL, Schema and manifests | [deployment/warehouse](../../../azure-fabric/deployment/warehouse/) · [Deployment CODE](deployment/CODE.md) |
| OMOP Writer business Python | [Writer source](../../../azure-fabric/warehouse/omop-foundation/writer/) · [Warehouse CODE](warehouse/CODE.md) |
| OpenLineage Publisher and Listener deployment | [Publisher](../../../azure-fabric/openlineage/) · [OpenLineage CODE](openlineage/CODE.md) |
| Terraform resources | [IaC modules](../../../azure-fabric/infra-terraform/) · [Terraform CODE](infra-terraform/CODE.md) |
| Shared pure Python engine | [Shared Engine](../data-platform/shared-engine/README.md) |

## Verified scope and acceptance boundaries

Shared Engine version 0.1.3 is [published to Environment](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41834029745) with an independently [completed isolated Spark 4.1 import](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41835694167). This does not prove the formal business Notebook's Engine guard is aligned or that FHIR→Bronze/Silver Approval→OMOP Gold warehouse COMMIT, replay and physical readback succeeded. See [FHIR E2E Change](../../../openspec/changes/fabric-fhir-omop-unified-e2e/tasks.md) and [OMOP Foundation](../../../openspec/changes/fabric-omop-foundation/tasks.md).

Current development follows [Native execution ADR](../../architecture/design/FABRIC-NATIVE-NOTEBOOK-PIPELINE-ENVIRONMENT-ADR-20261031.md), [Deployment ownership spec](../../../openspec/specs/fabric-deployment-component-ownership/spec.md) and [Safe Operations](../../engineering/operations/SAFE-OPERATIONS.md). Azure Capacity, Terraform apply, Notebook run and SQL/Delta write require independently authorized, observed execution.

The previous [Fabric system history and exact past configuration inputs](FABRIC-HISTORY-20261105.md) remains byte-identical; old dated architecture assumptions are not current deployment proof.
