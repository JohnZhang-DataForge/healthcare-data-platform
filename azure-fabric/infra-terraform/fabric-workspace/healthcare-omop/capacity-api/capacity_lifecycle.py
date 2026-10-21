#!/usr/bin/env python3
"""Capacity API boundary: trial read-only, paid Azure ARM inspect/suspend/resume.

This module NEVER creates or modifies a Fabric Workspace or Capacity definition.
Use GitHub Actions OIDC; do not store access tokens or client secrets.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

GUID = re.compile(r"^[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$")
ARM_ID = re.compile(
    r"^/subscriptions/([0-9a-fA-F-]{36})/resourceGroups/([A-Za-z0-9_.()-]{1,90})"
    r"/providers/Microsoft\.Fabric/capacities/([a-z][a-z0-9]{2,62})$", re.I
)
FABRIC_AUDIENCE = "https://api.fabric.microsoft.com"
ARM_AUDIENCE = "https://management.azure.com"
ARM_VERSION = "2023-11-01"
MAX_ATTEMPTS = 12


class CapacityError(RuntimeError):
    """Safe error message without authorization headers or token data."""


def http_request(url, method="GET", *, headers=None, body=None):
    request = urllib.request.Request(url, data=body, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            raw = response.read(262144)
            content = json.loads(raw) if raw else {}
            return response.status, content, dict(response.headers)
    except urllib.error.HTTPError as exc:
        raise CapacityError("HTTP {} from {} endpoint".format(exc.code, urllib.parse.urlsplit(url).hostname)) from None
    except urllib.error.URLError:
        raise CapacityError("Network request failed") from None


def oidc_token(tenant, client_id, audience):
    if not GUID.fullmatch(tenant) or not GUID.fullmatch(client_id):
        raise CapacityError("Missing or invalid Entra Tenant/Client ID")
    request_url = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL", "")
    request_token = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN", "")
    if not request_url.startswith("https://") or not request_token:
        raise CapacityError("GitHub OIDC context not available")
    sep = "&" if "?" in request_url else "?"
    url = request_url + sep + urllib.parse.urlencode({"audience": "api://AzureADTokenExchange"})
    _, oidc, _ = http_request(url, headers={"Authorization": "Bearer " + request_token})
    assertion = oidc.get("value")
    if not assertion:
        raise CapacityError("GitHub OIDC assertion missing")
    fields = urllib.parse.urlencode({
        "client_id": client_id,
        "grant_type": "client_credentials",
        "scope": audience + "/.default",
        "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
        "client_assertion": assertion,
    }).encode("utf-8")
    _, result, _ = http_request(
        "https://login.microsoftonline.com/{}/oauth2/v2.0/token".format(tenant),
        method="POST", headers={"Content-Type": "application/x-www-form-urlencoded"},
        body=fields,
    )
    token = result.get("access_token")
    if not token:
        raise CapacityError("Entra access token not issued; check federation and permissions")
    return token


def target(mode, config, paid_arm_id, subscription_id):
    if mode == "trial":
        cid = config.get("trial_capacity_id", "")
        if not GUID.fullmatch(cid):
            raise CapacityError("Trial Capacity ID not configured")
        return FABRIC_AUDIENCE + "/v1/capacities/" + cid, cid
    match = ARM_ID.fullmatch(paid_arm_id or "")
    if not match or not GUID.fullmatch(match.group(1)):
        raise CapacityError("Paid Capacity requires an existing valid Azure ARM resource ID")
    if not GUID.fullmatch(subscription_id or "") or match.group(1).lower() != subscription_id.lower():
        raise CapacityError("Paid Capacity subscription does not match selected Azure identity")
    return ARM_AUDIENCE + paid_arm_id + "?api-version=" + ARM_VERSION, paid_arm_id


def summarize(mode, expected, document):
    if mode == "trial":
        if str(document.get("id", "")).lower() != expected.lower():
            raise CapacityError("Trial capacity readback ID mismatch")
        result = {k: document.get(k) for k in ("id", "displayName", "sku", "region", "state")}
        return {k: v for k, v in result.items() if v is not None}
    if str(document.get("id", "")).lower() != expected.lower():
        raise CapacityError("Azure paid Capacity readback ARM ID mismatch")
    if document.get("type", "").lower() != "microsoft.fabric/capacities":
        raise CapacityError("ARM resource is not Microsoft.Fabric/capacities")
    sku = document.get("sku", {}).get("name", "")
    if not re.fullmatch(r"F[0-9]+", sku):
        raise CapacityError("Capacity is not a supported paid F SKU")
    state = document.get("properties", {}).get("state", "")
    if not state:
        raise CapacityError("Azure capacity state missing")
    return {"id": document["id"], "sku": sku, "state": state,
            "provisioningState": document.get("properties", {}).get("provisioningState")}


def execute(mode, operation, config, *, paid_arm_id="", subscription_id="", env=None, request=http_request, token_provider=oidc_token, sleep=time.sleep):
    env = os.environ if env is None else env
    if mode not in ("trial", "paid"):
        raise CapacityError("Unknown Capacity mode")
    if operation not in ("inspect", "suspend", "resume"):
        raise CapacityError("Unknown Capacity operation")
    if mode == "trial" and operation != "inspect":
        raise CapacityError("Trial Capacity never supports suspend/resume through this controller")
    url, expected = target(mode, config, paid_arm_id, subscription_id)
    audience = FABRIC_AUDIENCE if mode == "trial" else ARM_AUDIENCE
    tenant = env.get("FABRIC_TENANT_ID" if mode == "trial" else "ARM_TENANT_ID", "")
    client = env.get("FABRIC_CLIENT_ID" if mode == "trial" else "ARM_CLIENT_ID", "")
    # Validate permission to run paid write operations before obtaining any token.
    if operation != "inspect":
        if env.get("ENABLE_PAID_CAPACITY_OPERATIONS") != "true":
            raise CapacityError("Paid Capacity lifecycle operations are disabled")
        if env.get("CAPACITY_ACTION_CONFIRM") != operation.upper():
            raise CapacityError("Explicit matching operation confirmation required")
    token = token_provider(tenant, client, audience)
    headers = {"Authorization": "Bearer " + token, "Accept": "application/json"}
    _, data, _ = request(url, headers=headers)
    observed = summarize(mode, expected, data)
    if operation == "inspect":
        return {"mode": mode, "operation": operation, "outcome": "OBSERVED", "capacity": observed}
    state = observed["state"].lower()
    final_state = "suspended" if operation == "suspend" else "active"
    if state in (final_state, "paused" if operation == "suspend" else final_state):
        return {"mode": mode, "operation": operation, "outcome": "ALREADY_AT_TARGET", "capacity": observed}
    if operation == "suspend" and state != "active":
        raise CapacityError("Cannot suspend Capacity from current state: " + observed["state"])
    if operation == "resume" and state not in ("suspended", "paused"):
        raise CapacityError("Cannot resume Capacity from current state: " + observed["state"])
    request(url.replace("?api-version=", "/" + operation + "?api-version="),
            method="POST", headers=headers, body=b"")
    # ARM may return 202 Accepted asynchronously. Never claim completed just on POST.
    for attempt in range(MAX_ATTEMPTS):
        if attempt:
            sleep(5)
        _, current, _ = request(url, headers=headers)
        observed = summarize(mode, expected, current)
        if observed["state"].lower() in ({ "suspended", "paused" } if operation == "suspend" else {"active"}):
            return {"mode": mode, "operation": operation, "outcome": "CONFIRMED", "capacity": observed}
    raise CapacityError("Capacity change requested but final state not confirmed; inspect before retry")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Fabric Capacity read-only Trial / guarded paid lifecycle")
    parser.add_argument("--mode", required=True, choices=("trial", "paid"))
    parser.add_argument("--operation", default="inspect", choices=("inspect", "suspend", "resume"))
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("capacity.json"))
    args = parser.parse_args(argv)
    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        result = execute(args.mode, args.operation, config,
                         paid_arm_id=os.getenv("PAID_CAPACITY_ARM_ID", ""),
                         subscription_id=os.getenv("ARM_SUBSCRIPTION_ID", ""))
        print("#### FABRIC_CAPACITY_API_OUTPUT_BEGIN ####")
        print(json.dumps(result, sort_keys=True))
        print("#### FABRIC_CAPACITY_API_OUTPUT_END ####")
        return 0
    except (CapacityError, ValueError, OSError) as exc:
        print("CAPACITY_API_ERROR=" + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
