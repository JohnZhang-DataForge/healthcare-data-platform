"""Offline source registration contract tests. No Kubernetes, PG or HTTP calls.

OpenSpec-Change: deploy-local-ohdsi-atlas
Task: 2.3 (version-specific WebAPI3 registration safety)
"""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[5]
APP = ROOT / "local-data-platform" / "atlas" / "config"
SPEC = APP / "local-omop-source.json"
SCRIPT = APP / "register_local_omop_source.py"

class AtlasSourceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("atlas_source", SCRIPT)
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)
        cls.conf = json.loads(SPEC.read_text(encoding="utf-8"))

    def test_unique_source_key_and_v3_daimon_ordinals(self):
        self.assertEqual(self.conf["source_key"], "LOCAL_OMOP")
        self.assertEqual(self.conf["dialect"], "postgresql")
        self.assertEqual([(v["daimonType"],v["tableQualifier"],v["priority"])
                          for v in self.conf["daimons"]],
                         [("CDM","cdm",0),("Vocabulary","cdm",1),
                          ("Results","atlas_results",0),("Temp","atlas_temp",0)])
        self.assertIn("postgresql",self.conf["connection_string"])
        self.assertNotIn("password=",self.conf["connection_string"].lower())
        self.assertNotIn("user=",self.conf["connection_string"].lower())
        self.assertNotIn(";",self.conf["connection_string"])
        self.assertNotIn("'",self.conf["connection_string"])

    def test_source_contract_and_payload(self):
        self.assertEqual(self.module.config(), self.conf)
        body, content_type = self.module.multipart_source(self.conf,"safe_name","dummy-value")
        self.assertTrue(content_type.startswith("multipart/form-data; boundary="))
        self.assertIn(b'Content-Disposition: form-data; name="source"',body)
        self.assertIn(b'Content-Type: application/json',body)
        self.assertIn(b'"key":"LOCAL_OMOP"',body)
        self.assertIn(b'"password":"dummy-value"',body)
        self.assertIn(b'"daimonType":"Vocabulary"',body)

    def test_script_requires_explicit_execute_and_readonly_sql(self):
        code=SCRIPT.read_text(encoding="utf-8")
        self.assertIn('parser.add_argument("--execute",action="store_true")',code)
        self.assertIn("default_transaction_read_only=on",code)
        self.assertIn("BEGIN TRANSACTION READ ONLY;",code)
        self.assertIn("ROLLBACK;",code)
        self.assertIn('print("ATLAS_SOURCE_CREATE_HTTP="',code)
        self.assertIn('print("WEBAPI_SOURCE_DAIMON_PG17_READBACK=PASS")',code)
        self.assertNotIn("kubectl apply",code)
        self.assertNotIn("kubectl rollout",code)
        self.assertNotIn("INSERT INTO webapi.",code)
        self.assertNotIn("UPDATE cdm.",code)
        self.assertNotIn("CREATE TABLE",code)
        self.assertNotIn("CREATE ROLE",code)

    def test_schema_and_secret_paths_conform(self):
        self.assertFalse((ROOT/"local-data-platform/atlas/kubernetes").exists())
        self.assertFalse((ROOT/"local-data-platform/atlas/images").exists())
        self.assertEqual(self.conf["db_secret"]["name"],"atlas-webapi-db")
        self.assertEqual(self.conf["login_secret"]["name"],"atlas-initial-login")
        self.assertEqual(self.conf["expected_database"],"omop")
        self.assertEqual(self.conf["target_node"],"worker03")

if __name__=="__main__":
    unittest.main()
