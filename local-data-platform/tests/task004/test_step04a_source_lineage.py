"""Source lineage script must remain read-only and pinned to accepted batch."""
from pathlib import Path
import ast
import unittest
P=Path(__file__).resolve().parents[2]/"apps/task004/step04a_inspect_airflow_log_lineage.py"
class Contract(unittest.TestCase):
    def test_syntax(self): ast.parse(P.read_text())
    def test_accepted_batch(self):
        t=P.read_text()
        self.assertIn("task004-step03e-38324111846",t)
        self.assertIn("SOURCE_DATA_READBACK=NOT_RUN",t)
        self.assertIn("POSTGRESQL_MUTATION=NO",t)
    def test_no_side_effects(self):
        t=P.read_text()
        for x in ("subprocess","os.system","kubectl","psycopg","boto3","write_text(","unlink(","rmtree("):
            self.assertNotIn(x,t)
if __name__=="__main__": unittest.main()
