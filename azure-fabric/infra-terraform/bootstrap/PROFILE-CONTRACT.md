# Fabric Infrastructure Bootstrap — Offline Profile Contract (v1)

> **Status: static-only, NOT DEPLOYED.** Owner: `bootstrap-fabric-infrastructure`, OpenSpec Task 1.1. This file freezes inputs for the Python validator; it is **not** a Terraform variable file, an approval, a plan, an inventory check, or an Azure/Fabric authorization.

Entry: [`fabric_bootstrap_profile.py`](../tools/fabric_bootstrap_profile.py) — `python3 azure-fabric/infra-terraform/tools/fabric_bootstrap_profile.py --config PATH.json`. The program reads a local JSON file, rejects duplicate/unknown keys, emits only non-secret IDs and false verification flags, and cannot query a cloud API or state. Use [`test_fabric_bootstrap_profile.py`](../tests/test_fabric_bootstrap_profile.py) for acceptance and negative cases. The adjacent [example](bootstrap-profile.example.json) intentionally fails.

## Exact v1 JSON object

- `schema_version`: integer **1**, never bool or string.
- `environment`: distinct lowercase kebab-case, 1–40 chars, not `dev`, `main`, `default` or `production`.
- `bootstrap_mode`: explicitly `reuse-existing` or `fresh-bootstrap` (no auto-detection or fallback).
- `tenants.backend_tenant_id` (Tenant A) and `tenants.fabric_tenant_id` (Tenant B or A′): nonzero canonical UUID; equal IDs are supported but do not imply permission to reuse applications.
- `github_oidc.repository`: exact `JohnZhang-DataForge/healthcare-data-platform`; `github_oidc.environment`: exact `fabric-<environment>`. Desired subject is `repo:<repository>:environment:<environment>`. A protected GitHub Environment, repo/ref restrictions, and actual federated credentials still require separate verified setup (Task 1.2).
- `storage.account`: lowercase Azure Storage account name. In `reuse-existing`, it is fixed to inventoried legacy account `johnzhang`; this does **not** authorize management, import, or adoption. In `fresh-bootstrap`, must start with `hdp` and **cannot** equal `johnzhang`. This static prefix does not prove name vacancy.
- `storage.subscription_id`: nonzero canonical UUID; `storage.resource_group`: Azure-safe name, must be exactly `rg-hdp-<environment>` in fresh mode.
- `storage.landing_container`: `landing`; `storage.state_container`: `tfstate`; `storage.state_prefix`: `fabric/<environment>`. Never use old `dev/*.tfstate`; state prefix is **not** a blob RBAC boundary.
- `bootstrap_state.strategy`: fixed `isolated-local` for phase-0 bootstrap; `bootstrap_state.custody_reference`: non-secret local custody procedure ID matching `CUSTODY-...`. **This is NOT evidence that encryption, backup, custody or recovery are ready.** Do not run remote init against the backend being created; no automatic migrate/import.
- `capacity`: `{"mode":"reuse-existing","capacity_id":"<nonzero UUID>"}` **or** `{"mode":"create-new","sku":"F2","region":"eastus2","subscription_id":"<UUID>","estimated_monthly_usd":300,"monthly_budget_usd":500,"billing_owner":"non-secret-owner","cost_review_reference":"COST-REVIEW-00001"}`. Valid F-series selections are F2/F4/F8/F16/F32/F64/F128/F256/F512/F1024/F2048 (live product/SKU availability is not verified). For cross-tenant A→B, **Capacity Subscription (Tenant B) and Storage Subscription (Tenant A) may differ**; equality is not assumed even for A→A′. Both must be explicit, valid, and separately inventoried. The offline validator verifies only UUID structure, not Tenant/Subscription ownership. Numeric estimates must be finite positive and ≤ budget ≤ 1,000,000 USD.

**All fields are required for their mode** and other fields are rejected — including `client_secret`, `token`, `sas`, credentials and arbitrary embedded payloads. No Cost Review Reference or Boolean in this JSON represents payment approval. Creation requests return `BOOTSTRAP_PROFILE_HOLD_PAID_APPROVAL`, `paid_creation_authorized=false`. Existing Capacity IDs are unverified references, never an implicit create.

## Output and stop conditions

Output includes resolved tenancy topology (A→A′ or A→B), environment-scoped state keys for `workspace/onelake/connection`, target storage IDs, GitHub OIDC subject *target*, Capacity mode and ID when reused. It always reports `verified=false`, `remote_state_checked=false`, `initial_bootstrap_state_verified=false`, `oidc_verified=false`, `terraform_executed=false`. No backend import, live identity/RBAC or billing evidence is inferred.

**HOLD:** any known name conflict, identity collision, invalid JSON/credentials, unknown Tenant/Subscription, unresolved provider support or missing separate human authorization. This contract is not sufficient to drive Terraform apply. Phase 1 identity handoff, OIDC ref/environment controls, independent applications/Client IDs and approval evidence are separate Task 1.2/1.3 contracts.

## Identity handoff (Task 1.2)

The Bootstrap Profile's `github_oidc.environment` is a **namespace prefix only**, NOT an authorization to grant a cloud token. The two exact provisionable subjects and mandatory protected-environment branch rules are defined exclusively in [IDENTITY-CONTRACT.md](IDENTITY-CONTRACT.md). This separation prevents reusing a broad root-level GitHub Environment to grant both Backend and Fabric write identities.
