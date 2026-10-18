from pathlib import Path
import unittest
P=Path(__file__).resolve().parents[2]/"sql/task004/step04e-joint-reconciliation-readonly.sql"
class JointReconciliationSafety(unittest.TestCase):
 def test_readonly_and_complete(self):
  s=P.read_text()
  self.assertIn("REPEATABLE READ READ ONLY",s)
  for k in ("BATCH_IDENTITY","PERSON_COMMIT","VISIT_COMMIT","PERSON_EXACT_CONTENT","VISIT_EXACT_CONTENT","ORPHAN_VISITS","PERSON_DUPLICATE_KEYS","VISIT_DUPLICATE_KEYS","NON_BATCH_PERSON_MAPS","NON_BATCH_VISIT_MAPS"):
   self.assertIn(k,s)
  for x in ("INSERT INTO","UPDATE cdm.","DELETE FROM","TRUNCATE ","CREATE TABLE","ALTER TABLE"):
   self.assertNotIn(x,s)
 def test_identity_is_fixed(self):
  s=P.read_text()
  self.assertIn("task004-airflow-task004-step03e-38324111846",s)
  self.assertIn("ecc7cf3b75240e530f2cc96635b25e4eaf0794403e1b04d50d2248cd3aaa5cb1",s)
if __name__=="__main__":unittest.main()
