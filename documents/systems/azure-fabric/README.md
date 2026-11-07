---
status: active
scope: azure-fabric-system-overview
last_verified: 2026-11-06
---

# Azure / Microsoft Fabric — Lakehouse and OMOP Analytics

Fabric analytics is separated from the Local PG17 transactional OMOP writer. The physical Warehouse is an existing Workspace item; never invent a synthetic native Warehouse Git folder. [Fabric CODE](CODE.md) is the source owner map.

## Current business architecture — canonical-first, not PG-export-only

**批准的业务架构**：[Medallion Canonical ADR](../../architecture/design/FABRIC-MEDALLION-CANONICAL-ADR-20261030.md)；**批准的执行架构**：[Fabric-native ADR](../../architecture/design/FABRIC-NATIVE-NOTEBOOK-PIPELINE-ENVIRONMENT-ADR-20261031.md)；**唯一共享业务 Owner**：[Shared Engine rules](../../engineering/development/SHARED-DATA-ENGINE-STRUCTURE-AND-OWNERSHIP.md)。

- **当前在开发的真实 FHIR 主线**：FHIR R4 Adapter → 同一份 Canonical Patient/Encounter v1 → 已验收 G4 Approved Silver Delta (100 Patient / 5,918 Encounter / quarantine 0) → Shared OMOP Candidate + 经审查的来源 Concept Profile + 稳定 INT ID → 受控 Fabric Warehouse Gold。Candidate Delta、正式临床 Profile、Warehouse Gold COMMIT/Replay 和 Pipeline E2E **尚未通过**，不得以 Silver Approval 或 Vocabulary lexical lookup 代替。
- **各来源先各自做适配，之后共享**：CSV/FHIR/HL7 格式、字段和来源代码差异留在 Source/Entity Adapter 与版本化 Mapping Profile；Canonical 之后以唯一 Shared Engine 为目标共用纯业务计算。现有 Local PG 生产链仍是 legacy Local 实现，尚未完全替换为同一 Wheel；不能把目标架构写成双平台运行事实。
- **另一条独立路线**：已经提交的 Local PG OMOP → read-only snapshot Exporter → Azure Blob → Fabric 分析副本；Exporter/跨平台复制 E2E **未实现**，不是 Fabric FHIR Intake 前置。Fabric Warehouse 真实存在且是 Workspace-only，不是 PG 的自动镜像。

## Fabric 接管及优先顺序

Shared 核心已可支撑 Fabric 主线开发；**Local 进入维护模式**、暂不迁移既有 PG Mapper/Writer。保留 G4 Approved Silver **Patient 100 / Encounter 5,918 / Quarantine 0** 与历史处理 `engine-0.1.1`；正式 Notebook 仍默认 HALT。依据 [统一 FHIR→OMOP E2E OpenSpec](../../../openspec/changes/fabric-fhir-omop-unified-e2e/tasks.md) 依次处理 **P1.4/P1.5 来源版本/许可/临床 Mapping** → **P2.1 真实完整 Warehouse Identity/Allocator/Ledger 快照** → **P3.1 Candidate Delta/Approval-last/Replay** → **P4.1 Gold 单事务** → **P5.1 原生 Pipeline E2E**。复用已有 Shared Engine/Writer，不复制第二套。不得将合成 Concept 或 PROVISIONAL ID 当作真实提交 ID。

## Ownership at a glance

| Work | Source and map |
| --- | --- |
| Native Notebook, Pipeline, Environment, Lakehouse | [Native Git Items](../../../azure-fabric/workspaces/healthcare-omop/) · [Notebook](notebooks/CODE.md) · [Pipeline](pipelines/CODE.md) · [Environment](environments/CODE.md) |
| Warehouse SQL, Schema and manifests | [deployment/warehouse](../../../azure-fabric/deployment/warehouse/) · [Deployment CODE](deployment/CODE.md) |
| OMOP Writer business Python | [Writer source](../../../azure-fabric/warehouse/omop-foundation/writer/) · [Warehouse CODE](warehouse/CODE.md) |
| OpenLineage Publisher and Listener deployment | [Publisher](../../../azure-fabric/openlineage/) · [OpenLineage CODE](openlineage/CODE.md) |
| Terraform resources | [IaC modules](../../../azure-fabric/infra-terraform/) · [Terraform CODE](infra-terraform/CODE.md) |
| dbt Core SQL (future governed owner, not migrated) | [dbt engineering/Agent rules](dbt/README.md); current executable [HL7 CODE](../data-platform/hl7/CODE.md) |
| Shared pure Python engine | [Shared Engine](../data-platform/shared-engine/README.md) |

## Verified scope and acceptance boundaries

Shared Engine **0.1.6** [GA Published #42284453546](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42284453546), [formal Native Notebook definition readback #42291355563](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42291355563) and [real official import-only Spark 4.1 RUNTIME_SMOKE #42297766098](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42297766098) **PASS**. The Job completed with exact version exit and no clinical data/Delta/Gold operations. This proves a usable **FABRIC_READY_CORE**; it does not prove Candidate Delta, clinical Mapping, OMOP Gold COMMIT or Pipeline E2E. See [Unified E2E](../../../openspec/changes/fabric-fhir-omop-unified-e2e/tasks.md) and [OMOP Foundation](../../../openspec/changes/fabric-omop-foundation/tasks.md).

Current development follows [Native execution ADR](../../architecture/design/FABRIC-NATIVE-NOTEBOOK-PIPELINE-ENVIRONMENT-ADR-20261031.md), [Deployment ownership spec](../../../openspec/specs/fabric-deployment-component-ownership/spec.md) and [Safe Operations](../../engineering/operations/SAFE-OPERATIONS.md). Azure Capacity, Terraform apply, Notebook run and SQL/Delta write require independently authorized, observed execution.

The previous [Fabric system history and exact past configuration inputs](FABRIC-HISTORY-20261105.md) remains byte-identical; old dated architecture assumptions are not current deployment proof.
