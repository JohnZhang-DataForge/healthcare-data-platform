"""Static safety contract for STEP04A source-to-PostgreSQL read-only comparison."""
import ast
from pathlib import Path
import unittest
P=Path(__file__).resolve().parents[2]/"apps/task004/step04a_compare_source_postgres_readonly.py"
class ReadonlyContract(unittest.TestCase):
    def test_syntax(self): ast.parse(P.read_text())
    def test_batch_and_identity(self):
        t=P.read_text()
        self.assertIn("task004-step03e-38324111846",t)
        self.assertIn("ecc7cf3b75240e530f2cc96635b25e4eaf0794403e1b04d50d2248cd3aaa5cb1",t)
        self.assertIn("TRANSACTION READ ONLY",t)
        self.assertIn("EXISTING_CONTENT_CONFLICT_GATE=UNASSESSED",t)
    def test_no_database_or_cluster_mutation(self):
        t=P.read_text()
        for forbidden in ("INSERT INTO","UPDATE etl.","DELETE FROM","CREATE TABLE",
                          "kubectl apply","kubectl create","kubectl delete","airflow dags trigger"):
            self.assertNotIn(forbidden,t)
    def test_privacy_only_aggregates(self):
        t=P.read_text()
        self.assertIn("_EXISTING_MAPPING=",t)
        self.assertIn("_NEW_MAPPING_NEEDED=",t)
        self.assertNotIn("print(keys)",t)
        self.assertNotIn("print(db)",t)
if __name__=="__main__":unittest.main()
