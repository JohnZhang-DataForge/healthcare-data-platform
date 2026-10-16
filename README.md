# Healthcare Data Platform

A hands-on healthcare data engineering project using **synthetic clinical data** to explore batch ingestion, distributed processing, OMOP CDM, infrastructure automation, and data lineage.

The working local data path combines **Kubernetes, SeaweedFS (S3-compatible storage), Airflow, PySpark, and PostgreSQL OMOP**. A separate observability subsystem uses **OpenLineage and Marquez**. Azure / Microsoft Fabric integration is an additional, partially implemented roadmap, not a completed production pipeline.

## What this project demonstrates

- Independent generation and publication of validated Synthea batches
- Controlled ingestion and PySpark transformation of Patient / Encounter data
- Transactional loading of **OMOP Person and Visit** with batch identity, reconciliation, and idempotent replay protection
- Infrastructure-as-code for planned Microsoft Fabric Lakehouse, Notebook, and Data Pipeline resources
- Exploring Airflow/Spark data lineage in Marquez

The completed **Person / Visit** workflow has a recorded real end-to-end acceptance. Condition and other domains, full business dataset lineage, and cloud analytics end-to-end are not yet completed.

## Repository guide

| Directory | What you'll find |
| --- | --- |
| [`apps/`](apps/README.md) | Python applications for source generation, landing discovery, claims, and OMOP writing |
| [`airflow/`](airflow/README.md) | Airflow DAGs and orchestration helpers |
| [`spark/`](spark/README.md) | PySpark transformations, shared utilities, schemas, and job templates |
| [`sql/`](sql/README.md) | PostgreSQL SQL, staging, batch bookkeeping, and validation queries |
| [`contracts/`](contracts/README.md) | Versioned producer and writer data contracts |
| [`images/`](images/README.md) | Container build definitions |
| [`kubernetes/`](kubernetes/README.md) | Kubernetes workload manifests and templates |
| [`platform-portal/`](platform-portal/README.md) | OpenLineage/Marquez integration and supporting infrastructure |
| [`azure/infra-terraform/`](azure/infra-terraform/README.md) | Azure and Microsoft Fabric Terraform roots and modules |
| [`scripts/`](scripts/README.md) | Development and verification utilities |
| [`tests/`](tests/README.md) | Unit, contract, and regression tests |
| [`config/`](config/README.md) | Example local configuration |
| [`.github/`](.github/README.md) | GitHub Actions workflow definitions |
| [`documents/`](documents/README.md) | Architecture, components, operations, decisions, and project status |

## Architecture and evidence

The [system overview](documents/architecture/SYSTEM-OVERVIEW.md) explains the platform and its data flow. The [component guide](documents/components/README.md) and [project status](documents/status/PROJECT-STATUS.md) distinguish implemented features from proposals. [Historical test reports](documents/migration/LEGACY-DOCS-SNAPSHOT.md) remain accessible through Git history.

This is an evolving engineering lab using synthetic data, **not a production healthcare service or a one-command cluster installer**.
