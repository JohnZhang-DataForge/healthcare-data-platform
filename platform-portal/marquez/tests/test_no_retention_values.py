#!/usr/bin/env python3
"""Offline regression checks for the Marquez 0.51.1 retention-off contract."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[3]
VALUES = ROOT / "platform-portal/marquez/helm/values.yaml"
DEPLOY = ROOT / "platform-portal/marquez/kubernetes/deploy.sh"


class NoRetentionContractTests(unittest.TestCase):
    def test_values_explicitly_remove_entire_retention_map(self):
        contents = VALUES.read_text()
        # Upstream 0.51.1 treats the *presence* of a retention map as enabled.
        self.assertRegex(contents, r"(?m)^  dbRetention: null\s*$")
        self.assertNotRegex(contents, r"(?m)^  dbRetention:\s*\n")

    def test_deploy_enforces_rendered_and_live_config(self):
        script = DEPLOY.read_text()
        self.assertIn("MARQUEZ_RETENTION_MUST_BE_ABSENT_FROM_RENDERED_CONFIG", script)
        self.assertIn("MARQUEZ_RETENTION_STILL_ENABLED", script)
        self.assertIn("--reset-values", script)
        self.assertIn("rollout restart deployment/marquez", script)
        self.assertIn("MARQUEZ_RETENTION_JOB_NOT_STARTED=PASS", script)


if __name__ == "__main__":
    unittest.main()
