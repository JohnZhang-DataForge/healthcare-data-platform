# Fabric new-environment Terraform roots — SCAFFOLD ONLY

These three roots are isolated from the legacy seven Terraform roots in `components/`.
`workspace/`, `onelake/`, and `connection/` now declare separate, default-deny `fabric_workspace`, `fabric_lakehouse` and `fabric_connection` resources respectively. Connection uses only a verified schema and an existing Key Vault secret reference or explicitly reviewed Workspace Identity; no secrets are accepted by this Root. All resource creation approval flags default to false; Lakehouse additionally requires an independently verified Workspace ID and schema-enabled creation. Connection separately requires existing-connection inventory, supported AzureBlobs metadata, verified account/domain, Reader RBAC and its chosen credential mode. These flags are not live inventory. `prevent_destroy` guards all three new resources against accidental deletion, but cannot prevent out-of-band deletion or manual State tampering.
The Backend `azurerm` blocks are partial configurations; the approved offline
`tools/fabric_backend_config.py` determines the unique `fabric/<env>/<component>.tfstate`
key for each root. A Backend key string does not prove State vacancy or RBAC isolation.

This is **not** an executable deployment procedure. Do not run Terraform init,
plan, apply, destroy or state commands against these roots before the subsequent
Change tasks add authenticated backend/provider execution,
remote-state inventory, explicit approval and live resource ownership gates.

Authentication boundary: ARM_* is for the existing Storage Tenant A backend;
FABRIC_* is for the new Fabric Tenant B. These must not be aliased. Existing
Self-Runner `azure-infra.yaml`, existing `dev/*.tfstate`, Workspaces and
`johnzhang/landing` are untouched. Connection v1.13 schema has been verified **offline**, not against the live Fabric tenant. Notebook and Pipeline remain reserved for fabric-cicd. New `connection/SCHEMA.md` describes the secret-free Key Vault reference and gated Workspace Identity choices.

## Bootstrap dual-Storage origin (offline-only)

Existing v1 environment and standalone backend tools remain locked to `johnzhang`. New `fresh-bootstrap` Profile-bound v2 handoff can derive an HDP Storage ARM origin, the exact `fabric/<environment>/{workspace,onelake,connection}.tfstate` keys and non-secret Connection Root storage inputs. The Connection Root itself defaults to `reuse-existing`, demands an exact legacy account in that mode, and for fresh demands a distinct `hdp*` name and an independent `fresh_storage_provenance_verified` flag (default false). The handoff **never** sets that flag or `connection_creation_approved` true. Private network, existing-state inventory, verified Reader RBAC, SKU/capacity permissions and independent deployment authorization all remain HOLD. No `terraform init/plan/apply` is approved.

Controlled Self-Runner intake is now available as **offline HOLD only** in <https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/.github/workflows/fabric-controlled-entry.yml>. It does **not** perform any Terraform or cloud operation and does not run `dw-runner-set`. Future privileged Bootstrap/Plan/Apply jobs, protected Environments and approvals must be separately designed and authorized; all six Fabric roots remain non-deployed.
