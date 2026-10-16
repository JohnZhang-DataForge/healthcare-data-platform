# Azure Terraform Smoke Tests — legacy isolated roots

**Purpose:** keep historical Terraform OIDC test source *inside the single* `azure/` tree, separate from deployable Fabric/Blob resources. The previous top-level `infra/` was an early experiment location; it is no longer used on Healthcare Main.

| Test root | Proven behavior / caveat | Backend |
| --- | --- | --- |
| [`terraform-oidc-smoke/`](terraform-oidc-smoke/README.md) | Azure ARM OIDC/backend test; historical actual create/read/destroy occurred, but full historical run **FAILED** on output normalization; canonical `String` source change was not independently retested | `smoke/oidc-connectivity.tfstate` |
| [`landing-blob-smoke/`](landing-blob-smoke/README.md) | AzureAD data-plane Blob write check; the recorded test reached **403 AuthorizationPermissionMismatch** before proving write, and code has an **apply-capable** fixed Blob target | `smoke/landing-blob-write.tfstate` |

**Safety boundaries:**
- The [primary project](../README.md) uses **`azure/infra-terraform/components/`** and `dev/<component>.tfstate`; these tests are **not** one of its components and are **not** part of the approved OneLake-first deployment.
- The historical [Self-Runner OIDC Workflow](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/.github/workflows/azure-terraform-oidc-smoke.yml) is pinned to Healthcare commit `1a42403635a9e40944769c01b78aac0cced7e47f` and `healthcare/infra/azure/terraform-oidc-smoke`. The [Blob Workflow](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/.github/workflows/azure-terraform-landing-blob-write.yml) is pinned to Healthcare commit `f9d911be125753528e78a739ade1af8e36752db2` and `healthcare/infra/azure/landing-blob-smoke`. Those immutable historical checkouts remain available after the Main directory relocation; **their source and runtime behavior have not been updated or validated by this change**.
- If future testing requires running from the new directories, design and review a **separate** coordinated Self-Runner change updating checkout SHA, `working-directory`, the relative `git -C` source-sha assertion, and safety gates together. A historical Blob workflow currently contains a manual Azure **apply** step: **never dispatch it as part of a cleanup/migration**.
- Remote Azure State and actual resources have **not** been moved or deleted. The `backend.tf` files intentionally retain their exact backend keys and Azure OIDC auth settings. A file relocation is *not* a Terraform state migration.
- No new `infra/` should be created in the repository. Any future Azure IaC or smoke code belongs in `azure/` and uses component/capability names.

See [current project status](../../../documents/status/PROJECT-STATUS.md) and [safe runtime operations](../../../documents/operations/SAFE-OPERATIONS.md). Historical smoke evidence must never be mistaken for Fabric E2E completion.
