# Task 3.2 — Live Seed Identity Readiness (Tenant A/B, 2026-10-20)

This runbook deliberately separates **cloud reading**, **initial identity creation**
and **OIDC evidence**. The existing Identity Terraform Root owns all three new
applications, their service principals, groups and the two main-ref FICs.
**Never manually create duplicate Apps/FICs with `az ad app create`.** Do not
adopt the old `github-terraform` identity or access old Azure State.

## Scope and current evidence

- Execution repository: private `JohnZhang-DataForge/Self-Runner`, GitHub Free,
  no Environment approvals or additional repository.
- GitHub genuine immutable main-ref JWT: Self-Runner Run
  [39422174619](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39422174619)
  **PASS**, but Entra Exchange is **NOT TESTED**.
- Three new roles: `backend_operator`, `blob_reader` in Tenant A;
  `fabric_deployer` in Tenant B. Two main-ref FICs on the first and third;
  Blob Reader must have **zero GitHub FICs**.
- The same GitHub `sub` is intentionally shared for both FICs:
  `repo:JohnZhang-DataForge@337895338/Self-Runner@1413796156:ref:refs/heads/main`.
  Different apps/Tenants/RBAC are distinct scopes, **not phase isolation**.
- Do not create paid F SKU Capacity, initialize legacy `dev/*.tfstate`, modify
  the old `azure-infra.yaml`, or run an unreviewed Terraform Apply.

## 1. Supply actual non-secret inputs outside Git

Create a validated, real Bootstrap Profile v1 and Identity Request v3 based on
`bootstrap-profile.example.json` and `identity-request.example.json`.
The examples are **not runnable** and must not be treated as successful evidence.

Local variables used in following examples:

```bash
ROOT="azure-fabric/infra-terraform/bootstrap/identity"
TOOLS="azure-fabric/infra-terraform/tools"
PROFILE="/secure/fabric/trial-lab/profile.json"
IDENTITIES="/secure/fabric/trial-lab/identity-request.json"
RESOLVED="/secure/fabric/trial-lab/resolved-client-ids.json"
```

Paths above are illustrative, not a requirement to store client IDs as secrets.
State **may include sensitive provider content**; keep it under a separate,
access-controlled, encrypted disk path and never commit it or upload to workflow
artifacts. Pin a reviewed Healthcare Main SHA before doing any real plan.

## 2. Pre-create read-only inventory — one Tenant at a time

Sign in as the authorized Seed Operator and explicitly select **Tenant A**.
If Tenant A and B differ, switch to the separately authorized Tenant B context
for the second command; do not assume one login covers both aliases.

```bash
az login --tenant "<TENANT_A_UUID>"
python3 "$TOOLS/fabric_seed_identity_inventory.py" \
  --profile "$PROFILE" --identities "$IDENTITIES" \
  --tenant-role backend --phase before
```

Repeat with `az login --tenant "<TENANT_B_UUID>"` and
`--tenant-role fabric --phase before`. The probe checks the active
`az account show` tenant and exact expected application names. A matching
name, an Azure CLI read failure, or the wrong tenant returns **HOLD**.
The script itself makes **only allowed read-only Azure CLI calls**, never login
or Graph writes. Its stdout omits IDs, tokens and raw Azure errors.

A clean name inventory does not establish permission to provision, nor prove
an inaccessible app does not exist. The Seed Operator must independently confirm
Microsoft Entra application and service-principal visibility and appropriate
application-creation/Graph permissions.

## 3. Identity Root: Terraform is the only creator

Root: `azure-fabric/infra-terraform/bootstrap/identity/`.
Pinned AzureAD provider version 3.8.0; backend is isolated local State. Its
default `identity_creation_approved=false` means **count=0** for all resources.

Before any mutation: review exact Healthcare source SHA, role-specific Tenant A/B
IDs, the name inventory, Seed consent, AzureAD provider authentication in **both**
tenants, storage of the isolated local State, and a human-reviewed Terraform Plan.
For cross-tenant topology, independently prove provider authentication for both
aliases; `az login` to one tenant is **not** that proof. Use a non-repository,
access-controlled State path with Terraform's local backend configuration;
never rely on the default working-directory `terraform.tfstate`.

The operator may run an isolated `terraform init` and `terraform plan` after
those checks. The creation plan requires `identity_creation_approved=true`, but
setting that boolean alone is **not** approval. **Do not run `terraform apply`
until the saved, exact Plan, state path and three-app/two-FIC creation-only diff
have been reviewed.** In this session that review has not occurred.
No paid Fabric Capacity is part of the Identity Root.

## 4. Post-create read-only attestation

After a separately reviewed Identity Apply, export the actual Terraform
`identity_targets` output into a local, non-secret JSON file of this form:

```json
{
  "backend_operator": {"tenant_id": "<TENANT_A_UUID>", "client_id": "<NEW_BACKEND_APP_ID>"},
  "blob_reader": {"tenant_id": "<TENANT_A_UUID>", "client_id": "<NEW_READER_APP_ID>"},
  "fabric_deployer": {"tenant_id": "<TENANT_B_UUID>", "client_id": "<NEW_DEPLOYER_APP_ID>"}
}
```

Replace the placeholders with actual Terraform outputs; the validator rejects
fake IDs, duplicate IDs, cross-tenant role IDs and unexpected fields.

```bash
az login --tenant "<TENANT_A_UUID>"
python3 "$TOOLS/fabric_seed_identity_inventory.py" \
  --profile "$PROFILE" --identities "$IDENTITIES" \
  --tenant-role backend --phase after --resolved-ids "$RESOLVED"
az login --tenant "<TENANT_B_UUID>"
python3 "$TOOLS/fabric_seed_identity_inventory.py" \
  --profile "$PROFILE" --identities "$IDENTITIES" \
  --tenant-role fabric --phase after --resolved-ids "$RESOLVED"
```

The checks read application name/client ID, service principal, FIC count,
FIC name, exact issuer, audience and immutable main-ref subject. Each tenant
has its own independent PASS/HOLD. **This is cloud inventory evidence, not
Microsoft Entra token exchange or Azure RBAC/Fabric API permission evidence.**

## 5. Configure exactly five Self-Runner repository-level Actions Variables

Only after **both** Tenant A/B post-create checks PASS and the actual Tenant A
subscription is independently verified, configure non-secret UUID values using
the GitHub CLI authenticated as a repository administrator:

```bash
REPO="JohnZhang-DataForge/Self-Runner"
gh variable set FABRIC_OIDC_BACKEND_CLIENT_ID --repo "$REPO" --body "<NEW_BACKEND_APP_ID>"
gh variable set FABRIC_OIDC_BACKEND_TENANT_ID --repo "$REPO" --body "<TENANT_A_UUID>"
gh variable set FABRIC_OIDC_BACKEND_SUBSCRIPTION_ID --repo "$REPO" --body "<TENANT_A_SUBSCRIPTION_UUID>"
gh variable set FABRIC_OIDC_DEPLOYER_CLIENT_ID --repo "$REPO" --body "<NEW_DEPLOYER_APP_ID>"
gh variable set FABRIC_OIDC_DEPLOYER_TENANT_ID --repo "$REPO" --body "<TENANT_B_UUID>"
gh variable list --repo "$REPO" --json name --jq '.[].name'
```

Do not use the old `AZURE_*` variables. GitHub Actions Variables are
repository-wide and contain **only identifiers**, never tokens or client secrets.
Check that names exist and values correspond to the independently verified Apps;
the last command above checks **names only**, not values.

## 6. Actual OIDC exchange and next gates

Use the existing Self-Runner **manual** entry:
[Fabric OIDC Entra Readonly Probe](https://github.com/JohnZhang-DataForge/Self-Runner/actions/workflows/fabric-oidc-readonly-probe.yml).
Select Main; enter `target_environment=trial-lab`. Its two role jobs request
GitHub's actual JWT with `core.getIDToken`, pass it in memory to the Python
probe and attempt Microsoft Entra exchange separately for Backend and Deployer.

Record the **two jobs' actual** PASS/HOLD and workflow Run ID in OpenSpec,
without JWTs, access tokens or raw failure bodies. Exchange PASS does not
prove RBAC/State/Capacity. Afterward, separately inspect subscription inventory,
Trial Capacity's actual Fabric UUID, network path and isolated `fabric/trial-lab/*`
State key availability; only then run a reviewed isolated Terraform Plan.

Self-Runner `fabric-controlled-entry.yml` remains an **offline-only** Plan/Apply
manual selector. Choosing Plan there currently does **not** run Terraform;
choosing Apply never automatically follows Plan. No paid SKU or real Apply
authorization is inferred from a successful probe.

Official command references:
[Azure CLI Entra App](https://learn.microsoft.com/en-us/cli/azure/ad/app),
[Azure CLI FIC list](https://learn.microsoft.com/en-us/cli/azure/ad/app/federated-credential),
[GitHub CLI Variables](https://cli.github.com/manual/gh_variable_set).
