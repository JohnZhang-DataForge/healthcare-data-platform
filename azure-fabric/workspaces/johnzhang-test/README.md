# johnzhang-test: Fabric native Git items (source only)

This tree contains two native Fabric item definitions for a first no-data-write Smoke:

- `notebooks/nb_trial_smoke.Notebook/` — PySpark Notebook with stable `.platform` logicalId; prints a bounded PASS marker, does **not** read Blob or write OneLake.
- `pipelines/pl_trial_smoke.DataPipeline/` — TridentNotebook activity referencing the notebook's stable **logicalId**, and same-workspace all-zero `workspaceId` for Fabric binding. No schedule; never auto-run.

Ownership: `fabric-cicd` for Notebook + Pipeline only. Infrastructure (Workspace/Lakehouse/Connection) is Terraform-managed elsewhere. The root passed to `fabric-cicd` is `azure-fabric/workspaces/johnzhang-test/`, including both nested item folders. Neither this source commit nor CI validation publishes Fabric items. The GUID logical IDs are stable source identities, **not** live Fabric item GUIDs.

Pre-publish gates: read actual Terraform Workspace/Lakehouse outputs; review current Fabric inventory for same-name/different-logicalId conflicts; confirm service principal's Fabric Item create/update permissions; pin Healthcare SHA and item whitelist; disable orphan/deletion operations. After authorized publish, verify real item IDs and Pipeline-to-Notebook binding. Only then run a separately authorized no-write smoke and inspect Notebook/Pipeline run status and logs. OMOP data ETL is separate work.

Change authority: [deploy-fabric-connection-and-items](../../../openspec/changes/deploy-fabric-connection-and-items/tasks.md).
