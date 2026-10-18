# Systems — Subsystem documentation

> **Status: ACTIVE (Data Platform).** The five local component documents and CODE maps are now served from `systems/data-platform/`, with CI checking this path. Superseded originals are retained in Git history rather than the current Main tree. Azure/Fabric's canonical overview and source map live here; runnable Terraform is in `azure-fabric/infra-terraform/` only. Platform Portal remains at the old documentation path; staging does not imply deployment or end-to-end acceptance.

## Data Platform

- [Local Data Platform](data-platform/README.md) — Synthea generation, landing/discovery, Airflow, Spark, OMOP writer, PostgreSQL, and component-level source maps.

## Azure / Fabric — documentation staged

- [Azure / Microsoft Fabric](azure-fabric/README.md) · [CODE / source map](azure-fabric/CODE.md) — OneLake-first analytical replica, active Terraform source inventory and reserved future business modules. Old component brief remains during transition.

## Subsystems to migrate later

- [Platform Portal (current location)](../components/platform-portal/README.md) — developing OpenLineage / Marquez observability. Documentation relocation and source-map completion are deferred.

The intended final structure is `systems/data-platform/`, `systems/azure-fabric/` and `systems/platform-portal/` as peers. Azure/Fabric documentation and canonical Terraform source have migrated, and the old `azure/` path has been retired. Fabric Notebook/Pipeline placeholders are not delivered business functionality. Platform Portal has not been migrated. Placeholders are not delivered functionality.
