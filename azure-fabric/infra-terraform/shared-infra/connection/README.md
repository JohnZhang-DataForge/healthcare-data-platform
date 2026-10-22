# Shared Fabric Azure Blob Connection

Standalone, optional Terraform Root reusing `../../modules/connection`. Backend base key `shared-infra/connection.tfstate`, **default Terraform CLI Workspace**; no Workspace/OneLake/Capacity ownership.

The committed instance `terraform.tfvars` now stages a single `healthcare-omop-landing-blob` AzureBlobs WorkspaceIdentity Connection candidate, while the reusable Terraform variable still defaults to `null` when no instance is configured. **Staging source does not mean cloud deployment.** Before any separate authorized Connection Plan/Apply, verify tenant-supported AzureBlobs connection metadata and supported user-controlled-code credentials, compare actual Storage and Fabric tenants, inventory existing matching connections, and approve a real Blob Reader principal. **Workspace identity does not support cross-tenant connections**, and connection creation alone never proves Notebook access. ServicePrincipal requires an existing Fabric Key Vault secret reference. Never commit or print secrets, tokens, or account keys. Existing connection ownership requires an explicit import decision; `prevent_destroy` remains active.

`connection_readiness.py` provides **read-only** live OIDC inspection of Azure subscription tenant, existing Storage account, account-scope IAM inventory, Fabric-supported AzureBlobs methods/credentials, and existing account connections. This does not write Azure/Fabric resources or Terraform State, grant permissions, or prove a Notebook read. The Self-Runner workflow must use an exact Healthcare source SHA and an inspect-only gate. The Root output `connection_id` becomes known only after a separately authorized Apply; source and Plan do not prove the Connection exists. **The previous Azure RBAC 403 was resolved** by a scoped Runner RBAC administration role. Reader Apply and independent ARM readback passed; Fabric Connection Apply, Fabric GET readback, and subsequent no-change Plan passed on 2026-10-22. See latest OpenSpec for exact IDs/Runs. **Actual Blob data-plane read has not yet been validated.**

See [OpenSpec](../../../../openspec/changes/deploy-fabric-connection-and-items/tasks.md).

### Provider 1.13.0 Workspace Identity skip-test caveat

Live [Self-Runner Plan #39710912279](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39710912279) rejects `credential_details.skip_test_connection=true` at Plan with `Unsupported skip test connection`. For this provider version use `false`; this does **not** make Fabric Workspace Identity Connection status health-check reliable. Actual Blob reads are the acceptance criterion. No Connection created by that failed Plan.

### Verified Control Plane checkpoint (2026-10-22)

- Azure Blob `johnzhang/landing` Reader identity: `1ae64649-a7c3-497e-9fe3-69b37d27c453`; Reader [Apply #39774912636](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39774912636), GET [#39775311388](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39775311388), No Change [#39777806327](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39777806327).
- Fabric `AzureBlobs` WorkspaceIdentity Connection `healthcare-omop-landing-blob`, ID `92d67d9c-7a9d-4619-bcf3-2b48b5b93788`: [Apply #39775898394](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39775898394), independent [GET #39777494344](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39777494344), No Change [#39778085770](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39778085770).
- Standard workflow remains Plan/GET for push and requires explicit manual Apply authorization; temporary one-use Apply entries were removed.

> Connection and Reader control-plane completion does not authorize editing or deleting any source Blob object; the Workspace Identity is reader-only at the existing `landing` container.
