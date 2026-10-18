# Systems — Subsystem documentation

> **Status: ACTIVE.** Azure/Fabric and the five local Data Platform components have canonical documentation under `documents/systems/`. Platform Portal's current documentation remains under `documents/components/platform-portal/` pending its own migration. Source-tree migration is not cloud deployment or end-to-end acceptance.

## Data Platform

- [Local Data Platform](data-platform/README.md) — Synthea, landing/discovery, Airflow, Spark, OMOP writer, PostgreSQL, and component source maps.

## Azure / Fabric

- [Azure / Microsoft Fabric](azure-fabric/README.md) · [CODE / source map](azure-fabric/CODE.md) — OneLake-first analytical replica, Terraform in `azure-fabric/infra-terraform/`, and reserved Fabric-native Notebook/Pipeline sources.
- The legacy `azure/infra-terraform/` and `documents/components/azure-fabric/` paths were retired after source parity, document-link and workflow audits. The Azure Terraform plan-only evidence is preserved; no Apply or business E2E is implied.

## Subsystems to migrate later

- [Platform Portal (current location)](../components/platform-portal/README.md) — OpenLineage/Marquez observability. Documentation relocation and source-map completion remain separate work.

The `systems/platform-portal/` directory is a future target, not a current path.
