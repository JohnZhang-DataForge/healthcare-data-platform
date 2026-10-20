"""Static default-deny identity Terraform Root checks; never run providers."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1] / "bootstrap" / "identity"


class IdentityRootTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.versions = (ROOT / "versions.tf").read_text(encoding="utf-8")
        cls.providers = (ROOT / "providers.tf").read_text(encoding="utf-8")
        cls.variables = (ROOT / "variables.tf").read_text(encoding="utf-8")
        cls.main = (ROOT / "main.tf").read_text(encoding="utf-8")
        cls.outputs = (ROOT / "outputs.tf").read_text(encoding="utf-8")

    def test_provider_pinned_and_initial_state_independent(self):
        self.assertIn('source  = "hashicorp/azuread"', self.versions)
        self.assertIn('version = "= 3.8.0"', self.versions)
        self.assertIn('backend "local" {}', self.versions)
        self.assertNotIn('backend "azurerm"', self.versions)

    def test_tenant_aliases_and_no_implicit_seed_authorization(self):
        self.assertEqual(self.providers.count('provider "azuread"'), 2)
        for text in ('alias     = "backend"', 'alias     = "fabric"',
                     "tenant_id = var.backend_tenant_id",
                     "tenant_id = var.fabric_tenant_id"):
            self.assertIn(text, self.providers)

    def test_every_resource_opt_in_and_protected(self):
        self.assertRegex(self.variables,
                         r'variable "identity_creation_approved"\s*{[^}]+default\s*=\s*false')
        resources = re.findall(
            r'^resource "([^"]+)" "([^"]+)"\s*{(.*?)(?=^resource "|\Z)',
            self.main, re.M | re.S,
        )
        self.assertEqual(len(resources), 12)
        for typ, name, body in resources:
            with self.subTest(kind=typ, name=name):
                self.assertIn("var.identity_creation_approved ? 1 : 0", body)
                self.assertIn("prevent_destroy = true", body)
                self.assertNotIn("client_secret", body.lower())
                self.assertNotIn("use_existing", body.lower())

    def test_independent_apps_groups_and_federated_subjects(self):
        for kind, count in (
            ("azuread_application_registration", 3),
            ("azuread_service_principal", 3),
            ("azuread_group", 2),
            ("azuread_application_federated_identity_credential", 4),
        ):
            self.assertEqual(self.main.count('resource "' + kind + '"'), count)
        self.assertIn('audiences      = ["api://AzureADTokenExchange"]', self.main)
        self.assertIn('issuer         = "https://token.actions.githubusercontent.com"', self.main)
        for suffix in ("plan-backend", "apply-backend", "plan-deployer", "apply-deployer"):
            self.assertIn("environment:fabric-${var.environment}-" + suffix, self.main)
        self.assertIn("repo:JohnZhang-DataForge@337895338/Self-Runner@1413796156", self.main)
        self.assertNotIn("repo:JohnZhang-DataForge/healthcare-data-platform", self.main)
        self.assertNotIn("refs/pull/", self.main)
        self.assertNotIn('display_name = "github-terraform"', self.main)

    def test_no_other_tenant_or_remote_state_changes(self):
        source = self.versions + self.providers + self.variables + self.main + self.outputs
        for forbidden in (
            'resource "azurerm_', 'resource "azapi_', 'resource "fabric_',
            'data "azuread_', 'terraform_remote_state', "client_secret",
            'provisioner "local-exec"', 'provisioner "remote-exec"',
            "terraform apply", 'backend "azurerm"',
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn("verified          = false", self.outputs)


if __name__ == "__main__":
    unittest.main()
