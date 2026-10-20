"""Immutable Self-Runner OIDC topology: role/phase negative and nonauthorization tests."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from fabric_oidc_subject_audit import (
    inspect_source, OIDCSourceDrift, IMMUTABLE_PREFIX, BINDINGS,
    OWNER_ID, SELF_RUNNER_REPOSITORY_ID, HEALTHCARE_REPOSITORY_ID,
)

class OIDCExecutionTopologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "bootstrap/identity/main.tf").read_text(encoding="utf-8")

    def test_exact_four_immutable_phase_subjects_are_statically_aligned(self):
        v = inspect_source(self.source)
        self.assertEqual(v["status"], "FABRIC_OIDC_SOURCE_ALIGNED_LIVE_HOLD")
        self.assertEqual(set(v["subject_bindings"]), set(BINDINGS))
        self.assertIn("JohnZhang-DataForge@337895338", IMMUTABLE_PREFIX)
        self.assertIn("Self-Runner@1413796156", IMMUTABLE_PREFIX)
        self.assertNotEqual(SELF_RUNNER_REPOSITORY_ID, HEALTHCARE_REPOSITORY_ID)
        self.assertEqual(OWNER_ID, 337895338)
        for key in ("token_issued", "github_environment_protection_verified",
                    "provider_authenticated", "terraform_executed", "deployment_allowed"):
            self.assertIs(v[key], False)

    def test_legacy_or_misrouted_credentials_rejected(self):
        candidates = (
            ("Self-Runner@1413796156", "healthcare-data-platform@1404947726"),
            ("JohnZhang-DataForge@337895338/", "JohnZhang-DataForge/"),
            ("-plan-backend", "-apply-backend"),
            ("azuread.backend", "azuread.fabric"),
            ("azuread_application_registration.backend_operator[0].id",
             "azuread_application_registration.blob_reader[0].id"),
            ("var.identity_creation_approved ? 1 : 0", "true ? 1 : 0"),
            ("prevent_destroy = true", "prevent_destroy = false"),
        )
        for a, b in candidates:
            with self.subTest(change=a):
                marker = 'resource "azuread_application_federated_identity_credential" "backend_operator_plan"'
                prefix, credential_blocks = self.source.split(marker, 1)
                modified_blocks = credential_blocks.replace(a, b, 1)
                self.assertNotEqual(modified_blocks, credential_blocks)
                modified = prefix + marker + modified_blocks
                with self.assertRaises(OIDCSourceDrift):
                    inspect_source(modified)

    def test_missing_duplicate_foreign_subjects_fail(self):
        with self.assertRaises(OIDCSourceDrift):
            inspect_source("")
        with self.assertRaises(OIDCSourceDrift):
            inspect_source(self.source.replace('subject        = "', 'subject = "other-', 1))
        with self.assertRaises(OIDCSourceDrift):
            inspect_source(self.source.replace(
                'resource "azuread_application_federated_identity_credential" "backend_operator_plan"',
                'resource "azuread_application_federated_identity_credential" "foreign"'))

    def test_pr_ci_remains_unprivileged(self):
        ci = (ROOT.parents[1] / ".github/workflows/fabric-environment-preflight.yml").read_text()
        self.assertIn("test_fabric_oidc_subject_audit.py", ci)
        self.assertIn("permissions:\n  contents: read", ci)
        self.assertNotIn("id-token: write", ci)

if __name__ == "__main__":
    unittest.main()
