"""TASK004 STEP04A read-only SQL static policy checks; no DB connectivity needed."""
from pathlib import Path
import re
import unittest

SQL = Path(__file__).resolve().parents[2] / "sql/task004/step04a-readonly-schema-inventory.sql"

class ReadOnlyInventoryContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sql = SQL.read_text(encoding="utf-8")
        cls.executable = re.sub(r"(?m)^\s*--[^\n]*", "", cls.sql)
        cls.executable = re.sub(r"/\*.*?\*/", "", cls.executable, flags=re.S)

    def test_readonly_transaction_and_bounded_timeout(self):
        self.assertRegex(self.executable, r"(?i)BEGIN\s+TRANSACTION\s+ISOLATION\s+LEVEL\s+REPEATABLE\s+READ\s+READ\s+ONLY")
        self.assertRegex(self.executable, r"(?i)SET\s+LOCAL\s+statement_timeout")
        self.assertRegex(self.executable, r"(?i)SET\s+LOCAL\s+lock_timeout")
        self.assertRegex(self.executable, r"(?i)\bCOMMIT\s*;")

    def test_no_writes_or_side_effect_calls(self):
        forbidden = (r"\b(?:INSERT|UPDATE|DELETE|MERGE|UPSERT|TRUNCATE|ALTER|DROP|CREATE|GRANT|REVOKE|COPY|CALL|DO|VACUUM|REFRESH|REINDEX|CLUSTER|LOCK)\b",
                     r"\bpg_advisory_(?:lock|xact_lock)\s*\(", r"\b(?:dblink|lo_import|pg_read_file|pg_write_file)\s*\(")
        for pattern in forbidden:
            with self.subTest(pattern=pattern):
                self.assertNotRegex(self.executable, r"(?i)" + pattern)

    def test_expected_tables_in_catalog_scope(self):
        for schema, table in (("cdm","person"),("cdm","visit_occurrence"),("etl","person_stage"),
                              ("etl","person_id_map"),("etl","visit_occurrence_id_map")):
            with self.subTest(table=table):
                self.assertIn(f"('{schema}','{table}')", self.sql)

if __name__ == "__main__":
    unittest.main()
