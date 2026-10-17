# Fabric Notebooks — processing and Delta load

The Notebook component belongs to the existing Fabric Workspace `healthcare-omop`. Its future **native Git item sources** belong under [`azure-fabric/workspaces/healthcare-omop/notebooks/`](../../../../azure-fabric/workspaces/healthcare-omop/notebooks/), currently with a reserved `ingestion/` grouping.

The planned Notebook receives `export_id` and `manifest_uri` from the Data Pipeline, reads the **already exported** local OMOP snapshot from Azure Blob, validates the manifest, counts, schema, PK uniqueness, FK integrity, and hashes, then performs repeatable/controlled Delta loading into a Lakehouse. It does **not** redo local Synthea/Canonical/OMOP mapping.

**Current implementation: NOT BUILT.** There are no `*.Notebook/` item folders or connected Git Integration in the workspace source tree. The [Terraform-owned Bootstrap Notebook](../../../../azure-fabric/infra-terraform/modules/notebook/definitions/notebook-content.py) deliberately raises `RuntimeError`; that file belongs to Terraform, not to this component's Git-native source map.

When a real Notebook is created, retain its Fabric-created item folder, `.platform` identity and actual `notebook-content.py`/other provider-generated files. Decide a single deployment owner (Fabric Git or Terraform), preserve the existing Item GUID and validate runtime/permissions before enabling real data writes. Do not invent metadata merely to fill this directory.

**Sources:** [Notebooks CODE.md](CODE.md) · [Pipelines](../pipelines/README.md) · [Azure-Fabric system](../README.md) · [Source tree](../../../../azure-fabric/README.md).
