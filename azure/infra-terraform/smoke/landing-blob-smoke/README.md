# Terraform OIDC data-plane write smoke — landing (legacy, isolated root)

> **Source relocation (2026-10-16):** now at `azure/infra-terraform/smoke/landing-blob-smoke/` with the **same** remote State Key `smoke/landing-blob-write.tfstate`. Not part of normal Fabric deployment; **do not apply this fixed-name Blob test without new explicit permission**. The original Self-Runner Workflow is pinned to a historical Healthcare SHA with the former `infra/azure/` path, so it still refers to the original immutable source snapshot. Do not repoint its `working-directory` alone. [Smoke safety/index](../README.md).


One-time test: write an informational `.txt` Blob into an **existing** container with Terraform's AzureAD Blob Data Plane authentication.

- Account: `johnzhang` (already exists; never manage or destroy it here)
- Target container: `landing` (assumed existing; if actual name is different, STOP and verify before retrying)
- Blob: `terraform-smoke/oidc-landing-20261015.txt` (new isolated object; no overwrite of pre-existing business files intended)
- Backend: `johnzhang/tfstate` key `smoke/landing-blob-write.tfstate`, separate from ARM/production states
- Expected file content: static harmless text describing the CI/OIDC Terraform test; no credentials or patient data
- Mode: `terraform apply`, then remote state refresh and readback; **do not destroy** the blob after success, so the user can inspect it in Portal.
- Access: Self-Runner's Azure federated service principal must have **Storage Blob Data Contributor** at the `landing` container (or relevant parent scope). `Contributor` at Resource Group alone is not sufficient for Azure AD data-plane blob access.
- The provider intentionally sets `storage_use_azuread = true` to avoid using Storage Account Keys as a bypass.
- If Azure returns `403 AuthorizationPermissionMismatch`, grant the identity data access on the `landing` container, then rerun.
- After verifying the file, do not run `terraform destroy` unless the user explicitly asks to remove the test blob.
