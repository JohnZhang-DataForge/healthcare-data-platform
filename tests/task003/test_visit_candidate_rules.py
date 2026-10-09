import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'apps/task003'))
from visit_candidate_rules import validate_rules


class CandidateRulesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        def read(rel):
            return json.loads((ROOT / rel).read_text(encoding='utf-8'))
        cls.mapping = read('spark/contracts/omop/visit-class-v1.json')
        cls.raw = read('spark/contracts/canonical/encounter-v1.json')
        cls.candidate = read('spark/contracts/omop/visit-candidate-v1.json')

    def check_rejected(self, mutate):
        mapping, raw, candidate = map(copy.deepcopy, (
            self.mapping, self.raw, self.candidate))
        mutate(mapping, raw, candidate)
        with self.assertRaises(ValueError):
            validate_rules(mapping, raw, candidate)

    def test_contract_positive_and_expected_classes(self):
        classes = validate_rules(self.mapping, self.raw, self.candidate)
        self.assertEqual(len(classes), 10)
        self.assertEqual(classes['emergency'], 9203)
        self.assertEqual(classes['virtual'], 722455)
        self.assertEqual(classes['inpatient'], 9201)

    def test_disallow_aggregation(self):
        self.check_rejected(lambda m,r,c: m['visit_model'].update(aggregation=True))

    def test_missing_class(self):
        self.check_rejected(lambda m,r,c: m['class_to_visit_concept'].pop('urgentcare'))

    def test_invalid_concept(self):
        self.check_rejected(lambda m,r,c: m['class_to_visit_concept']['home'].update(concept_id=0))

    def test_wrong_source_value(self):
        self.check_rejected(lambda m,r,c: m.update(visit_source_value='source_code'))

    def test_bad_visit_type(self):
        self.check_rejected(lambda m,r,c: m.update(visit_type_concept_id=0))

    def test_id_allocation_early(self):
        self.check_rejected(lambda m,r,c: c.update(visit_occurrence_id_allocated=True))

    def test_no_missing_candidate_key(self):
        self.check_rejected(lambda m,r,c: c.update(primary_key=['person_id']))

    def test_no_duplicate_candidate_field(self):
        self.check_rejected(lambda m,r,c: c['fields'].append(copy.deepcopy(c['fields'][0])))

    def test_deferred_field_nullable(self):
        def mutate(m,r,c):
            next(x for x in c['fields'] if x['name'] == 'provider_id')['nullable'] = False
        self.check_rejected(mutate)

    def test_preserved_source_field(self):
        def mutate(m,r,c):
            c['fields'][:] = [x for x in c['fields'] if x['name'] != 'reason_code']
        self.check_rejected(mutate)

    def test_candidate_field_order_matches_mapper_projection(self):
        # Verify the AST of the PySpark function without requiring local PySpark.
        import ast
        path = ROOT / 'spark/apps/visit/map_encounter_to_visit_candidate.py'
        tree = ast.parse(path.read_text(encoding='utf-8'))
        calls = [n for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                 and n.func.attr == 'alias' and n.args and isinstance(n.args[0], ast.Constant)]
        aliases = {n.args[0].value for n in calls}
        candidate = {x['name'] for x in self.candidate['fields']}
        self.assertTrue(aliases.issubset(candidate))
        self.assertNotIn('visit_occurrence_id', candidate)


if __name__ == '__main__':
    unittest.main()
