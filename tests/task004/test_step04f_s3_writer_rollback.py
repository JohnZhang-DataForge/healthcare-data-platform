import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
class S3WriterCLI(unittest.TestCase):
 def test_s3_writer_option_and_fail_closed(self):
  text=(ROOT/"apps/task004/cdm_runtime_cli.py").read_text()
  self.assertIn("--rollback-from-s3",text)
  self.assertIn("execute_rollback(supplied,rows,args.rollback_from_s3)",text)
  self.assertIn("rows=read(s3,supplied,args.rollback_from_s3",text)
  self.assertNotIn("allow_commit=True",text)
 def test_existing_executor_always_rollback(self):
  text=(ROOT/"airflow/dags/task004_cdm_postgres_rollback_executor.py").read_text()
  self.assertIn("allow_commit=False",text)
  self.assertIn('sql.endswith("ROLLBACK;',text)
if __name__=="__main__":unittest.main()
