#!/usr/bin/env python3
"""Offline check of Fabric supported-connection-types API response.

Reads a *saved* API response; never requests a token, calls Fabric or writes State.
Does not approve a connection resource or infer connector names.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


class UnsupportedConnection(ValueError):
    """The supplied connector contract is incomplete or unsupported."""


def unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise UnsupportedConnection("duplicate JSON key")
        obj[key] = value
    return obj


def inspect_metadata(data, *, connection_type, creation_method, credential_type,\n                     user_controlled_code=False):
    if not isinstance(data, dict) or not isinstance(data.get("value"), list):
        raise UnsupportedConnection("expected supportedConnectionTypes response")
    if data.get("continuationToken") or data.get("continuationUri"):
        raise UnsupportedConnection("incomplete paginated response; collect all pages")
    if not isinstance(connection_type, str) or not connection_type.strip():
        raise UnsupportedConnection("explicit connection type required")
    if not isinstance(creation_method, str) or not creation_method.strip():
        raise UnsupportedConnection("explicit creation method required")
    if credential_type not in ("ServicePrincipal", "WorkspaceIdentity"):
        raise UnsupportedConnection("unapproved credential type")
    matches = [x for x in data["value"] if isinstance(x, dict) and x.get("type") == connection_type]
    if len(matches) != 1:
        raise UnsupportedConnection("connection type absent or ambiguous")
    record = matches[0]
    if credential_type not in record.get("supportedCredentialTypes", []):
        raise UnsupportedConnection("credential not supported by selected type")
    if type(user_controlled_code) is not bool:
        raise UnsupportedConnection("user-controlled-code flag must be boolean")
    if user_controlled_code and credential_type not in record.get(
        "supportedCredentialTypesForUsageInUserControlledCode", []
    ):
        raise UnsupportedConnection("credential not allowed in user-controlled code")
    methods = record.get("creationMethods")
    if not isinstance(methods, list):
        raise UnsupportedConnection("missing creation methods")
    selected = [m for m in methods if isinstance(m, dict) and m.get("name") == creation_method]
    if len(selected) != 1 or not isinstance(selected[0].get("parameters"), list):
        raise UnsupportedConnection("creation method absent, ambiguous or missing parameters")
    parameters = selected[0]["parameters"]
    names = set()
    safe = []
    for item in parameters:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str) or not item["name"].strip():
            raise UnsupportedConnection("invalid parameter declaration")
        name = item["name"]
        if name in names or not isinstance(item.get("required"), bool):
            raise UnsupportedConnection("duplicate name or missing required flag")
        names.add(name)
        data_type = item.get("dataType")
        allowed_types = {"Text", "Number", "Boolean", "Duration", "Date",
                         "DateTime", "DateTimeZone", "Time"}
        if data_type not in allowed_types:
            raise UnsupportedConnection("invalid or absent data type")
        allowed_values = item.get("allowedValues", [])
        if not isinstance(allowed_values, list) or any(
            not isinstance(value, str) for value in allowed_values
        ) or len(allowed_values) != len(set(allowed_values)):
            raise UnsupportedConnection("invalid allowed values")
        safe.append({"name": name, "required": item["required"],
                     "data_type": data_type, "allowed_values": allowed_values})
    return {
        "status": "METADATA_OFFLINE_PASS",
        "connection_type": connection_type,
        "creation_method": creation_method,
        "credential_type": credential_type,\n        "user_controlled_code": user_controlled_code,
        "parameters": safe,
        "tenant_access_verified": False,
        "credential_delivery_verified": False,
        "terraform_executed": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--response", required=True, type=Path)\n    parser.add_argument("--user-controlled-code", action="store_true")
    parser.add_argument("--connection-type", required=True)
    parser.add_argument("--creation-method", required=True)
    parser.add_argument("--credential-type", choices=("ServicePrincipal", "WorkspaceIdentity"), required=True)
    args = parser.parse_args()
    try:
        response = json.loads(args.response.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
        output = inspect_metadata(response, connection_type=args.connection_type,
                                  creation_method=args.creation_method, credential_type=args.credential_type,\n                                  user_controlled_code=args.user_controlled_code)
    except (OSError, ValueError, TypeError):
        print("STATUS=FAIL; connection metadata is missing or unsupported")
        return 2
    print(json.dumps(output, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
