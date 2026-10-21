# Fabric Terraform Environment — Single Root

This is the **only live Terraform Root** for Fabric infrastructure in the
current account. It calls the existing reusable `modules/workspace`,
`modules/onelake`, and `modules/connection` directly. Business Notebooks and
Pipelines belong to `fabric-cicd`, not Terraform.

## Naming and State

A **non-default Terraform CLI Workspace** is named exactly like its target
Microsoft Fabric Workspace. For example, `healthcare-omop` → `healthcare-omop`;
`healthcare-qa` → `healthcare-qa`. The Root derives the Fabric
`display_name` from `terraform.workspace` (not a duplicate input variable).
The AzureRM Backend base key is `fabric/platform.tfstate`, and each named
Terraform Workspace gets its **own State** under the same existing Backend.

The original seven independent Roots and unused Modules were retired from the
current Git tree. Their historical Terraform State blobs, e.g.
`dev/workspace.tfstate` and `dev/onelake.tfstate`, have NOT been removed,
migrated, or edited. Their source can be audited via the previous Git commit:
https://github.com/JohnZhang-DataForge/healthcare-data-platform/tree/20a6449000fe10eac642ab2dbcef37976339572b/azure-fabric/infra-terraform

## Existing `healthcare-omop` — Import is mandatory if not managed

1. Verify real Fabric Workspace GUID, Capacity and tenant identity.
2. Inspect the legacy State blobs and this composed Root State. Do not allow
   two active States to own the **same Fabric Workspace GUID**. A retired Root
   may still have remote State even when its HCL source is deleted.
3. Select `healthcare-omop` as Terraform CLI Workspace.
4. Only when its GUID is not already owned by another State, use the
   Workflow's explicit `adopt` action (Terraform Import) to record the
   existing Workspace as `module.workspace.fabric_workspace.current`.
5. Check `terraform state show` for exact GUID and display name, then
   `plan`. Never directly create another `healthcare-omop`.

`existing_workspace_imported` defaults to false; a normal Plan for the
existing `healthcare-omop` is guarded until imported. It is a safety
acknowledgement, not an automatic State lookup.

## Brand-new Workspace — No Import

For a new name (e.g. `healthcare-qa`), the same Root can select/create its
Terraform CLI Workspace and then plan/apply the matching Fabric Workspace,
Workspace IAM and Lakehouse automatically. The Runner uses Terraform variable
**defaults** when there is no exact `environments/<workspace>.tfvars` file,
so new names don't require copied Terraform code or a `dev.tfvars`.

You may add a version-controlled, **nonsecret** per-Workspace file
`environments/healthcare-qa.tfvars` later to override description, Lakehouse
name, role assignments or data access roles. A `connection` variable is opt-in
until the correct authorized Azure Blob Reader identity is configured.

## Runtime prerequisites and operations

Use the existing Self-Runner `Azure-Infra-TF` Workflow and its single-account
OIDC setup. It must have appropriate Fabric Provider/API, Capacity, Backend
AzureAD Blob and existing Landing permissions.

- `inspect`: read-only State/ownership diagnostics. Do this first for
  `healthcare-omop` (already created in Fabric).
- `adopt`: explicit State **write/import** for an existing Workspace GUID,
  after auditing old State ownership. Not required for truly new Workspaces.
- `plan`: inspect proposed changes (including the first creation for a
  *new* Workspace). No Fabric resource creation.
- `apply`: execute a fresh saved and checked Plan. Destruction/Replacement
  is blocked; existing `healthcare-omop` identity must remain unchanged.

The existing account's Capacity ID, Workspace GUID (for adoption), and
optional nonsecret Landing Connection metadata come from the configured
Runner environment. Do **not** commit credentials, secrets or actual backend
State. Capacity isn't created/purchased here.

**Status**: Static Terraform Init/Validate is not live Backend/Import/Plan/Apply
verification. Real OIDC permissions, State ownership, current Capacity and
connection access must be tested before declaring deployment success.
