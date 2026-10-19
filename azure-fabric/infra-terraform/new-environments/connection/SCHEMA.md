# Fabric Blob Connection — Provider Schema / Deployment Gate

Status: **resource declared but not deployed**; default-deny, 2026-10-19. Nothing has been initialized, planned, applied, imported or remotely inventoried.

Provider: `microsoft/fabric ~> 1.13.0`; the official `fabric_connection` resource exists and supports Service Principal authentication. Its required fields are `display_name`, `connectivity_type`, `connection_details` (`type`, `creation_method`, optional `parameters`), and `credential_details` (`credential_type`). For cloud connectors, `ShareableCloud` is a supported connectivity type. Service Principal credentials require `client_id`, `tenant_id` and an explicitly supported secret-reference/write-only secret strategy; Provider OIDC does **not** automatically provide the connection's data-source credential.

Official Provider schema: https://microsoft.github.io/terraform-provider-fabric/resources/connection/
Microsoft Create Connection API: https://learn.microsoft.com/en-us/rest/api/fabric/core/connections/create-connection
Microsoft List Supported Connection Types API: https://learn.microsoft.com/en-us/rest/api/fabric/core/connections/list-supported-connection-types

## Remaining gates before any Terraform/Cloud execution

1. Confirm from an authoritative supported-connection-types response for the **target tenant/capacity** the Azure Blob Storage connector `type`, exact `creation_method`, required parameter **names**, credential kinds, and whether Service Principal/Workspace Identity is supported. Documentation does not guarantee those values for an individual tenant.
2. Distinguish the Fabric **deployment** identity in Tenant B from the Azure Blob **data reader** in Tenant A. Choose approved credential delivery; do not store secrets, SAS, account keys or bearer tokens in JSON, Terraform source, CI logs, plan artifacts or Git. Cross-tenant authentication must be proven independently, not assumed from a client ID.
3. Inventory an existing connection before deciding new-create vs explicit import; review permissions to `johnzhang/landing`. Do not create an additional Azure Storage Account/Container or grant RBAC automatically.
4. The isolated `fabric_connection.azure_blob` Root now declares only `AzureBlobs` / `AzureBlobs` with required `account` and `domain` parameters. No real values are assumed for domain or SP. Its `prevent_destroy` and default-false approval flags are not live inventory. Attach it to the independent `fabric/<env>/connection.tfstate` Backend only after separate authorization and state vacancy checks.
5. Revisit actual published Provider schema and available official examples for the pinned version before attempting a non-offline `terraform validate`, `init`, `plan` or `apply`.

The connection root now has `main.tf`, `variables.tf`, and `outputs.tf`, plus the existing Provider/Backend declarations. **Never use anonymous access as a substitute for Blob Reader.** The provider's `WorkspaceIdentity` mode is optional and independently gated; being present in API metadata does not prove it works across tenants.

## Offline tenant metadata contract (next slice)

- [Validator](../../tools/fabric_connection_metadata.py) and [tests](../../tests/test_fabric_connection_metadata.py) accept a saved response from the [List Supported Connection Types API](https://learn.microsoft.com/en-us/rest/api/fabric/core/connections/list-supported-connection-types). The tool requires explicit type, creation_method and credential_type, rejects incomplete pagination, and outputs the declared parameter names; it **does not query the tenant or approve a deployment**.
- All example tests use an intentionally fictitious connector type; actual Azure Blob creation parameters are not inferred. Subsequent authorized metadata acquisition must protect tokens and personal details; do not commit an unreviewed live payload or credentials.

## Metadata contract hardening

Supported Connection Types API also supplies `dataType`, optional `allowedValues`, and `supportedCredentialTypesForUsageInUserControlledCode`. Connection creation eligibility is not equivalent to eligibility for Notebook/Pipeline user-controlled code. The offline validator checks both when `--user-controlled-code` is requested, rejects unknown parameter data types or invalid allowed-values declarations, and never elevates these checks to live tenant authorization. Source: https://learn.microsoft.com/en-us/rest/api/fabric/core/connections/list-supported-connection-types

## Task 2.4 guarded implementation: safe credential handoff (offline)

- Pinned **microsoft/fabric v1.13.0** documentation is authoritative for this Root: https://github.com/microsoft/terraform-provider-fabric/blob/v1.13.0/docs/resources/connection.md . The released Schema provides `service_principal_credentials.service_principal_secret_reference` with `connection_id`, `secret_name` and optional `version`, or the credential type `WorkspaceIdentity`. The reference points to an **existing Fabric Key Vault connection**; the Terraform code does not accept the secret value, `client_secret_wo`, keys or SAS. Reference metadata may still reside in State.
- `ServicePrincipal` mode: a *third* Reader app in Storage Tenant A must have independently granted minimum Blob Reader permissions; it cannot be the Backend Operator or Fabric Deployer. The existing Fabric Key Vault connection, access to its secret, and supported credential reference behavior must be reviewed separately. Backend and Fabric provider OIDC identities are supplied outside this Root; variable declarations DO NOT prove the real runtime identity.
- `WorkspaceIdentity` mode: no secret fields, but the intended Fabric Workspace identity and read-only access to the actual Storage account/container must be independently verified. **Cross-tenant A→B cannot be assumed supported** merely because metadata names this credential type.
- `account` is fixed to existing Storage `johnzhang`; `domain` is intentionally required with no guessed default, and needs a separately documented AzureBlobs endpoint review. Both modes default to `connection_creation_approved=false`, `connection_inventory_verified=false`, `connector_metadata_verified=false`, `blob_domain_verified=false`, `reader_access_verified=false`. Mode-specific confirmations are also default false. User-code usage defaults false, while `skip_test_connection=false` means a future authorized operation must actually test connectivity.
- `prevent_destroy` blocks normal destroy/replacement, and no connection role assignment, Storage resource, RBAC, data source, import or remote-state lookup has been added. Existing connections must be inventoried before choosing create vs explicit authorized import. This does not protect against out-of-band deletion or manual State manipulation.
- The current metadata fixture records user-observed non-secret `AzureBlobs` values, but does not prove authorization or the target account's real Reader grants. This PR runs source-only Python tests; **do not run Terraform init, plan, apply, destroy, import or cloud API writes** without separate authorization. A separately authorized Provider schema validation, State inventory and SP/OIDC live verification remain outstanding.
