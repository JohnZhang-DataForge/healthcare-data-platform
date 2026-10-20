#!/usr/bin/env python3
"""Strict, offline Bootstrap identity/OIDC request and resolved-ID contract.

No GitHub/Azure/Fabric calls, credential creation, Terraform, or privilege grants.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from fabric_bootstrap_profile import (
    InvalidBootstrapProfile, _fields, _no_duplicate_keys, _uuid, validate,
)

REPOSITORY = "JohnZhang-DataForge/Self-Runner"
IMMUTABLE_PREFIX = "repo:JohnZhang-DataForge@337895338/Self-Runner@1413796156"
ISSUER = "https://token.actions.githubusercontent.com"
AUDIENCE = "api://AzureADTokenExchange"
MAIN_REF = "refs/heads/main"
SEED_REF_RE = re.compile(r"^SEED-[A-Z0-9-]{8,72}$")
ROLES = ("backend_operator", "fabric_deployer", "blob_reader")
# Main-ref trust is shared across all main workflows. Separate Azure Entra App
# permissions restrict impact, but OIDC does not bind an individual workflow.
OIDC_BINDINGS = {"plan_backend": "backend_operator",
                 "plan_deployer": "fabric_deployer"}


def validate_identity_request(bootstrap_profile: object, request: object) -> dict:
    """Validate planned, *uncreated* apps and narrow federated credential subjects."""
    p = validate(bootstrap_profile)
    r = _fields(request, {"schema_version", "environment", "seed_operator",
                          "applications", "oidc_bindings"}, "identity_request")
    if type(r["schema_version"]) is not int or r["schema_version"] != 3:
        raise InvalidBootstrapProfile("unsupported identity schema")
    if r["environment"] != p["environment"]:
        raise InvalidBootstrapProfile("identity environment differs from Bootstrap profile")

    seed = _fields(r["seed_operator"], {"backend_tenant_id", "fabric_tenant_id",
                                       "authorization_reference"}, "seed_operator")
    if (_uuid(seed["backend_tenant_id"]) != p["backend_tenant_id"]
            or _uuid(seed["fabric_tenant_id"]) != p["fabric_tenant_id"]):
        raise InvalidBootstrapProfile("seed tenant mismatch")
    if (not isinstance(seed["authorization_reference"], str)
            or not SEED_REF_RE.fullmatch(seed["authorization_reference"])
            or "PENDING" in seed["authorization_reference"]
            or "EXAMPLE" in seed["authorization_reference"]):
        raise InvalidBootstrapProfile("seed custody approval reference invalid")

    apps = _fields(r["applications"], set(ROLES), "applications")
    names = set()
    for role in ROLES:
        app = _fields(apps[role], {"operation", "tenant_id", "display_name"},
                      f"applications.{role}")
        tenant_id = p["fabric_tenant_id"] if role == "fabric_deployer" else p["backend_tenant_id"]
        expected_name = f"hdp-{p['environment']}-{role.replace('_', '-')}"
        if (app["operation"] != "create-new"
                or _uuid(app["tenant_id"]) != tenant_id
                or app["display_name"] != expected_name
                or app["display_name"] in names):
            raise InvalidBootstrapProfile("role identity, ownership or tenant mismatch")
        names.add(app["display_name"])

    bindings = _fields(r["oidc_bindings"], set(OIDC_BINDINGS), "oidc_bindings")
    resolved_bindings = {}
    for binding_name, role in OIDC_BINDINGS.items():
        binding = _fields(
            bindings[binding_name],
            {"repository", "ref", "issuer", "audience", "trust_mode"},
            f"oidc_bindings.{binding_name}"
        )
        if (binding["repository"] != REPOSITORY
                or binding["ref"] != MAIN_REF
                or binding["issuer"] != ISSUER
                or binding["audience"] != AUDIENCE
                or binding["trust_mode"] != "single-operator-main-ref"):
            raise InvalidBootstrapProfile("unsafe OIDC issuer, repository or main-ref scope")
        resolved_bindings[binding_name] = {
            "tenant_id": apps[role]["tenant_id"],
            "application_role": role,
            "issuer": ISSUER,
            "audience": AUDIENCE,
            "subject": f"{IMMUTABLE_PREFIX}:ref:{MAIN_REF}",
            "required_branch_ref": MAIN_REF,
            "workflow_role_isolation_by_oidc": False,
        }

    return {
        "status": "BOOTSTRAP_IDENTITY_STATIC_HOLD",
        "bootstrap_mode": p["bootstrap_mode"],
        "environment": p["environment"],
        "identity_topology": p["identity_topology"],
        "seed_authorization_verified": False,
        "github_environment_protection_verified": False,
        "github_environment_required": False,
        "workflow_role_isolation_by_oidc": False,
        "apply_authorized": False,
        "application_inventory_verified": False,
        "app_client_ids_resolved": False,
        "applications": {
            role: {"operation": "create-new", "display_name": apps[role]["display_name"],
                   "tenant_id": apps[role]["tenant_id"]}
            for role in ROLES
        },
        "oidc_bindings": resolved_bindings,
        "credential_values_present": False,
        "verified": False,
        "cloud_executed": False,
        "terraform_executed": False,
    }


def validate_resolved_client_ids(bootstrap_profile: object, resolved: object) -> dict:
    """Validate independent post-create IDs before any downstream handoff.

    This does NOT prove that the applications exist or that their permissions work.
    """
    p = validate(bootstrap_profile)
    ids = _fields(resolved, set(ROLES), "resolved_client_ids")
    result = {}
    for role in ROLES:
        item = _fields(ids[role], {"tenant_id", "client_id"}, f"resolved.{role}")
        expected = p["fabric_tenant_id"] if role == "fabric_deployer" else p["backend_tenant_id"]
        if _uuid(item["tenant_id"]) != expected:
            raise InvalidBootstrapProfile("resolved application tenant mismatch")
        result[role] = _uuid(item["client_id"])
    if len(set(result.values())) != len(ROLES):
        raise InvalidBootstrapProfile("role client IDs must be independently allocated")
    return {"status": "RESOLVED_IDS_FORMAT_PASS_NOT_VERIFIED",
            "client_ids": result, "verified": False, "cloud_executed": False}


def load(profile_path: Path, identities_path: Path) -> dict:
    with profile_path.open(encoding="utf-8") as stream:
        profile = json.load(stream, object_pairs_hook=_no_duplicate_keys)
    with identities_path.open(encoding="utf-8") as stream:
        request = json.load(stream, object_pairs_hook=_no_duplicate_keys)
    return validate_identity_request(profile, request)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--identities", required=True, type=Path)
    args = parser.parse_args(argv)
    print("#### FABRIC_BOOTSTRAP_IDENTITY_OUTPUT_BEGIN ####")
    try:
        result = load(args.profile, args.identities)
    except (OSError, ValueError, TypeError, KeyError):
        # Never echo an attacker-controlled field or embedded secret.
        print("STATUS=FAIL; offline identity request rejected")
        print("#### FABRIC_BOOTSTRAP_IDENTITY_OUTPUT_END ####")
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    print("#### FABRIC_BOOTSTRAP_IDENTITY_OUTPUT_END ####")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
