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
                if component in ("workspace", "onelake"):
                    expected.update({"main.tf", "variables.tf", "outputs.tf"})
                if component == "connection":
                    expected.update({"SCHEMA.md", "main.tf", "variables.tf", "outputs.tf"})
                self.assertEqual(names, expected)
                versions = (location / "versions.tf").read_text(encoding="utf-8")
                self.assertIn('backend "azurerm" {}', versions)
                self.assertIn('source  = "microsoft/fabric"', versions)
                self.assertNotIn("dev/", versions)
                self.assertNotIn("johnzhang", versions)

    def test_no_resource_or_execution_bypasses(self):
        contents = "\n".join(
            p.read_text(encoding="utf-8")
            for p in (ROOT / "connection").glob("*.tf")
        )
        # Exactly one new Connection is explicitly owned; no additional
        # data sources, modules, IAM, import or execution are allowed.
        self.assertEqual(contents.count('resource "fabric_connection"'), 1)
        self.assertNotRegex(contents, r'(?m)^\s*(?:data|module|import|removed|moved|provisioner)\s*["{]')
        self.assertNotIn("local-exec", contents)
        self.assertNotIn("client_secret_wo", contents)
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

    def test_lakehouse_depends_on_verified_workspace_and_approval(self):
        main = (ROOT / "onelake" / "main.tf").read_text(encoding="utf-8")
        variables = (ROOT / "onelake" / "variables.tf").read_text(encoding="utf-8")
        self.assertIn('resource "fabric_lakehouse" "current"', main)
        self.assertIn("var.workspace_id", main)
        self.assertIn("enable_schemas = true", main)
        self.assertIn("prevent_destroy = true", main)
        self.assertIn("var.lakehouse_creation_approved", main)
        self.assertIn("var.workspace_id_verified", main)
        self.assertIn('var.lakehouse_name == "HDP-${var.environment}-omop"', main)
        self.assertEqual(variables.count("default = false"), 2)
        self.assertNotIn("role_assignment", main)
        self.assertNotIn('resource "fabric_notebook"', main)

    def test_connection_schema_gate_blocks_unverified_resource(self):
        location = ROOT / "connection"
        schema = (location / "SCHEMA.md").read_text(encoding="utf-8")
        self.assertIn("resource declared but not deployed", schema)
        self.assertIn("List Supported Connection Types API", schema)
        self.assertIn("creation_method", schema)
        self.assertIn("Service Principal", schema)
        self.assertIn("Tenant A", schema)
        self.assertIn("connection.tfstate", schema)
        self.assertTrue((location / "main.tf").exists())

    def test_safety_documented(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for marker in ("SCAFFOLD ONLY", "dev/*.tfstate",
                       "init", "plan", "apply", "destroy", "fabric-cicd"):
            self.assertIn(marker, readme)


if __name__ == "__main__":
    unittest.main()
