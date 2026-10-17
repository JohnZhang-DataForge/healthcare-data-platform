# Azure / Microsoft Fabric Terraform — technical design and evidence

**Status (October 16, 2026):** infrastructure source is present in `azure-fabric/infra-terraform/`, with all seven roots **successfully planned after the source-path cutover**; this is not deployment or cloud-data E2E acceptance. The [Self-Runner Azure-Infra-TF workflow](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/.github/workflows/azure-infra.yaml) defaults to **Plan** but technically supports an explicitly selected **Apply**. It does not expose Destroy. None of these code-organization changes authorizes Apply. See the [developer entry](../README.md) for the compact directory guide and [code-root guide](../../README.md) for business-code boundaries.

## Root/module implementation model

```text
Self-Runner Azure-Infra-TF (component / dev / operation)
    |
    v
azure-fabric/infra-terraform/components/<component>/
    versions.tf / providers.tf / modules.tf / variables.tf
    iam.tf / outputs.tf / environments/dev.tfvars
    |
    | source = ../../modules/<component>
    v
azure-fabric/infra-terraform/modules/<component>/
    main.tf    resource definitions and data lookups
    iam.tf     optional component-specific permissions and boundaries
    outputs.tf resource IDs / outputs
    |
    v
Azure Blob remote State: johnzhang/tfstate/dev/<component>.tfstate
```

There are exactly **seven separately selected roots**: `storage`, `workspace`, `onelake`, `data-factory`, `notebook`, `warehouse`, `foundation-iam`. Per-root State isolation allows independent Plans but **does not apply dependencies automatically**. Non-workspace Fabric items take the existing Workspace GUID from workflow variables; never invent a GUID or assume it can reference an unapplied separate root output.

## IAM and existing resource boundaries

| Root | IAM owner | Current default / boundary |
| --- | --- | --- |
| `storage` | [`modules/storage/iam.tf`](../modules/storage/iam.tf) | Existing Storage/Blob resource looked up, not created here; `blob_role_assignments={}` means no additional component grants |
| `workspace` | [`modules/workspace/iam.tf`](../modules/workspace/iam.tf) | Fabric Workspace Admin/Member/Contributor/Viewer grants; `role_assignments={}` by default |
| `onelake` | [`modules/onelake/iam.tf`](../modules/onelake/iam.tf) | `fabric_onelake_data_access_security` **preview**; `data_access_roles={}` means no grants |
| `data-factory` / `notebook` | Each module's `iam.tf` documents item/workspace boundary | Do not fabricate item permissions unsupported by the actual Fabric provider |
| `warehouse` | [`modules/warehouse/iam.tf`](../modules/warehouse/iam.tf) | Workspace membership; SQL `GRANT/REVOKE` belong to a separate SQL delivery process |
| `foundation-iam` | [`modules/foundation-iam/iam.tf`](../modules/foundation-iam/iam.tf) | Optional shared Resource Group RBAC only, `shared_role_bindings={}` by default; never duplicate per-component grants |

- **This IaC does not create Azure role definitions.** It can optionally assign existing Azure role names to Entra **object IDs**. Normal RG Contributor does **not** include `Microsoft.Authorization/roleAssignments/write`; new assignments require appropriate authorization. No escalation, new principal IDs or duplicate grants should be fabricated to make a Plan succeed.
- **Preserve manually bootstrapped infrastructure:** the existing OMOP Resource Group/Storage Account, `johnzhang` Storage, `landing`, `tfstate` and bootstrap Service Principal permissions are not all lifecycle-managed by these modules. Import/reconcile before any proposed adoption; do not recreate Portal-assigned RG Contributor, Blob Data Contributor or Service Principal OIDC federation.
- **Existing Fabric Workspace:** `healthcare-omop` was provisioned manually. Its identity, capacity/Trial and current permissions need independent verification. The workflow explicitly blocks `workspace` **Apply** until `module.workspace.fabric_workspace.current` is present in the corresponding Terraform State. A matching name in code is not an import or permission grant.
- **Azure RBAC is not Fabric data authorization.** Workspace item roles, OneLake data-access rules and Blob data-plane RBAC are separate from Azure Resource Group rights. The `onelake` root enables preview via [`components/onelake/providers.tf`](../components/onelake/providers.tf); granting access requires explicit non-empty members/paths, live provider support and review.

## Remote State, OIDC and workflow boundaries

Terraform root State keys are unchanged by the source-path copy: `dev/storage.tfstate`, `dev/workspace.tfstate`, `dev/onelake.tfstate`, `dev/data-factory.tfstate`, `dev/notebook.tfstate`, `dev/warehouse.tfstate`, `dev/foundation-iam.tfstate`. The private backend is the pre-existing `johnzhang/tfstate` Blob container, authenticated with GitHub OIDC/Azure AD. Runner local disk is ephemeral and must not own permanent State. Never commit State, planfile, credentials, actual `.env`, personal data or secrets.

The OIDC federated identity is bound to **Self-Runner** rather than `healthcare-data-platform`. The manual workflow checks out the Healthcare repository from `main`, and the log reports the **actual Healthcare source SHA**. Its component/environment input is allowlisted; the operation can be `plan` or `apply` (default Plan). It performs Terraform formatting, remote backend init, validation, and saved Plan with locking. Apply, if separately authorized, uses the exact saved Plan and rejects plans containing deletion/replacement; Destroy is not provided. These workflow guards are *not* a substitute for an explicit infrastructure change authorization and independent State/import review.

The former `components/iam` / `modules/iam` root was replaced with `foundation-iam`. Historical `dev/iam.tfstate` is **not** migrated or removed. If a State object is discovered at that key, inspect before adoption. Old one-off OIDC/Blob smoke roots were removed earlier; their historical evidence exists in Git history and must not be reintroduced as deployable roots. Two old manual Self-Runner smoke workflows refer to frozen Healthcare commits and are **not** an alternative to the normal Azure-Infra-TF workflow.

The original [`azure/infra-terraform/`](../../../azure/infra-terraform/README.md) remains physically present. The new copy is selected for execution. **Do not independently Apply both copies against identical backend State keys.**

## Fabric Bootstrap and source ownership

Terraform currently creates **Item shells**, not working business ETL. The [Notebook module](../modules/notebook/main.tf) reads `modules/notebook/definitions/notebook-content.py` with parameter cells `export_id` and `manifest_uri` and raises `RuntimeError` until ETL is implemented. The [Pipeline module](../modules/data-factory/main.tf) uses a [Fail activity definition](../modules/data-factory/definitions/pipeline-disabled.json) when `notebook_id=""`; supplying a real GUID selects [Notebook activity JSON](../modules/data-factory/definitions/pipeline-notebook.json) but **does not** make the Notebook a working loader. There are no real PG Exporter/Blob publication or Delta load implementations yet. Warehouse is optional, not in the first MVP path. Fabric Trial Capacity is not created by these Terraform roots.

The new `azure-fabric/workspaces/healthcare-omop/` path is reserved for Fabric Git-native items with generated `.platform` metadata. Do not simply duplicate these Bootstrap sources into `*.Notebook/` / `*.DataPipeline/` and claim Git integration. When the actual Workspace Git connection and item ownership are designed, reconcile identities and choose **one authoritative deployment mechanism** for each Fabric Item before replacing the fail-closed Bootstrap.

## Verified Plan evidence

These are bounded **historical GitHub Actions outcomes**, not a live query of cloud resources, permissions or Terraform State today.

| Date/phase | Resource/root | Evidence | Verified scope |
| --- | --- | --- | --- |
| October 15, OIDC/backend | `storage` | [Run 38761100632](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38761100632) | Existing OMOP/johnzhang lookup, remote backend, Plan; no Apply |
| October 15, IAM refactor | `foundation-iam` | [Run 38767227655, attempt 2](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38767227655/attempts/2) | IAM root Plan with empty shared grants |
| October 15, Fabric provider fix | `onelake` | [Run 38797932758, attempt 2](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38797932758/attempts/2) | Fabric provider `microsoft/fabric 1.13.0` resolution; one Lakehouse addition proposed |
| October 15, MVP Plans | `onelake`, `notebook`, `data-factory` | [Runs 38799966270](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38799966270), [38832798550](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38832798550), [38832801221](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38832801221) | Each Plan PASS and separately proposed **1 add / 0 change / 0 destroy**, no Apply |
| **October 16, new-path regression** | `storage`, `workspace`, `onelake`, `data-factory`, `notebook`, `warehouse`, `foundation-iam` | See individual runs below | All seven manual Plan Jobs SUCCESS; **operation=plan**, no Apply requested |

**New-path Plan-only runs (2026-10-16 EDT):** [storage 38988729752](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38988729752), [workspace 38988731519](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38988731519), [onelake 38988732887](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38988732887), [data-factory 38988734473](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38988734473), [notebook 38988735923](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38988735923), [warehouse 38988737433](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38988737433), [foundation-iam 38988738899](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38988738899). Their GitHub Actions job titles are `plan / <component> / dev`; all seven Jobs have `conclusion=success` and the [read-only dispatch workflow 38988718305](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38988718305) succeeded. Exact resource add/change/delete counts for this *new* regression should be read from each archived Plan log, **not inferred from job success**.

These new runs supersede older statements such as “post-cutover Plan pending” or “Fabric provider not yet validated”. **They do not supersede** the requirement for import, Blob data permissions, Fabric tenant authorization, actual Fabric Item creation, Notebook/Pipeline E2E or independently verified Delta data.

## Deployment and data boundaries

- Confirm live Workspace ID/capacity, manually created Blob, IAM principals and existing Fabric Items **before** any future Apply. Never assume empty Terraform State implies there is no pre-existing resource.
- Keep `storage` and `workspace` as separately managed legacy-adoption concerns. OneLake Lakehouse, Notebook and Pipeline are the minimum proposed Fabric items; Warehouse and any new Azure Data Factory account are **not** required.
- Fabric Workspace data access does not automatically grant Blob permissions. Exporter snapshots should be consistent, immutable and verified with Manifest/hash before any Notebook can accept them.
- Do not claim full Azure analytics completion until the PG snapshot, Blob READY publication, Notebook/Delta idempotency and independent reconciliation have run successfully with durable evidence.
