"""No-cloud static safety gates for Fabric Capacity AzAPI root."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1] / "bootstrap" / "capacity"


class CapacityRootStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.versions = (ROOT / "versions.tf").read_text(encoding="utf-8")
        cls.providers = (ROOT / "providers.tf").read_text(encoding="utf-8")
        cls.variables = (ROOT / "variables.tf").read_text(encoding="utf-8")
        cls.main = (ROOT / "main.tf").read_text(encoding="utf-8")
        cls.outputs = (ROOT / "outputs.tf").read_text(encoding="utf-8")

    def test_pinned_azapi_and_isolated_bootstrap_state(self):
        self.assertIn('source  = "Azure/azapi"', self.versions)
        self.assertIn('version = "= 2.8.0"', self.versions)
        self.assertIn('backend "local" {}', self.versions)
        self.assertNotIn('backend "azurerm"', self.versions)
        self.assertIn("tenant_id       = var.fabric_tenant_id", self.providers)
        self.assertIn("subscription_id = var.capacity_subscription_id", self.providers)

    def test_default_reuse_and_all_paid_approvals_false(self):
        self.assertRegex(
            self.variables, r'variable "capacity_mode"\s*{[^}]+default\s*=\s*"reuse-existing"'
        )
        for name in (
            "capacity_creation_approved",
            "independent_billing_approval_verified",
            "protected_environment_approval_verified",
            "subscription_and_rg_inventory_verified",
            "name_and_sku_quota_verified",
            "seed_operator_authorized",
        ):
            self.assertRegex(
                self.variables, rf'variable "{name}"\s*{{[^}}]+default\s*=\s*false'
            )
            self.assertIn("var." + name, self.main)
        self.assertIn('var.capacity_mode == "create-new"', self.main)
        self.assertIn("count     = local.paid_creation_gate ? 1 : 0", self.main)
        self.assertNotRegex(self.main, r'\bdata "(?:azapi_|azurerm_|fabric_)')

    def test_exact_arm_schema_and_destroy_protection(self):
        self.assertEqual(self.main.count('resource "azapi_resource"'), 1)
        self.assertIn('"Microsoft.Fabric/capacities@2023-11-01"', self.main)
        for expected in (
            "parent_id = var.capacity_resource_group_id",
            "location  = var.capacity_region",
            "members = var.capacity_administrators",
            "name = var.capacity_sku",
            'tier = "Fabric"',
            "prevent_destroy = true",
        ):
            self.assertIn(expected, self.main)
        self.assertNotIn("suspend", self.main.lower())
        self.assertNotIn("resume", self.main.lower())
        self.assertNotIn("force_delete", self.main.lower())
        self.assertNotIn('resource "fabric_', self.main)

    def test_paid_evidence_bound_to_exact_source_and_scope(self):
        for gate in (
            "var.capacity_resource_group_id != null",
            "var.capacity_region != null",
            "var.capacity_sku != null",
            "length(var.capacity_administrators) > 0",
            "var.estimated_monthly_usd > 0",
            "var.monthly_budget_usd >= var.estimated_monthly_usd",
            "var.approved_cost_review_reference != null",
            "var.reviewed_source_sha != null",
        ):
            self.assertIn(gate, self.main)
        self.assertIn("capacity_subscription_id", self.variables)
        self.assertIn("fabric_tenant_id", self.variables)
        self.assertIn("var.capacity_subscription_id", self.main)

    def test_reuse_never_becomes_new_azure_capacity_uuid(self):
        self.assertIn("reused_fabric_uuid", self.outputs)
        self.assertIn("created_azure_arm_id", self.outputs)
        self.assertRegex(self.outputs, r"created_fabric_uuid\s*=\s*null")
        self.assertRegex(self.outputs, r"capacity_id_verified\s*=\s*false")
        self.assertIn('var.capacity_mode == "reuse-existing" ? var.existing_capacity_id : null', self.outputs)
        self.assertRegex(self.outputs, r"external_inventory_read\s*=\s*false")

    def test_no_credentials_migration_or_live_terraform(self):
        src = self.versions + self.providers + self.variables + self.main + self.outputs
        for banned in ("client_secret", "access_token", "storage_account_key", "sas_token",
                       "terraform apply", "terraform init", "terraform destroy",
                       "terraform import", "remote-exec", "local-exec",
                       "az login", 'backend "azurerm"', "data \""):
            self.assertNotIn(banned, src)


if __name__ == "__main__":
    unittest.main()
