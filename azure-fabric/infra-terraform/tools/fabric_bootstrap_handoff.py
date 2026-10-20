#!/usr/bin/env python3
"""Non-secret, offline value-only Bootstrap to Fabric Root handoff.

Takes four *unverified* objects and emits a safe preview or explicit HOLD.
It never produces approval flags, Terraform variable files, cloud credentials,
backend commands, or a deployable/authorized plan.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from fabric_bootstrap_identity import validate_resolved_client_ids
from fabric_bootstrap_profile import (
    InvalidBootstrapProfile, _fields, _no_duplicate_keys, _uuid, validate,
)
from fabric_environment_preflight import validate as validate_legacy_environment
from fabric_deployment_target import target

STORAGE_FIELDS = {
    "bootstrap_mode", "backend_tenant_id", "storage_subscription_id",
    "storage_account_id", "storage_account_name", "landing_container",
    "backend_container", "backend_state_prefix", "backend_operator_scope",
    "blob_reader_scope", "resource_ownership_status", "remote_state_checked",
    "initial_state_custody_checked", "cloud_access_verified",
}
CAPACITY_FIELDS = {
    "capacity_mode", "capacity_origin", "fabric_tenant_id",
    "capacity_subscription_id", "reused_fabric_uuid", "created_azure_arm_id",
    "created_fabric_uuid", "resource_ownership", "capacity_id_verified",
    "paid_approval_verified", "external_inventory_read",
}


def _equal(actual: object, expected: object, label: str) -> None:
    if actual != expected or type(actual) is not type(expected):
        raise InvalidBootstrapProfile(f"{label}: incompatible origin or verification flag")


def _arm_id(value: object, expected: str, label: str, *, optional: bool) -> None:
    if optional and value is None:
        return
    if not isinstance(value, str) or value.lower() != expected.lower():
        raise InvalidBootstrapProfile(f"{label}: unexpected Azure resource ownership")


def handoff(profile: object, resolved_clients: object, storage_target: object,
            capacity_target: object) -> dict:
    """Validate provenance, then return only non-executable, unverified facts."""
    p = validate(profile)
    identity = validate_resolved_client_ids(profile, resolved_clients)
    clients = identity["client_ids"]
    s = _fields(storage_target, STORAGE_FIELDS, "storage_target")
    c = _fields(capacity_target, CAPACITY_FIELDS, "capacity_target")
    for key, expected in {
        "bootstrap_mode": p["bootstrap_mode"],
        "backend_tenant_id": p["backend_tenant_id"],
        "storage_subscription_id": p["storage_subscription_id"],
        "storage_account_name": p["storage_account"],
        "landing_container": "landing",
        "backend_container": "tfstate",
        "backend_state_prefix": f"fabric/{p['environment']}",
        "resource_ownership_status": "NOT_VERIFIED",
        "remote_state_checked": False,
        "initial_state_custody_checked": False,
        "cloud_access_verified": False,
    }.items():
        _equal(s[key], expected, f"storage_target.{key}")
    account = p["storage_account"]
    account_id = (
        f"/subscriptions/{p['storage_subscription_id']}"
        f"/resourceGroups/{p['storage_resource_group']}"
        f"/providers/Microsoft.Storage/storageAccounts/{account}"
    )
    _arm_id(s["storage_account_id"], account_id, "storage_target.storage_account_id",
            optional=p["bootstrap_mode"] == "fresh-bootstrap")
    if p["bootstrap_mode"] == "reuse-existing":
        _equal(s["backend_operator_scope"], None, "storage_target.backend_operator_scope")
        _equal(s["blob_reader_scope"], None, "storage_target.blob_reader_scope")
    else:
        for field, container in (("backend_operator_scope", "tfstate"),
                                 ("blob_reader_scope", "landing")):
            _arm_id(s[field], account_id + f"/blobServices/default/containers/{container}",
                    f"storage_target.{field}", optional=True)
        if (s["backend_operator_scope"] is None) != (s["blob_reader_scope"] is None):
            raise InvalidBootstrapProfile("incomplete fresh-only role scopes")
        if s["storage_account_id"] is None and s["backend_operator_scope"] is not None:
            raise InvalidBootstrapProfile("RBAC scope without new storage")

    for key, expected in {
        "capacity_mode": p["capacity_mode"],
        "capacity_origin": p["capacity_mode"],
        "fabric_tenant_id": p["fabric_tenant_id"],
        "resource_ownership": "NOT_VERIFIED",
        "capacity_id_verified": False,
        "paid_approval_verified": False,
        "external_inventory_read": False,
    }.items():
        _equal(c[key], expected, f"capacity_target.{key}")
    capacity_subscription = _uuid(c["capacity_subscription_id"])
    if p["capacity_mode"] == "reuse-existing":
        _equal(c["reused_fabric_uuid"], p["capacity_id"],
               "capacity_target.reused_fabric_uuid")
        _equal(c["created_azure_arm_id"], None, "capacity_target.created_azure_arm_id")
        _equal(c["created_fabric_uuid"], None, "capacity_target.created_fabric_uuid")
    else:
        _equal(capacity_subscription, p["capacity_subscription_id"],
               "capacity_target.capacity_subscription_id")
        _equal(c["reused_fabric_uuid"], None, "capacity_target.reused_fabric_uuid")
        _equal(c["created_fabric_uuid"], None, "capacity_target.created_fabric_uuid")
        name = f"hdp{p['environment'].replace('-', '')}capacity"
        expected = (
            f"/subscriptions/{capacity_subscription}/resourceGroups/"
            f"rg-hdp-{p['environment']}/providers/Microsoft.Fabric/capacities/{name}"
        )
        _arm_id(c["created_azure_arm_id"], expected, "capacity_target.created_azure_arm_id",
                optional=True)

    result = {
        "status": "STATIC_HANDOFF_HOLD_EXTERNAL_INVENTORY",
        "environment": p["environment"],
        "identity_topology": p["identity_topology"],
        "bootstrap_mode": p["bootstrap_mode"],
        "capacity_mode": p["capacity_mode"],
        "source_status": "UNVERIFIED_FORMAT_ONLY",
        "backend_tenant_id": p["backend_tenant_id"],
        "fabric_tenant_id": p["fabric_tenant_id"],
        "storage_subscription_id": p["storage_subscription_id"],
        "capacity_subscription_id": capacity_subscription,
        "storage_account_name": account,
        "storage_account_arm_id": s["storage_account_id"],
        "reused_fabric_capacity_uuid": p["capacity_id"],
        "created_capacity_arm_id": c["created_azure_arm_id"],
        "state_keys": p["state_keys"],
        "identity_client_ids": clients,
        "proposed_legacy_compatible_environment": None,
        "proposed_legacy_compatible_backend": None,
        "proposed_bootstrap_environment": None,
        "proposed_bootstrap_backend": None,
        "proposed_connection_storage_variables": None,
        "blocked_roots": [],
        "verified": False,
        "external_inventory_verified": False,
        "capacity_id_verified": False,
        "billing_approved": False,
        "backend_state_checked": False,
        "github_oidc_verified": False,
        "terraform_executed": False,
    }
    if p["capacity_mode"] == "create-new":
        # Azure ARM ID cannot substitute for Fabric workspace Capacity UUID.
        result["status"] = "STATIC_HANDOFF_HOLD_PAID_CAPACITY_UUID"
        result["blocked_roots"] = ["workspace", "onelake", "connection"]
    else:
        is_fresh = p["bootstrap_mode"] == "fresh-bootstrap"
        candidate = {
            "schema_version": 2 if is_fresh else 1,
            **({"bootstrap_mode": "fresh-bootstrap"} if is_fresh else {}),
            "environment": p["environment"],
            "backend": {"storage_account": account, "container": "tfstate",
                        "tenant_id": p["backend_tenant_id"],
                        "state_prefix": f"fabric/{p['environment']}"},
            "landing": {"storage_account": account, "container": "landing"},
            "fabric": {"tenant_id": p["fabric_tenant_id"],
                       "capacity_id": p["capacity_id"],
                       "workspace_name": f"HDP-{p['environment']}"},
        }
        preview = validate_legacy_environment(
            candidate, bootstrap_profile=profile if is_fresh else None
        )
        bindings = target({
            **preview, "backend_tenant_id": p["backend_tenant_id"],
            "fabric_tenant_id": p["fabric_tenant_id"],
        }, clients["backend_operator"], clients["fabric_deployer"],
            p["backend_tenant_id"], p["fabric_tenant_id"])
        if bindings["backend"]["state_keys"] != p["state_keys"]:
            raise InvalidBootstrapProfile("State key handoff disagrees with approved profile")
        # The Connection Root now supports either Storage origin but keeps
        # fresh provenance and all deployment approvals DEFAULT FALSE.
        result["proposed_connection_storage_variables"] = {
            "bootstrap_mode": p["bootstrap_mode"],
            "storage_account_name": account,
            "fresh_storage_provenance_verified": False,
            "connection_creation_approved": False,
        }
        if is_fresh:
            result["status"] = "STATIC_HANDOFF_HOLD_FRESH_EXTERNAL_APPROVALS"
            result["proposed_bootstrap_environment"] = candidate
            result["proposed_bootstrap_backend"] = bindings["backend"]
        else:
            result["proposed_legacy_compatible_environment"] = candidate
            result["proposed_legacy_compatible_backend"] = bindings["backend"]
    return result


def load(profile_path: Path, clients_path: Path, storage_path: Path,
         capacity_path: Path) -> dict:
    paths = (profile_path, clients_path, storage_path, capacity_path)
    objects = []
    for path in paths:
        with path.open(encoding="utf-8") as stream:
            objects.append(json.load(stream, object_pairs_hook=_no_duplicate_keys))
    return handoff(*objects)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--resolved-clients", required=True, type=Path)
    parser.add_argument("--storage-target", required=True, type=Path)
    parser.add_argument("--capacity-target", required=True, type=Path)
    args = parser.parse_args(argv)
    print("#### FABRIC_BOOTSTRAP_HANDOFF_OUTPUT_BEGIN ####")
    try:
        result = load(args.profile, args.resolved_clients,
                      args.storage_target, args.capacity_target)
    except (OSError, ValueError, TypeError, KeyError):
        print("STATUS=FAIL; non-secret handoff rejected")
        print("#### FABRIC_BOOTSTRAP_HANDOFF_OUTPUT_END ####")
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    print("#### FABRIC_BOOTSTRAP_HANDOFF_OUTPUT_END ####")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
