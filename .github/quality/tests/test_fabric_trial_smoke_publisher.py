"""Safe source/outputs checks for scoped Fabric Trial Git-native publisher."""
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "azure-fabric/deployment/trial_smoke_publisher.py"
SOURCE = ROOT / "azure-fabric/workspaces/johnzhang-test"
spec = importlib.util.spec_from_file_location("fabric_trial_smoke_publisher", SCRIPT)
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


class TrialSmokePublisher(unittest.TestCase):
    def test_source_contract_does_not_need_credentials(self):
        payload = publisher.validate_source(SOURCE)
        self.assertNotEqual(payload["notebook_logical_id"], payload["pipeline_logical_id"])

    def test_output_ownership_gates(self):
        with tempfile.TemporaryDirectory() as temp:
            ws, lake = Path(temp) / "workspace.json", Path(temp) / "onelake.json"
            ws.write_text(json.dumps({
                "fabric_workspace_name": {"value": "johnzhang-test", "sensitive": False},
                "fabric_workspace_id": {"value": "11111111-1111-4111-8111-111111111111", "sensitive": False}
            }))
            lake.write_text(json.dumps({
                "fabric_workspace_id": {"value": "11111111-1111-4111-8111-111111111111", "sensitive": False},
                "lakehouse_id": {"value": "22222222-2222-4222-8222-222222222222", "sensitive": False}
            }))
            self.assertEqual(publisher.validate_outputs(ws, lake)[0],
                             "11111111-1111-4111-8111-111111111111")
            doc = json.loads(lake.read_text())
            doc["fabric_workspace_id"]["value"] = "99999999-9999-4999-8999-999999999999"
            lake.write_text(json.dumps(doc))
            with self.assertRaisesRegex(ValueError, "does not belong"):
                publisher.validate_outputs(ws, lake)

    def test_explicit_confirmation_gate(self):
        with patch.dict(os.environ, {"FABRIC_TRIAL_PUBLISH_ALLOWED": "false"}):
            with self.assertRaises(PermissionError):
                publisher.publish(SOURCE, "11111111-1111-4111-8111-111111111111", "bad")

    def test_no_unsafe_publish_calls(self):
        source = SCRIPT.read_text()
        self.assertIn("publish_all_items(workspace)", source)
        self.assertNotIn("import unpublish_all_orphan_items", source)
        self.assertNotIn("unpublish_all_orphan_items(workspace)", source)
        self.assertNotIn("terraform apply", source)
        self.assertNotIn("terraform destroy", source)
        self.assertIn("if before:", source)
        self.assertIn('choices=("validate", "publish")', source)


if __name__ == "__main__":
    unittest.main()
