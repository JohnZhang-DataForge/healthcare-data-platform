# Azure & Microsoft Fabric infrastructure

Terraform configuration for the project's **Azure storage and Microsoft Fabric analytics infrastructure**. The intended Azure data flow starts with an OMOP export to an existing Blob landing area, then uses a Fabric Data Pipeline and Notebook to load a OneLake Lakehouse.

## Directory layout

| Folder | Contents |
| --- | --- |
| [`components/`](components/) | Independent Terraform root modules with environment-specific configuration |
| [`modules/`](modules/) | Reusable Terraform definitions and IAM boundaries |
| [`docs/`](docs/) | Infrastructure architecture and permission details |

The component roots include `storage`, `workspace`, `onelake`, `notebook`, `data-factory`, `warehouse`, and `foundation-iam`. The first implementation focuses on **OneLake / Notebook / Data Pipeline**, not Warehouse.

## Project scope

Existing storage and workspace resources are treated separately from proposed new Fabric items. The Lakehouse, Notebook, and Data Pipeline have documented **Terraform Plan results, but no corresponding Apply or completed cloud data pipeline acceptance**.

The companion Self-Runner repository hosts the manual `Azure-Infra-TF` workflow. Terraform state is stored in separate Azure Blob backend keys per component; configuration files are not evidence of live deployment.

For technical implementation history, IAM, state boundaries, and test evidence, see [Technical Reference](TECHNICAL-REFERENCE.md), [Infrastructure Architecture](docs/ARCHITECTURE.md), and the [Azure/Fabric component](../../documents/components/azure-fabric/README.md).

The old one-off Terraform smoke test modules have been removed from Main.
