import os,sys,unittest
from unittest.mock import patch,MagicMock
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"airflow/dags"))
from task004_cdm_postgres_rollback_executor import execute_rollback
class Tests(unittest.TestCase):
 def test_reject_reader(self):
  with patch.dict(os.environ,{"PGUSER":"cdm_reader","PGHOST":"h","PGPORT":"5432","PGPASSWORD":"p"},clear=True):
   with self.assertRaisesRegex(ValueError,"writer_identity"):execute_rollback({},[],"person")
 def test_missing_secret(self):
  with patch.dict(os.environ,{"PGUSER":"cdm_writer"},clear=True):
   with self.assertRaisesRegex(ValueError,"writer_connection"):execute_rollback({},[],"person")
 def test_reject_nonrollback_sql(self):
  with patch.dict(os.environ,{"PGUSER":"cdm_writer","PGHOST":"h","PGPORT":"5432","PGPASSWORD":"p"},clear=True),patch("task004_cdm_postgres_rollback_executor.render",return_value="COMMIT;\n"):
   with self.assertRaisesRegex(ValueError,"nonrollback_sql"):execute_rollback({},[{}],"person")
 def test_reject_meta_commands(self):
  with patch.dict(os.environ,{"PGUSER":"cdm_writer","PGHOST":"h","PGPORT":"5432","PGPASSWORD":"p"},clear=True),patch("task004_cdm_postgres_rollback_executor.render",return_value="SELECT 1;\nROLLBACK;\n"):
   with self.assertRaisesRegex(ValueError,"unrecognized_sql"):execute_rollback({},[{}],"person")
 def test_container_contains_executor(self):
  d=(ROOT/"images/task004-cdm-runtime/Dockerfile").read_text()
  self.assertIn("task004_cdm_postgres_rollback_executor.py",d)
  cli=(ROOT/"apps/task004/cdm_runtime_cli.py").read_text()
  self.assertIn("--rollback-entity",cli)
  self.assertNotIn("allow_commit=True",cli)
if __name__=="__main__":unittest.main()
