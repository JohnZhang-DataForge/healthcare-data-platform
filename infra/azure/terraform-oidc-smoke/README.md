# Azure Terraform OIDC smoke test

**Disposable test only.** The official Terraform source is stored in the Healthcare repository. The execution and federated GitHub OIDC identity belong to `JohnZhang-DataForge/Self-Runner`, branch `main`.

- State: pre-existing Azure Storage Account `johnzhang`, private container `tfstate`, isolated key `smoke/oidc-connectivity.tfstate`.
- Target: existing Resource Group `OMOP`; **no new Resource Group**.
- Creates: an empty **Incremental** ARM deployment `hdp-tf-oidc-probe` under Microsoft.Resources/deployments, no nested resources. This verifies actual Azure control-plane write permissions without creating billable workload resources.
- Workflow: pinned Healthcare SHA, init / validate / plan, create-read-idempotency, and always-attempted destroy.
- No Azure Resource Provider subscription registration is required for this core ARM deployment. Previous Managed Identity probe did not create a resource because `Microsoft.ManagedIdentity` was not registered; it was removed from test source.
- The deployment mode MUST stay **Incremental**. Never use `Complete` against the existing `OMOP` group.
- This module must never manage the existing `OMOP` Resource Group, the `johnzhang` Storage Account or the `tfstate` container.
- Required Self-Runner repo variables: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`. App `hdp-github-terraform` needs RG `OMOP` Contributor and `tfstate` Storage Blob Data Contributor.
- Keep real Healthcare/Fabric Terraform code in a separate directory/state. Do not store state, access tokens, secrets, or Azure access keys in GitHub.

## Live evidence (2026-10-15)

- Self-Runner GitHub Actions [38727959062](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38727959062) (third attempt): GitHub variables, OIDC, Azure Blob remote backend, validate, plan, actual ARM deployment apply, resource ID read-back and destroy all succeeded.
- Actual Azure mutation: `1 added` in existing `OMOP` group, then `1 destroyed`; no nested workload resources.
- Workflow overall **FAIL** because repeat plan detected ARM output `type = "String"` normalized by Azure from original `"string"`. Updated probe source now uses canonical `String` (not yet retested), so idempotency is **PENDING**, not PASS.
- First probe run [38672734725](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38672734725) confirmed OIDC/backend and cleanup of 0 resources, but failed creating a managed identity due to missing subscription RP registration; that code was replaced.
- The smoke module is not production IaC. No dedicated Resource Group or paid infrastructure was created by these tests. One-time push trigger has been removed from the runner workflow.
