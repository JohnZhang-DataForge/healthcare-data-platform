"""Read-only, aggregate-only TASK004 STEP04A map inventory contract."""
import pathlib
import re
import unittest

SQL = pathlib.Path(__file__).resolve().parents[2] / "sql/task004/step04a-readonly-map-inventory.sql"

class MappingInventoryContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        src = SQL.read_text()
        cls.text = re.sub(r"(?m)^\s*--[^\n]*", "", src)
        cls.text = re.sub(r"'(?:''|[^'])*'", "''", cls.text)

    def test_read_only_transaction(self):
        self.assertRegex(self.text, r"(?i)BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        self.assertRegex(self.text, r"(?i)SET LOCAL statement_timeout")
        self.assertRegex(self.text, r"(?i)SET LOCAL lock_timeout")

    def test_no_mutating_statements(self):
        self.assertNotRegex(self.text, r"(?i)\b(?:INSERT|UPDATE|DELETE|MERGE|TRUNCATE|ALTER|DROP|CREATE|COPY|CALL|DO|GRANT|REVOKE|LOCK)\b")

    def test_aggregate_guards(self):
        for token in ("count(DISTINCT (source_system,source_person_id))",
                      "count(DISTINCT (source_system,source_encounter_id))",
                      "mappings_without_target","orphan_person_fk","duplicate_business_key_groups",
                      "stage_matching_target_ids"):
            self.assertIn(token,self.text)
        self.assertNotRegex(self.text,r"(?i)\bSELECT\s+\*")

if __name__ == "__main__":
    unittest.main()
