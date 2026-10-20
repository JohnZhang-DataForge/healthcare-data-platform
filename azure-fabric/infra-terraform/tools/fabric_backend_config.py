#!/usr/bin/env python3
"""Generate inert AzureRM backend arguments for a NEW Fabric environment.

No Terraform process, token request, cloud call, remote-state read or filesystem write.
Callers must not confuse a validated key with an available or empty remote state.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from fabric_deployment_target import build, COMPONENTS
from fabric_environment_preflight import InvalidEnvironment


def backend_arguments(deployment: dict, component: str, backend_client_id: str) -> dict[str, str]:
    """Return an exact allowlisted backend-config mapping; no secrets or side effects."""
    if component not in COMPONENTS:
        raise InvalidEnvironment("component is not a supported new Fabric root")
    from fabric_deployment_target import _uuid
    client = _uuid(backend_client_id, "backend client")
    backend = deployment["backend"]
    key = backend["state_keys"][component]
    expected = f"fabric/{deployment['environment']}/{component}.tfstate"
    if key != expected or key.startswith("dev/"):
        raise InvalidEnvironment("unsafe or mismatched backend key")
    if backend["container_name"] != "tfstate":
        raise InvalidEnvironment("backend container must remain tfstate")
    account = backend["storage_account_name"]
    mode = backend.get("bootstrap_mode")
    if mode == "reuse-existing":
        if account != "johnzhang" or backend.get("storage_account_arm_id") is not None:
            raise InvalidEnvironment("reuse mode cannot change legacy account")
    elif mode == "fresh-bootstrap":
        if (deployment.get("bootstrap_mode") != mode
                or not isinstance(account, str)
                or not re.fullmatch(r"hdp[a-z0-9]{0,21}", account)
                or not isinstance(backend.get("storage_account_arm_id"), str)):
            raise InvalidEnvironment("fresh backend is not Bootstrap-derived")
        source = backend["storage_account_arm_id"]
        expected_tail = (
            f"/resourceGroups/rg-hdp-{deployment['environment']}"
            f"/providers/Microsoft.Storage/storageAccounts/{account}"
        )
        if (not re.fullmatch(r"/subscriptions/[0-9a-f-]{36}", source[:-len(expected_tail)])
                or not source.endswith(expected_tail)):
            raise InvalidEnvironment("fresh backend ARM origin mismatch")
    else:
        raise InvalidEnvironment("unsupported backend origin")
    return {
        "storage_account_name": account,
        "container_name": "tfstate",
        "key": expected,
        "tenant_id": backend["tenant_id"],
        "client_id": client,
        "use_oidc": "true",
        "use_azuread_auth": "true",
    }


def render_backend_config(arguments: dict[str, str]) -> str:
    """Produce literal -backend-config lines, never a Terraform command."""
    ordered = ("storage_account_name", "container_name", "key", "tenant_id",
               "client_id", "use_oidc", "use_azuread_auth")
    if set(arguments) != set(ordered):
        raise InvalidEnvironment("unexpected backend configuration fields")
    if any(not isinstance(arguments[k], str) for k in ordered):
        raise InvalidEnvironment("invalid backend value type")
    # Values originate from strict UUID and environment validators, not untrusted free text.
    if any("\n" in arguments[k] or "\r" in arguments[k] or '"' in arguments[k]
           for k in ordered):
        raise InvalidEnvironment("unsafe backend value")
    return "".join(f'{key}="{arguments[key]}"\n' for key in ordered)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--component", choices=COMPONENTS, required=True)
    parser.add_argument("--backend-client-id", required=True)
    parser.add_argument("--backend-tenant-id", required=True)
    parser.add_argument("--fabric-client-id", required=True)
    parser.add_argument("--fabric-tenant-id", required=True)
    args = parser.parse_args()
    try:
        deployment = build(args.config, args.backend_client_id, args.fabric_client_id,
                           args.backend_tenant_id, args.fabric_tenant_id)
        result = backend_arguments(deployment, args.component, args.backend_client_id)
        # Only render an inert preview; never execute or write a tfbackend file.
        print("#### FABRIC_BACKEND_OFFLINE_OUTPUT_BEGIN ####")
        print(render_backend_config(result), end="")
        print("REMOTE_STATE_CHECKED=NO\nTERRAFORM_EXECUTED=NO")
        print("#### FABRIC_BACKEND_OFFLINE_OUTPUT_END ####")
    except (OSError, ValueError, KeyError, TypeError):
        print("STATUS=FAIL; offline Fabric backend contract rejected")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
