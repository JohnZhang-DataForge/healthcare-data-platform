#!/usr/bin/env python3
"""Static-only GitHub OIDC subject compatibility audit (never cloud auth).

Frozen metadata from GitHub repository API at 2026-10-20. Current credentials
are NOT provisioned. No provider/oidc/GitHub API calls, secrets, or Terraform.
"""
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

# Both repositories were created after the immutable default threshold
# 2026-07-15 (Healthcare 2026-10-05 / Self-Runner 2026-10-11).
CURRENT_OIDC_REPO = f"{OWNER}/{HEALTHCARE}"
CONTROLLER_REPO = f"{OWNER}/{SELF_RUNNER}"
ENV_TOKEN = "${var.environment}"


class OIDCSourceDrift(ValueError):
    pass


def inspect_source(hcl: str) -> dict:
    """Only the *present* legacy source is accepted; modifications require review."""
    if not isinstance(hcl, str):
        raise OIDCSourceDrift("invalid Terraform source")
    subjects = re.findall(r'(?m)^\s*subject\s*=\s*"([^"\r\n]+)"\s*$', hcl)
    expected = {
        f"repo:{CURRENT_OIDC_REPO}:environment:fabric-{ENV_TOKEN}-backend",
        f"repo:{CURRENT_OIDC_REPO}:environment:fabric-{ENV_TOKEN}-deployer",
    }
    if len(subjects) != 2 or len(set(subjects)) != 2 or set(subjects) != expected:
        raise OIDCSourceDrift("federation subjects changed; trusted topology needs review")
    prefix = f"repo:{OWNER}@{OWNER_ID}/{HEALTHCARE}@{HEALTHCARE_REPOSITORY_ID}"
    controller_prefix = f"repo:{OWNER}@{OWNER_ID}/{SELF_RUNNER}@{SELF_RUNNER_REPOSITORY_ID}"
    immutable_expected = {
        f"{prefix}:environment:fabric-{ENV_TOKEN}-backend",
        f"{prefix}:environment:fabric-{ENV_TOKEN}-deployer",
    }
    if any(s.startswith(prefix) for s in subjects):
        raise OIDCSourceDrift("immutable OIDC unexpectedly present in legacy contract")
    return {
        "status": "FABRIC_OIDC_SUBJECT_ARCHITECTURE_HOLD",
        "current_literal_subjects": sorted(subjects),
        "expected_immutable_healthcare_subjects_FOR_DESIGN_ONLY": sorted(immutable_expected),
        "example_immutable_self_runner_phase_subject_FOR_DESIGN_ONLY":
            f"{controller_prefix}:environment:fabric-{ENV_TOKEN}-plan",
        "github_repositories_created_after_immutable_default": True,
        "self_runner_controller_repo_distinct_from_issuer_repo": True,
        "role_env_names_different_from_plan_apply_env_names": True,
        "blockers": [
            "DECLARED_OIDC_IS_NAME_ONLY_BUT_REPOSITORIES_CREATED_AFTER_2026_07_15",
            "SELF_RUNNER_CONTROLLER_REPOSITORY_DIFFERS_FROM_ENROLLED_HEALTHCARE_OIDC",
            "ROLE_SPECIFIC_BACKEND_AND_DEPLOYER_SUBJECTS_DO_NOT_MATCH_PHASE_JOB_SUBJECT",
            "REPOSITORY_OR_ENVIRONMENT_OIDC_TOKEN_PREVIEW_NOT_CHECKED",
            "PROTECTED_GITHUB_ENVIRONMENT_BRANCH_AND_REVIEWER_RULES_NOT_CHECKED",
            "NO_PRIVILEGED_EXECUTOR_OR_ACCOUNT_BILLING_AUTHORIZATION",
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
        print("STATUS=FAIL; OIDC topology requires reviewed update")
        print("#### FABRIC_OIDC_SUBJECT_AUDIT_OUTPUT_END ####")
        return 2
    print(json.dumps(status, indent=2, sort_keys=True))
    print("#### FABRIC_OIDC_SUBJECT_AUDIT_OUTPUT_END ####")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
