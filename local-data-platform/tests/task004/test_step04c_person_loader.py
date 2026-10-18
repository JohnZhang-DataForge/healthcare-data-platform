from pathlib import Path
import sys,unittest,datetime
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"apps/task004"))
from step04c_person_sql_builder import prepare,generate,BATCH
def row(i):
    return dict(source_record_id="person-%02d"%i,source_batch_id=BATCH,source_system="synthea",source_version="v3.3.0",source_ingest_date="2026-10-12",gender_code="M",race_code="white",ethnicity_code="nonhispanic",birth_date="1990-01-20")
class PersonContract(unittest.TestCase):
    def test_23_and_safe_sql(self):
        people=prepare([row(i) for i in range(23)])
        sql=generate(people,rollback=True)
        self.assertIn("ROLLBACK;",sql)
        self.assertNotIn("\nCOMMIT;",sql)
        for gate in ("CONCEPT_GATE","HISTORIC_CDM_GATE","STAGE_CONFLICT","EXISTING_PERSON_CONFLICT","PERSON_READBACK"):
            self.assertIn(gate,sql)
    def test_explicit_commit(self):
        self.assertTrue(generate(prepare([row(i) for i in range(23)]),rollback=False).endswith("COMMIT;\n"))
    def test_other_race_maps_explicitly_to_unmapped_concept_zero(self):
        a=[row(i) for i in range(23)];a[0]['race_code']='other'
        mapped=prepare(a)
        person=next(v for v in mapped if v['source_key']=='person-00')
        self.assertEqual(person['canonical_payload']['race_concept_id'],0)
        self.assertEqual(person['canonical_payload']['race_source_value'],'other')
    def test_duplicate_key_fail(self):
        with self.assertRaises(RuntimeError):prepare([row(0)]*23)
    def test_unknown_concept_fail(self):
        a=[row(i) for i in range(23)];a[0]["gender_code"]="X"
        with self.assertRaises(RuntimeError):prepare(a)
    def test_wrong_batch_fail(self):
        a=[row(i) for i in range(23)];a[0]["source_batch_id"]="wrong"
        with self.assertRaises(RuntimeError):prepare(a)
if __name__=="__main__":unittest.main()
