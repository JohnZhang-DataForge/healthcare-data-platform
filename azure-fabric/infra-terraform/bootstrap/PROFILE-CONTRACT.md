# Fabric Infrastructure Bootstrap Profile Contract — Self-Runner Main-Ref (v1)

This strict offline profile defines a **logical deployment target** and input assumptions. It neither authenticates to Azure nor grants cloud access. The profile `environment` (for example `trial-lab`) names an isolated Fabric deployment / State prefix. It is **not** a GitHub Actions Environment.

### Core input contract

- `schema_version=1`, `environment` is a distinct lowercase kebab-case target (1–40 chars), rejecting old `dev`, `main`, `default`, `production`.
- `bootstrap_mode` is exactly `reuse-existing` or `fresh-bootstrap`. Never infer a mode from missing cloud inventory.
- `tenants.backend_tenant_id`, `tenants.fabric_tenant_id` are explicit nonzero canonical UUIDs. Equal tenants and cross-tenant scenarios are both allowed, but Backend and Fabric Apps remain separate.
- `github_oidc.repository=JohnZhang-DataForge/Self-Runner` and `github_oidc.ref=refs/heads/main`. GitHub Free/private has **no protected Environment** in the selected single-operator architecture. Actual GitHub immutable Subject verified in issuer Run [39422174619](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39422174619) is `repo:JohnZhang-DataForge@337895338/Self-Runner@1413796156:ref:refs/heads/main`.
- `storage.subscription_id` and `storage.resource_group` refer to an inventoried target; `landing_container=landing`, `state_container=tfstate`, and `state_prefix=fabric/<environment>`. Do not touch legacy `dev/*.tfstate`; State key prefix is **not** a blob RBAC permission boundary.
- `bootstrap_state.strategy=isolated-local` with an explicit non-secret custody reference for initial Seed authorization, avoiding circular State bootstrap.
- `capacity.mode=reuse-existing` binds a verified Capacity UUID in later cloud inventory. `create-new` requires complete F SKU/Region/cost estimate and billing evidence even to pass syntactic validation; **this does not authorize a paid creation**.

### Verification boundary

Outputs are deterministic non-secret previews of Tenant topology, new State keys, Capacity mode and verified=false flags. A valid offline Profile does **not** prove real Entra App IDs, their federated credentials, protected runtime, Azure permissions, Storage State vacancy, Trial Capacity or Terraform authorization.

The v3 [Identity contract](IDENTITY-CONTRACT.md) defines **two** Main-ref FICs for **two different** newly created Entra Apps. They share an identical GitHub OIDC Subject across Self-Runner Main workflows, without per-workflow/role/phase issuer isolation. This is a documented personal-lab tradeoff, not an Environment reviewer. Paid F SKU or destructive Apply require separately reviewed evidence. All new resource Roots default to no creation.

Run the offline contracts using the `azure-fabric/infra-terraform/tests` suite; never put secrets, access tokens, credential files, `terraform.tfstate` or Plan output into Git.
