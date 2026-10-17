# Fabric Data Pipelines — orchestration

The Pipeline component belongs to the existing Fabric Workspace `healthcare-omop`. Its future **native Git item sources** belong under [`azure-fabric/workspaces/healthcare-omop/pipelines/`](../../../../azure-fabric/workspaces/healthcare-omop/pipelines/).

A future Fabric Data Pipeline receives `export_id` and `manifest_uri`, invokes a real [Fabric Notebook](../notebooks/README.md), and enforces explicit success/failure gates before acknowledging a completed analytical snapshot. This is a Fabric **Data Pipeline item**, not an Azure Data Factory service resource, and it is **not** the PySpark transformation implementation.

**Current implementation: NOT BUILT.** There is no native `*.DataPipeline/` source item or Git integration; only a `.gitkeep` placeholder. Terraform currently holds a [Fail activity definition](../../../../azure-fabric/infra-terraform/modules/data-factory/definitions/pipeline-disabled.json) and an [unexecuted Notebook activity template](../../../../azure-fabric/infra-terraform/modules/data-factory/definitions/pipeline-notebook.json); the fail-closed default must remain until the actual Notebook identity and processing code exist.

Future Fabric Git items should retain their generated `.platform` and `pipeline-content.json`; do not fabricate item metadata or deploy an empty-success activity. Select one deployment owner for the same Pipeline identity before enabling Fabric Git sync alongside Terraform.

**Sources:** [Pipelines CODE.md](CODE.md) · [Notebooks](../notebooks/README.md) · [Azure-Fabric system](../README.md) · [Source tree](../../../../azure-fabric/README.md).
