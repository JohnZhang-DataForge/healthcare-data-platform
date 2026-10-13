from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]/"sql/task004"
class MigrationSafety(unittest.TestCase):
 def test_migration_additive_and_transactional(self):
  s=(ROOT/"step04c-batch-schema-v1-authorized.sql").read_text()
  for required in ("BEGIN;","COMMIT;","HISTORICAL_BASELINE_CHANGED","CREATE TABLE etl.task004_batch_ledger","CREATE TABLE etl.task004_batch_stage","CREATE TABLE etl.task004_batch_commit","PRIMARY KEY (batch_id,entity,source_system,source_key)"):
   self.assertIn(required,s)
  for prohibited in ("TRUNCATE ","DELETE FROM ","UPDATE cdm.","INSERT INTO cdm.","DROP TABLE ","ALTER TABLE cdm."):
   self.assertNotIn(prohibited,s)
 def test_readback_is_readonly(self):
  s=(ROOT/"step04c-batch-schema-v1-readback.sql").read_text()
  self.assertIn("REPEATABLE READ READ ONLY",s)
  self.assertIn("HISTORIC_PERSON_ROWS",s)
  self.assertIn("HISTORIC_VISIT_ROWS",s)
if __name__=="__main__": unittest.main()
