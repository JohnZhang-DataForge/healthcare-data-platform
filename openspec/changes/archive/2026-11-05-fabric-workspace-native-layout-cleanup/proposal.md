# Remove superseded Fabric workspace placeholders

## Context

The existing Fabric Workspace `healthcare-omop` has canonical native Git item folders
`nb_fhir_ingest.Notebook/`, `pl_fhir_ingest.DataPipeline/`, `lh_omop_analytics.Lakehouse/`
and `env_healthcare.Environment/`. Two earlier planning placeholders,
`notebooks/ingestion/.gitkeep` and `pipelines/.gitkeep`, now duplicate the native layout.

## Change

- Delete **only** these two empty obsolete `.gitkeep` files, dropping the empty directories.
- Clarify that `dw-omop-5.4` is physically in the **same Fabric Workspace**, but is an
  existing, manually created, **Workspace-only** Warehouse protected from Git UpdateFromGit.
- Preserve the SQL DDL, Writer, migrations and tests in `azure-fabric/warehouse/`:
  these are source files, **not a Fabric native Warehouse item definition**.

## Non-goals and safety

No Warehouse creation, deletion, migration, Git serialization, pipeline change or Spark execution.
Do not create a `dw-omop-5.4.Warehouse/` native Git item until a separate reviewed migration
explicitly updates Warehouse protection, item identity and Git synchronization policy.
