"""Offline Bootstrap identity/OIDC contract: negative and replay tests."""
from copy import deepcopy
from pathlib import Path
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from fabric_bootstrap_profile import InvalidBootstrapProfile
from fabric_bootstrap_identity import (
    validate_identity_request, validate_resolved_client_ids, load, main,
)

A = "899a04e8-8d3d-486c-88a1-7bdeb22d5f1a"
B = "cb50fc2d-f9be-449a-9ae7-276884d0de55"
SUB = "6c0cc7f1-6912-4b25-805f-732be3882da8"
CAP = "18da26c5-dc71-43d2-b6fa-1ed15e24e7cb"


def profile(cross=False):
    return {
        "schema_version": 1, "environment": "lab-b",
        "bootstrap_mode": "fresh-bootstrap",
        "tenants": {"backend_tenant_id": A, "fabric_tenant_id": B if cross else A},
        "github_oidc": {"repository": "JohnZhang-DataForge/Self-Runner",
                        "environment": "fabric-lab-b"},
        "storage": {"account": "hdplabbstorage", "subscription_id": SUB,
                    "resource_group": "rg-hdp-lab-b", "landing_container": "landing",
                    "state_container": "tfstate", "state_prefix": "fabric/lab-b"},
        "bootstrap_state": {"strategy": "isolated-local",
                            "custody_reference": "CUSTODY-OFFLINE-PLAN-01"},
        "capacity": {"mode": "reuse-existing", "capacity_id": CAP},
    }


def request(cross=False):
    ftenant = B if cross else A
    repo = "JohnZhang-DataForge/Self-Runner"
    def binding(env):
        return {"repository": repo, "environment": env,
                "ref": "refs/heads/main",
                "issuer": "https://token.actions.githubusercontent.com",
                "audience": "api://AzureADTokenExchange",
                "protected_environment_required": True}
    return {
        "schema_version": 2, "environment": "lab-b",
        "seed_operator": {"backend_tenant_id": A, "fabric_tenant_id": ftenant,
                          "authorization_reference": "SEED-ADMIN-APPROVAL-0001"},
        "applications": {
            name: {"operation": "create-new",
                   "tenant_id": ftenant if name == "fabric_deployer" else A,
                   "display_name": f"hdp-lab-b-{name.replace('_', '-')}"}
            for name in ("backend_operator", "fabric_deployer", "blob_reader")
        },
        "oidc_bindings": {
            "plan_backend": binding("fabric-lab-b-plan-backend"),
            "apply_backend": binding("fabric-lab-b-apply-backend"),
            "plan_deployer": binding("fabric-lab-b-plan-deployer"),
            "apply_deployer": binding("fabric-lab-b-apply-deployer"),
        },
    }


def ids(cross=False):
    client_ids = ("35174fe8-88a8-4d12-b97c-c395f64fd1eb",
                  "76fc48a8-6a93-46be-a33b-3e41de8d8ae5",
                  "639629c1-89c3-4a11-98dc-d8506aa5203e")
    return {role: {"client_id": cid, "tenant_id": B if cross and role == "fabric_deployer" else A}
            for role, cid in zip(("backend_operator", "fabric_deployer", "blob_reader"), client_ids)}


class IdentityContractTests(unittest.TestCase):
    def reject(self, p, r):
        with self.assertRaises(InvalidBootstrapProfile):
            validate_identity_request(p, r)

    def test_same_tenant_separate_apps_and_exact_environments(self):
        result = validate_identity_request(profile(), request())
        self.assertEqual(result["identity_topology"], "same-tenant")
        self.assertEqual(result["oidc_bindings"]["plan_backend"]["subject"],
                         "repo:JohnZhang-DataForge@337895338/Self-Runner@1413796156:environment:fabric-lab-b-plan-backend")
        self.assertNotEqual(result["oidc_bindings"]["plan_backend"]["subject"],
                            result["oidc_bindings"]["plan_deployer"]["subject"])
        self.assertFalse(result["seed_authorization_verified"])
        self.assertFalse(result["github_environment_protection_verified"])
        self.assertFalse(result["cloud_executed"])
        self.assertEqual(result, validate_identity_request(profile(), deepcopy(request())))

    def test_cross_tenant_is_explicit_and_valid(self):
        result = validate_identity_request(profile(True), request(True))
        self.assertEqual(result["identity_topology"], "cross-tenant")
        self.assertEqual(result["applications"]["fabric_deployer"]["tenant_id"], B)
        self.assertEqual(result["applications"]["backend_operator"]["tenant_id"], A)

    def test_missing_unknown_or_secret_fields(self):
        for key in ("seed_operator", "applications", "oidc_bindings"):
            r = request()
            r.pop(key)
            self.reject(profile(), r)
        for location, name in (((), "token"),
                               (("seed_operator",), "password"),
                               (("applications", "fabric_deployer"), "client_secret"),
                               (("oidc_bindings", "plan_backend"), "id_token")):
            r = request()
            target = r
            for part in location:
                target = target[part]
            target[name] = "NEVER_SHOW_SECRET"
            self.reject(profile(), r)

    def test_ref_and_environment_protection(self):
        for key, value in (("ref", "refs/pull/1/merge"),
                           ("ref", "refs/heads/feature/attacker"),
                           ("environment", "fabric-lab-b"),
                           ("environment", "fabric-other-plan-backend"),
                           ("repository", "wrong/other"),
                           ("issuer", "https://attacker.invalid"),
                           ("audience", "wrong-audience"),
                           ("protected_environment_required", False),
                           ("protected_environment_required", "true")):
            with self.subTest(key=key):
                r = request()
                r["oidc_bindings"]["plan_backend"][key] = value
                self.reject(profile(), r)

    def test_seed_is_not_implicit_administrator_credential(self):
        for key, value in (("backend_tenant_id", B),
                           ("fabric_tenant_id", B),
                           ("authorization_reference", "PENDING"),
                           ("authorization_reference", "SEED-EXAMPLE-0001")):
            r = request()
            r["seed_operator"][key] = value
            self.reject(profile(), r)

    def test_no_old_app_automatic_adoption_or_tenant_mixup(self):
        for key, value in (("operation", "reuse-existing"),
                           ("operation", "adopt-existing"),
                           ("display_name", "github-terraform"),
                           ("display_name", "hdp-other-backend-operator"),
                           ("tenant_id", B)):
            r = request()
            r["applications"]["backend_operator"][key] = value
            self.reject(profile(), r)
        r = request(True)
        r["applications"]["fabric_deployer"]["tenant_id"] = A
        self.reject(profile(True), r)
        r = request()
        r["applications"]["blob_reader"]["display_name"] = r["applications"]["backend_operator"]["display_name"]
        self.reject(profile(), r)

    def test_resolved_ids_must_be_distinct_and_tenant_bound(self):
        result = validate_resolved_client_ids(profile(True), ids(True))
        self.assertFalse(result["verified"])
        self.assertEqual(len(set(result["client_ids"].values())), 3)
        duplicate = ids()
        duplicate["blob_reader"]["client_id"] = duplicate["backend_operator"]["client_id"]
        with self.assertRaises(InvalidBootstrapProfile):
            validate_resolved_client_ids(profile(), duplicate)
        wrong = ids(True)
        wrong["fabric_deployer"]["tenant_id"] = A
        with self.assertRaises(InvalidBootstrapProfile):
            validate_resolved_client_ids(profile(True), wrong)

    def test_duplicate_json_key_and_secret_cli_redaction(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            pf, ident = base / "profile.json", base / "identities.json"
            pf.write_text(json.dumps(profile()), encoding="utf-8")
            ident.write_text('{"environment":"one","environment":"two"}', encoding="utf-8")
            with self.assertRaises(InvalidBootstrapProfile):
                load(pf, ident)
            r = request()
            r["client_secret"] = "DONT-ECHO-SECRET"
            ident.write_text(json.dumps(r), encoding="utf-8")
            buffer = StringIO()
            with redirect_stdout(buffer):
                code = main(["--profile", str(pf), "--identities", str(ident)])
            self.assertEqual(code, 2)
            self.assertNotIn("DONT-ECHO-SECRET", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
