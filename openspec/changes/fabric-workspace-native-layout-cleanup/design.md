# Design — Workspace-native Git layout cleanup

## Existing canonical resource boundaries

The current Fabric Workspace `healthcare-omop` owns physical Notebook,
DataPipeline, Lakehouse, Environment and the manually created Warehouse
`dw-omop-5.4` (ID `7a6d08da-278d-4603-8a3b-28640110984c`).

Git-native item definitions are the immediate root-level directories
`nb_fhir_ingest.Notebook/`, `pl_fhir_ingest.DataPipeline/`,
`lh_omop_analytics.Lakehouse/`, `env_healthcare.Environment/`.
The old `notebooks/ingestion/.gitkeep` and `pipelines/.gitkeep` were
non-functional empty placeholders, not item definitions. Delete only those.

The separate `azure-fabric/warehouse/omop-cdm-5.4/` and
`azure-fabric/warehouse/omop-foundation/` folders contain checked-in
SQL migrations, writer/planner code and tests used by Self-Runner.
This physical Warehouse belongs to the Workspace, but is currently
**Workspace-only and protected** against automatic Git UpdateFromGit.
Putting scripts in a new `*.Warehouse` native folder is **not**
equivalent to moving or managing the actual Warehouse resource.

## Safety and acceptance

- Do not modify real Fabric resources, notebook business code, pipeline
  parameters, Git Item logicalId, SQL DDL, Warehouse/Blob data or Self-Runner.
- Keep existing Warehouse source paths unchanged for CI and migration scripts.
- Replace five legacy markdown directory links with existing native root
  Notebook/Pipeline paths, and correct stale `.gitkeep` status statements.
- Document logical Warehouse ownership in the canonical
  `documents/systems/azure-fabric/warehouse/CODE.md`.
- Validate OpenSpec (no specification delta), repository docs links,
  Notebook contract, PR checks and merged main before closing tasks.
