"""Safe offline AzureRM backend argument generation for new Fabric environments."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from fabric_backend_config import backend_arguments, render_backend_config  # noqa: E402
from fabric_deployment_target import build  # noqa: E402
from fabric_environment_preflight import InvalidEnvironment  # noqa: E402

TENANT_A = "11111111-1111-4111-8111-111111111111"
TENANT_B = "22222222-2222-4222-8222-222222222222"
CAPACITY = "33333333-3333-4333-8333-333333333333"
CLIENT_B = "44444444-4444-4444-8444-444444444444"


def approved(environment="lab-b"):
    return {
        "schema_version": 1, "environment": environment,
        "backend": {"storage_account": "johnzhang", "container": "tfstate",
                    "tenant_id": TENANT_A, "state_prefix": f"fabric/{environment}"},
        "landing": {"storage_account": "johnzhang", "container": "landing"},
        "fabric": {"tenant_id": TENANT_B, "capacity_id": CAPACITY,
                   "workspace_name": f"HDP-{environment}"},
    }


class BackendConfigTests(unittest.TestCase):
    def deployment(self, value):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            return build(path, TENANT_A, CLIENT_B, TENANT_A, TENANT_B)

    def test_components_have_separate_keys(self):
        profile = self.deployment(approved())
        for component in ("workspace", "onelake", "connection"):
            with self.subTest(component=component):
                args = backend_arguments(profile, component, TENANT_A)
                self.assertEqual(args["key"], f"fabric/lab-b/{component}.tfstate")
                self.assertEqual(args["tenant_id"], TENANT_A)
                self.assertEqual(args["client_id"], TENANT_A)
                self.assertEqual(args["use_oidc"], "true")
                self.assertNotIn("dev/", render_backend_config(args))

    def test_multiple_environments_do_not_collide(self):
        first = backend_arguments(self.deployment(approved("lab-a")), "workspace", TENANT_A)
        second = backend_arguments(self.deployment(approved("lab-b")), "workspace", TENANT_A)
        self.assertNotEqual(first["key"], second["key"])

    def test_reject_legacy_and_path_traversal(self):
        for bad in ("dev", "../dev", "fabric/dev", "lab/other"):
            with self.subTest(bad=bad):
                item = approved()
                item["backend"]["state_prefix"] = bad
                with self.assertRaises(InvalidEnvironment):
                    self.deployment(item)

    def test_reject_unsupported_component(self):
        with self.assertRaises(InvalidEnvironment):
            backend_arguments(self.deployment(approved()), "storage", TENANT_A)

    def test_reject_mismatched_state(self):
        profile = self.deployment(approved())
        profile["backend"]["state_keys"]["workspace"] = "dev/workspace.tfstate"
        with self.assertRaises(InvalidEnvironment):
            backend_arguments(profile, "workspace", TENANT_A)

    def test_reject_unapproved_storage(self):
        profile = self.deployment(approved())
        profile["backend"]["container_name"] = "landing"
        with self.assertRaises(InvalidEnvironment):
            backend_arguments(profile, "workspace", TENANT_A)

    def test_reject_credential_field_and_output_injection(self):
        profile = approved()
        profile["backend"]["client_secret"] = "do-not-print"
        with self.assertRaises(InvalidEnvironment):
            self.deployment(profile)
        args = backend_arguments(self.deployment(approved()), "workspace", TENANT_A)
        args["key"] = 'fabric/lab-b/workspace.tfstate"\nsecret="bad'
        with self.assertRaises(InvalidEnvironment):
            render_backend_config(args)

    def test_fresh_backend_arguments_are_derived_not_legacy_fallback(self):
        from fabric_bootstrap_handoff import handoff
        from test_fabric_bootstrap_handoff import fixtures
        h = handoff(*fixtures(cross=True, fresh=True))
        fresh_backend = h["proposed_bootstrap_backend"]
        deployment = {
            "environment": h["environment"], "bootstrap_mode": "fresh-bootstrap",
            "backend": fresh_backend,
        }
        args = backend_arguments(deployment, "workspace", fresh_backend["tenant_id"])
        self.assertEqual(args["storage_account_name"], "hdplabbstorage")
        self.assertIn("fabric/lab-b/workspace.tfstate", render_backend_config(args))
        mutated = json.loads(json.dumps(deployment))
        mutated["backend"]["storage_account_name"] = "johnzhang"
        with self.assertRaises(InvalidEnvironment):
            backend_arguments(mutated, "workspace", fresh_backend["tenant_id"])
        mutated = json.loads(json.dumps(deployment))
        mutated["backend"]["storage_account_arm_id"] = mutated["backend"]["storage_account_arm_id"].replace(
            "hdplabbstorage", "johnzhang"
        )
        with self.assertRaises(InvalidEnvironment):
            backend_arguments(mutated, "workspace", fresh_backend["tenant_id"])

    def test_reject_unknown_backend_field(self):
        args = backend_arguments(self.deployment(approved()), "workspace", TENANT_A)
        args["access_key"] = "forbidden"
        with self.assertRaises(InvalidEnvironment):
            render_backend_config(args)


if __name__ == "__main__":
    unittest.main()
