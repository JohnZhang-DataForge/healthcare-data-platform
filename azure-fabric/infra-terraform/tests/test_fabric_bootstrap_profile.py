"""Fail-closed, side-effect-free Fabric infrastructure Bootstrap profile tests."""
from copy import deepcopy
from pathlib import Path
import json
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from fabric_bootstrap_profile import InvalidBootstrapProfile, load, validate

A = "899a04e8-8d3d-486c-88a1-7bdeb22d5f1a"
B = "cb50fc2d-f9be-449a-9ae7-276884d0de55"
CAP = "18da26c5-dc71-43d2-b6fa-1ed15e24e7cb"
SUB = "6c0cc7f1-6912-4b25-805f-732be3882da8"


def reuse():
    return {
        "schema_version": 1,
        "environment": "lab-b",
        "bootstrap_mode": "reuse-existing",
        "tenants": {"backend_tenant_id": A, "fabric_tenant_id": A},
        "github_oidc": {
            "repository": "JohnZhang-DataForge/Self-Runner",
            "environment": "fabric-lab-b",
        },
        "storage": {
            "account": "johnzhang", "subscription_id": SUB,
            "resource_group": "existing-rg",
            "landing_container": "landing",
            "state_container": "tfstate", "state_prefix": "fabric/lab-b",
        },
        "bootstrap_state": {
            "strategy": "isolated-local", "custody_reference": "CUSTODY-OFFLINE-PLAN-01",
        },
        "capacity": {"mode": "reuse-existing", "capacity_id": CAP},
    }


def fresh():
    p = reuse()
    p["bootstrap_mode"] = "fresh-bootstrap"
    p["tenants"]["fabric_tenant_id"] = B
    p["storage"]["account"] = "hdplabbstorage"
    p["storage"]["resource_group"] = "rg-hdp-lab-b"
    return p


def create_capacity():
    p = fresh()
    p["capacity"] = {
        "mode": "create-new", "sku": "F2", "region": "eastus2",
        "subscription_id": SUB, "estimated_monthly_usd": 300,
        "monthly_budget_usd": 500, "billing_owner": "approved-owner",
        "cost_review_reference": "COST-REVIEW-20261019",
    }
    return p


class BootstrapProfileTests(unittest.TestCase):
    def reject(self, candidate):
        with self.assertRaises(InvalidBootstrapProfile):
            validate(candidate)

    def test_reuse_existing_is_never_authorized(self):
        r = validate(reuse())
        self.assertEqual(r["status"], "BOOTSTRAP_STATIC_CONTRACT_PASS")
        self.assertEqual(r["identity_topology"], "same-tenant")
        self.assertEqual(r["capacity_id"], CAP)
        self.assertEqual(r["state_keys"]["workspace"], "fabric/lab-b/workspace.tfstate")
        self.assertFalse(r["paid_creation_authorized"])
        self.assertFalse(r["terraform_executed"])
        self.assertFalse(r["remote_state_checked"])
        self.assertFalse(r["oidc_verified"])

    def test_fresh_cross_tenant_is_not_live_verified(self):
        p = fresh()
        r = validate(p)
        self.assertEqual(r["identity_topology"], "cross-tenant")
        self.assertEqual(r["storage_account"], "hdplabbstorage")
        self.assertFalse(r["external_inventory_verified"])
        self.assertFalse(r["initial_bootstrap_state_verified"])
        self.assertEqual(r["capacity_mode"], "reuse-existing")

    def test_paid_capacity_request_never_becomes_approval(self):
        r = validate(create_capacity())
        self.assertEqual(r["capacity_mode"], "create-new")
        self.assertIsNone(r["capacity_id"])
        self.assertTrue(r["paid_creation_requested"])
        self.assertEqual(r["status"], "BOOTSTRAP_PROFILE_HOLD_PAID_APPROVAL")
        self.assertFalse(r["cost_review_verified"])
        self.assertFalse(r["paid_creation_authorized"])

    def test_secret_and_unknown_fields_rejected_everywhere(self):
        for path, value in [
            ((), {"client_secret": "fake-secret"}),
            (("tenants",), {"token": "fake"}),
            (("github_oidc",), {"audience_secret": "fake"}),
            (("storage",), {"account_key": "fake"}),
            (("bootstrap_state",), {"state_access_key": "fake"}),
            (("capacity",), {"secret": "fake"}),
        ]:
            with self.subTest(path=path):
                p = reuse()
                target = p
                for key in path:
                    target = target[key]
                target.update(value)
                self.reject(p)

    def test_missing_and_duplicate_json_fields(self):
        p = reuse()
        del p["tenants"]
        self.reject(p)
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "dupe.json"
            file.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
            with self.assertRaises(InvalidBootstrapProfile):
                load(file)

    def test_bad_modes_and_legacy_environment_names_rejected(self):
        for name in ("dev", "main", "production", "default", "lab_b", "../dev", "A", ""):
            with self.subTest(name=name):
                p = reuse()
                p["environment"] = name
                self.reject(p)
        for mode in ("", "auto", "adopt-existing", "fresh", None):
            with self.subTest(mode=mode):
                p = reuse()
                p["bootstrap_mode"] = mode
                self.reject(p)

    def test_legacy_or_unapproved_storage_in_fresh(self):
        for name in ("johnzhang", "JohnZhang", "tfstate", "hdp-", "hdpx"):
            with self.subTest(name=name):
                p = fresh()
                p["storage"]["account"] = name
                if name == "hdpx":
                    # This name is actually valid: new resources still require
                    # independent remote inventory and the tool never creates it.
                    self.assertFalse(validate(p)["remote_state_checked"])
                else:
                    self.reject(p)

    def test_reuse_rejects_wrong_storage(self):
        p = reuse()
        p["storage"]["account"] = "hdpnewstore"
        self.reject(p)

    def test_state_key_and_container_conflicts_rejected(self):
        for prefix in ("dev", "dev/workspace.tfstate", "fabric/lab-c", "/fabric/lab-b"):
            with self.subTest(prefix=prefix):
                p = reuse()
                p["storage"]["state_prefix"] = prefix
                self.reject(p)
        p = fresh()
        p["storage"]["state_container"] = "landing"
        self.reject(p)

    def test_oidc_repository_and_environment_scoping(self):
        for key, value in (("repository", "attacker/repo"),
                           ("environment", "fabric-production"),
                           ("environment", "pull_request"),
                           ("environment", "fabric-lab-b:refs/heads/main")):
            with self.subTest(key=key, value=value):
                p = reuse()
                p["github_oidc"][key] = value
                self.reject(p)

    def test_uuid_checks_and_cross_tenant_allowed(self):
        for x in ("00000000-0000-0000-0000-000000000000", "INVALID", 2, None):
            with self.subTest(value=x):
                p = fresh()
                p["tenants"]["backend_tenant_id"] = x
                self.reject(p)
        p = reuse()
        p["tenants"]["fabric_tenant_id"] = B
        self.assertEqual(validate(p)["identity_topology"], "cross-tenant")

    def test_capacity_modes_are_mutually_exclusive(self):
        for extra in ("sku", "billing_owner", "monthly_budget_usd", "cost_review_reference"):
            p = reuse()
            p["capacity"][extra] = "F2"
            self.reject(p)
        p = create_capacity()
        p["capacity"]["capacity_id"] = CAP
        self.reject(p)

    def test_capacity_creation_requires_complete_nonplaceholder_costs(self):
        for key, value in (
            ("sku", "P1"), ("sku", "F0"), ("region", "East US"),
            ("subscription_id", "REPLACE_ME"),
            ("estimated_monthly_usd", -1), ("estimated_monthly_usd", True),
            ("monthly_budget_usd", 0), ("monthly_budget_usd", 100),
            ("billing_owner", "wrong owner!"),
            ("cost_review_reference", "PENDING-COST-REVIEW"),
            ("cost_review_reference", "EXAMPLE-COST-REVIEW"),
        ):
            with self.subTest(key=key, value=value):
                p = create_capacity()
                p["capacity"][key] = value
                self.reject(p)

    def test_capacity_missing_cost_or_identifier_rejected(self):
        for key in create_capacity()["capacity"]:
            with self.subTest(key=key):
                p = create_capacity()
                del p["capacity"][key]
                self.reject(p)

    def test_bootstrap_state_cannot_cycle_back_into_new_backend(self):
        for strategy in ("new-remote", "azurerm", "tfstate", "migrate-state"):
            candidate = fresh()
            candidate["bootstrap_state"]["strategy"] = strategy
            self.reject(candidate)
        candidate = fresh()
        candidate["bootstrap_state"]["custody_reference"] = "PENDING"
        self.reject(candidate)

    def test_new_resource_names_and_subscriptions_are_bound(self):
        for field, value in (("resource_group", "johnzhang"),
                             ("resource_group", "rg-hdp-other"),
                             ("resource_group", "invalid space"),
                             ("subscription_id", "not-a-uuid")):
            candidate = fresh()
            candidate["storage"][field] = value
            self.reject(candidate)
        candidate = create_capacity()
        candidate["capacity"]["subscription_id"] = "7cb66f5d-4c20-4c31-9bc1-0547e25b745f"
        summary = validate(candidate)
        self.assertEqual(summary["identity_topology"], "cross-tenant")
        self.assertNotEqual(summary["capacity_subscription_id"], summary["storage_subscription_id"])
        self.assertFalse(summary["paid_creation_authorized"])

    def test_fabric_sku_and_profile_determinism(self):
        for invalid_sku in ("F3", "F9999", "P1", "F0"):
            candidate = create_capacity()
            candidate["capacity"]["sku"] = invalid_sku
            self.reject(candidate)
        candidate = fresh()
        first = validate(candidate)
        self.assertEqual(first, validate(deepcopy(candidate)))
        self.assertFalse(first["verified"])
        self.assertFalse(first["initial_bootstrap_state_verified"])
        self.assertEqual(first["storage_subscription_id"], SUB)

    def test_sensitive_strings_not_echoed_by_cli(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from fabric_bootstrap_profile import main
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "secret.json"
            p = reuse()
            p["client_secret"] = "NEVER_PRINT_SECRET_VALUE"
            file.write_text(json.dumps(p), encoding="utf-8")
            output = StringIO()
            with redirect_stdout(output):
                exit_code = main(["--config", str(file)])
            self.assertEqual(exit_code, 2)
            self.assertNotIn("NEVER_PRINT_SECRET_VALUE", output.getvalue())


if __name__ == "__main__":
    unittest.main()
