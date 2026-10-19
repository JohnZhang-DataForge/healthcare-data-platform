# Fabric Blob Connection — Provider Schema / Deployment Gate

Status: **schema reviewed, resource NOT implemented**, 2026-10-19.

Provider: `microsoft/fabric ~> 1.13.0`; the official `fabric_connection` resource exists and supports Service Principal authentication. Its required fields are `display_name`, `connectivity_type`, `connection_details` (`type`, `creation_method`, optional `parameters`), and `credential_details` (`credential_type`). For cloud connectors, `ShareableCloud` is a supported connectivity type. Service Principal credentials require `client_id`, `tenant_id` and an explicitly supported secret-reference/write-only secret strategy; Provider OIDC does **not** automatically provide the connection's data-source credential.

Official Provider schema: https://microsoft.github.io/terraform-provider-fabric/resources/connection/
Microsoft Create Connection API: https://learn.microsoft.com/en-us/rest/api/fabric/core/connections/create-connection
Microsoft List Supported Connection Types API: https://learn.microsoft.com/en-us/rest/api/fabric/core/connections/list-supported-connection-types

## Required next gate before any resource definition

1. Confirm from an authoritative supported-connection-types response for the **target tenant/capacity** the Azure Blob Storage connector `type`, exact `creation_method`, required parameter **names**, credential kinds, and whether Service Principal/Workspace Identity is supported. Documentation does not guarantee those values for an individual tenant.
2. Distinguish the Fabric **deployment** identity in Tenant B from the Azure Blob **data reader** in Tenant A. Choose approved credential delivery; do not store secrets, SAS, account keys or bearer tokens in JSON, Terraform source, CI logs, plan artifacts or Git. Cross-tenant authentication must be proven independently, not assumed from a client ID.
3. Inventory an existing connection before deciding new-create vs explicit import; review permissions to `johnzhang/landing`. Do not create an additional Azure Storage Account/Container or grant RBAC automatically.
4. Add an isolated `fabric_connection` resource only after documented names and safe credential method are verified, with default-deny approvals and no automatic destructive updates. Wire it to the independent `fabric/<env>/connection.tfstate` Backend after separate authorization.
5. Revisit actual published Provider schema and available official examples for the pinned version before attempting a non-offline `terraform validate`, `init`, `plan` or `apply`.

The current connection root intentionally contains just `providers.tf` and `versions.tf`. **Never invent connector creation parameters or use anonymous access as a substitute for Blob Reader.**

## Offline tenant metadata contract (next slice)

- [Validator](../../tools/fabric_connection_metadata.py) and [tests](../../tests/test_fabric_connection_metadata.py) accept a saved response from the [List Supported Connection Types API](https://learn.microsoft.com/en-us/rest/api/fabric/core/connections/list-supported-connection-types). The tool requires explicit type, creation_method and credential_type, rejects incomplete pagination, and outputs the declared parameter names; it **does not query the tenant or approve a deployment**.
- All example tests use an intentionally fictitious connector type; actual Azure Blob creation parameters are not inferred. Subsequent authorized metadata acquisition must protect tokens and personal details; do not commit an unreviewed live payload or credentials.
