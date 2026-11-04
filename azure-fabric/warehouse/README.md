# Fabric Warehouse SQL source and Workspace ownership

## Physical Fabric ownership

The existing OMOP Warehouse **`dw-omop-5.4` is an item of the same
`healthcare-omop` Microsoft Fabric Workspace** as the Notebook, Pipeline,
Environment and Lakehouse.

| Fabric item | Physical identity | Git authoring location |
|---|---|---|
| Workspace | `healthcare-omop` / `745ce03b-15b6-4870-b0e5-8c5750aa18dc` | `azure-fabric/workspaces/healthcare-omop/` |
| Notebook | `nb_fhir_ingest` / `8311ab6b-3484-4e96-8370-badeeb751633` | `workspaces/healthcare-omop/nb_fhir_ingest.Notebook/` |
| Pipeline | `pl_fhir_ingest` | `workspaces/healthcare-omop/pl_fhir_ingest.DataPipeline/` |
| Environment | `env_healthcare` | `workspaces/healthcare-omop/env_healthcare.Environment/` |
| Lakehouse | `lh_omop_analytics` / `e67c42ee-5ab2-4bc8-a013-7bdf9741ef68` | `workspaces/healthcare-omop/lh_omop_analytics.Lakehouse/` |
| **Warehouse** | **`dw-omop-5.4` / `7a6d08da-278d-4603-8a3b-28640110984c`** | **Workspace-only actual item; SQL source in `azure-fabric/warehouse/`** |

This is a **physical resource ownership** vs. **Git source layout** distinction.
The manually created Warehouse already exists in the Fabric Workspace, and the
current Git UpdateFromGit protection intentionally treats it as an existing
Workspace-only resource. There is **no native**
`workspaces/healthcare-omop/dw-omop-5.4.Warehouse/` in this repository.

## What is stored here

- [`omop-cdm-5.4/`](./omop-cdm-5.4/): reviewed official CDM 5.4 adapted SQL
  DDL files, tests and manifests; deployed schema 39 tables / 432 columns.
- [`omop-foundation/`](./omop-foundation/): SQL management/audit schemas,
  identity planners, Concept Profile gate, tests and manifests.

These files are **migration/development sources** run by separately authorized
Self-Runner processes, not Fabric Git item definitions. Never relocate them
under the native Workspace Git folder as though they were a `.Warehouse` item
without an explicit OpenSpec migration, updating every dependency and CI path,
and an independently reviewed real Fabric item GUID/type and Git protection
verification. A name-only match is not sufficient.

The old placeholder directories `workspaces/healthcare-omop/notebooks/ingestion/`
and `workspaces/healthcare-omop/pipelines/` were superseded by the actual native
`*.Notebook` and `*.DataPipeline` item folders, and are removed.

No data, deployment, Warehouse schema or Workspace item was modified by this
repository layout cleanup.
