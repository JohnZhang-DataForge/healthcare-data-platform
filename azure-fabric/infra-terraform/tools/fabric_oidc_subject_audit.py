#!/usr/bin/env python3
"""Reviewed static two-app main-ref Self-Runner identity; Entra live still HOLD."""
from __future__ import annotations
import json
from pathlib import Path
import re

OWNER = "JohnZhang-DataForge"
OWNER_ID = 337895338
HEALTHCARE = "healthcare-data-platform"
HEALTHCARE_REPOSITORY_ID = 1404947726
SELF_RUNNER = "Self-Runner"
SELF_RUNNER_REPOSITORY_ID = 1413796156
IMMUTABLE_PREFIX = f"repo:{OWNER}@{OWNER_ID}/{SELF_RUNNER}@{SELF_RUNNER_REPOSITORY_ID}"
BINDINGS = {
    "backend_operator_plan": ("backend", "backend_operator"),
    "fabric_deployer_plan": ("fabric", "fabric_deployer"),
}

class OIDCSourceDrift(ValueError):
    pass

def inspect_source(hcl: str) -> dict:
    if not isinstance(hcl, str):
        raise OIDCSourceDrift("invalid source")
    blocks = re.findall(
        r'(?ms)^resource "azuread_application_federated_identity_credential" "([^"]+)"\s*\{(.*?)(?=^resource "|\Z)',
        hcl)
    if len(blocks) != len(BINDINGS) or set(n for n, _ in blocks) != set(BINDINGS):
        raise OIDCSourceDrift("unexpected federated credential ownership")
    subjects = {}
    for name, body in blocks:
        alias, app = BINDINGS[name]
        expected = f"{IMMUTABLE_PREFIX}:ref:refs/heads/main"
        if (not re.search(r'(?m)^\s*subject\s*=\s*"' + re.escape(expected) + r'"\s*$', body)
                or f"provider       = azuread.{alias}" not in body
                or f"application_id = azuread_application_registration.{app}[0].id" not in body
                or "count          = var.identity_creation_approved ? 1 : 0" not in body
                or "prevent_destroy = true" not in body
                or len(re.findall(r'(?m)^\s*subject\s*=', body)) != 1):
            raise OIDCSourceDrift("immutable main-ref subject/application drift")
        subjects[name] = expected
    if re.search(r'(?m)^\s*subject\s*=\s*"repo:[^"@]+/', hcl):
        raise OIDCSourceDrift("name-only federated subject")
    return {
        "status": "FABRIC_OIDC_SOURCE_ALIGNED_LIVE_HOLD",
        "subject_bindings": subjects,
        "immutable_executor_repository": f"{OWNER}/{SELF_RUNNER}",
        "executor_repository_id": SELF_RUNNER_REPOSITORY_ID,
        "source_repository": f"{OWNER}/{HEALTHCARE}",
        "github_repositories_created_after_immutable_default": True,
        "separate_backend_and_fabric_tenants_required": True,
        "protected_phase_environments_required": False,
        "workflow_isolation_by_oidc_subject": False,
        "role_separation_by_enra_app": True,
        "blockers": [
            "NO_GITHUB_ENVIRONMENT_ON_PRIVATE_FREE_REPO",
            "SHARED_MAIN_REF_SUBJECT_ACROSS_WORKFLOWS",
            "ENTRA_APP_CREDENTIAL_AND_RBAC_NOT_CREATED_OR_VERIFIED",
            "STATE_AND_FABRIC_TRIAL_INVENTORY_NOT_VERIFIED",
            "NO_ISOLATED_TRUSTED_TERRAFORM_PLAN_YET",
        ],
        "token_issued": False,
        "github_environment_protection_verified": False,
        "provider_authenticated": False,
        "terraform_executed": False,
        "deployment_allowed": False,
    }

def main() -> int:
    path = Path(__file__).resolve().parents[1] / "bootstrap/identity/main.tf"
    print("#### FABRIC_OIDC_SUBJECT_AUDIT_OUTPUT_BEGIN ####")
    try:
        status = inspect_source(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        print("STATUS=FAIL; federation topology requires reviewed update")
        print("#### FABRIC_OIDC_SUBJECT_AUDIT_OUTPUT_END ####")
        return 2
    print(json.dumps(status, indent=2, sort_keys=True))
    print("#### FABRIC_OIDC_SUBJECT_AUDIT_OUTPUT_END ####")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
