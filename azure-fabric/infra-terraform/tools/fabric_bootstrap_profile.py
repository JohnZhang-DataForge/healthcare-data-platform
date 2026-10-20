#!/usr/bin/env python3
"""Strict offline profile validator for Fabric infrastructure Bootstrap.

No Terraform, Azure, GitHub, credential, remote State or network operations.
Passing validation NEVER authorizes paid Capacity creation or an Apply.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from uuid import UUID

ENV_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
ACCOUNT_RE = re.compile(r"^[a-z][a-z0-9]{2,23}$")
RG_RE = re.compile(r"^[A-Za-z0-9_.()-]{1,90}$")
STATE_CUSTODY_RE = re.compile(r"^CUSTODY-[A-Z0-9-]{7,72}$")
ALLOWED_F_SKUS = {"F2", "F4", "F8", "F16", "F32", "F64",
                  "F128", "F256", "F512", "F1024", "F2048"}
REGION_RE = re.compile(r"^[a-z][a-z0-9]{1,30}$")
SKU_RE = re.compile(r"^F[1-9][0-9]{0,3}$")
REVIEW_RE = re.compile(r"^[A-Z][A-Z0-9-]{6,80}$")
REPOSITORY = "JohnZhang-DataForge/healthcare-data-platform"
LEGACY_ENVIRONMENTS = {"dev", "main", "default", "production"}


class InvalidBootstrapProfile(ValueError):
    """Bootstrap profile is incomplete, ambiguous or unsafe."""


def _no_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidBootstrapProfile("duplicate JSON key")
        result[key] = value
    return result


def _fields(value: object, expected: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != expected:
        raise InvalidBootstrapProfile(f"{label}: missing, unexpected or secret fields")
    return value


def _uuid(value: object) -> str:
    if not isinstance(value, str):
        raise InvalidBootstrapProfile("expected canonical UUID")
    try:
        parsed = UUID(value)
    except (TypeError, ValueError, AttributeError) as error:
        raise InvalidBootstrapProfile("expected canonical UUID") from error
    if parsed.int == 0 or str(parsed) != value.lower():
        raise InvalidBootstrapProfile("expected nonzero canonical UUID")
    return str(parsed)


def _match(pattern: re.Pattern, value: object, label: str) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise InvalidBootstrapProfile(f"{label}: invalid value")
    return value


def validate(profile: object) -> dict:
    """Return only a non-secret, explicitly non-authorizing offline summary."""
    obj = _fields(
        profile,
        {"schema_version", "environment", "bootstrap_mode", "tenants",
         "github_oidc", "storage", "bootstrap_state", "capacity"},
        "profile",
    )
    if type(obj["schema_version"]) is not int or obj["schema_version"] != 1:
        raise InvalidBootstrapProfile("unsupported schema version")
    env = _match(ENV_RE, obj["environment"], "environment")
    if len(env) > 40 or env in LEGACY_ENVIRONMENTS:
        raise InvalidBootstrapProfile("reserved or too-long environment")
    mode = obj["bootstrap_mode"]
    if type(mode) is not str or mode not in ("reuse-existing", "fresh-bootstrap"):
        raise InvalidBootstrapProfile("unsupported Bootstrap mode")

    tenants = _fields(obj["tenants"], {"backend_tenant_id", "fabric_tenant_id"}, "tenants")
    backend_tenant = _uuid(tenants["backend_tenant_id"])
    fabric_tenant = _uuid(tenants["fabric_tenant_id"])

    oidc = _fields(obj["github_oidc"], {"repository", "environment"}, "github_oidc")
    if oidc["repository"] != REPOSITORY or oidc["environment"] != f"fabric-{env}":
        raise InvalidBootstrapProfile("OIDC must bind this repo to protected environment")

    storage = _fields(obj["storage"], {"account", "subscription_id", "resource_group",
                                      "landing_container", "state_container",
                                      "state_prefix"}, "storage")
    account = _match(ACCOUNT_RE, storage["account"], "storage.account")
    storage_subscription_id = _uuid(storage["subscription_id"])
    storage_rg = _match(RG_RE, storage["resource_group"], "storage.resource_group")
    if storage_rg.endswith("."):
        raise InvalidBootstrapProfile("Azure resource group must not end with a dot")
    if storage["landing_container"] != "landing" or storage["state_container"] != "tfstate":
        raise InvalidBootstrapProfile("unsupported container mapping")
    if storage["state_prefix"] != f"fabric/{env}":
        raise InvalidBootstrapProfile("state prefix is not isolated")
    if mode == "reuse-existing" and account != "johnzhang":
        raise InvalidBootstrapProfile("reuse-existing requires inventoried legacy account")
    if mode == "fresh-bootstrap":
        if account == "johnzhang" or not account.startswith("hdp"):
            raise InvalidBootstrapProfile("fresh Bootstrap must target a new HDP storage account")
        if storage_rg != f"rg-hdp-{env}":
            raise InvalidBootstrapProfile("fresh Bootstrap resource group must bind environment")

    initial_state = _fields(
        obj["bootstrap_state"], {"strategy", "custody_reference"}, "bootstrap_state"
    )
    if initial_state["strategy"] != "isolated-local":
        raise InvalidBootstrapProfile(
            "Bootstrap state must be isolated from its own new remote backend"
        )
    _match(STATE_CUSTODY_RE, initial_state["custody_reference"],
           "bootstrap_state.custody_reference")

    capacity = obj["capacity"]
    if not isinstance(capacity, dict) or capacity.get("mode") not in (
        "reuse-existing", "create-new"
    ):
        raise InvalidBootstrapProfile("unsupported Capacity mode")
    cap_mode = capacity["mode"]
    if cap_mode == "reuse-existing":
        _fields(capacity, {"mode", "capacity_id"}, "capacity")
        capacity_id = _uuid(capacity["capacity_id"])
    else:
        _fields(
            capacity,
            {"mode", "sku", "region", "subscription_id", "estimated_monthly_usd",
             "monthly_budget_usd", "billing_owner", "cost_review_reference"},
            "capacity",
        )
        _match(SKU_RE, capacity["sku"], "capacity.sku")
        if capacity["sku"] not in ALLOWED_F_SKUS:
            raise InvalidBootstrapProfile("unsupported Fabric F SKU")
        _match(REGION_RE, capacity["region"], "capacity.region")
        capacity_subscription_id = _uuid(capacity["subscription_id"])
        if mode == "fresh-bootstrap" and capacity_subscription_id != storage_subscription_id:
            raise InvalidBootstrapProfile("fresh Capacity and Storage subscriptions differ")
        owner = capacity["billing_owner"]
        if not isinstance(owner, str) or not re.fullmatch(r"[A-Za-z0-9._@-]{2,80}", owner):
            raise InvalidBootstrapProfile("invalid billing owner")
        ref = _match(REVIEW_RE, capacity["cost_review_reference"], "cost review reference")
        if ref.startswith(("PENDING", "EXAMPLE", "REPLACE")):
            raise InvalidBootstrapProfile("cost review must not be a placeholder")
        estimate = capacity["estimated_monthly_usd"]
        budget = capacity["monthly_budget_usd"]
        if (type(estimate) not in (int, float) or type(budget) not in (int, float)
                or not (0 < estimate <= budget <= 1000000)):
            raise InvalidBootstrapProfile("cost estimate/budget invalid or insufficient")
        capacity_id = None

    # Not a deployment config: NEVER convert an input cost reference into proof
    # of billing approval. External inventory, budgets and approvals remain HOLD.
    return {
        "status": ("BOOTSTRAP_PROFILE_HOLD_PAID_APPROVAL" if cap_mode == "create-new"
                   else "BOOTSTRAP_STATIC_CONTRACT_PASS"),
        "environment": env,
        "bootstrap_mode": mode,
        "identity_topology": "same-tenant" if backend_tenant == fabric_tenant else "cross-tenant",
        "backend_tenant_id": backend_tenant,
        "fabric_tenant_id": fabric_tenant,
        "github_oidc_subject_target": f"repo:{REPOSITORY}:environment:fabric-{env}",
        "storage_account": account,
        "storage_subscription_id": storage_subscription_id,
        "storage_resource_group": storage_rg,
        "initial_bootstrap_state_strategy": "isolated-local",
        "landing_container": "landing",
        "backend_container": "tfstate",
        "state_keys": {
            part: f"fabric/{env}/{part}.tfstate"
            for part in ("workspace", "onelake", "connection")
        },
        "capacity_mode": cap_mode,
        "capacity_id": capacity_id,
        "paid_creation_requested": cap_mode == "create-new",
        "cost_review_verified": False,
        "paid_creation_authorized": False,
        "verified": False,
        "initial_bootstrap_state_verified": False,
        "remote_state_checked": False,
        "external_inventory_verified": False,
        "oidc_verified": False,
        "terraform_executed": False,
    }


def load(path: Path) -> dict:
    with path.open(encoding="utf-8") as stream:
        data = json.load(stream, object_pairs_hook=_no_duplicate_keys)
    return validate(data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args(argv)
    print("#### FABRIC_BOOTSTRAP_PROFILE_OUTPUT_BEGIN ####")
    try:
        result = load(args.config)
    except (OSError, ValueError, TypeError):
        # Do not leak malformed user-supplied values into public logs.
        print("STATUS=FAIL; offline Bootstrap profile rejected")
        print("#### FABRIC_BOOTSTRAP_PROFILE_OUTPUT_END ####")
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    print("#### FABRIC_BOOTSTRAP_PROFILE_OUTPUT_END ####")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
