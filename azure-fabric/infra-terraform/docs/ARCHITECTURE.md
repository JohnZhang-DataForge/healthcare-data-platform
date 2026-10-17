# Healthcare Azure Terraform Resource/IAM Architecture v2

Status: **code only; PLAN-ONLY workflow**; no Apply or Destroy authorized.

```text
Self-Runner Actions → Azure-Infra-TF (select component / dev)
      |
      v
healthcare-data-platform/azure-fabric/infra-terraform/components/<component>/
      |   versions.tf, providers.tf, variables.tf, modules.tf, outputs.tf
      |   environments/dev.tfvars   (resource settings + concrete WHO/ROLE)
      |
      v
azure-fabric/infra-terraform/modules/<component>/
      main.tf    — resource/data lookup definitions
      iam.tf     — provider-supported permission binding HOW (optional)
      outputs.tf — resource IDs and new assignment IDs
      |
      v
tfstate: johnzhang/tfstate/dev/<component>.tfstate (independent key per root)
```

## IAM ownership rules

1. **Component-owned IAM**. Storage container-level grants live in `modules/storage/iam.tf`; their principal OBJECT IDs and role names come from `components/storage/environments/dev.tfvars`. Workspace-level Fabric grants live in `modules/workspace/iam.tf`. OneLake data path roles live in `modules/onelake/iam.tf` using provider **preview** (empty default). All access changes are considered with the corresponding root's resources in the same Terraform plan/state.
2. **Foundation IAM is NOT a catch-all**. `foundation-iam` exclusively manages optionally NEW shared Azure Resource Group-level roles; it does not touch existing Portal-created github-terraform Bootstrap grants. Resource-specific role bindings must not be repeated here.
3. **Do not fabricate incompatible IAM**. Fabric item permissions and Azure RBAC are different APIs. The Data Pipeline/Notebook/Warehouse module IAM files record the supported boundary; Warehouse SQL object grants are handled by a separate SQL delivery process, not falsely declared with `azurerm_role_assignment`.
4. **No privilege escalation / duplicate grants**. Bootstrap credentials and `tfstate` access remain operator-owned. Adding assignments requires Microsoft.Authorization/roleAssignments/write beyond plain Contributor; existing grants must be imported/adopted only after separate approval.
5. **Ownership lifecycle**. Only a root component should own a grant. Keep per-environment keys separate. Avoid cyclic workspace/item/module references; the Workspace GUID is explicitly passed for non-workspace items. Separate root states mean plans are independent and no root automatically applies another root.

## OneLake IAM preview

The Microsoft Fabric provider supports `fabric_onelake_data_access_security` but marks it preview. The `onelake` component explicitly opts in with `preview = true`. Roles are conditional on `data_access_roles`; default `{}` creates nothing. Reviewing paths, members, access levels, Fabric tenant/Service Principal permissions and existing role import is mandatory before a future Apply.

## Acceptance scope

- Previous storage-only plan: Run 38761100632, PASS, `apply=no`.
- New IAM ownership refactor: storage + foundation-iam plan regressions required.
- Fabric roots: scaffold only until Fabric permission/workspace setup and provider-specific validation succeed.
- Workflows remain manual **PLAN ONLY**, no Terraform Apply/Destroy steps, no migrations of old backend state and no modifications to the existing Blob test file.

## Regression proof (2026-10-15)

The component IAM refactor passed live OIDC remote-state plans:
- Foundation IAM: [Run 38767227655, attempt 2](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38767227655), PASS; no new grant assignments.
- Storage IAM: [Run 38761100632, rerun](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38761100632), PASS; existing OMOP/johnzhang lookup.
- Both: recursive Terraform formatting, remote state, validation/plan; no Apply/Destroy.

Other Fabric components cannot be called verified merely from recursive formatting and require separate Fabric provider validation against real Fabric tenant permissions. OneLake access security is preview and does not auto-create any roles while `data_access_roles = {}`.
