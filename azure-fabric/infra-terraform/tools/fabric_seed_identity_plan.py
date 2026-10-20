#!/usr/bin/env python3
"""Plan-only live Entra Identity Root bootstrap in isolated, private LOCAL custody.

Requires independently authorized Azure CLI user access in BOTH target tenants.
No Terraform apply/destroy/import; never accesses legacy Terraform State.
Real Terraform binary Plan and local State material stay outside the source repo.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
from uuid import UUID

from fabric_bootstrap_identity import load as load_identity
from fabric_bootstrap_profile import load as load_profile

HEALTHCARE_URL = "https://github.com/JohnZhang-DataForge/healthcare-data-platform.git"
SOURCE_REL = Path("azure-fabric/infra-terraform/bootstrap/identity")
SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
EXACT_RESOURCES = {
    "azuread_application_registration.backend_operator[0]",
    "azuread_application_registration.blob_reader[0]",
    "azuread_application_registration.fabric_deployer[0]",
    "azuread_service_principal.backend_operator[0]",
    "azuread_service_principal.blob_reader[0]",
    "azuread_service_principal.fabric_deployer[0]",
    "azuread_group.backend_operators[0]",
    "azuread_group.fabric_deployers[0]",
    "azuread_application_federated_identity_credential.backend_operator_plan[0]",
    "azuread_application_federated_identity_credential.fabric_deployer_plan[0]",
}
FORBIDDEN_AUTH_ENV = (
    "ARM_CLIENT_ID", "ARM_CLIENT_SECRET", "ARM_CLIENT_CERTIFICATE_PATH",
    "ARM_OIDC_TOKEN", "ARM_USE_OIDC", "ARM_USE_MSI", "ARM_TENANT_ID",
    "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET", "AZURE_FEDERATED_TOKEN_FILE",
    "AZURE_TENANT_ID", "TF_CLI_ARGS", "TF_CLI_ARGS_plan", "TF_CLI_ARGS_init",
    "TF_VAR_identity_creation_approved", "TF_VAR_backend_tenant_id",
    "TF_VAR_fabric_tenant_id", "TF_VAR_environment",
)


class SeedPlanHold(ValueError):
    pass


def _json_no_duplicates(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise SeedPlanHold("duplicate JSON key")
        obj[key] = value
    return obj


def run(args: list[str], stage: str, *, cwd: Path | None = None,
        allowed: tuple[int, ...] = (0,), stdout_limit: int = 8_000_000) -> tuple[int, str]:
    """Capture all tool output in memory; never emit provider/Graph/token diagnostics."""
    try:
        done = subprocess.run(args, cwd=cwd, input=None, capture_output=True,
                              text=True, timeout=180, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SeedPlanHold(stage) from exc
    if done.returncode not in allowed or len(done.stdout) > stdout_limit:
        raise SeedPlanHold(stage)
    return done.returncode, done.stdout.strip()


def verify_source(repo: Path, sha: str) -> Path:
    if not SHA_RE.fullmatch(sha) or int(sha, 16) == 0:
        raise SeedPlanHold("SOURCE_SHA")
    if not (repo / ".git").exists():
        raise SeedPlanHold("SOURCE_REPOSITORY")
    _, actual = run(["git", "-C", str(repo), "rev-parse", "HEAD"], "SOURCE_HEAD")
    if actual != sha:
        raise SeedPlanHold("SOURCE_HEAD")
    _, dirty = run(["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=no"],
                   "SOURCE_DIRTY")
    if dirty:
        raise SeedPlanHold("SOURCE_DIRTY")
    _, remote = run(["git", "ls-remote", "--exit-code", HEALTHCARE_URL,
                     "refs/heads/main"], "SOURCE_MAIN")
    if remote != sha + "\trefs/heads/main":
        raise SeedPlanHold("SOURCE_MAIN")
    source = repo / SOURCE_REL
    if not source.is_dir() or len(list(source.glob("*.tf"))) < 4:
        raise SeedPlanHold("SOURCE_ROOT")
    return source


def verify_custody(repo: Path, custody: Path) -> None:
    """Require a fresh private empty dir outside Healthcare checkout, no symlinks."""
    if custody.is_symlink() or not custody.is_dir() or custody.resolve() != custody:
        raise SeedPlanHold("CUSTODY_PATH")
    resolved = custody.resolve()
    source = repo.resolve()
    if resolved == source or source in resolved.parents or resolved in source.parents:
        raise SeedPlanHold("CUSTODY_OUTSIDE_REPO")
    st = resolved.stat()
    if (st.st_uid != os.getuid() or stat.S_IMODE(st.st_mode) != 0o700
            or not stat.S_ISDIR(st.st_mode)):
        raise SeedPlanHold("CUSTODY_PERMISSIONS")
    if list(resolved.iterdir()):
        raise SeedPlanHold("CUSTODY_NOT_FRESH")


def validate_cloud_access(tenant_a: str, tenant_b: str) -> None:
    """Only Azure CLI user login; no old app/SPN/OIDC credentials accepted."""
    if any(os.environ.get(k) for k in FORBIDDEN_AUTH_ENV):
        raise SeedPlanHold("SEED_AUTH_OVERRIDE")
    _, raw = run(["az", "account", "show", "--output", "json"],
                 "SEED_CLI_LOGIN", stdout_limit=20000)
    try:
        account = json.loads(raw, object_pairs_hook=_json_no_duplicates)
        user = account.get("user")
        if not isinstance(user, dict) or user.get("type") != "user":
            raise SeedPlanHold("SEED_INTERACTIVE_USER_REQUIRED")
    except (ValueError, TypeError, AttributeError) as exc:
        raise SeedPlanHold("SEED_INTERACTIVE_USER_REQUIRED") from exc
    for tenant in set((tenant_a, tenant_b)):
        # Never log or store the returned access token; only assert successful
        # tenant-specific token acquisition. Provider still separately authorizes.
        run(["az", "account", "get-access-token", "--tenant", tenant,
             "--resource-type", "ms-graph", "--output", "none"],
            "SEED_TENANT_TOKEN")


def review_plan_json(raw: str) -> dict:
    try:
        doc = json.loads(raw, object_pairs_hook=_json_no_duplicates)
    except (ValueError, TypeError) as exc:
        raise SeedPlanHold("PLAN_JSON_FORMAT") from exc
    if not isinstance(doc, dict) or doc.get("resource_drift"):
        raise SeedPlanHold("PLAN_DRIFT")
    changes = doc.get("resource_changes")
    if not isinstance(changes, list) or len(changes) != len(EXACT_RESOURCES):
        raise SeedPlanHold("PLAN_RESOURCE_COUNT")
    seen = set()
    for resource in changes:
        if not isinstance(resource, dict):
            raise SeedPlanHold("PLAN_RESOURCE_FORMAT")
        address = resource.get("address")
        action = resource.get("change", {}).get("actions")
        if (not isinstance(address, str) or address not in EXACT_RESOURCES
                or address in seen or resource.get("mode") != "managed"
                or action != ["create"] or resource.get("module_address") is not None):
            raise SeedPlanHold("PLAN_RESOURCE_ACTION")
        seen.add(address)
    if seen != EXACT_RESOURCES:
        raise SeedPlanHold("PLAN_RESOURCE_MISMATCH")
    return {
        "status": "SEED_IDENTITY_LIVE_PLAN_CREATED_REVIEW_REQUIRED",
        "planned_creates": len(EXACT_RESOURCES),
        "planned_updates": 0,
        "planned_deletes": 0,
        "new_app_registrations": 3,
        "new_service_principals": 3,
        "new_groups": 2,
        "new_github_federated_credentials": 2,
        "paid_capacity_changes": 0,
        "terraform_apply_executed": False,
        "seed_authorization_independently_verified": False,
        "app_name_inventory_independently_verified": False,
        "cross_tenant_azure_permissions_independently_verified": False,
        "state_custody_encryption_verified": False,
    }


def execute(profile: Path, identities: Path, repo: Path, sha: str, custody: Path) -> dict:
    summary = load_profile(profile)
    contract = load_identity(profile, identities)
    if summary["environment"] != contract["environment"]:
        raise SeedPlanHold("CONTRACT_MISMATCH")
    if summary["bootstrap_mode"] != "fresh-bootstrap":
        raise SeedPlanHold("FRESH_ONLY")
    if summary["capacity_mode"] != "reuse-existing":
        raise SeedPlanHold("PAID_CAPACITY_NOT_ACCEPTED")
    source = verify_source(repo, sha)
    verify_custody(repo, custody)
    validate_cloud_access(summary["backend_tenant_id"], summary["fabric_tenant_id"])

    # Terraform's local backend, .terraform, binary plan and any future State
    # are created ONLY within caller-owned 0700 custody; no State in Git.
    root = custody / "identity-root"
    root.mkdir(mode=0o700)
    for tf in sorted(source.glob("*.tf")):
        if tf.is_symlink() or not tf.is_file():
            raise SeedPlanHold("SOURCE_TF_FILE")
        shutil.copyfile(tf, root / tf.name)
        (root / tf.name).chmod(0o600)
    plan = custody / "identity.tfplan"
    backend = root / "terraform.tfstate"
    run(["terraform", f"-chdir={root}", "init", "-no-color", "-input=false",
         f"-backend-config=path={backend}"], "TF_INIT")
    run(["terraform", f"-chdir={root}", "validate", "-no-color"], "TF_VALIDATE")
    code, _ = run([
        "terraform", f"-chdir={root}", "plan", "-no-color", "-input=false",
        "-detailed-exitcode", f"-out={plan}",
        f"-var=environment={summary['environment']}",
        f"-var=backend_tenant_id={summary['backend_tenant_id']}",
        f"-var=fabric_tenant_id={summary['fabric_tenant_id']}",
        "-var=identity_creation_approved=true",
    ], "TF_PLAN", allowed=(2,))
    del code
    if not plan.is_file() or plan.stat().st_size < 100:
        raise SeedPlanHold("TF_PLAN_FILE")
    plan.chmod(0o600)
    _, raw = run(["terraform", f"-chdir={root}", "show", "-json", str(plan)],
                 "TF_SHOW", stdout_limit=8_000_000)
    result = review_plan_json(raw)
    result["healthcare_source_sha"] = sha
    result["target_environment"] = summary["environment"]
    result["plan_sha256"] = hashlib.file_digest(plan.open("rb"), "sha256").hexdigest()
    result["binary_plan_bytes"] = plan.stat().st_size
    result["plan_location"] = "PRIVATE_LOCAL_CUSTODY_ONLY"
    result["remote_backend_initialized"] = False
    result["legacy_state_accessed"] = False
    result["manual_plan_review_required"] = True
    manifest = custody / "identity-plan-manifest.json"
    manifest.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    manifest.chmod(0o600)
    # Check for Main ref movement during the cloud Plan window.
    verify_source(repo, sha)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--identities", required=True, type=Path)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--healthcare-main-sha", required=True)
    parser.add_argument("--custody-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    print("#### FABRIC_SEED_IDENTITY_PLAN_OUTPUT_BEGIN ####")
    os.umask(0o077)
    stage = "HOLD"
    try:
        result = execute(args.profile, args.identities,
                         args.repo_root.absolute(), args.healthcare_main_sha,
                         args.custody_dir.absolute())
        print(json.dumps(result, sort_keys=True))
        status = 0
    except Exception:
        # Terraform/Graph output and errors can include sensitive credentials.
        print("STATUS=HOLD; plan creation or strict create-only review rejected")
        print("RAW_TERRAFORM_AZURE_DIAGNOSTICS=REDACTED")
        status = 2
    print("#### FABRIC_SEED_IDENTITY_PLAN_OUTPUT_END ####")
    return status


if __name__ == "__main__":
    sys.exit(main())
