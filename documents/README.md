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

[Architecture](architecture/SYSTEM-OVERVIEW.md) · [Data Flow](architecture/DATA-FLOW.md) · [Architecture Decisions](architecture/decisions/README.md) · [Engineering](engineering/README.md) · [Safe Operations](engineering/operations/SAFE-OPERATIONS.md) · [Human-readable directory map](engineering/development/REPOSITORY-STRUCTURE-AND-HUMAN-NAVIGATION.md).

Agents start with [root AGENTS.md](../AGENTS.md). New capabilities follow [OpenSpec lifecycle](engineering/development/OPENSPEC-DEVELOPMENT-LIFECYCLE.md), [Active Changes](../openspec/changes/) and [Current Specs](../openspec/specs/). [Archive](../openspec/changes/archive/) preserves accepted history.

## Evidence boundary

Local Synthea/CSV→Airflow/Spark→PG17 Person/Visit previously reached E2E COMMIT and independent readback. The Shared Engine 0.1.3 Environment Publish and isolated Spark Import also passed, but formal business Fabric FHIR/OMOP Gold E2E requires separate evidence. [Published Environment details](systems/azure-fabric/environments/CODE.md). Public Marquez Browser UX passed isolated Chromium/WebKit verification; public frontend controls are not API permissions. [Public Web overview](systems/platform-portal/portal/PUBLIC-MARQUEZ-WEB.md).

Full prior directory migration notes, old deployment assumptions and dated acceptance/failure history are preserved **unchanged** in [Document Index History](INDEX-HISTORY-20261105.md), not treated as current project state.
