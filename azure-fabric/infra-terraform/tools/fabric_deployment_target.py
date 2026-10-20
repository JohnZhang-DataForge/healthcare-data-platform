#!/usr/bin/env python3
"""Offline deployment-target contract. Never authenticate or execute Terraform."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from uuid import UUID

from fabric_environment_preflight import InvalidEnvironment, load


COMPONENTS = ("workspace", "onelake", "connection")
AUTH_NAMES = {
    "backend": ("BACKEND_CLIENT_ID", "BACKEND_TENANT_ID"),
    "fabric": ("FABRIC_CLIENT_ID", "FABRIC_TENANT_ID"),
}


def _uuid(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise InvalidEnvironment(f"{label} must be a UUID")
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError) as error:
        raise InvalidEnvironment(f"{label} must be a UUID") from error
    if parsed.int == 0 or str(parsed) != value.lower():
        raise InvalidEnvironment(f"{label} must be a canonical nonzero UUID")
    return str(parsed)


def target(profile: dict, backend_client_id: str, fabric_client_id: str,
           backend_tenant_id: str, fabric_tenant_id: str) -> dict:
    """Construct inert backend arguments after strict identity and state checks."""
    # Both tenant IDs must explicitly match the independently validated profile.
    btenant = _uuid(backend_tenant_id, "backend identity tenant")
    ftenant = _uuid(fabric_tenant_id, "fabric identity tenant")
    bid = _uuid(backend_client_id, "backend client")
    fid = _uuid(fabric_client_id, "fabric client")
    if bid == fid:
        raise InvalidEnvironment("backend and fabric deployment identities must differ")
    if btenant != profile["backend_tenant_id"] or ftenant != profile["fabric_tenant_id"]:
        raise InvalidEnvironment("identity tenant does not match approved environment")
    keys = profile["state_keys"]
    if set(keys) != set(COMPONENTS):
        raise InvalidEnvironment("unexpected state components")
    prefix = f"fabric/{profile['environment']}/"
    expected = {item: f"{prefix}{item}.tfstate" for item in COMPONENTS}
    if keys != expected:
        raise InvalidEnvironment("state keys are not isolated")
    mode = profile.get("bootstrap_mode", "reuse-existing")
    account = profile.get("storage_account_name", "johnzhang")
    arm_id = profile.get("storage_account_arm_id")
    if mode == "reuse-existing":
        if account != "johnzhang" or arm_id is not None:
            raise InvalidEnvironment("legacy account binding is immutable")
    elif mode == "fresh-bootstrap":
        if (profile.get("bootstrap_profile_bounded") is not True
                or not isinstance(account, str)
                or not re.fullmatch(r"hdp[a-z0-9]{0,21}", account)
                or not isinstance(arm_id, str)
                or not re.fullmatch(
                    r"/subscriptions/[0-9a-f-]{36}/resourceGroups/"
                    + re.escape("rg-hdp-" + profile["environment"])
                    + r"/providers/Microsoft[.]Storage/storageAccounts/"
                    + re.escape(account), arm_id)):
            raise InvalidEnvironment("fresh backend must originate in Bootstrap Profile")
    else:
        raise InvalidEnvironment("unsupported storage origin")
    return {
        "status": "OFFLINE_TARGET_PASS",
        "environment": profile["environment"],
        "identity_topology": ("same-tenant" if btenant == ftenant else "cross-tenant"),
        "bootstrap_mode": mode,
        "backend": {
            "bootstrap_mode": mode,
            "storage_account_name": account,
            "storage_account_arm_id": arm_id,
            "container_name": "tfstate",
            "use_oidc": "true",
            "use_azuread_auth": "true",
            "tenant_id": btenant,
            "state_keys": expected,
        },
        "fabric": {"tenant_id": ftenant, "workspace_name": profile["workspace_name"]},
        "identity_separation_verified_offline": True,
        "remote_state_checked": False,
        "terraform_executed": False,
    }


def build(config_path: Path, backend_client_id: str, fabric_client_id: str,
          backend_tenant_id: str, fabric_tenant_id: str) -> dict:
    from fabric_environment_preflight import _object_without_duplicates, validate
    with config_path.open(encoding="utf-8") as stream:
        raw = json.load(stream, object_pairs_hook=_object_without_duplicates)
    summary = validate(raw)
    return target({
        **summary,
        "backend_tenant_id": raw["backend"]["tenant_id"].lower(),
        "fabric_tenant_id": raw["fabric"]["tenant_id"].lower(),
    }, backend_client_id, fabric_client_id, backend_tenant_id, fabric_tenant_id)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--backend-client-id", required=True)
    parser.add_argument("--fabric-client-id", required=True)
    parser.add_argument("--backend-tenant-id", required=True)
    parser.add_argument("--fabric-tenant-id", required=True)
    args = parser.parse_args()
    try:
        result = build(args.config, args.backend_client_id, args.fabric_client_id,
                       args.backend_tenant_id, args.fabric_tenant_id)
    except (OSError, ValueError, KeyError, TypeError) as error:
        # Deliberately do not print arbitrary input strings or user-supplied secrets.
        print("STATUS=FAIL; check offline environment and identity contract")
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
