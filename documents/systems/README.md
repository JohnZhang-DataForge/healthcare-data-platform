# Systems — Subsystem documentation

> **Migration stage: NEW SOURCE MAPS.** Data Platform component docs and source maps are the destination for navigation and CODE-map CI. Old documentation copies remain temporarily for cleanup and rollback. Azure/Fabric and Platform Portal continue to use their existing paths until separately migrated; no runtime deployment is implied.

## Data Platform

- [Local Data Platform](data-platform/README.md) — Synthea generation, landing/discovery, Airflow, Spark, OMOP writer, PostgreSQL, and component-level source maps.

## Subsystems to migrate later

- [Azure / Microsoft Fabric (current location)](../components/azure-fabric/README.md) — developing OMOP analytics replica. Documentation relocation and source-map completion are deferred.
- [Platform Portal (current location)](../components/platform-portal/README.md) — developing OpenLineage / Marquez observability. Documentation relocation and source-map completion are deferred.

The intended final structure is `systems/data-platform/`, `systems/azure-fabric/` and `systems/platform-portal/` as peers. Azure and Portal folders will be created when their documentation migration is approved; no placeholder is treated as delivered functionality.
