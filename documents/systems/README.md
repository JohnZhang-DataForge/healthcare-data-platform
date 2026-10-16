# Systems — Subsystem documentation

> **Migration stage: PREPARATION.** The new paths are staged copies while the repository navigational entry points, governance and CODE-map CI still refer to the original documentation locations. Until those references have been migrated and validated, the original documents remain authoritative. No application source or runtime deployment is moved by this step.

## Data Platform

- [Local Data Platform](data-platform/README.md) — Synthea generation, landing/discovery, Airflow, Spark, OMOP writer, PostgreSQL, and component-level source maps.

## Subsystems to migrate later

- [Azure / Microsoft Fabric (current location)](../components/azure-fabric/README.md) — developing OMOP analytics replica. Documentation relocation and source-map completion are deferred.
- [Platform Portal (current location)](../components/platform-portal/README.md) — developing OpenLineage / Marquez observability. Documentation relocation and source-map completion are deferred.

The intended final structure is `systems/data-platform/`, `systems/azure-fabric/` and `systems/platform-portal/` as peers. Azure and Portal folders will be created when their documentation migration is approved; no placeholder is treated as delivered functionality.
