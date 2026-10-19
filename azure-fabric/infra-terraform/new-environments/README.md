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
