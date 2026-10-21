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
    names = []
    for item in items:
        details = item.get("connectionDetails") or {}
        if details.get("type") != "AzureBlobs":
            continue
        params = details.get("parameters") or []
        if isinstance(params, list) and any(
            x.get("name") == "account" and x.get("value") == account for x in params
        ):
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
                                    "https://management.azure.com/")):
            raise RuntimeError("Unexpected pagination host/path")
        url = next_url
    raise RuntimeError("Inventory pagination exceeds safety limit")


def inspect(subscription, group, account):
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
    try:
        assignments = pages(arm + scope +
            "/providers/Microsoft.Authorization/roleAssignments?api-version=2022-04-01&%24filter=atScope()",
            azure_token)
        print("ACCOUNT_SCOPE_RBAC_ASSIGNMENT_COUNT=" + str(len(assignments)))
        print("BLOB_READER_AUTHORIZED=UNVERIFIED_NO_APPROVED_READER_PRINCIPAL")
    except RuntimeError:
        print("ACCOUNT_SCOPE_RBAC_INVENTORY=UNVERIFIED")
        print("BLOB_READER_AUTHORIZED=UNVERIFIED")
    fabric_token = token_for(fabric_tenant, fabric_client, "https://api.fabric.microsoft.com/.default")
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
    args = parser.parse_args()
    try:
        inspect(args.subscription, args.resource_group, args.storage_account)
    except (RuntimeError, KeyError) as exc:
        print("READINESS_FAILURE=" + str(exc))
        print("STATUS=BLOCKED_NO_CLOUD_MUTATION")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
