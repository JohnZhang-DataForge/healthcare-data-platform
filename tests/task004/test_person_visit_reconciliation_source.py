import ast,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
class T(unittest.TestCase):
 def test_python_parses(self):
  ast.parse((ROOT/"spark/apps/task004/reconcile_person_visit.py").read_text())
 def test_wrapper_is_additive_read_only_reconciliation(self):
  s=(ROOT/"scripts/task004/05f-reconcile-person-visit.sh").read_text()
  self.assertIn("BATCH_RECONCILIATION=PASS",s)
  self.assertIn("POSTGRESQL_MUTATION=NO",s)
  self.assertNotIn("psql ",s)
  self.assertNotIn(".write.",(ROOT/"spark/apps/task004/reconcile_person_visit.py").read_text())
 def test_template_is_task004(self):
  s=(ROOT/"spark/manifests/task004/person-visit-reconciliation.yaml.tpl").read_text()
  self.assertIn("healthcare-task: task004",s)
  self.assertIn("reconcile_person_visit.py",s)
