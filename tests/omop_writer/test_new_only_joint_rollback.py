"""No COMMIT/Claim ever: NEW_ONLY real S3 Person+Visit SQL in ONE PG transaction."""
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"airflow"/"dags"))
sys.path.insert(0,str(ROOT/"apps"/"omop_writer"))
from build_s3_rollback_plan import build
from task004_cdm_dynamic_adapters import digest
from joint_s3_rollback import (
    PSQL_PREFIX, ENDING, compose_joint_rollback, verified_plan, strip_transaction, for_psycopg
)
from precommit_gate import validate_input

BATCH="synthea-new-only-gh-38497355290"
SHA="dfb5d30e83c6a9b35b3a723137a5f3ab67649ad94ef1801e2bae3ef42fe5fa80"
PREFIX="source=synthea/source_version=v3.3.0/ingest_date=2026-10-14/batch_id="+BATCH+"/"
def ctx():
    return build(batch_id=BATCH,manifest_uri="s3://health-landing/"+PREFIX+"manifest.json",
                 manifest_sha256=SHA,
                 person_processing_uri="s3a://health-processing/"+PREFIX+"entity=patient/run_id=task004-person-20261014T032923Z-9/work/normalized/data/",
                 visit_processing_uri="s3a://health-processing/"+PREFIX+"entity=encounter/run_id=task004-encounter-20261014T032923Z-8/work/normalized/data/",
                 person_rows=1,visit_rows=1,writer_identity_version="synthea-new-only-v1")
def rows():
    p={"gender_concept_id":8507,"year_of_birth":1980,"person_source_value":"p-1"}
    v={"visit_concept_id":9202,"visit_type_concept_id":32827,"visit_start_date":"2026-10-13",
       "visit_end_date":"2026-10-13","visit_source_value":"ambulatory"}
    person={"source_key":"p-1","canonical_payload":p,
            "row_fingerprint":digest({"source_person_key":None,"payload":p})}
    visit={"source_key":"v-1","source_person_key":"p-1","canonical_payload":v,
           "row_fingerprint":digest({"source_person_key":"p-1","payload":v})}
    return [person],[visit]

class JointRollbackTests(unittest.TestCase):
    def test_positive_joint_rollback_one_begin_one_rollback_no_commit(self):
        c=ctx();p,v=rows()
        self.assertFalse(c["database_mutation_authorized"])
        self.assertEqual(c["writer_identity_version"],"synthea-new-only-v1")
        validate_input(c,p,v)
        sql=compose_joint_rollback(c,p,v)
        self.assertTrue(sql.startswith(PSQL_PREFIX))
        self.assertTrue(sql.endswith(ENDING))
        self.assertEqual(sql.count("\nBEGIN;\n"),1)
        self.assertEqual(sql.count("ROLLBACK;"),1)
        self.assertNotIn("COMMIT;",sql)
        self.assertEqual(sql.count("CREATE TEMP TABLE task004_rows ON COMMIT DROP AS"),2)
        self.assertEqual(sql.count("DROP TABLE task004_rows;"),1)
        self.assertEqual(sql.count("INSERT INTO cdm.person"),1)
        self.assertEqual(sql.count("INSERT INTO cdm.visit_occurrence"),1)
        self.assertLess(sql.index("INSERT INTO cdm.person"),sql.index("BLOCKED:PERSON_COMMIT_MISSING"))
        self.assertLess(sql.index("BLOCKED:PERSON_COMMIT_MISSING"),sql.index("INSERT INTO cdm.visit_occurrence"))
        self.assertIn("BLOCKED:EXISTING_TARGET_DRIFT",sql)
        self.assertIn("BLOCKED:JOINT_CHECKPOINTS",sql)
        self.assertIn("BLOCKED:JOINT_STAGE_COUNT",sql)
        self.assertIn("BLOCKED:JOINT_LEDGER_DRIFT",sql)
        driver_sql=for_psycopg(sql)
        self.assertTrue(driver_sql.startswith("BEGIN;\\n".replace("\\\\n","\\n")))
        self.assertTrue(driver_sql.endswith("ROLLBACK;\\n".replace("\\\\n","\\n")))
        self.assertNotIn("set ON_ERROR_STOP",driver_sql)
        self.assertNotIn("COMMIT;",driver_sql)
    def test_legacy_or_version_drift_rejected(self):
        c=ctx();p,v=rows()
        for key,value in [("writer_identity_version",None),("writer_identity_version","bad"),
                          ("plan_sha256","a"*64),("database_mutation_authorized",True)]:
            with self.subTest(key=key,value=value):
                broken=dict(c);broken[key]=value
                with self.assertRaises(ValueError):compose_joint_rollback(broken,p,v)
    def test_parent_key_and_fingerprint_guard(self):
        c=ctx();p,v=rows();v[0]["source_person_key"]="not-present"
        with self.assertRaises(ValueError):compose_joint_rollback(c,p,v)
        p,v=rows();p[0]["row_fingerprint"]="f"*64
        with self.assertRaises(ValueError):compose_joint_rollback(c,p,v)
    def test_hidden_commit_or_second_begin_denied(self):
        for raw in [PSQL_PREFIX+"SELECT 1;\nCOMMIT;\n"+ENDING,
                    PSQL_PREFIX+"BEGIN;\n"+ENDING,
                    "BEGIN;\nSELECT 1;\n"+ENDING]:
            with self.assertRaises(ValueError):strip_transaction(raw)
    def test_no_legacy_write_escalation_in_cli(self):
        src=(ROOT/"apps/omop_writer/joint_s3_rollback.py").read_text()
        self.assertIn('connect("cdm_reader",readonly=True)',src)
        self.assertIn('connect("cdm_writer",readonly=False)',src)
        self.assertIn("POSTGRESQL_SEQUENCE_COUNTERS_MAY_ADVANCE=YES",src)
        self.assertNotIn('choices=["audit","rollback","commit"]',src)

if __name__=="__main__":
    unittest.main()
