from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"apps/task004"))
from step04d_visit_sql_builder import prepare,generate,BATCH
def row(i):
 return dict(source_encounter_id="visit-%04d"%i,source_person_id="person-01",source_system="synthea",source_batch_id=BATCH,source_version="v3.3.0",source_ingest_date="2026-10-12",encounter_class="ambulatory",start_datetime="2026-01-01T12:00:00Z",end_datetime="2026-01-01T14:00:00Z")
class VisitContract(unittest.TestCase):
 def test_sql_rollback_and_safety(self):
  s=generate(prepare([row(i) for i in range(3592)]))
  self.assertTrue(s.endswith("ROLLBACK;\n"))
  for required in ("PERSON_FK","VISIT_CONCEPTS","VISIT_STAGE_REPLAY","EXISTING_VISIT_CONTENT","VISIT_DB_READBACK","VISIT_CHECKPOINT_CONFLICT"):
   self.assertIn(required,s)
  self.assertNotIn("DELETE FROM cdm.",s)
 def test_replay_commit_is_explicit(self):
  self.assertTrue(generate(prepare([row(i) for i in range(3592)]),rollback=False).endswith("COMMIT;\n"))
 def test_duplicate_blocked(self):
  with self.assertRaises(RuntimeError):prepare([row(0)]*3592)
 def test_unapproved_visit_class_blocked(self):
  a=[row(i) for i in range(3592)];a[0]["encounter_class"]="unknown"
  with self.assertRaises(RuntimeError):prepare(a)
 def test_inverted_dates_blocked(self):
  a=[row(i) for i in range(3592)];a[0]["end_datetime"]="2026-01-01T11:00:00Z"
  with self.assertRaises(RuntimeError):prepare(a)
 def test_canonical_ntz_assumed_utc(self):
  a=[row(i) for i in range(3592)];a[0]["start_datetime"]="2026-01-01 12:00:00"
  mapped=prepare(a)
  self.assertEqual(mapped[0]['canonical_payload']['visit_start_datetime'],'2026-01-01 12:00:00.000000')
if __name__=="__main__":unittest.main()
