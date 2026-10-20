"""Pin fail-closed cross-repo immutable OIDC mismatch, without cloud access."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from fabric_oidc_subject_audit import (  # noqa: E402
    inspect_source, OIDCSourceDrift,
    OWNER_ID, HEALTHCARE_REPOSITORY_ID, SELF_RUNNER_REPOSITORY_ID,
)


class OIDCExecutionTopologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "bootstrap/identity/main.tf").read_text(encoding="utf-8")

    def test_known_incompatible_hcl_requires_redesign_before_executor(self):
        v = inspect_source(self.source)
        self.assertEqual(v["status"], "FABRIC_OIDC_SUBJECT_ARCHITECTURE_HOLD")
        self.assertTrue(v["github_repositories_created_after_immutable_default"])
        self.assertTrue(v["self_runner_controller_repo_distinct_from_issuer_repo"])
        self.assertTrue(v["role_env_names_different_from_plan_apply_env_names"])
        self.assertEqual(len(v["current_literal_subjects"]), 2)
        for key in ("token_issued", "github_environment_protection_verified",
                    "provider_authenticated", "terraform_executed",
                    "deployment_allowed"):
            self.assertIs(v[key], False)
        self.assertEqual(OWNER_ID, 337895338)
        self.assertNotEqual(HEALTHCARE_REPOSITORY_ID, SELF_RUNNER_REPOSITORY_ID)
        self.assertIn("SELF_RUNNER_CONTROLLER_REPOSITORY_DIFFERS_FROM_ENROLLED_HEALTHCARE_OIDC",
                      v["blockers"])

    def test_metadata_contains_correct_immutable_proposal_not_a_grant(self):
        v = inspect_source(self.source)
        for s in v["expected_immutable_healthcare_subjects_FOR_DESIGN_ONLY"]:
            self.assertIn("JohnZhang-DataForge@337895338", s)
            self.assertIn("healthcare-data-platform@1404947726", s)
        self.assertIn("Self-Runner@1413796156",
                      v["example_immutable_self_runner_phase_subject_FOR_DESIGN_ONLY"])
        self.assertNotIn("@", v["current_literal_subjects"][0])

    def test_prevent_silent_identity_subject_modification(self):
        for old, replacement in (
            ("healthcare-data-platform", "Self-Runner"),
            ("-backend", "-plan"),
            ("-deployer", "-apply"),
            ("repo:JohnZhang-DataForge/healthcare-data-platform:",
             "repo:JohnZhang-DataForge@337895338/healthcare-data-platform@1404947726:"),
        ):
            with self.subTest(replacement=replacement):
                changed = self.source.replace(old, replacement)
                self.assertNotEqual(changed, self.source)
                with self.assertRaises(OIDCSourceDrift):
                    inspect_source(changed)

    def test_missing_duplicate_and_foreign_subjects_fail(self):
        actual = self.source
        self.assertRegex(actual, r'subject\s*=')
        with self.assertRaises(OIDCSourceDrift):
            inspect_source("")
        with self.assertRaises(OIDCSourceDrift):
            inspect_source(actual.replace("subject", "untrusted_subject"))
        with self.assertRaises(OIDCSourceDrift):
            inspect_source(actual.replace("backend-github", "fabric-github")
                           .replace('environment:fabric-${var.environment}-backend',
                                    'environment:fabric-${var.environment}-deployer'))

    def test_ci_has_unprivileged_subject_audit(self):
        ci = (ROOT.parents[1] / ".github/workflows/fabric-environment-preflight.yml").read_text()
        self.assertIn("test_fabric_oidc_subject_audit.py", ci)
        self.assertIn("permissions:\n  contents: read", ci)
        self.assertNotIn("id-token: write", ci)


if __name__ == "__main__":
    unittest.main()
