"""Fail-closed static contracts for local OMOP encounter-bounded OP v1 SQL."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[5] / "local-data-platform"
SQL = ROOT / "apps/omop_writer/observation_period_encounter_v1.sql"

def statements():
    raw = SQL.read_text()
    return "\n".join(s for s in raw.splitlines() if not s.lstrip().startswith("--"))

class ObservationPeriodV1Tests(unittest.TestCase):
    def test_immutable_scope_and_transaction(self):
        sql=statements()
        self.assertEqual(len(re.findall(r"(?im)^\s*BEGIN\s*;",sql)),1)
        self.assertEqual(len(re.findall(r"(?im)^\s*COMMIT\s*;",sql)),1)
        self.assertEqual(len(re.findall(r"(?im)^\s*INSERT\s+INTO\b",sql)),1)
        self.assertRegex(sql,r"INSERT INTO cdm\.observation_period\s*\(")
        for x in ("UPDATE ", "DELETE FROM", "TRUNCATE ", "DROP TABLE",
                  "CREATE TABLE", "ON CONFLICT", "MERGE INTO", "GRANT ",
                  "SET ROLE", "ALTER TABLE", "cdm.person SET"):
            self.assertNotIn(x,sql.upper() if x.isupper() else sql)
        self.assertIn("LOCK TABLE cdm.observation_period",sql)
        self.assertIn("pg_try_advisory_xact_lock",sql)
        self.assertIn("SET LOCAL statement_timeout",sql)
        self.assertIn("SET LOCAL lock_timeout",sql)

    def test_event_bounds_and_real_vocabulary(self):
        sql=statements()
        self.assertIn("MIN(visit_start_date)",sql)
        self.assertIn("MAX(visit_end_date)",sql)
        self.assertIn("FROM cdm.visit_occurrence",sql)
        self.assertIn("GROUP BY person_id",sql)
        self.assertIn("period_type_concept_id",sql)
        self.assertIn("concept_id=44814724",sql)
        self.assertIn("concept_name='Period covering healthcare encounters'",sql)
        self.assertNotIn("CURRENT_DATE AS observation_period_end_date",sql)
        self.assertNotIn("birth_datetime::date AS observation_period_start_date",sql)
        self.assertNotIn("INTERVAL '365 days'",sql)

    def test_zero_target_and_historical_source_gates(self):
        sql=statements()
        for term in (
             "(SELECT COUNT(*) FROM cdm.observation_period) <> 0",
             "(SELECT COUNT(*) FROM cdm.person) <> 1394",
             "(SELECT COUNT(*) FROM cdm.visit_occurrence) <> 200556",
             "source_system='synthea'",
             "status='COMPLETED'",
             "OP_V1_INCOMPLETE_IDENTITY_MAP",
             "OP_V1_PERSON_WITHOUT_VISIT",
             "OP_V1_VISIT_INVALID_DATE",
             "OP_V1_ORPHAN_OR_PREBIRTH_VISIT",
             "OP_V1_NOT_ALL_PERSONS_INSERTED",
             "OP_V1_IN_TRANSACTION_READBACK_DRIFT",
             "GET DIAGNOSTICS inserted_count = ROW_COUNT",
        ):
            self.assertIn(term,sql)

    def test_source_is_reviewer_owned_and_no_exposed_passwords(self):
        src=SQL.read_text()
        self.assertIn("OpenSpec-Change: derive-local-omop-observation-period",src)
        self.assertIn("OpenSpec-Task: 1.1",src)
        self.assertNotIn("PGPASSWORD=",src)
        self.assertNotIn("ssh",src.lower())
        self.assertNotIn("atlas_demo",src)
        self.assertLess(len(src),20000)

if __name__=="__main__":
    unittest.main()
