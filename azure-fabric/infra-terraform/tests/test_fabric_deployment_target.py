"""Offline backend/provider identity and state-isolation contract tests."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from fabric_deployment_target import build  # noqa: E402
from fabric_environment_preflight import InvalidEnvironment  # noqa: E402

A = "11111111-1111-4111-8111-111111111111"
B = "22222222-2222-4222-8222-222222222222"
C = "33333333-3333-4333-8333-333333333333"
D = "44444444-4444-4444-8444-444444444444"


def profile():
    return {
        "schema_version": 1, "environment": "lab-b",
        "backend": {"storage_account": "johnzhang", "container": "tfstate",
                    "tenant_id": A, "state_prefix": "fabric/lab-b"},
        "landing": {"storage_account": "johnzhang", "container": "landing"},
        "fabric": {"tenant_id": B, "capacity_id": C, "workspace_name": "HDP-lab-b"},
    }


class DeploymentTargetTests(unittest.TestCase):
    def check(self, data, *, backend_client=A, fabric_client=B,
              backend_tenant=A, fabric_tenant=B):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "environment.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            return build(path, backend_client, fabric_client,
                         backend_tenant, fabric_tenant)

    def test_cross_tenant_state(self):
        data = self.check(profile())
        self.assertEqual(data["backend"]["state_keys"]["connection"],
                         "fabric/lab-b/connection.tfstate")
        self.assertFalse(data["remote_state_checked"])
        self.assertFalse(data["terraform_executed"])
        self.assertNotIn("dev/", json.dumps(data))

    def test_same_tenant_with_separate_identities(self):
        data = profile()
        data["fabric"]["tenant_id"] = A
        self.assertEqual(self.check(data, fabric_tenant=A)["status"], "OFFLINE_TARGET_PASS")

    def test_identity_mismatch_blocked(self):
        with self.assertRaises(InvalidEnvironment):
            self.check(profile(), backend_tenant=B)
        with self.assertRaises(InvalidEnvironment):
            self.check(profile(), fabric_tenant=A)

    def test_shared_deployer_blocked(self):
        with self.assertRaises(InvalidEnvironment):
            self.check(profile(), fabric_client=A)

    def test_malformed_identity_blocked(self):
        with self.assertRaises(InvalidEnvironment):
            self.check(profile(), backend_client="fake-token")

    def test_legacy_or_foreign_state_blocked(self):
        for prefix in ("dev", "dev/workspace.tfstate", "fabric/lab-a", "../lab-b"):
            data = profile()
            data["backend"]["state_prefix"] = prefix
            with self.subTest(prefix=prefix), self.assertRaises(InvalidEnvironment):
                self.check(data)

    def test_credential_in_profile_blocked(self):
        data = profile()
        data["backend"]["client_secret"] = "do-not-log"
        with self.assertRaises(InvalidEnvironment):
            self.check(data)


if __name__ == "__main__":
    unittest.main()
