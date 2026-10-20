#!/usr/bin/env python3
"""Read-only Seed Operator inventory: no cloud writes, state or secrets.

Run under an explicitly selected Azure CLI tenant. Cloud errors and all
application identifiers are intentionally omitted from stdout.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from fabric_bootstrap_identity import (
    AUDIENCE, IMMUTABLE_PREFIX, ISSUER, MAIN_REF,
    load, validate_resolved_client_ids,
)
from fabric_bootstrap_profile import _no_duplicate_keys, validate

ROLES = {"backend": ("backend_operator", "blob_reader"),
         "fabric": ("fabric_deployer",)}
FIC_SUFFIX = {"backend_operator": "backend-plan-github",
              "fabric_deployer": "fabric-plan-github"}


class InventoryHold(ValueError):
    pass


def read_az(*command: str) -> object:
    # No 'az login', graph write, Terraform, GitHub writes or subscription changes.
    allowed = (("az", "account", "show"),
               ("az", "ad", "app", "list"),
               ("az", "ad", "app", "show"),
               ("az", "ad", "sp", "show"),
               ("az", "ad", "app", "federated-credential", "list"))
    if not any(command[:len(p)] == p for p in allowed):
        raise InventoryHold("not a permitted read-only operation")
    try:
        result = subprocess.run([*command, "--only-show-errors", "-o", "json"],
                                capture_output=True, text=True,
                                timeout=30, check=False)
        if result.returncode or len(result.stdout) > 300000:
            raise InventoryHold("Azure inventory unavailable")
        return json.loads(result.stdout, object_pairs_hook=_no_duplicate_keys)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        raise InventoryHold("Azure inventory unavailable") from exc


def verify_fics(records: object, environment: str, role: str) -> None:
    if not isinstance(records, list):
        raise InventoryHold("invalid FIC inventory")
    if role == "blob_reader":
        if records:
            raise InventoryHold("Blob Reader is not permitted a GitHub OIDC FIC")
        return
    if len(records) != 1 or not isinstance(records[0], dict):
        raise InventoryHold("expected exactly one role FIC")
    expected = {"name": f"hdp-{environment}-{FIC_SUFFIX[role]}",
                "issuer": ISSUER,
                "subject": f"{IMMUTABLE_PREFIX}:ref:{MAIN_REF}",
                "audiences": [AUDIENCE]}
    if any(records[0].get(k) != v for k, v in expected.items()):
        raise InventoryHold("FIC scope mismatch")


def inspect(profile: dict, request: dict, role: str, phase: str,
            resolved: dict | None = None) -> dict:
    if role not in ROLES or phase not in ("before", "after"):
        raise InventoryHold("unsupported phase or tenant role")
    original_profile = profile
    profile = validate(original_profile)
    tenant = profile["fabric_tenant_id"] if role == "fabric" else profile["backend_tenant_id"]
    active = read_az("az", "account", "show")
    if not isinstance(active, dict) or str(active.get("tenantId", "")).lower() != tenant:
        raise InventoryHold("wrong active Azure CLI tenant")
    ids = {}
    if phase == "after":
        if resolved is None:
            raise InventoryHold("missing resolved Client IDs")
        ids = validate_resolved_client_ids(original_profile, resolved)["client_ids"]
    for app_role in ROLES[role]:
        name = request["applications"][app_role]["display_name"]
        result = read_az("az", "ad", "app", "list", "--display-name", name, "--all")
        if not isinstance(result, list):
            raise InventoryHold("invalid application inventory")
        exact = [app for app in result
                 if isinstance(app, dict) and app.get("displayName") == name]
        if phase == "before":
            if exact:
                raise InventoryHold("application name collision; do not adopt")
            continue
        if len(exact) != 1 or str(exact[0].get("appId", "")).lower() != ids[app_role]:
            raise InventoryHold("client ID ownership mismatch")
        app = read_az("az", "ad", "app", "show", "--id", ids[app_role])
        sp = read_az("az", "ad", "sp", "show", "--id", ids[app_role])
        if (not isinstance(app, dict) or app.get("displayName") != name
                or str(app.get("appId", "")).lower() != ids[app_role]
                or not isinstance(sp, dict)
                or str(sp.get("appId", "")).lower() != ids[app_role]):
            raise InventoryHold("app registration or SP evidence mismatch")
        verify_fics(read_az("az", "ad", "app", "federated-credential",
                            "list", "--id", ids[app_role]),
                    profile["environment"], app_role)
    return {"status": "INVENTORY_READONLY_PASS_NOT_AUTHORIZATION",
            "role": role, "phase": phase, "checked": len(ROLES[role]),
            "fic_verified": phase == "after",
            "entra_exchange": "NOT_TESTED", "terraform_plan_apply": "NO"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--identities", required=True, type=Path)
    parser.add_argument("--tenant-role", required=True, choices=tuple(ROLES))
    parser.add_argument("--phase", required=True, choices=("before", "after"))
    parser.add_argument("--resolved-ids", type=Path)
    args = parser.parse_args(argv)
    print("#### FABRIC_SEED_INVENTORY_OUTPUT_BEGIN ####")
    try:
        with args.profile.open(encoding="utf-8") as stream:
            profile = json.load(stream, object_pairs_hook=_no_duplicate_keys)
        request = load(args.profile, args.identities)
        if args.phase == "after":
            if not args.resolved_ids:
                raise InventoryHold("resolved client IDs missing")
            with args.resolved_ids.open(encoding="utf-8") as stream:
                ids = json.load(stream, object_pairs_hook=_no_duplicate_keys)
        else:
            if args.resolved_ids:
                raise InventoryHold("unexpected client IDs during precreate")
            ids = None
        print(json.dumps(inspect(profile, request, args.tenant_role, args.phase, ids),
                         sort_keys=True))
        status = 0
    except Exception:
        print("STATUS=HOLD; Azure identity inventory not verified")
        print("CLOUD_ERROR_DETAILS=REDACTED")
        status = 2
    print("#### FABRIC_SEED_INVENTORY_OUTPUT_END ####")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
