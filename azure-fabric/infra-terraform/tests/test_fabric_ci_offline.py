"""Reject deployment-capable commands and cloud credentials in Fabric PR validation.

No cloud SDK, Terraform binary or network required for this source-only regression.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github/workflows/fabric-environment-preflight.yml"


class OfflineWorkflowTests(unittest.TestCase):
    def test_format_only_terraform_invocation(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("terraform_version: '1.13.0'", workflow)
        self.assertIn("terraform fmt -check -diff", workflow)
        self.assertIn("permissions:\n  contents: read", workflow)
        # Ignore comments; only check actual YAML shell command lines.
        for line in workflow.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if re.search(r"^terraform\s+(?!fmt\b)", stripped):
                self.fail("CI must not run stateful Terraform commands")
        forbidden = (
            r"\baz\s+(?:login|rest|account|storage|role)\b",
            r"\b(?:curl|wget)\b.*(?:management\.azure|api\.fabric\.microsoft)",
            r"\b(?:terraform\s+(?:init|validate|plan|apply|destroy|import|state|refresh|force-unlock))\b",
            r"\b(?:ARM_CLIENT_SECRET|FABRIC_CLIENT_SECRET|AZURE_CLIENT_SECRET)\b",
        )
        for pattern in forbidden:
            with self.subTest(pattern=pattern):
                self.assertNotRegex(workflow, pattern)

    def test_no_apply_approval_or_checkout_tokens(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("persist-credentials: false", workflow)
        self.assertNotIn("id-token: write", workflow)
        self.assertNotIn("environment: production", workflow)
        self.assertNotIn("terraform apply", workflow)


if __name__ == "__main__":
    unittest.main()
