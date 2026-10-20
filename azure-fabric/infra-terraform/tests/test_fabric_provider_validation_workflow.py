"""Constrain provider-level PR testing to no-backend, no-token init/validate.

Provider plugins are downloaded and HCL validated; no Azure/Fabric credentials,
remote State, graph privileges or live planning are granted by this workflow.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github/workflows/fabric-provider-init-validate.yml"
EXPECTED_ROOTS = (
    "bootstrap/identity", "bootstrap/storage", "bootstrap/capacity",
    "new-environments/workspace", "new-environments/onelake",
    "new-environments/connection",
)


class ProviderValidationSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = WORKFLOW.read_text(encoding="utf-8")

    def test_exact_six_roots_explicit_matrix(self):
        for root in EXPECTED_ROOTS:
            self.assertIn("azure-fabric/infra-terraform/" + root, self.w)
        self.assertEqual(self.w.count("- {name:"), 6)
        self.assertNotIn("components/", self.w)

    def test_real_init_and_schema_validation_no_backend(self):
        self.assertIn('terraform_version: \'1.13.5\'', self.w)
        self.assertIn('init -backend=false -input=false -no-color', self.w)
        self.assertIn('validate -no-color', self.w)
        self.assertIn('if: github.event_name == \'pull_request\'', self.w)
        self.assertIn("github.ref == 'refs/heads/main'", self.w)
        self.assertNotIn("terraform -chdir=\"$CHECK_ROOT\" init -no-color", self.w)

    def test_strict_unprivileged_scope(self):
        self.assertIn("permissions:\n  contents: read", self.w)
        self.assertIn("runs-on: ubuntu-latest", self.w)
        self.assertIn("persist-credentials: false", self.w)
        for forbidden in ("id-token: write", "secrets.", "vars.", "ARM_CLIENT_ID",
                          "FABRIC_CLIENT_ID", "azure/login@", "dw-runner-set",
                          "terraform plan", "terraform apply", "terraform destroy",
                          "terraform import", "terraform state", "backend-config=",
                          "actions/upload-artifact@"):
            self.assertNotIn(forbidden, self.w)
        self.assertNotRegex(self.w, r"(?m)^\s*environment:")
        self.assertNotRegex(self.w, r"(?m)^\s*(?:push|repository_dispatch|workflow_run):")


if __name__ == "__main__":
    unittest.main()
