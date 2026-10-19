"""Static safety contract for inert multi-environment Fabric Terraform root scaffolds."""
from pathlib import Path
import re
import unittest

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE / "new-environments"
COMPONENTS = ("workspace", "onelake", "connection")


class IsolatedRootSkeletonTests(unittest.TestCase):
    def test_three_independent_partial_backends(self):
        for component in COMPONENTS:
            with self.subTest(component=component):
                location = ROOT / component
                names = {p.name for p in location.iterdir() if p.is_file()}
                expected = {"versions.tf", "providers.tf"}
                if component == "workspace":
                    expected.update({"main.tf", "variables.tf", "outputs.tf"})
                self.assertEqual(names, expected)
                versions = (location / "versions.tf").read_text(encoding="utf-8")
                self.assertIn('backend "azurerm" {}', versions)
                self.assertIn('source  = "microsoft/fabric"', versions)
                self.assertNotIn("dev/", versions)
                self.assertNotIn("johnzhang", versions)

    def test_no_resource_or_execution_bypasses(self):
        for component in ("onelake", "connection"):
            contents = "\n".join(
                p.read_text(encoding="utf-8")
                for p in (ROOT / component).glob("*.tf")
            )
            # No module, resource, data, provisioner, or local-exec allowed in
            # this scaffold; ownership and schema are later Change tasks.
            self.assertNotRegex(
                contents,
                r'(?m)^\s*(?:resource|data|module|import|removed|moved|provisioner)\s*["{]',
            )
            self.assertNotIn("local-exec", contents)
            self.assertNotIn("client_secret", contents)
            self.assertNotIn("access_key", contents)

    def test_provider_uses_explicit_fabric_oidc_not_backend_identity(self):
        for component in COMPONENTS:
            provider = (ROOT / component / "providers.tf").read_text(encoding="utf-8")
            self.assertIn('provider "fabric"', provider)
            self.assertRegex(provider, r"use_oidc\s*=\s*true")
            self.assertNotRegex(provider, r"(?m)^\s*(?:tenant_id|client_id)\s*=")
            self.assertNotIn("var.azure", provider.lower())

    def test_workspace_requires_explicit_approval_and_blocks_destroy(self):
        main = (ROOT / "workspace" / "main.tf").read_text(encoding="utf-8")
        variables = (ROOT / "workspace" / "variables.tf").read_text(encoding="utf-8")
        self.assertIn('resource "fabric_workspace" "current"', main)
        self.assertIn("prevent_destroy = true", main)
        self.assertIn("precondition {", main)
        self.assertIn("var.workspace_creation_approved", main)
        self.assertIn('var.workspace_name == "HDP-${var.environment}"', main)
        self.assertIn("default = false", variables)
        self.assertIn("var.capacity_id", variables)
        self.assertNotIn("role_assignment", main)

    def test_safety_documented(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for marker in ("SCAFFOLD ONLY", "no resources", "dev/*.tfstate",
                       "init", "plan", "apply", "destroy", "fabric-cicd"):
            self.assertIn(marker, readme)


if __name__ == "__main__":
    unittest.main()
