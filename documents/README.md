# Project documentation

This directory brings together the **architecture, component explanations, technical decisions, and operating context** for the Healthcare Data Platform. It complements the source code without trying to duplicate it.

## Browse by topic

| Folder | What it covers |
| --- | --- |
| [`architecture/`](architecture/SYSTEM-OVERVIEW.md) | System architecture, processing/data flow, and infrastructure layout |
| [`components/`](components/README.md) | Responsibilities of Synthea, landing, Airflow, Spark, OMOP, Portal, and Azure/Fabric |
| [`decisions/`](decisions/README.md) | Major long-lived design choices and their rationale |
| [`development/`](development/DEVELOPMENT-WORKFLOW.md) | Engineering conventions, code organization, and testing practices |
| [`operations/`](operations/README.md) | Operational concepts, checks, and shared-resource safety |
| [`status/`](status/PROJECT-STATUS.md) | What has been implemented, verified, proposed, or left to do |
| [`migration/`](migration/MIGRATION-STATUS.md) | Documentation consolidation history, audit, and future OpenSpec preparation |

## Suggested reading

Start with the [system overview](architecture/SYSTEM-OVERVIEW.md) for the big picture, then browse the [components](components/README.md) or [data flow](architecture/DATA-FLOW.md) relevant to your interests. The [project status](status/PROJECT-STATUS.md) distinguishes verified capabilities from planned work.

Older TASK-based records were removed from the active source tree; the [historical documentation index](migration/LEGACY-DOCS-SNAPSHOT.md) links to their preserved Git snapshots.

[Back to the main project](../README.md).
