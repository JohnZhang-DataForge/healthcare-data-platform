#!/usr/bin/env python3
"""Offline, fail-closed validation of a new Fabric deployment environment.

This tool never accesses Azure, Fabric, GitHub, Terraform or remote state.
Only non-secret identifiers are accepted in its input file.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from uuid import UUID

ENV_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
STATE_COMPONENTS = ("workspace", "onelake", "connection")
LEGACY_ENVIRONMENTS = {"dev", "main", "default", "production"}


class InvalidEnvironment(ValueError):
    """An environment is unsafe, incomplete or ambiguous."""


def _object_without_duplicates(items: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in items:
        if key in result:
            raise InvalidEnvironment(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _fields(value: object, location: str, required: set[str]) -> dict[str, object]:
    if not isinstance(value, dict):
        raise InvalidEnvironment(f"{location} must be a JSON object")
    actual = set(value)
    missing = sorted(required - actual)
    extra = sorted(actual - required)
    if missing:
        raise InvalidEnvironment(f"{location} missing fields: {', '.join(missing)}")
    if extra:
        raise InvalidEnvironment(
            f"{location} unexpected fields (credentials are forbidden): {', '.join(extra)}"
        )
    return value


def _literal(obj: dict[str, object], key: str, expected: str, location: str) -> None:
    if obj[key] != expected or not isinstance(obj[key], str):
        raise InvalidEnvironment(f"{location}.{key} must be {expected!r}")


def _uuid(value: object, location: str) -> None:
    if not isinstance(value, str) or not UUID_RE.fullmatch(value):
        raise InvalidEnvironment(f"{location} must be a canonical UUID")
    if UUID(value).int == 0:
        raise InvalidEnvironment(f"{location} must not be a nil UUID")


def validate(config: object) -> dict[str, object]:
    """Return a safe summary, or raise InvalidEnvironment without any side effects."""
    data = _fields(
        config, "config", {"schema_version", "environment", "backend", "landing", "fabric"}
    )
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise InvalidEnvironment("schema_version must be integer 1")

    environment = data["environment"]
    if (
        not isinstance(environment, str)
        or len(environment) > 40
        or not ENV_RE.fullmatch(environment)
        or environment in LEGACY_ENVIRONMENTS
    ):
        raise InvalidEnvironment("environment must be a distinct lowercase kebab-case name")

    backend = _fields(
        data["backend"], "backend",
        {"storage_account", "container", "tenant_id", "state_prefix"},
    )
    landing = _fields(data["landing"], "landing", {"storage_account", "container"})
    fabric = _fields(data["fabric"], "fabric", {"tenant_id", "capacity_id", "workspace_name"})

    _literal(backend, "storage_account", "johnzhang", "backend")
    _literal(backend, "container", "tfstate", "backend")
    _literal(landing, "storage_account", "johnzhang", "landing")
    _literal(landing, "container", "landing", "landing")
    _uuid(backend["tenant_id"], "backend.tenant_id")
    _uuid(fabric["tenant_id"], "fabric.tenant_id")
    _uuid(fabric["capacity_id"], "fabric.capacity_id")

    identity_topology = (
        "same-tenant" if backend["tenant_id"].lower() == fabric["tenant_id"].lower()
        else "cross-tenant"
    )

    prefix = f"fabric/{environment}"
    _literal(backend, "state_prefix", prefix, "backend")
    workspace = f"HDP-{environment}"
    _literal(fabric, "workspace_name", workspace, "fabric")

    return {
        "status": "STATIC_PREFLIGHT_PASS",
        "environment": environment,
        "workspace_name": workspace,
        "identity_topology": identity_topology,
        "backend_location": "johnzhang/tfstate",
        "landing_location": "johnzhang/landing",
        "state_keys": {
            component: f"{prefix}/{component}.tfstate" for component in STATE_COMPONENTS
        },
        "external_access_verified": False,
        "terraform_executed": False,
    }


def load(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as file:
        data = json.load(file, object_pairs_hook=_object_without_duplicates)
    return validate(data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args(argv)
    print("#### FABRIC_ENVIRONMENT_PREFLIGHT_OUTPUT_BEGIN ####")
    try:
        summary = load(args.config)
    except (OSError, ValueError) as error:
        print("STATUS=FAIL", file=sys.stderr)
        print(f"REASON={error}", file=sys.stderr)
        print("#### FABRIC_ENVIRONMENT_PREFLIGHT_OUTPUT_END ####")
        return 2
    print(json.dumps(summary, indent=2, sort_keys=True))
    print("#### FABRIC_ENVIRONMENT_PREFLIGHT_OUTPUT_END ####")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
