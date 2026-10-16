# Platform components

Short introductions to the major functional parts of the Healthcare Data Platform, from synthetic source generation through OMOP storage and analytics.

| Component | What it does |
| --- | --- |
| [Synthea](synthea/README.md) | Generates synthetic clinical source batches |
| [Landing](landing/README.md) | Validates and discovers published batches and tracks claims |
| [Airflow](airflow/README.md) | Coordinates processing and writer tasks |
| [Spark](spark/README.md) | Transforms clinical records and checks data quality |
| [OMOP Writer](omop/README.md) | Commits standardized Person/Visit data to PostgreSQL |
| [Platform Portal](platform-portal/README.md) | Observes workflow metadata and data lineage using Marquez |
| [Azure/Fabric](azure-fabric/README.md) | Planned analytical copy using Azure Blob, Fabric Notebook, and OneLake |

The actual source lives in [`apps/`](../../apps/README.md), [`airflow/`](../../airflow/README.md), [`spark/`](../../spark/README.md), and other top-level directories.

For the full architecture, see [System Overview](../architecture/SYSTEM-OVERVIEW.md). Older Task-named code paths are cataloged in the [legacy refactor plan](LEGACY-CODE-REFACTOR-PLAN.md).
