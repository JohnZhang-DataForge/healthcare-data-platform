# Azure / Microsoft Fabric analytics

This component describes the planned **analytics copy of standardized OMOP data** in Microsoft Fabric.

## Intended data path

1. Export a consistent, read-only snapshot from local PostgreSQL OMOP.
2. Publish the snapshot to an existing Azure Blob landing area.
3. Orchestrate a Fabric PySpark Notebook through a Fabric Data Pipeline.
4. Validate and load the data into a OneLake Lakehouse.

## What exists today

Terraform code for Lakehouse, Notebook, and Data Pipeline items and successful **Plan-only** evidence. The actual Azure business data export, Notebook ETL, cloud resource Apply, and full OneLake ingestion have not been completed.

**Related material**

- [Azure infrastructure code](../../../azure/infra-terraform/README.md)
- [Detailed architecture and validation notes](TECHNICAL-REFERENCE.md)
- [System data flow](../../architecture/DATA-FLOW.md)
- [Current project status](../../status/PROJECT-STATUS.md)

[All components](../README.md).
