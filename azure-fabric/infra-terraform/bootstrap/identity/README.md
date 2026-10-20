# Fabric Bootstrap Identity Root — offline-only

OpenSpec: bootstrap-fabric-infrastructure Task 2.2. This is source code, NOT a deployed or Provider-initialized tenant. No Terraform init, validate, plan, apply, destroy, import or remote cloud queries have been run.

- The isolated Root pins hashicorp/azuread 3.8.0, with separate Tenant A and Tenant B provider aliases even when both point to the same tenant (A-to-A-prime). Three distinct NEW Entra applications and service principals: Backend Operator and Blob Reader in Tenant A, Fabric Deployer in Tenant B. Names are hdp-{environment}-{role}.
- Two optional security groups only organize identities; they do not grant Graph, subscription, Storage, Fabric tenant or workspace permissions or add members. No automatic handling of existing github-terraform application or other existing resources. Exact name inventory and a separately authorized Seed Operator remain required.
- Two GitHub federated credentials bind the exact Healthcare repository and separate fabric-{environment}-backend and fabric-{environment}-deployer protected Environments. GitHub environment OIDC subject does NOT include branch, so the GitHub Environment must separately enforce deployment from refs/heads/main and reviewer protection. This is NOT currently configured or verified.
- All ten resources use count=0 by default via identity_creation_approved=false, with prevent_destroy=true. Changing a bool is not authorization. Any actual execution requires separate Seed/Graph/admin access, verified inventory, backend custody and explicit authorization. The initial Terraform backend is isolated local state; encryption, custody, backups and recoverability are manual prerequisite gates.
- Outputs contain non-secret IDs, all unverified. Never commit tfstate, secrets, tokens, credentials or private environment tfvars; the existing infra-terraform/.gitignore excludes state.
- Offline checks: terraform fmt -check only, Python negative/static tests, hosted CI without id-token permissions or cloud commands.

Design sources: [Provider/ARM references](../PROVIDER-SCHEMA-REFERENCE.md), [Identity and OIDC contract](../IDENTITY-CONTRACT.md), [Profile contract](../PROFILE-CONTRACT.md).
