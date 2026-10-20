#!/usr/bin/env python3
"""Offline, fail-closed Fabric execution-readiness BLOCKER report (never approval).

Five local non-secret input documents are required. The Self-Runner intake
summary is NOT authenticated evidence, even when its fields look correct.
No Cloud SDK, Terraform, GitHub API, remote state, OS subprocess or file writes.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from fabric_bootstrap_handoff import handoff
from fabric_bootstrap_profile import InvalidBootstrapProfile, _no_duplicate_keys

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
ROOTS = frozenset({"identity", "storage", "capacity",
                   "workspace", "onelake", "connection"})
BOOTSTRAP_ROOTS = frozenset({"identity", "storage", "capacity"})
PHASES = frozenset({"bootstrap", "plan", "apply"})
INTAKE_FALSE_FLAGS = frozenset({
    "source_sha_live_verified",
    "reviewed_plan_artifact_verified",
    "protected_environments_verified",
    "separate_authorization_verified",
    "capacity_billing_authorized",
    "remote_state_checked",
    "cloud_access_attempted",
    "terraform_executed",
    "self_runner_used",
    "deployment_allowed",
})
INTAKE_FIELDS = INTAKE_FALSE_FLAGS | frozenset({
    "status", "phase", "root", "environment", "controller_commit",
    "requested_healthcare_commit", "plan_digest_format_checked",
})
HANDOFF_FALSE_FLAGS = frozenset({
    "verified", "external_inventory_verified", "capacity_id_verified",
    "billing_approved", "backend_state_checked", "github_oidc_verified",
    "terraform_executed",
})


def _sha(value: object, label: str) -> str:
    if not isinstance(value, str) or SHA_RE.fullmatch(value) is None or int(value, 16) == 0:
        raise InvalidBootstrapProfile(f"{label}: expected nonzero full source commit")
    return value


def readiness(profile: object, resolved_clients: object, storage_target: object,
              capacity_target: object, controller_intake: object,
              expected_healthcare_sha: str) -> dict[str, object]:
    """Return an offline HOLD report; never a deployable or authenticated grant."""
    pinned_sha = _sha(expected_healthcare_sha, "expected Healthcare SHA")
    if not isinstance(controller_intake, dict) or set(controller_intake) != INTAKE_FIELDS:
        raise InvalidBootstrapProfile("controller intake is incomplete or contains unsafe fields")
    intake = controller_intake
    if intake["status"] != "FABRIC_CONTROLLED_ENTRY_OFFLINE_INTAKE_HOLD":
        raise InvalidBootstrapProfile("controller did not report an offline-only HOLD")
    phase, root = intake["phase"], intake["root"]
    if not isinstance(phase, str) or phase not in PHASES:
        raise InvalidBootstrapProfile("unsupported dispatch phase")
    if not isinstance(root, str) or root not in ROOTS:
        raise InvalidBootstrapProfile("root not in six isolated Terraform roots")
    if phase == "bootstrap" and root not in BOOTSTRAP_ROOTS:
        raise InvalidBootstrapProfile("bootstrap cannot own a downstream Fabric resource")
    _sha(intake["controller_commit"], "controller SHA")
    _sha(intake["requested_healthcare_commit"], "requested Healthcare SHA")
    if intake["requested_healthcare_commit"] != pinned_sha:
        raise InvalidBootstrapProfile("Healthcare requested SHA differs from supplied review SHA")
    if type(intake["plan_digest_format_checked"]) is not bool:
        raise InvalidBootstrapProfile("plan digest syntax flag must be boolean")
    if intake["plan_digest_format_checked"] is not (phase == "apply"):
        raise InvalidBootstrapProfile("plan digest syntax phase mismatch")
    for flag in INTAKE_FALSE_FLAGS:
        if intake[flag] is not False:
            raise InvalidBootstrapProfile("offline controller cannot assert live authorization")
    h = handoff(profile, resolved_clients, storage_target, capacity_target)
    if intake["environment"] != h["environment"]:
        raise InvalidBootstrapProfile("controller environment differs from Bootstrap ownership")
    for flag in HANDOFF_FALSE_FLAGS:
        if h[flag] is not False:
            raise InvalidBootstrapProfile("static handoff must not claim real cloud authorization")
    if h["source_status"] != "UNVERIFIED_FORMAT_ONLY":
        raise InvalidBootstrapProfile("unexpected handoff provenance state")
    if set(h["state_keys"]) != {"workspace", "onelake", "connection"}:
        raise InvalidBootstrapProfile("unexpected downstream backend state roots")
    for name, key in h["state_keys"].items():
        if key != f"fabric/{h['environment']}/{name}.tfstate":
            raise InvalidBootstrapProfile("remote state targets are not environment isolated")

    blockers = [
        "INTAKE_JSON_IS_NOT_TRUSTED_PROVENANCE",
        "MAIN_SOURCE_SHA_NOT_EXTERNALLY_VERIFIED",
        "PROTECTED_GITHUB_ENVIRONMENT_AND_REVIEWERS_NOT_VERIFIED",
        "OIDC_BACKEND_AND_FABRIC_PERMISSIONS_NOT_VERIFIED",
        "REMOTE_STATE_VACANCY_AND_RESOURCE_OWNERSHIP_UNKNOWN",
        "FABRIC_CAPACITY_UUID_AND_TENANT_NOT_VERIFIED",
        "TERRAFORM_PROVIDER_AND_NETWORK_NOT_LIVE_VALIDATED",
        "INDEPENDENT_EXECUTION_AUTHORIZATION_ABSENT",
    ]
    if phase == "apply":
        blockers.append("REVIEWED_BINARY_PLAN_AND_SAVED_DIGEST_NOT_VERIFIED")
    if phase == "bootstrap":
        blockers.append("ADMIN_SEED_AND_INITIAL_STATE_CUSTODY_NOT_VERIFIED")
    if h["bootstrap_mode"] == "fresh-bootstrap":
        blockers.append("FRESH_PRIVATE_NETWORK_DNS_AND_STATE_CUSTODY_NOT_VERIFIED")
    if h["capacity_mode"] == "create-new":
        blockers.append("PAID_CAPACITY_BILLING_APPROVAL_AND_FABRIC_UUID_ABSENT")
    # Keep this a blocker summary, not a tfvars/checkout/permission token.
    return {
        "status": "FABRIC_OFFLINE_INTEGRATION_HOLD",
        "reviewed_sha_claim": pinned_sha,
        "controller_sha_claim": intake["controller_commit"],
        "phase": phase,
        "root": root,
        "environment": h["environment"],
        "bootstrap_mode": h["bootstrap_mode"],
        "capacity_mode": h["capacity_mode"],
        "identity_topology": h["identity_topology"],
        "handoff_status": h["status"],
        "expected_state_keys": h["state_keys"],
        "blocking_reasons": blockers,
        "source_commit_retrieved_from_github": False,
        "signed_plan_verified": False,
        "billing_authorization_verified": False,
        "cloud_access_attempted": False,
        "remote_state_checked": False,
        "runner_invoked": False,
        "terraform_executed": False,
        "deployment_allowed": False,
    }


def load(paths: list[Path], expected_sha: str) -> dict[str, object]:
    if len(paths) != 5:
        raise InvalidBootstrapProfile("exactly five non-secret input documents required")
    objs = []
    for path in paths:
        with path.open(encoding="utf-8") as fd:
            objs.append(json.load(fd, object_pairs_hook=_no_duplicate_keys))
    return readiness(*objs, expected_healthcare_sha=expected_sha)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("profile", "resolved_clients", "storage_target",
                 "capacity_target", "controller_intake"):
        parser.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    parser.add_argument("--expected-healthcare-sha", required=True)
    args = parser.parse_args(argv)
    print("#### FABRIC_OFFLINE_READINESS_OUTPUT_BEGIN ####")
    try:
        paths = [getattr(args, name) for name in (
            "profile", "resolved_clients", "storage_target",
            "capacity_target", "controller_intake"
        )]
        result = load(paths, args.expected_healthcare_sha)
    except (OSError, ValueError, TypeError, KeyError):
        # Never echo user-supplied values, which might be credentials.
        print("STATUS=FAIL; static readiness input rejected")
        print("#### FABRIC_OFFLINE_READINESS_OUTPUT_END ####")
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    print("#### FABRIC_OFFLINE_READINESS_OUTPUT_END ####")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
