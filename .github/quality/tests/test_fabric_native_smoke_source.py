"""Offline verification of Fabric Git-native Trial Notebook/Pipeline definitions."""
import json
import unittest
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "azure-fabric/workspaces/johnzhang-test"
NB = SRC / "notebooks/nb_trial_smoke.Notebook"
PL = SRC / "pipelines/pl_trial_smoke.DataPipeline"
ZERO_WORKSPACE = "00000000-0000-0000-0000-000000000000"


class FabricNativeSmokeContract(unittest.TestCase):
    def read_json(self, path):
        return json.loads(path.read_text())

    def test_git_native_item_types_and_stable_distinct_logical_ids(self):
        notebook = self.read_json(NB / ".platform")
        pipeline = self.read_json(PL / ".platform")
        ids = set()
        for path, doc, kind, name in [
            (NB, notebook, "Notebook", "nb_trial_smoke"),
            (PL, pipeline, "DataPipeline", "pl_trial_smoke"),
        ]:
            self.assertEqual(doc["metadata"]["type"], kind)
            self.assertEqual(doc["metadata"]["displayName"], name)
            self.assertEqual(path.name, name + "." + kind)
            lid = doc["config"]["logicalId"]
            UUID(lid)
            self.assertNotEqual(lid, ZERO_WORKSPACE)
            ids.add(lid)
            self.assertEqual(doc["config"]["version"], "2.0")
            self.assertIn("platformProperties/2.0.0", doc["$schema"])
        self.assertEqual(len(ids), 2)

    def test_pipeline_binds_exact_same_workspace_notebook(self):
        notebook = self.read_json(NB / ".platform")
        data = self.read_json(PL / "pipeline-content.json")
        self.assertNotIn("annotations", data)
        self.assertEqual(len(data["properties"]["activities"]), 1)
        activity = data["properties"]["activities"][0]
        self.assertEqual(activity["type"], "TridentNotebook")
        self.assertEqual(activity["typeProperties"]["notebookId"], notebook["config"]["logicalId"])
        self.assertEqual(activity["typeProperties"]["workspaceId"], ZERO_WORKSPACE)
        self.assertEqual(activity["policy"]["retry"], 0)
        self.assertNotIn("concurrency", data)
        self.assertNotIn("trigger", data)

    def test_notebook_is_explicit_no_write_smoke(self):
        source = (NB / "notebook-content.py").read_text()
        self.assertIn('"name": "synapse_pyspark"', source)
        self.assertIn("FABRIC_NOTEBOOK_SMOKE=PASS", source)
        self.assertIn("MODE=NO_DATA_WRITE", source)
        for unsafe in ("spark.sql(", ".save(", ".write.", "notebookutils.fs.", "dbutils.fs.",
                       "abfss://", "https://", "DROP TABLE", "CREATE TABLE"):
            self.assertNotIn(unsafe, source)

    def test_no_terraform_fabric_items_under_new_roots(self):
        for folder in ["fabric-workspace", "shared-infra"]:
            tree = ROOT / "azure-fabric/infra-terraform" / folder
            for file in tree.rglob("*.tf"):
                text = file.read_text()
                for kind in ("fabric_notebook", "fabric_data_pipeline"):
                    self.assertNotIn('resource "' + kind + '"', text)

    def test_exactly_one_smoke_item_of_each_type(self):
        self.assertEqual([p.name for p in (SRC / "notebooks").glob("*.Notebook")],
                         ["nb_trial_smoke.Notebook"])
        self.assertEqual([p.name for p in (SRC / "pipelines").glob("*.DataPipeline")],
                         ["pl_trial_smoke.DataPipeline"])


if __name__ == "__main__":
    unittest.main()
