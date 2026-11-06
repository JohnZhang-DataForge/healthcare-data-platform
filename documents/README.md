# Healthcare Data Platform — Documentation

Human-readable, current component navigation. Select a system overview first, then its CODE map for source files. Historical PR/Run timelines live in archived changes and historical snapshots, not at the top of this page.

## Systems

| System | What it owns | Source root |
| --- | --- | --- |
| [Local Data Platform](systems/data-platform/README.md) | Airflow, Spark, source producers and OMOP transactional writers; operational Task compatibility paths remain | [Local source](../local-data-platform/) |
| [Azure / Fabric](systems/azure-fabric/README.md) | Native Notebook/Pipeline/Environment, Warehouse schema/Writer, Terraform | [Fabric source](../azure-fabric/) |
| [Platform Portal](systems/platform-portal/README.md) | Marquez, OpenLineage, PG14 and public read-only presentation | [Portal source](../platform-portal/) |
| [Shared Data Engine](systems/data-platform/shared-engine/README.md) | One platform-neutral Python/PySpark Wheel | [Shared source](../shared-data-engine/) |

## Architecture and engineering

**先读批准的业务架构，再读最近的任务：** [2026-10-30 Medallion Canonical ADR](architecture/design/FABRIC-MEDALLION-CANONICAL-ADR-20261030.md) 明确 **CSV/FHIR/HL7 各有 Source/Entity Adapter → 单一 Canonical Patient/Encounter → 共享 OMOP Mapper/DQ/Identity/Reconciliation**；[2026-10-31 Fabric Native ADR](architecture/design/FABRIC-NATIVE-NOTEBOOK-PIPELINE-ENVIRONMENT-ADR-20261031.md) 固定 Notebook/Pipeline/唯一 Wheel 的执行边界；[Shared Engine Ownership](engineering/development/SHARED-DATA-ENGINE-STRUCTURE-AND-OWNERSHIP.md) 固定代码 Owner。Local PG CDM→Fabric 快照复制是另一项尚未完成的数据产品，并非 FHIR→Canonical→OMOP 的先决链路。目标共享架构不代表 Local 旧生产转换代码已经全部迁移。

[Architecture](architecture/SYSTEM-OVERVIEW.md) · [Data Flow](architecture/DATA-FLOW.md) · [Architecture Decisions](architecture/decisions/README.md) · [Engineering](engineering/README.md) · [Safe Operations](engineering/operations/SAFE-OPERATIONS.md) · [Human-readable directory map](engineering/development/REPOSITORY-STRUCTURE-AND-HUMAN-NAVIGATION.md).

Agents start with [root AGENTS.md](../AGENTS.md). New capabilities follow [OpenSpec lifecycle](engineering/development/OPENSPEC-DEVELOPMENT-LIFECYCLE.md), [Active Changes](../openspec/changes/) and [Current Specs](../openspec/specs/). [Archive](../openspec/changes/archive/) preserves accepted history.

## Evidence boundary

Local Synthea/CSV→Airflow/Spark→PG17 Person/Visit previously reached E2E COMMIT and independent readback. The Shared Engine 0.1.3 Environment Publish and isolated Spark Import also passed, but formal business Fabric FHIR/OMOP Gold E2E requires separate evidence. [Published Environment details](systems/azure-fabric/environments/CODE.md). Public Marquez Browser UX passed isolated Chromium/WebKit verification; public frontend controls are not API permissions. [Public Web overview](systems/platform-portal/portal/PUBLIC-MARQUEZ-WEB.md).

Full prior directory migration notes, old deployment assumptions and dated acceptance/failure history are preserved **unchanged** in [Document Index History](INDEX-HISTORY-20261105.md), not treated as current project state.
