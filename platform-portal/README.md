# Platform Portal — data lineage and observability

This directory contains the **OpenLineage and Marquez observability subsystem** for the Healthcare Data Platform.

It collects workflow and processing metadata so that jobs, runs, and related datasets can be explored separately from the clinical data stored in OMOP PostgreSQL.

## Contents

| Folder | Purpose |
| --- | --- |
| [`marquez/`](marquez/) | Marquez deployment configuration and service utilities |
| [`openlineage/airflow/`](openlineage/airflow/README.md) | Airflow integration and event-verification scripts |
| [`openlineage/spark/`](openlineage/spark/README.md) | Standalone Spark/OpenLineage probe, renderer, and tests |
| [`postgres/`](postgres/README.md) | PostgreSQL 14 manifests for the Marquez metadata store |

Airflow integration and the separate Spark smoke have some recorded real test evidence. **Complete lineage for the production-like Person/Visit workload is not yet established.**

More background is in the [Portal component documentation](../documents/components/platform-portal/README.md) and [architecture overview](../documents/architecture/SYSTEM-OVERVIEW.md).
