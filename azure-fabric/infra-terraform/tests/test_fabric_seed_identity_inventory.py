"""No-cloud tests for live Seed inventory's deny-by-default boundary."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from fabric_bootstrap_profile import validate
from fabric_seed_identity_inventory import InventoryHold, inspect, read_az, verify_fics
from test_fabric_bootstrap_identity import profile, request, ids, A, B

RESOLVED = ids()
NAMES = {f"hdp-lab-b-{role.replace('_', '-')}": obj["client_id"]
         for role, obj in RESOLVED.items()}
REVERSE = {v: k for k, v in NAMES.items()}
SUBJECT = "repo:JohnZhang-DataForge@337895338/Self-Runner@1413796156:ref:refs/heads/main"


def fake_az(*command):
    if command[:3] == ("az", "account", "show"):
        return {"tenantId": A}
    if command[:4] == ("az", "ad", "app", "list"):
        name = command[5]
        return [{"displayName": name, "appId": NAMES[name]}]
    if command[:4] == ("az", "ad", "app", "show"):
        cid = command[5]
        return {"displayName": REVERSE[cid], "appId": cid}
    if command[:4] == ("az", "ad", "sp", "show"):
        return {"appId": command[5]}
    if command[:5] == ("az", "ad", "app", "federated-credential", "list"):
        cid = command[6]
        name = REVERSE[cid]
        if name.endswith("blob-reader"):
            return []
        suffix = "backend-plan-github" if name.endswith("backend-operator") else "fabric-plan-github"
        return [{"name": "hdp-lab-b-" + suffix,
                 "issuer": "https://token.actions.githubusercontent.com",
                 "audiences": ["api://AzureADTokenExchange"],
                 "subject": SUBJECT}]
    raise AssertionError("unexpected read")


class LiveIdentityInventoryTests(unittest.TestCase):
    def test_before_no_collisions(self):
        def empty(*cmd):
            return {"tenantId": A} if cmd[1] == "account" else []
        with patch("fabric_seed_identity_inventory.read_az", side_effect=empty):
            outcome = inspect(profile(), request(), "backend", "before")
        self.assertEqual(outcome["checked"], 2)
        self.assertFalse(outcome["fic_verified"])

    def test_existing_application_fails_closed(self):
        with patch("fabric_seed_identity_inventory.read_az", side_effect=fake_az):
            with self.assertRaises(InventoryHold):
                inspect(profile(), request(), "backend", "before")

    def test_postcreate_exact_apps_fics_and_sp(self):
        with patch("fabric_seed_identity_inventory.read_az", side_effect=fake_az):
            for role, expected in (("backend", 2), ("fabric", 1)):
                result = inspect(profile(), request(), role, "after", RESOLVED)
                self.assertEqual(result["checked"], expected)
                self.assertTrue(result["fic_verified"])
                self.assertEqual(result["terraform_plan_apply"], "NO")

    def test_cross_tenant_context_fails(self):
        with patch("fabric_seed_identity_inventory.read_az", side_effect=fake_az):
            with self.assertRaises(InventoryHold):
                inspect(profile(True), request(True), "fabric", "before")

    def test_duplicate_role_id_rejected(self):
        bad = ids()
        bad["fabric_deployer"]["client_id"] = bad["backend_operator"]["client_id"]
        with patch("fabric_seed_identity_inventory.read_az", side_effect=fake_az):
            with self.assertRaises(ValueError):
                inspect(profile(), request(), "fabric", "after", bad)

    def test_tampered_fic_rejected(self):
        record = {"name": "hdp-lab-b-backend-plan-github",
                  "issuer": "https://token.actions.githubusercontent.com",
                  "subject": SUBJECT, "audiences": ["api://AzureADTokenExchange"]}
        verify_fics([record], "lab-b", "backend_operator")
        for field, value in (("name", "other"), ("issuer", "https://invalid"),
                             ("subject", "refs/pull/12/merge"),
                             ("audiences", ["wrong"])):
            with self.subTest(field=field), self.assertRaises(InventoryHold):
                verify_fics([dict(record, **{field: value})], "lab-b", "backend_operator")
        with self.assertRaises(InventoryHold):
            verify_fics([record, record], "lab-b", "backend_operator")
        with self.assertRaises(InventoryHold):
            verify_fics([record], "lab-b", "blob_reader")

    def test_only_readonly_az_commands(self):
        with patch("fabric_seed_identity_inventory.subprocess.run") as runner:
            with self.assertRaises(InventoryHold):
                read_az("az", "ad", "app", "create", "--display-name", "legacy")
            runner.assert_not_called()

    def test_redact_graph_error(self):
        with patch("fabric_seed_identity_inventory.subprocess.run") as runner:
            runner.return_value.returncode = 1
            runner.return_value.stdout = ""
            runner.return_value.stderr = "secret-looking-error-detail"
            with self.assertRaises(InventoryHold) as err:
                read_az("az", "ad", "app", "list")
            self.assertNotIn("secret-looking-error-detail", str(err.exception))


if __name__ == "__main__":
    unittest.main()
