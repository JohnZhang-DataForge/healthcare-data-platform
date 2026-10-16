# Systems — Subsystem documentation

> **Status: ACTIVE (Data Platform).** The five local component documents and CODE maps are now served from `systems/data-platform/`, with CI checking this path. Superseded originals are retained in Git history rather than the current Main tree. Azure/Fabric and Platform Portal continue at their current documentation paths until separate migration; this does not imply deployed or E2E-complete functionality.

## Data Platform

- [Local Data Platform](data-platform/README.md) — Synthea generation, landing/discovery, Airflow, Spark, OMOP writer, PostgreSQL, and component-level source maps.

## Subsystems to migrate later

- [Azure / Microsoft Fabric (current location)](../components/azure-fabric/README.md) — developing OMOP analytics replica. Documentation relocation and source-map completion are deferred.
- [Platform Portal (current location)](../components/platform-portal/README.md) — developing OpenLineage / Marquez observability. Documentation relocation and source-map completion are deferred.

The intended final structure is `systems/data-platform/`, `systems/azure-fabric/` and `systems/platform-portal/` as peers. Azure and Portal folders will be created when their documentation migration is approved; no placeholder is treated as delivered functionality.
