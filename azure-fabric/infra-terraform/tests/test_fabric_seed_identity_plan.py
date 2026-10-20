"""Isolated real Seed Terraform plan-only policy: no Azure or Terraform execution in CI."""
from __future__ import annotations

from pathlib import Path
import json
import os
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

from fabric_seed_identity_plan import (
    EXACT_RESOURCES, FORBIDDEN_AUTH_ENV, SeedPlanHold, execute,
    review_plan_json, verify_custody, verify_source, validate_cloud_access,
)

A = "899a04e8-8d3d-486c-88a1-7bdeb22d5f1a"
B = "cb50fc2d-f9be-449a-9ae7-276884d0de55"
SHA = "a" * 40


def plan(actions=None, extra=None):
    changes = []
    for name in sorted(EXACT_RESOURCES):
        typ, resource = name.split(".", 1)
        base = resource[:-3]
        changes.append({"address": name, "mode": "managed",
                        "type": typ, "name": base, "index": 0,
                        "change": {"actions": list(actions or ("create",))}})
    data = {"format_version": "1.2", "resource_changes": changes}
    if extra:
        data.update(extra)
    return json.dumps(data)


class SeedIdentityRealPlanTests(unittest.TestCase):
    def test_exact_ten_create_plan_only(self):
        result = review_plan_json(plan())
        self.assertEqual(result["planned_creates"], 10)
        self.assertEqual(result["new_app_registrations"], 3)
        self.assertEqual(result["new_github_federated_credentials"], 2)
        self.assertFalse(result["terraform_apply_executed"])
        self.assertFalse(result["seed_authorization_independently_verified"])
        self.assertFalse(result["state_custody_encryption_verified"])

    def test_fail_for_any_noncreate_or_unknown_resource(self):
        for actions in (("update",), ("delete",), ("delete", "create"),
                        ("read",), ("no-op",), ("create", "delete")):
            with self.subTest(actions=actions), self.assertRaises(SeedPlanHold):
                review_plan_json(plan(actions))
        content = json.loads(plan())
        for address in ("azuread_application_registration.github_terraform[0]",
                        "azapi_resource.paid_capacity[0]",
                        "azurerm_storage_account.legacy[0]"):
            wrong = json.loads(plan())
            wrong["resource_changes"][0]["address"] = address
            with self.subTest(address=address), self.assertRaises(SeedPlanHold):
                review_plan_json(json.dumps(wrong))
        for drift in ([{"address": "azuread_group.developers"}], [1]):
            with self.assertRaises(SeedPlanHold):
                review_plan_json(plan(extra={"resource_drift": drift}))
        content["resource_changes"].append(content["resource_changes"][0])
        with self.assertRaises(SeedPlanHold):
            review_plan_json(json.dumps(content))

    def test_duplicate_json_fields_hold(self):
        with self.assertRaises(SeedPlanHold):
            review_plan_json('{"resource_changes":[],"resource_changes":[]}')

    def test_fresh_custody_owner_only_empty_outside_checkout(self):
        with tempfile.TemporaryDirectory() as repo, tempfile.TemporaryDirectory() as run:
            root, private = Path(repo), Path(run)
            private.chmod(0o700)
            verify_custody(root, private)
            private.chmod(0o755)
            with self.assertRaises(SeedPlanHold):
                verify_custody(root, private)
            private.chmod(0o700)
            (private / "legacy.tfstate").write_text("do-not-open")
            with self.assertRaises(SeedPlanHold):
                verify_custody(root, private)
            with self.assertRaises(SeedPlanHold):
                verify_custody(root, root)

    def test_symlink_custody_rejected(self):
        with tempfile.TemporaryDirectory() as base:
            root = Path(base)
            real = root / "secure"
            real.mkdir(mode=0o700)
            link = root / "alias"
            link.symlink_to(real, target_is_directory=True)
            with self.assertRaises(SeedPlanHold):
                verify_custody(root / "checkout", link)

    def test_auth_override_and_legacy_client_env_refused(self):
        with patch.dict(os.environ, {"ARM_CLIENT_ID": A}):
            with self.assertRaises(SeedPlanHold):
                validate_cloud_access(A, B)
        with patch.dict(os.environ, {"AZURE_CLIENT_ID": A}):
            with self.assertRaises(SeedPlanHold):
                validate_cloud_access(A, B)

    def test_user_login_and_both_tenant_tokens(self):
        calls = []
        def fake_run(args, stage, **kwargs):
            calls.append(args)
            if stage == "SEED_CLI_LOGIN":
                return 0, json.dumps({"user": {"type": "user"}})
            return 0, ""
        env = {k: "" for k in FORBIDDEN_AUTH_ENV}
        with patch.dict(os.environ, env), patch(
                "fabric_seed_identity_plan.run", side_effect=fake_run):
            validate_cloud_access(A, B)
        self.assertEqual(sum("get-access-token" in arg for cmd in calls for arg in cmd), 2)
        self.assertFalse(any("client-secret" in " ".join(cmd) for cmd in calls))

    def test_source_pin_rejects_old_sha_and_dirty_checkout(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            (repo / ".git").mkdir()
            with patch("fabric_seed_identity_plan.run",
                       return_value=(0, "f" * 40)):
                with self.assertRaises(SeedPlanHold):
                    verify_source(repo, SHA)
            with patch("fabric_seed_identity_plan.run",
                       side_effect=[(0, SHA), (0, " M main.tf")]):
                with self.assertRaises(SeedPlanHold):
                    verify_source(repo, SHA)

    def test_execution_uses_private_local_tf_only_and_no_apply(self):
        from test_fabric_bootstrap_identity import profile, request
        p, i = profile(), request()
        p["bootstrap_mode"] = "fresh-bootstrap"
        p["storage"]["account"] = "hdplabbdata"
        p["storage"]["resource_group"] = "rg-hdp-lab-b"
        with tempfile.TemporaryDirectory() as base:
            base = Path(base)
            src = base / "checkout/azure-fabric/infra-terraform/bootstrap/identity"
            src.mkdir(parents=True)
            (src / "main.tf").write_text('terraform { backend "local" {} }')
            (src / "versions.tf").write_text('terraform {}')
            run_dir = base / "private"
            run_dir.mkdir(mode=0o700)
            pf, req = base / "profile.json", base / "request.json"
            pf.write_text(json.dumps(p))
            req.write_text(json.dumps(i))
            commands = []
            def fake_run(args, stage, **kwargs):
                commands.append((args, stage))
                if stage == "TF_PLAN":
                    (run_dir / "identity.tfplan").write_bytes(b"PLAN" * 100)
                    return 2, ""
                if stage == "TF_SHOW":
                    return 0, plan()
                return 0, ""
            with patch("fabric_seed_identity_plan.verify_source", return_value=src), \
                 patch("fabric_seed_identity_plan.validate_cloud_access"), \
                 patch("fabric_seed_identity_plan.run", side_effect=fake_run):
                outcome = execute(pf, req, base / "checkout", SHA, run_dir)
            self.assertEqual(outcome["planned_creates"], 10)
            self.assertTrue((run_dir / "identity.tfplan").exists())
            self.assertTrue((run_dir / "identity-plan-manifest.json").exists())
            self.assertFalse(any("apply" in arg or "destroy" in arg
                                 for args, _ in commands for arg in args))
            self.assertTrue(any("init" in args and
                                any("terraform.tfstate" in arg for arg in args)
                                for args, _ in commands))
            self.assertEqual(stat.S_IMODE((run_dir / "identity.tfplan").stat().st_mode),
                             0o600)
            self.assertFalse((base / "checkout" / "terraform.tfstate").exists())

    def test_non_fresh_profile_rejected_before_cloud(self):
        from test_fabric_bootstrap_identity import profile, request
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            pf, req = base / "profile.json", base / "request.json"
            pf.write_text(json.dumps(profile()))
            req.write_text(json.dumps(request()))
            with patch("fabric_seed_identity_plan.validate_cloud_access") as cloud:
                with self.assertRaises(SeedPlanHold):
                    execute(pf, req, base, SHA, base / "state")
                cloud.assert_not_called()


if __name__ == "__main__":
    unittest.main()
