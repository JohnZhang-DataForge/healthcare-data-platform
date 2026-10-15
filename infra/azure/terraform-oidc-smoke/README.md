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
