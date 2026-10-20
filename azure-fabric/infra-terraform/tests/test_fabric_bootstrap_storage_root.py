"""Static-only storage/bootstrap RBAC safeguards. No Terraform or Azure SDK."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1] / "bootstrap" / "storage"


class StorageBootstrapRootTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.versions = (ROOT / "versions.tf").read_text(encoding="utf-8")
        cls.providers = (ROOT / "providers.tf").read_text(encoding="utf-8")
        cls.variables = (ROOT / "variables.tf").read_text(encoding="utf-8")
        cls.main = (ROOT / "main.tf").read_text(encoding="utf-8")
        cls.outputs = (ROOT / "outputs.tf").read_text(encoding="utf-8")

    def test_isolated_local_state_and_exact_azurerm_provider(self):
        self.assertIn('backend "local" {}', self.versions)
        self.assertNotIn('backend "azurerm"', self.versions)
        self.assertIn('source  = "hashicorp/azurerm"', self.versions)
        self.assertIn('version = "= 4.60.0"', self.versions)
        self.assertIn("tenant_id       = var.backend_tenant_id", self.providers)
        self.assertIn("subscription_id = var.storage_subscription_id", self.providers)

    def test_mode_is_explicit_and_reuse_has_no_managed_resources(self):
        self.assertRegex(
            self.variables, r'variable "bootstrap_mode"\s*{[^}]+default\s*=\s*"reuse-existing"'
        )
        self.assertIn('var.bootstrap_mode == "fresh-bootstrap"', self.main)
        self.assertNotRegex(self.main, r'\bdata "azurerm_')
        self.assertNotIn("terraform_remote_state", self.main)
        self.assertNotIn('resource "azurerm_storage_account" "existing"', self.main)
        self.assertIn('var.bootstrap_mode == "reuse-existing" ? var.reuse_existing_storage_account_id', self.outputs)
        self.assertIn('storageAccounts/johnzhang$', self.variables)
        for unsafe in ('dev/workspace.tfstate', 'dev/storage.tfstate',
                       'terraform import', 'terraform state mv', "github-terraform"):
            self.assertNotIn(unsafe, self.main)

    def test_all_creation_and_reconciliation_flags_default_false(self):
        for name in (
            "fresh_storage_creation_approved",
            "new_resource_inventory_verified",
            "seed_operator_authorized",
            "initial_state_custody_verified",
            "private_connectivity_verified",
            "rbac_creation_approved",
            "identity_provenance_verified",
        ):
            self.assertRegex(
                self.variables,
                rf'variable "{name}"\s*{{[^}}]+default\s*=\s*false',
            )
        self.assertIn("local.fresh_gate", self.main)
        self.assertIn("local.rbac_gate", self.main)
        self.assertIn("var.bootstrap_mode == \"fresh-bootstrap\"", self.main)
        self.assertIn("var.private_connectivity_verified", self.main)
        self.assertIn("var.backend_operator_object_id != var.blob_reader_object_id", self.main)

    def test_resources_only_create_new_and_prevent_destroy(self):
        resources = re.findall(
            r'^resource "([^"]+)" "([^"]+)"\s*{(.*?)(?=^resource "|\Z)',
            self.main, re.M | re.S,
        )
        self.assertEqual(len(resources), 6)
        for kind, name, body in resources:
            with self.subTest(resource=kind, name=name):
                self.assertIn("prevent_destroy = true", body)
                self.assertRegex(body, r'count\s*=\s*local\.(?:fresh_gate|rbac_gate) \? 1 : 0')
        self.assertEqual(self.main.count('resource "azurerm_resource_group"'), 1)
        self.assertEqual(self.main.count('resource "azurerm_storage_account"'), 1)
        self.assertEqual(self.main.count('resource "azurerm_storage_container"'), 2)
        self.assertEqual(self.main.count('resource "azurerm_role_assignment"'), 2)
        self.assertNotRegex(self.main, r'\bresource "(?:fabric_|azuread_|azapi_)')

    def test_storage_is_private_and_uses_arm_api_containers(self):
        for field in ("min_tls_version          = \"TLS1_2\"",
                      "allow_nested_items_to_be_public = false",
                      "shared_access_key_enabled       = false",
                      "default_to_oauth_authentication = true",
                      "public_network_access_enabled  = false"):
            self.assertIn(field, self.main)
        self.assertEqual(self.main.count('container_access_type = "private"'), 2)
        self.assertEqual(
            self.main.count("storage_account_id    = azurerm_storage_account.fresh[0].id"),
            2,
        )
        self.assertIn('name                  = "tfstate"', self.main)
        self.assertIn('name                  = "landing"', self.main)

    def test_rbac_requires_real_sp_object_ids_and_least_privilege(self):
        self.assertIn("backend_operator_object_id", self.variables)
        self.assertIn("blob_reader_object_id", self.variables)
        self.assertIn("SERVICE PRINCIPAL object ID", self.variables)
        self.assertIn(
            "scope                = azurerm_storage_container.backend[0].resource_manager_id",
            self.main,
        )
        self.assertIn(
            "scope                = azurerm_storage_container.landing[0].resource_manager_id",
            self.main,
        )
        self.assertIn('role_definition_name = "Storage Blob Data Contributor"', self.main)
        self.assertIn('role_definition_name = "Storage Blob Data Reader"', self.main)
        self.assertEqual(self.main.count('principal_type       = "ServicePrincipal"'), 2)
        self.assertNotIn('scope = azurerm_storage_account', self.main)
        self.assertNotIn('role_definition_name = "Owner"', self.main)

    def test_no_secrets_execution_or_live_proof(self):
        combined = self.versions + self.providers + self.variables + self.main + self.outputs
        for forbidden in (
            "client_secret", "storage_account_key", "sas_token", "client_certificate",
            "az login", "terraform apply", "terraform plan", "terraform init",
            'backend "azurerm"', "remote-exec", "local-exec",
        ):
            self.assertNotIn(forbidden, combined)
        self.assertIn("remote_state_checked         = false", self.outputs)
        self.assertIn("cloud_access_verified        = false", self.outputs)


if __name__ == "__main__":
    unittest.main()
