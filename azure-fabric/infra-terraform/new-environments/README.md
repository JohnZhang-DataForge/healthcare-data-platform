# Fabric new-environment Terraform roots — SCAFFOLD ONLY

These three roots are isolated from the legacy seven Terraform roots in `components/`.
They deliberately contain **no resources, modules, data sources or outputs**.
The Backend `azurerm` blocks are partial configurations; the approved offline
`tools/fabric_backend_config.py` determines the unique `fabric/<env>/<component>.tfstate`
key for each root. A Backend key string does not prove State vacancy or RBAC isolation.

This is **not** an executable deployment procedure. Do not run Terraform init,
plan, apply, destroy or state commands against these roots before the subsequent
Change tasks add real resources, authenticated backend/provider execution,
remote-state inventory, explicit approval and live resource ownership gates.

Authentication boundary: ARM_* is for the existing Storage Tenant A backend;
FABRIC_* is for the new Fabric Tenant B. These must not be aliased. Existing
Self-Runner `azure-infra.yaml`, existing `dev/*.tfstate`, Workspaces and
`johnzhang/landing` are untouched. Connection resource schema is not yet
verified. Notebook and Pipeline remain reserved for fabric-cicd.
