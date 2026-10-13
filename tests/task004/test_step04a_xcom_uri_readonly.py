from pathlib import Path
import ast
import unittest
P=Path(__file__).resolve().parents[2]/"apps/task004/step04a_xcom_uri_readonly.py"
class Contract(unittest.TestCase):
    def test_source_syntax(self): ast.parse(P.read_text())
    def test_pinned_batch(self):
        t=P.read_text()
        self.assertIn("task004-step03e-38324111846",t)
        self.assertIn("XCom.get_one(",t)
        self.assertIn("DATA_MUTATION=NO",t)
    def test_no_mutation(self):
        t=P.read_text()
        for word in ("XCom.set(","session.commit(","session.add(","kubectl","subprocess"):
            self.assertNotIn(word,t)
if __name__=="__main__": unittest.main()
