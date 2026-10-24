"""Airflow Discovery image must resolve v1 and v2 side-by-side; never claim."""
import copy
import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/"apps/task004"),str(ROOT/"apps/landing_discovery"),
             str(ROOT/"tests/synthea_new_only"),str(ROOT/"tests/landing_discovery")]
from test_v2_consumer import fixture as v2_fixture, BATCH as V2_BATCH, PREFIX as V2_PREFIX
from test_scan_ready_batches import ready_manifest,key_for,FakeS3,encoded
from scan_ready_batches import discover_ready_batches
from resolve_verified_landing_file import validate_manifest, ResolverError


class AirflowV2ReadOnlyTests(unittest.TestCase):
    def test_image_copies_explicit_v2_module_and_exact_contract(self):
        d=(ROOT/"images/landing-discovery-runtime/Dockerfile").read_text()
        self.assertIn("apps/task004/validate_new_only_v2_manifest.py",d)
        self.assertIn("contracts/synthea/new-only/csv-contract-v2.json",d)
        self.assertIn("/opt/healthcare/task004/csv-contract-v2.json",d)
        self.assertIn("apps/task004/resolve_verified_landing_file.py",d)
        self.assertNotIn("psycopg",d.lower())
        self.assertNotIn("postgres",d.lower())

    def test_mixed_v1_v2_discovery_remains_read_only(self):
        v2,remote=v2_fixture()
        v1=ready_manifest("legacy-v1")
        v1key=key_for("legacy-v1")
        v2key=V2_PREFIX+"manifest.json"
        got=discover_ready_batches(FakeS3([[v1key,v2key]],
                         {v1key:encoded(v1),v2key:remote[v2key]}))
        self.assertEqual(got["ready_count"],2)
        self.assertEqual(got["quarantined_count"],0)
        self.assertEqual({x["batch_id"] for x in got["ready_batches"]},
                         {"legacy-v1",V2_BATCH})
        self.assertFalse(got["processing_authorized"])
        self.assertFalse(got["database_mutation"])

    def test_wrong_v2_header_is_quarantined_but_v1_remains(self):
        v2,remote=v2_fixture()
        v2["files"][0]["header"]=["FORGED"]
        v2key=V2_PREFIX+"manifest.json"
        v1key=key_for("legacy-v1")
        got=discover_ready_batches(FakeS3([[v1key,v2key]],{
            v1key:encoded(ready_manifest("legacy-v1")),
            v2key:encoded(v2)
        }))
        self.assertEqual(got["ready_count"],1)
        self.assertEqual(got["quarantined_count"],1)
        self.assertEqual(got["ready_batches"][0]["batch_id"],"legacy-v1")

    def test_v1_header_only_never_gets_v2_allowance(self):
        v1=ready_manifest("legacy-v1")
        v1["files"][0]["row_count"]=0
        with self.assertRaisesRegex(ResolverError,"row_count must be > 0"):
            validate_manifest(v1,"legacy-v1","s3://health-landing/"+key_for("legacy-v1"))

    def test_producer_and_claim_are_not_activated(self):
        dag=(ROOT/"airflow/dags/landing_batch_discovery.py").read_text()
        self.assertIn('"CLAIM_ENABLE": "NO"',dag)
        self.assertIn('"CLAIM_ALLOWLIST": ""',dag)
        self.assertIn('dag_id="landing_batch_discovery"',dag)
        self.assertIn('"*/15 * * * *"',dag)
        self.assertNotIn("generate_new_only",dag)
        self.assertNotIn("publish_v2_verified",dag)


if __name__=="__main__":
    unittest.main()
