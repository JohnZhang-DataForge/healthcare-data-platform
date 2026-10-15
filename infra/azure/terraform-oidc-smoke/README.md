# Azure Terraform OIDC smoke test

**Disposable test only.** Canonical Terraform source lives in this Healthcare repository. The GitHub Actions runner and Azure federated credential belong to `JohnZhang-DataForge/Self-Runner`, branch `main`.

- Backend: existing Azure Storage Account `johnzhang`, private container `tfstate`, isolated key `smoke/oidc-connectivity.tfstate`.
- Target: existing Resource Group `OMOP`, no new resource groups.
- Creates temporarily: `azurerm_user_assigned_identity.probe` named `id-hdp-tf-oidc-probe`.
- The runner checks OIDC authentication, remote state, create/read, idempotent plan, then always attempts destroy. Verify any failed cleanup manually before retrying.
- The identity has no Azure RBAC roles and should never be used for workloads.
- Never import the existing `johnzhang` account, `tfstate` container or `OMOP` group into this smoke module.
- Requires the Self-Runner repository variables `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` and the Azure app `hdp-github-terraform` to have `Contributor` at RG `OMOP` plus `Storage Blob Data Contributor` at `johnzhang/tfstate`.
- Never store Azure keys, secrets, Terraform state, or Azure access tokens in GitHub source or artifacts.
- This smoke test is separate from future Fabric application Terraform code/state. Do not run a recursive `terraform destroy` outside this directory.
