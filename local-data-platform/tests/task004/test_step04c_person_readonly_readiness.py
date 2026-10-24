from pathlib import Path
import unittest
P=Path(__file__).resolve().parents[2]/"sql/task004/step04c-person-readonly-readiness.sql"
class PersonReadiness(unittest.TestCase):
    def test_readonly_contract(self):
        s=P.read_text()
        self.assertIn("REPEATABLE READ READ ONLY",s)
        self.assertIn("POSTGRESQL_MUTATION=NO",s)
        for banned in ("TRUNCATE ","INSERT INTO ","DELETE FROM ","UPDATE cdm.","CREATE TABLE ","ALTER TABLE "):
            self.assertNotIn(banned,s)
    def test_historical_and_batch_safety(self):
        s=P.read_text()
        for name in ("HISTORIC_MAP_TARGET_GAPS","MAP_BUSINESS_KEY_UNIQUE_INDEX",
                     "PROPOSED_BATCH_STAGE_PRESENT","PERSON_STAGE_HAS_BATCH_ID",
                     "MAP_DUPLICATE_BUSINESS_KEYS"):
            self.assertIn(name,s)
if __name__=="__main__":unittest.main()
