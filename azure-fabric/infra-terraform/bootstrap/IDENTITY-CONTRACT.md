# Bootstrap Identity and Self-Runner immutable OIDC contract (v2)

**OpenSpec Task 3.2 — source alignment, live verification pending.** The Healthcare repository supplies reviewed IaC at an immutable commit; Self-Runner is the only designated GitHub Actions executor and OIDC token issuer. The two repositories' verified 2026-10-20 IDs are owner `337895338`, Healthcare `1404947726`, Self-Runner `1413796156`. Re-query GitHub OIDC preview and actual token claim before live credential enrollment.

Identity v2 request contains `schema_version=2`, `environment`, separately authorized `seed_operator`, three distinct new `applications` for Tenant A Backend Operator, Tenant A Blob Reader and Tenant B Fabric Deployer, and **exactly four** `oidc_bindings` named `plan_backend`, `apply_backend`, `plan_deployer`, `apply_deployer`. Each binding requires Self-Runner repository, exact `fabric-<env>-<phase>-<role>` Environment, `refs/heads/main` branch policy, official GitHub OIDC issuer, Azure TokenExchange audience and explicit `protected_environment_required=true`. A JSON approval flag is NOT verified GitHub Environment configuration.

Each Application's federated credential uses its appropriate immutable subject:

```text
repo:JohnZhang-DataForge@337895338/Self-Runner@1413796156:environment:fabric-<env>-plan-backend
repo:JohnZhang-DataForge@337895338/Self-Runner@1413796156:environment:fabric-<env>-apply-backend
repo:JohnZhang-DataForge@337895338/Self-Runner@1413796156:environment:fabric-<env>-plan-deployer
repo:JohnZhang-DataForge@337895338/Self-Runner@1413796156:environment:fabric-<env>-apply-deployer
```

Plan and Apply are separate protected jobs/Environments; no single job attempts both Entra principals with one immutable OIDC `sub`. GitHub Environment protection MUST restrict deployments to trusted `main` and require separately verified reviewers, including a dedicated `fabric-<env>-bootstrap` Environment for initial external Seed identity provisioning. The bootstrap Seed may span two tenants only via separately authorized identities; never rely on the self-created SPN to create itself. Blob Reader remains without CI OIDC credentials; its separate landing-data authentication needs review.

Plan/Apply share each role's application identity, so **phase separation in GitHub does not produce different Azure permissions**; enforce independent protected approvals, immutable plan provenance, State scope, deny destructive or paid actions, and avoid uncontrolled workflows. Do not trust unverified PR refs, claims, or user-supplied plan digests as approvals.

Contract and Terraform root default to no resource creation, `prevent_destroy`, initial isolated local State (with separately verified secure custody), no legacy App import, no rights granted by merely creating Entra applications. Resolved client IDs remain unverified until real inventory. No token, administrator consent, Storage State, GitHub protected Environment, Capacity Trial or Cloud Plan has been successfully tested in this code-only revision.

Official: https://learn.microsoft.com/en-us/entra/workload-id/workload-identities-github-immutable-subjects
