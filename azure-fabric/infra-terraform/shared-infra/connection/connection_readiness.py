#!/usr/bin/env python3
"""Read-only Fabric/Azure Blob Connection discovery using GitHub Actions OIDC.

Never creates a connection, modifies RBAC, or touches Terraform state.
Reports metadata only; never prints JWTs, API responses, or credentials.
"""
import argparse
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen


def require_env(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError("Missing required environment variable: " + name)
    return value


def json_request(url, *, bearer=None, form=None):
    headers = {"Accept": "application/json"}
    data = None
    if bearer is not None:
        headers["Authorization"] = "Bearer " + bearer
    if form is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        data = urlencode(form).encode("utf-8")
    request = Request(url, headers=headers, data=data, method="POST" if form is not None else "GET")
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except HTTPError as exc:
        # Deliberately exclude response bodies and headers: they can contain credentials.
        raise RuntimeError("HTTP " + str(exc.code) + " from authorized endpoint") from None
    except URLError:
        raise RuntimeError("Authorized endpoint unreachable") from None


def token_for(tenant, client_id, scope):
    oidc_url = require_env("ACTIONS_ID_TOKEN_REQUEST_URL")
    oidc_auth = require_env("ACTIONS_ID_TOKEN_REQUEST_TOKEN")
    joiner = "&" if "?" in oidc_url else "?"
    assertion = json_request(
        oidc_url + joiner + urlencode({"audience": "api://AzureADTokenExchange"}),
        bearer=oidc_auth,
    )["value"]
    form = {
        "client_id": client_id,
        "scope": scope,
        "grant_type": "client_credentials",
        "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
        "client_assertion": assertion,
    }
    return json_request(
        "https://login.microsoftonline.com/" + quote(tenant, safe="") + "/oauth2/v2.0/token",
        form=form,
    )["access_token"]


def azure_blobs_metadata(items):
    matches = []
    for item in items:
        if item.get("type") != "AzureBlobs":
            continue
        methods = item.get("creationMethods") or []
        azure_method = next((m for m in methods if m.get("name") == "AzureBlobs"), None)
        matches.append({
            "method": azure_method is not None,
            "required_parameters": sorted(
                x.get("name", "") for x in (azure_method or {}).get("parameters", [])
                if x.get("required")
            ),
            "credentials": sorted(item.get("supportedCredentialTypes") or []),
            "user_code_credentials": sorted(
                item.get("supportedCredentialTypesForUsageInUserControlledCode") or []
            ),
        })
    return matches


def storage_connection_names(items, account):
    """Fabric LIST returns connectionDetails.path rather than create parameters."""
    names = []
    for item in items:
        details = item.get("connectionDetails") or {}
        if details.get("type") != "AzureBlobs":
            continue
        path = details.get("path", "")
        if isinstance(path, str) and account.lower() in path.lower():
            names.append(item.get("displayName", "<unnamed>"))
    return sorted(names)


def pages(url, token, limit=20):
    """Read every page or fail closed instead of pretending inventory is exhaustive."""
    result = []
    for _ in range(limit):
        page = json_request(url, bearer=token)
        result.extend(page.get("value", []))
        next_url = page.get("continuationUri") or page.get("nextLink")
        if not next_url:
            return result
        if not next_url.startswith(("https://api.fabric.microsoft.com/v1/connections",
                                    "https://api.fabric.microsoft.com/v1/workspaces",
                                    "https://management.azure.com/")):
            raise RuntimeError("Unexpected pagination host/path")
        url = next_url
    raise RuntimeError("Inventory pagination exceeds safety limit")



def inspect_workspace_identity(workspace_name, token, fabric_client):
    """GET-only check after a failed Fabric provisionIdentity long-running operation.

    Do not equate a missing workspaceIdentity field with a healthy provisioning
    state: the failed/stuck state is only visible in Fabric's Workspace settings.
    """
    base = "https://api.fabric.microsoft.com/v1/workspaces"
    workspaces = pages(base, token)
    found = [w for w in workspaces if w.get("displayName") == workspace_name]
    if len(found) != 1:
        raise RuntimeError("Expected exactly one accessible named Fabric workspace")
    workspace_id = found[0].get("id", "")
    if not workspace_id or not all(x in "0123456789abcdef-" for x in workspace_id.lower()):
        raise RuntimeError("Invalid Fabric workspace ID in discovery")
    workspace = json_request(base + "/" + quote(workspace_id, safe=""), bearer=token)
    if workspace.get("id") != workspace_id:
        raise RuntimeError("Workspace GET returned a different ID")
    identity = workspace.get("workspaceIdentity")
    print("TARGET_WORKSPACE_ID=" + workspace_id)
    print("WORKSPACE_IDENTITY_IN_FABRIC_API=" + ("PRESENT" if identity else "ABSENT"))
    if identity:
        print("WORKSPACE_IDENTITY_APPLICATION_ID=" + str(identity.get("applicationId", "UNAVAILABLE")))
        print("WORKSPACE_IDENTITY_PRINCIPAL_ID=" + str(identity.get("servicePrincipalId", "UNAVAILABLE")))
    print("WORKSPACE_CAPACITY_ID=" + str(workspace.get("capacityId", "UNAVAILABLE")))
    roles = pages(base + "/" + quote(workspace_id, safe="") + "/roleAssignments", token)
    assigned = [
        a.get("role") for a in roles
        if ((a.get("principal") or {}).get("servicePrincipalDetails") or {})
        .get("aadAppId", "").lower() == fabric_client.lower()
    ]
    print("RUNNER_SERVICE_PRINCIPAL_EXPLICIT_WORKSPACE_ROLES=" +
          json.dumps(sorted(set(assigned))))
    print("WORKSPACE_IDENTITY_PROVISIONING_STATE=NOT_EXPOSED_BY_GET_WORKSPACE")
    print("WORKSPACE_IDENTITY_CLOUD_WRITES=NO")



def summarize_scope_role_assignments(items):
    """Account/container RBAC metadata only; credentials and token bodies excluded."""
    results = []
    for item in items:
        props = item.get("properties") or {}
        principal = props.get("principalId")
        role = props.get("roleDefinitionId")
        scope = props.get("scope")
        if not all(isinstance(v, str) and v for v in (principal, role, scope)):
            raise RuntimeError("Role assignment inventory missing required metadata")
        results.append({
            "principal_id": principal.lower(),
            "role_definition_id": role.rsplit("/", 1)[-1].lower(),
            "scope": scope,
        })
    return sorted(results, key=lambda r: (r["principal_id"], r["role_definition_id"], r["scope"]))



def verify_exact_connection(connection_id, account, token):
    """Read one Fabric Connection by ID, not list entries that omit details."""
    if not connection_id or not all(c in "0123456789abcdef-" for c in connection_id.lower()):
        raise RuntimeError("Invalid expected Fabric Connection ID")
    base = "https://api.fabric.microsoft.com/v1/connections/"
    item = json_request(base + quote(connection_id, safe=""), bearer=token)
    if item.get("id", "").lower() != connection_id.lower():
        raise RuntimeError("Fabric Connection GET returned mismatched ID")
    if item.get("displayName") != "healthcare-omop-landing-blob":
        raise RuntimeError("Unexpected Fabric Connection display name")
    details = item.get("connectionDetails") or {}
    if details.get("type") != "AzureBlobs":
        raise RuntimeError("Fabric Connection type is not AzureBlobs")
    # Fabric GET's ListConnectionDetails has {type, path}; create-parameters
    # do not appear in the GET response. AzureBlobs path is non-credential
    # datasource metadata, so match the account/domain without logging it.
    path = details.get("path")
    if not isinstance(path, str) or not path:
        raise RuntimeError("Fabric Connection details.path was not returned")
    if account.lower() not in path.lower() or "blob.core.windows.net" not in path.lower():
        raise RuntimeError("Fabric Connection path did not match expected Blob account/domain")
    # No credentialDetails printed. Even if GET omits them, do not infer auth
    # or successful data access from the connection's existence alone.
    print("EXACT_FABRIC_CONNECTION_ID=" + connection_id)
    print("EXACT_FABRIC_CONNECTION_NAME=" + item["displayName"])
    print("EXACT_FABRIC_CONNECTION_TYPE=AzureBlobs")
    print("EXACT_FABRIC_CONNECTION_ACCOUNT=" + account)
    print("EXACT_FABRIC_CONNECTION_GET=PASS")
    print("ACTUAL_BLOB_READ=NOT_TESTED")


def inspect(subscription, group, account, workspace_name=None, landing_container=None, expected_connection_id=None):
    azure_tenant = require_env("ARM_TENANT_ID")
    fabric_tenant = require_env("FABRIC_TENANT_ID")
    azure_client = require_env("ARM_CLIENT_ID")
    fabric_client = require_env("FABRIC_CLIENT_ID")
    print("#### FABRIC_BLOB_CONNECTION_READINESS_BEGIN ####")
    print("EXPECTED_AZURE_TENANT=" + azure_tenant)
    print("CONFIGURED_FABRIC_TENANT=" + fabric_tenant)
    print("TENANT_RELATION=" + ("SAME" if azure_tenant.lower() == fabric_tenant.lower() else "DIFFERENT"))
    print("WORKSPACE_IDENTITY_CROSS_TENANT_SUPPORTED=NO")

    azure_token = token_for(azure_tenant, azure_client, "https://management.azure.com/.default")
    arm = "https://management.azure.com"
    sub = json_request(arm + "/subscriptions/" + quote(subscription, safe="") +
                       "?api-version=2022-12-01", bearer=azure_token)
    actual_tenant = sub.get("tenantId")
    if not actual_tenant:
        raise RuntimeError("ARM subscription tenantId unavailable")
    print("SUBSCRIPTION_TENANT=" + actual_tenant)
    if actual_tenant.lower() != azure_tenant.lower():
        raise RuntimeError("ARM_TENANT_ID does not own the target Azure subscription")

    scope = ("/subscriptions/" + quote(subscription, safe="") +
             "/resourceGroups/" + quote(group, safe="") +
             "/providers/Microsoft.Storage/storageAccounts/" + quote(account, safe=""))
    storage = json_request(arm + scope + "?api-version=2023-01-01", bearer=azure_token)
    if storage.get("name", "").lower() != account.lower():
        raise RuntimeError("Unexpected storage account returned by ARM")
    print("STORAGE_ACCOUNT_FOUND=YES")
    print("HIERARCHICAL_NAMESPACE=" + str(
        (storage.get("properties") or {}).get("isHnsEnabled", False)).upper())
    print("PUBLIC_NETWORK_ACCESS=" + str(
        (storage.get("properties") or {}).get("publicNetworkAccess", "UNKNOWN")))
    assignments = []
    try:
        assignments = pages(arm + scope +
            "/providers/Microsoft.Authorization/roleAssignments?api-version=2022-04-01&%24filter=atScope()",
            azure_token)
        print("ACCOUNT_SCOPE_RBAC_ASSIGNMENT_COUNT=" + str(len(assignments)))
        print("BLOB_READER_AUTHORIZED=UNVERIFIED_NO_APPROVED_READER_PRINCIPAL")
    except RuntimeError:
        print("ACCOUNT_SCOPE_RBAC_INVENTORY=UNVERIFIED")
        print("BLOB_READER_AUTHORIZED=UNVERIFIED")
    if landing_container:
        if not landing_container.replace("-", "").replace("_", "").isalnum():
            raise RuntimeError("Invalid Landing container name")
        container_scope = scope + "/blobServices/default/containers/" + quote(landing_container, safe="")
        # atScope(): includes assignments at or above the requested scope,
        # but not assignments at child scopes; output retains each true scope.
        container_roles = pages(arm + container_scope +
            "/providers/Microsoft.Authorization/roleAssignments?api-version=2022-04-01&%24filter=atScope()",
            azure_token)
        print("ACCOUNT_SCOPE_APPLICABLE_ROLE_ASSIGNMENTS=" +
              json.dumps(summarize_scope_role_assignments(assignments), sort_keys=True))
        print("LANDING_SCOPE_APPLICABLE_ROLE_ASSIGNMENTS=" +
              json.dumps(summarize_scope_role_assignments(container_roles), sort_keys=True))
        print("RBAC_SCOPE_ENUMERATION=AT_OR_ABOVE_SCOPE_EXCLUDES_CHILDREN")
    fabric_token = token_for(fabric_tenant, fabric_client, "https://api.fabric.microsoft.com/.default")
    if workspace_name:
        inspect_workspace_identity(workspace_name, fabric_token, fabric_client)
    base = "https://api.fabric.microsoft.com/v1/connections"
    types = pages(base + "/supportedConnectionTypes?showAllCreationMethods=true", fabric_token)
    matches = azure_blobs_metadata(types)
    print("AZURE_BLOBS_SUPPORTED=" + ("YES" if matches and any(m["method"] for m in matches) else "NO"))
    print("AZURE_BLOBS_METADATA=" + json.dumps(matches, sort_keys=True))
    if not matches or not any(m["method"] for m in matches):
        raise RuntimeError("Fabric tenant does not expose expected AzureBlobs creation method")
    connections = pages(base, fabric_token)
    names = storage_connection_names(connections, account)
    print("EXISTING_ACCOUNT_AZURE_BLOBS_CONNECTION_NAMES=" + json.dumps(names))
    if expected_connection_id:
        verify_exact_connection(expected_connection_id, account, fabric_token)
    print("FABRIC_CONNECTION_INVENTORY_COMPLETE=YES")
    print("FABRIC_CONNECTION_APPLIED=NO")
    print("AZURE_RBAC_CHANGED=NO")
    print("TERRAFORM_STATE_ACCESSED=NO")
    print("STATUS=READ_ONLY_DISCOVERY_PASS_NOT_BLOB_RUNTIME_VALIDATED")
    print("#### FABRIC_BLOB_CONNECTION_READINESS_END ####")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--subscription", required=True)
    parser.add_argument("--resource-group", required=True)
    parser.add_argument("--storage-account", required=True)
    parser.add_argument("--workspace-name", required=False)
    parser.add_argument("--landing-container", required=False)
    parser.add_argument("--expected-connection-id", required=False)
    args = parser.parse_args()
    try:
        inspect(args.subscription, args.resource_group, args.storage_account, args.workspace_name, args.landing_container, args.expected_connection_id)
    except (RuntimeError, KeyError) as exc:
        print("READINESS_FAILURE=" + str(exc))
        print("STATUS=BLOCKED_NO_CLOUD_MUTATION")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
