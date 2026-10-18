#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1 GIT_PAGER=cat

printf '%s\n' '#### TASK003 STEP05F1 MAPPING SOURCE OUTPUT BEGIN ####'
STAGE=''
finish() {
    rc=$?
    trap - EXIT
    [[ -z "$STAGE" ]] || rm -rf -- "$STAGE"
    echo "INSTALL_EXIT_CODE=$rc"
    echo '#### TASK003 STEP05F1 MAPPING SOURCE OUTPUT END ####'
    exit "$rc"
}
trap finish EXIT

ROOT="${HEALTHCARE_PROJECT_ROOT:-/data/spark/healthcare-data-platform}"
[[ -d "$ROOT/.git" ]] || { echo 'ERROR: project Git repo missing'; exit 1; }
for rel in \
    spark/contracts/canonical/encounter-v1.json \
    spark/contracts/omop/visit-class-v1.json \
    spark/apps/visit/validate_encounter_raw_for_visit.py \
    scripts/task003/05e-validate-visit-raw.sh
do
    [[ -s "$ROOT/$rel" ]] || { echo "ERROR: missing dependency $rel"; exit 1; }
done

STAGE="$(mktemp -d)"
mkdir -p "$STAGE/apps/task003" "$STAGE/spark/apps/visit" \
    "$STAGE/spark/contracts/omop" "$STAGE/tests/task003" "$STAGE/scripts/task003"

cat > "$STAGE/spark/contracts/omop/visit-candidate-v1.json" <<'JSON_CONTRACT'
{
  "contract_name": "omop.visit_candidate",
  "contract_version": "v1",
  "mapping_contract": "spark/contracts/omop/visit-class-v1.json",
  "target_table": "cdm.visit_occurrence",
  "visit_occurrence_id_allocated": false,
  "publish_status": "NOT_PUBLISHED",
  "primary_key": ["source_system", "source_encounter_id"],
  "fields": [
    {"name": "source_system", "type": "string", "nullable": false},
    {"name": "source_encounter_id", "type": "string", "nullable": false},
    {"name": "source_person_id", "type": "string", "nullable": false},
    {"name": "person_id", "type": "integer", "nullable": false},
    {"name": "visit_concept_id", "type": "integer", "nullable": false},
    {"name": "visit_start_date", "type": "date", "nullable": false},
    {"name": "visit_start_datetime", "type": "timestamp", "nullable": false},
    {"name": "visit_end_date", "type": "date", "nullable": false},
    {"name": "visit_end_datetime", "type": "timestamp", "nullable": false},
    {"name": "visit_type_concept_id", "type": "integer", "nullable": false},
    {"name": "provider_id", "type": "integer", "nullable": true},
    {"name": "care_site_id", "type": "integer", "nullable": true},
    {"name": "visit_source_value", "type": "string", "nullable": false},
    {"name": "visit_source_concept_id", "type": "integer", "nullable": true},
    {"name": "admitted_from_concept_id", "type": "integer", "nullable": true},
    {"name": "admitted_from_source_value", "type": "string", "nullable": true},
    {"name": "discharged_to_concept_id", "type": "integer", "nullable": true},
    {"name": "discharged_to_source_value", "type": "string", "nullable": true},
    {"name": "preceding_visit_occurrence_id", "type": "integer", "nullable": true},
    {"name": "encounter_class", "type": "string", "nullable": false},
    {"name": "source_code", "type": "string", "nullable": false},
    {"name": "source_description", "type": "string", "nullable": true},
    {"name": "source_organization_id", "type": "string", "nullable": true},
    {"name": "source_provider_id", "type": "string", "nullable": true},
    {"name": "source_payer_id", "type": "string", "nullable": true},
    {"name": "reason_code", "type": "string", "nullable": true},
    {"name": "reason_description", "type": "string", "nullable": true},
    {"name": "source_version", "type": "string", "nullable": false},
    {"name": "source_batch_id", "type": "string", "nullable": false},
    {"name": "source_ingest_date", "type": "date", "nullable": false},
    {"name": "processing_run_id", "type": "string", "nullable": false},
    {"name": "raw_publish_run_id", "type": "string", "nullable": false},
    {"name": "canonical_version", "type": "string", "nullable": false},
    {"name": "source_file", "type": "string", "nullable": false},
    {"name": "source_file_sha256", "type": "string", "nullable": false},
    {"name": "source_file_size_bytes", "type": "long", "nullable": false}
  ]
}
JSON_CONTRACT

cat > "$STAGE/apps/task003/visit_candidate_rules.py" <<'PY_RULES'
"""Pure-Python rules for TASK003 Encounter -> Visit Candidate (no I/O)."""

DEFERRED_FIELDS = (
    'provider_id', 'care_site_id', 'admitted_from_concept_id',
    'admitted_from_source_value', 'discharged_to_concept_id',
    'discharged_to_source_value', 'preceding_visit_occurrence_id',
)
PRESERVED_SOURCE = (
    'source_code', 'source_description', 'source_organization_id',
    'source_provider_id', 'source_payer_id', 'reason_code',
    'reason_description',
)


def validate_rules(mapping, raw_contract, candidate_contract):
    if mapping.get('visit_model', {}).get('mode') != 'one_source_encounter_per_visit_occurrence':
        raise ValueError('Unexpected Visit cardinality')
    if mapping['visit_model'].get('aggregation') is not False:
        raise ValueError('Aggregation is not supported')
    if mapping['visit_model'].get('stable_id_map') != 'etl.visit_occurrence_id_map':
        raise ValueError('Unexpected Visit ID map')
    if mapping.get('source_system') != 'synthea' or mapping.get('source_version') != 'v3.3.0':
        raise ValueError('Unexpected source contract')
    if mapping.get('visit_source_value') != 'encounter_class':
        raise ValueError('visit_source_value must use encounter_class')
    if mapping.get('visit_source_concept_id') is not None:
        raise ValueError('visit_source_concept_id must remain NULL')
    if mapping.get('visit_type_concept_id') != 32827:
        raise ValueError('Unexpected visit type concept')
    if tuple(mapping.get('deferred_target_fields', ())) != DEFERRED_FIELDS:
        raise ValueError('Deferred target fields changed')
    if tuple(mapping.get('source_fields_preserved_for_future_mapping', ())) != PRESERVED_SOURCE:
        raise ValueError('Preserved source fields changed')

    if raw_contract.get('entity') != 'encounter' or raw_contract.get('canonical_version') != 'v1':
        raise ValueError('Unexpected canonical Encounter contract')
    raw_names = {x['name'] for x in raw_contract['fields']}
    if len(raw_names) != len(raw_contract['fields']):
        raise ValueError('Duplicate Raw field')
    if not set(PRESERVED_SOURCE).issubset(raw_names):
        raise ValueError('Missing preserved Raw source fields')
    if raw_contract.get('primary_key') != ['source_system', 'source_encounter_id']:
        raise ValueError('Unexpected Raw primary key')

    classes = mapping.get('class_to_visit_concept')
    if not isinstance(classes, dict) or set(classes) != set(raw_contract['allowed_encounter_classes']):
        raise ValueError('Raw and Visit class mappings disagree')
    for key, value in classes.items():
        concept = value.get('concept_id') if isinstance(value, dict) else None
        if type(concept) is not int or concept <= 0:
            raise ValueError('Invalid Visit concept for ' + key)

    if candidate_contract.get('contract_version') != 'v1':
        raise ValueError('Unknown candidate contract version')
    if candidate_contract.get('target_table') != 'cdm.visit_occurrence':
        raise ValueError('Unexpected target table')
    if candidate_contract.get('visit_occurrence_id_allocated') is not False:
        raise ValueError('Candidate must not allocate Visit ID')
    if candidate_contract.get('publish_status') != 'NOT_PUBLISHED':
        raise ValueError('Candidate source must not claim to be published')
    if candidate_contract.get('primary_key') != ['source_system', 'source_encounter_id']:
        raise ValueError('Unexpected candidate key')

    fields = candidate_contract['fields']
    names = [item['name'] for item in fields]
    if len(names) != len(set(names)):
        raise ValueError('Duplicate candidate field')
    if 'visit_occurrence_id' in names:
        raise ValueError('Premature Visit ID in candidate schema')
    if not {'person_id', 'visit_concept_id', 'visit_start_date',
            'visit_end_date', 'visit_type_concept_id'}.issubset(names):
        raise ValueError('Missing required OMOP Visit fields')
    if not set(DEFERRED_FIELDS).issubset(names):
        raise ValueError('Missing nullable deferred Visit fields')
    if not set(PRESERVED_SOURCE).issubset(names):
        raise ValueError('Missing preserved source field')
    if not set(names).issubset(raw_names | {
        'person_id', 'raw_publish_run_id', 'visit_concept_id',
        'visit_start_date', 'visit_start_datetime',
        'visit_end_date', 'visit_end_datetime', 'visit_type_concept_id',
        'visit_source_value', 'visit_source_concept_id',
        *DEFERRED_FIELDS,
    }):
        raise ValueError('Unexpected candidate field')
    valid_types = {'string', 'integer', 'date', 'timestamp', 'long'}
    for item in fields:
        if item.get('type') not in valid_types or type(item.get('nullable')) is not bool:
            raise ValueError('Invalid candidate schema field')
        if item['name'] in DEFERRED_FIELDS and item['nullable'] is not True:
            raise ValueError('Deferred field must be nullable')
    return {key: value['concept_id'] for key, value in classes.items()}
PY_RULES

cat > "$STAGE/spark/apps/visit/map_encounter_to_visit_candidate.py" <<'PY_SPARK'
"""Pure PySpark DataFrame transform. No Spark job startup or storage writes.

The caller must verify APPROVED Raw, pinned contracts, JDBC Person mapping,
concept validity and counts before publishing the returned candidate DataFrame.
"""


DEFERRED_TYPES = {
    'provider_id': 'int', 'care_site_id': 'int',
    'visit_source_concept_id': 'int',
    'admitted_from_concept_id': 'int',
    'admitted_from_source_value': 'string',
    'discharged_to_concept_id': 'int',
    'discharged_to_source_value': 'string',
    'preceding_visit_occurrence_id': 'int',
}


def map_encounter_to_candidate(raw, persons, mapping, context):
    """Return one unapproved candidate row per raw Encounter; no I/O or writes.

    persons must contain source_system, source_person_id, person_id.
    The caller must verify the Person map/CDM FK and one-to-one join.
    """
    from pyspark.sql import functions as F

    if context['mapping_contract_sha256'] is None:
        raise ValueError('Missing pinned mapping contract SHA')
    mapping_ids = mapping['class_to_visit_concept']
    pairs = []
    for klass, info in sorted(mapping_ids.items()):
        pairs.extend((F.lit(klass), F.lit(info['concept_id'])))
    visit_concept = F.element_at(F.create_map(*pairs), F.col('encounter_class'))

    person_reference = persons.select('source_system', 'source_person_id', 'person_id')
    joined = raw.join(
        person_reference, ['source_system', 'source_person_id'], 'left'
    )
    fields = [
        F.col('source_system'),
        F.col('source_encounter_id'),
        F.col('source_person_id'),
        F.col('person_id').cast('int').alias('person_id'),
        visit_concept.cast('int').alias('visit_concept_id'),
        F.to_date('start_datetime').alias('visit_start_date'),
        F.col('start_datetime').cast('timestamp').alias('visit_start_datetime'),
        F.to_date('end_datetime').alias('visit_end_date'),
        F.col('end_datetime').cast('timestamp').alias('visit_end_datetime'),
        F.lit(mapping['visit_type_concept_id']).cast('int').alias('visit_type_concept_id'),
        F.lit(None).cast('int').alias('provider_id'),
        F.lit(None).cast('int').alias('care_site_id'),
        F.col('encounter_class').alias('visit_source_value'),
        F.lit(None).cast('int').alias('visit_source_concept_id'),
        F.lit(None).cast('int').alias('admitted_from_concept_id'),
        F.lit(None).cast('string').alias('admitted_from_source_value'),
        F.lit(None).cast('int').alias('discharged_to_concept_id'),
        F.lit(None).cast('string').alias('discharged_to_source_value'),
        F.lit(None).cast('int').alias('preceding_visit_occurrence_id'),
        F.col('encounter_class'),
        F.col('source_code'),
        F.col('source_description'),
        F.col('source_organization_id'),
        F.col('source_provider_id'),
        F.col('source_payer_id'),
        F.col('reason_code'),
        F.col('reason_description'),
        F.col('source_version'),
        F.col('source_batch_id'),
        F.col('source_ingest_date'),
        F.col('processing_run_id'),
        F.lit(context['raw_publish_run_id']).alias('raw_publish_run_id'),
        F.col('canonical_version'),
        F.col('source_file'),
        F.col('source_file_sha256'),
        F.col('source_file_size_bytes'),
    ]
    return joined.select(*fields)
PY_SPARK

cat > "$STAGE/tests/task003/test_visit_candidate_rules.py" <<'PY_TEST'
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
PY_TEST

# Verify generated candidate schema covers exactly the Spark output projection.
python3 - "$STAGE" <<'PY_VERIFY'
import ast
import json
import sys
from pathlib import Path

base = Path(sys.argv[1])
contract = json.loads((base / 'spark/contracts/omop/visit-candidate-v1.json').read_text())
path = base / 'spark/apps/visit/map_encounter_to_visit_candidate.py'
tree = ast.parse(path.read_text())
func = next(n for n in tree.body if isinstance(n, ast.FunctionDef))
fields = next(n for n in ast.walk(func) if isinstance(n, ast.Assign)
              and any(isinstance(t, ast.Name) and t.id == 'fields' for t in n.targets))
projected = []
for n in fields.value.elts:
    if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'alias':
        projected.append(n.args[0].value)
    elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'col':
        projected.append(n.args[0].value)
    else:
        raise ValueError('Unknown Spark projection expression')
expected = [x['name'] for x in contract['fields']]
if projected != expected:
    raise ValueError('Candidate contract and Spark projection order differ: ' + repr((projected, expected)))
print('CANDIDATE_PROJECTION_CONTRACT=PASS')
PY_VERIFY

# Unit tests run against stage files and immutable existing contracts.
mkdir -p "$STAGE/spark/contracts/canonical"
cp -- "$ROOT/spark/contracts/canonical/encounter-v1.json" \
      "$STAGE/spark/contracts/canonical/encounter-v1.json"
cp -- "$ROOT/spark/contracts/omop/visit-class-v1.json" \
      "$STAGE/spark/contracts/omop/visit-class-v1.json"
python3 -m compileall -q "$STAGE/apps" "$STAGE/spark/apps" "$STAGE/tests"
PYTHONPATH="$STAGE/apps/task003" \
python3 -m unittest discover -s "$STAGE/tests/task003" \
    -p 'test_visit_candidate_rules.py' -v

# Only allow identical re-installation; no silent overwrite of existing work.
FILES=(
    apps/task003/visit_candidate_rules.py
    spark/apps/visit/map_encounter_to_visit_candidate.py
    spark/contracts/omop/visit-candidate-v1.json
    tests/task003/test_visit_candidate_rules.py
)
for rel in "${FILES[@]}"; do
    if [[ -L "$ROOT/$rel" ]] || {
        [[ -e "$ROOT/$rel" ]] && ! cmp -s "$STAGE/$rel" "$ROOT/$rel"
    }; then
        echo "ERROR: existing canonical source conflicts: $rel"
        exit 1
    fi
done

GENERATOR=scripts/task003/05f-prepare-visit-candidate-mapping.sh
if [[ -L "$ROOT/$GENERATOR" ]] || {
    [[ -e "$ROOT/$GENERATOR" ]] && ! cmp -s "${BASH_SOURCE[0]}" "$ROOT/$GENERATOR"
}; then
    echo 'ERROR: canonical generator conflicts'
    exit 1
fi

for rel in "${FILES[@]}"; do
    mkdir -p "$(dirname "$ROOT/$rel")"
    install -m 644 "$STAGE/$rel" "$ROOT/$rel"
    echo "CANONICAL_SOURCE_READY=$rel"
done
mkdir -p "$ROOT/scripts/task003"
install -m 755 "${BASH_SOURCE[0]}" "$ROOT/$GENERATOR"
echo "CANONICAL_GENERATOR_READY=$GENERATOR"
echo 'STEP05F1_LOCAL_SOURCE_AND_TESTS=PASS'
echo 'SPARK_APPLICATION_SUBMITTED=NO'
echo 'IDS_ALLOCATED=0'
echo 'S3_WRITE=NO'
echo 'DATABASE_WRITE=NO'
echo 'GIT_COMMIT=NO'
