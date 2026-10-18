import pathlib,sys,unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"airflow/dags"))
from task004_cdm_postgres_readonly import validate_readonly
class PgReadOnly(unittest.TestCase):
 def test_missing_secret(self):
  with patch.dict("os.environ",{},clear=True):
   with self.assertRaisesRegex(ValueError,"postgres_credentials"):validate_readonly({"batch_id":"x"})
 def test_wrong_principal(self):
  with patch.dict("os.environ",{"PGHOST":"example","PGPORT":"5432","PGUSER":"omop_admin","PGPASSWORD":"secret"},clear=True):
   with self.assertRaisesRegex(ValueError,"postgres_principal"):validate_readonly({"batch_id":"x"})
 def test_image_packaging(self):
  d=(ROOT/"images/task004-cdm-runtime/Dockerfile").read_text()
  self.assertIn("psycopg[binary]",d)
  self.assertIn("task004_cdm_postgres_readonly.py",d)
  cli=(ROOT/"apps/task004/cdm_runtime_cli.py").read_text()
  self.assertIn("--validate-postgres",cli)
  self.assertNotIn("allow_commit=True",cli)
if __name__=="__main__":unittest.main()
