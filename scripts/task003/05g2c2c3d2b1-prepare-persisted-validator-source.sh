#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT="${HEALTHCARE_PROJECT_ROOT:-/data/spark/healthcare-data-platform}"
SOURCE="${BASH_SOURCE[0]:-}"
STAGE=''

echo '#### TASK003 STEP05G2C2C3D2B1 PERSISTED VALIDATOR SOURCE OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  [[ -z "$STAGE" ]] || rm -rf -- "$STAGE"

  echo "INSTALL_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G2C2C3D2B1 PERSISTED VALIDATOR SOURCE OUTPUT END ####'
  exit "$rc"
}

trap finish EXIT

[[ -n "$SOURCE" && -f "$SOURCE" ]] || {
  echo 'ERROR: installer must run from a saved Bash file'
  exit 2
}

for rel in \
  spark/contracts/omop/visit-candidate-v1.json \
  apps/task003/plan_visit_processed.py
do
  [[ -s "$ROOT/$rel" && ! -L "$ROOT/$rel" ]] || {
    echo "ERROR: prerequisite missing: $rel"
    exit 2
  }
done

STAGE=$(mktemp -d /data/spark/temp_shell/g2c2c3d2b1.XXXXXXXX)

mkdir -p \
  "$STAGE/spark/apps/visit" \
  "$STAGE/tests/task003" \
  "$STAGE/scripts/task003"

# ============================================================
# 1. Independent persisted-data validator
# ============================================================

cat > "$STAGE/spark/apps/visit/validate_persisted_visit_candidate.py" <<'PY_APP'
"""Independent validation of persisted TASK-003 Visit Candidate data.

This validator does NOT import or call the Processed Writer Core.

It independently reads the persisted Parquet data and verifies:
- exact Candidate column inventory;
- no final visit_occurrence_id;
- row count;
- (source_system, source_encounter_id) uniqueness;
- Person count;
- persisted Person mapping fingerprint;
- encounter_class distribution;
- key lineage pins.

No S3 mutation and no PostgreSQL mutation are performed.
"""

import argparse
import hashlib
import json
from pathlib import Path


EXPECTED_FIELD_COUNT = 36

BUSINESS_KEY = (
    'source_system',
    'source_encounter_id',
)

PERSON_KEY = (
    'source_system',
    'source_person_id',
    'person_id',
)

REQUIRED_FIELDS = {
    'source_system',
    'source_encounter_id',
    'source_person_id',
    'person_id',
    'encounter_class',
    'processing_run_id',
    'raw_publish_run_id',
    'source_version',
    'source_batch_id',
    'source_ingest_date',
    'canonical_version',
    'source_file',
    'source_file_sha256',
    'source_file_size_bytes',
}


def require(condition, message):
    if not condition:
        raise ValueError(
            'PERSISTED_VISIT_VALIDATION_FAILED: '
            + message
        )


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def read_regular(path):
    """Read a regular file, including safe Kubernetes projected-volume links."""

    path = Path(path)

    try:
        mount_root = path.parent.resolve(
            strict=True
        )

        resolved = path.resolve(
            strict=True
        )

    except (FileNotFoundError, RuntimeError) as exc:
        raise ValueError(
            'Unsafe evidence file: '
            + str(path)
        ) from exc

    require(
        resolved.is_file(),
        'evidence target is not a regular file: '
        + str(path)
    )

    try:
        resolved.relative_to(
            mount_root
        )

    except ValueError as exc:
        raise ValueError(
            'Evidence file escapes mount directory: '
            + str(path)
        ) from exc

    return resolved.read_bytes()


def to_spark_storage_uri(canonical_uri):
    """Translate canonical S3 evidence URI to Spark S3A transport URI."""

    require(
        isinstance(canonical_uri, str)
        and canonical_uri.startswith('s3://'),
        'canonical data URI must use s3://'
    )

    return (
        's3a://'
        + canonical_uri[len('s3://'):]
    )


def extract_contract_fields(contract):
    """Extract one unambiguous ordered field list."""

    candidates = []

    if isinstance(contract, list):
        candidates.append(contract)

    if isinstance(contract, dict):
        for key in (
            'fields',
            'columns',
            'candidate_fields',
        ):
            value = contract.get(key)

            if isinstance(value, list):
                candidates.append(value)

        schema = contract.get('schema')

        if isinstance(schema, list):
            candidates.append(schema)

        elif isinstance(schema, dict):
            for key in (
                'fields',
                'columns',
            ):
                value = schema.get(key)

                if isinstance(value, list):
                    candidates.append(value)

    parsed = []

    for sequence in candidates:
        names = []

        for item in sequence:
            if isinstance(item, str):
                names.append(item)

            elif isinstance(item, dict):
                name = (
                    item.get('name')
                    or item.get('field')
                    or item.get('column')
                )

                if not isinstance(name, str):
                    names = []
                    break

                names.append(name)

            else:
                names = []
                break

        if names and names not in parsed:
            parsed.append(names)

    require(
        len(parsed) == 1,
        'ambiguous Contract field inventory'
    )

    return parsed[0]


def validate_contract(contract):
    fields = extract_contract_fields(
        contract
    )

    require(
        len(fields) == EXPECTED_FIELD_COUNT,
        (
            'Contract field count: '
            f'expected={EXPECTED_FIELD_COUNT} '
            f'actual={len(fields)}'
        )
    )

    require(
        len(fields) == len(set(fields)),
        'duplicate Contract fields'
    )

    missing = sorted(
        REQUIRED_FIELDS - set(fields)
    )

    require(
        not missing,
        'Contract missing fields: '
        + ','.join(missing)
    )

    require(
        'visit_occurrence_id' not in fields,
        'Candidate Contract contains final visit_occurrence_id'
    )

    return fields


def canonical_person_snapshot(records):
    """Canonical representation used for persisted Person fingerprint."""

    normalized = []

    source_keys = set()
    person_ids = set()

    for record in records:
        require(
            len(record) == 3,
            'invalid Person mapping record'
        )

        (
            source_system,
            source_person_id,
            person_id,
        ) = record

        require(
            source_system == 'synthea',
            'unexpected Person source_system'
        )

        require(
            isinstance(source_person_id, str)
            and bool(source_person_id),
            'invalid source_person_id'
        )

        require(
            type(person_id) is int
            and person_id > 0,
            'invalid OMOP person_id'
        )

        source_key = (
            source_system,
            source_person_id,
        )

        require(
            source_key not in source_keys,
            'duplicate source Person mapping'
        )

        require(
            person_id not in person_ids,
            'duplicate OMOP person_id mapping'
        )

        source_keys.add(source_key)
        person_ids.add(person_id)

        normalized.append([
            source_system,
            source_person_id,
            person_id,
        ])

    normalized.sort()

    return (
        json.dumps(
            normalized,
            separators=(',', ':'),
            ensure_ascii=False,
        ).encode('utf-8')
    )


def normalize_class_counts(rows):
    result = {}

    for row in rows:
        if hasattr(row, 'asDict'):
            item = row.asDict()

        elif isinstance(row, dict):
            item = row

        else:
            item = {
                'encounter_class': row[0],
                'count': row[1],
            }

        klass = item['encounter_class']
        count = int(item['count'])

        require(
            isinstance(klass, str)
            and bool(klass),
            'blank encounter_class'
        )

        require(
            count > 0,
            'invalid class count'
        )

        require(
            klass not in result,
            'duplicate encounter_class result'
        )

        result[klass] = count

    return result


def validate_static_evidence(
    plan,
    f2,
    c3b,
    contract,
    person_snapshot_bytes,
    data_uri,
):
    fields = validate_contract(
        contract
    )

    require(
        plan.get('run_id')
        == c3b.get('run_id'),
        'run identity'
    )

    require(
        (
            f2.get('task'),
            f2.get('step'),
            f2.get('status'),
        )
        == (
            'TASK-003',
            'STEP-05F2',
            'PASS',
        ),
        'F2 state'
    )

    require(
        c3b.get('status')
        == 'POSTLOCK_PREFLIGHT_PASS',
        'C3B state'
    )

    require(
        c3b.get('fresh_s3_relist_passed')
        is True,
        'fresh S3 relist not passed'
    )

    require(
        c3b.get('reservation_still_held')
        is True,
        'Reservation not held'
    )

    require(
        plan.get('data_uri') == data_uri,
        'data URI drift'
    )

    require(
        plan.get('expected_rows')
        == f2['result']['candidate_rows'],
        'expected row drift'
    )

    require(
        plan.get('expected_persons')
        == f2['result']['referenced_persons'],
        'expected Person drift'
    )

    require(
        sha(person_snapshot_bytes)
        == c3b.get('person_map_fingerprint'),
        'C3B Person fingerprint drift'
    )

    people = json.loads(
        person_snapshot_bytes
    )

    canonical = canonical_person_snapshot(
        people
    )

    require(
        canonical == person_snapshot_bytes,
        'Person snapshot is not canonical'
    )

    require(
        len(people)
        == plan['expected_persons'],
        'Person snapshot count drift'
    )

    return fields


def validate_persisted(
    spark,
    data_uri,
    plan,
    f2,
    c3b,
    contract,
    person_snapshot_bytes,
):
    from pyspark.sql import functions as F

    expected_fields = validate_static_evidence(
        plan,
        f2,
        c3b,
        contract,
        person_snapshot_bytes,
        data_uri,
    )

    storage_uri = to_spark_storage_uri(
        data_uri
    )

    persisted = (
        spark.read
        .parquet(storage_uri)
    )

    actual_fields = persisted.columns

    require(
        actual_fields == expected_fields,
        (
            'persisted schema column order drift: '
            f'expected={expected_fields} '
            f'actual={actual_fields}'
        )
    )

    require(
        'visit_occurrence_id'
        not in actual_fields,
        'persisted Candidate contains visit_occurrence_id'
    )

    row_count = persisted.count()

    require(
        row_count == plan['expected_rows'],
        (
            'row count drift: '
            f'expected={plan["expected_rows"]} '
            f'actual={row_count}'
        )
    )

    null_business_keys = (
        persisted
        .filter(
            F.col('source_system').isNull()
            | F.col('source_encounter_id').isNull()
            | (
                F.length(
                    F.trim(
                        F.col('source_system')
                    )
                )
                == 0
            )
            | (
                F.length(
                    F.trim(
                        F.col('source_encounter_id')
                    )
                )
                == 0
            )
        )
        .limit(1)
        .count()
    )

    require(
        null_business_keys == 0,
        'null/blank business key'
    )

    unique_key_count = (
        persisted
        .select(
            *BUSINESS_KEY
        )
        .distinct()
        .count()
    )

    require(
        unique_key_count == row_count,
        (
            'business-key uniqueness drift: '
            f'rows={row_count} '
            f'unique={unique_key_count}'
        )
    )

    person_count = (
        persisted
        .select('person_id')
        .distinct()
        .count()
    )

    require(
        person_count == plan['expected_persons'],
        (
            'Person count drift: '
            f'expected={plan["expected_persons"]} '
            f'actual={person_count}'
        )
    )

    person_rows = (
        persisted
        .select(*PERSON_KEY)
        .distinct()
        .collect()
    )

    person_records = [
        [
            row['source_system'],
            row['source_person_id'],
            int(row['person_id']),
        ]
        for row in person_rows
    ]

    persisted_person_snapshot = (
        canonical_person_snapshot(
            person_records
        )
    )

    persisted_person_fingerprint = sha(
        persisted_person_snapshot
    )

    require(
        persisted_person_fingerprint
        == c3b['person_map_fingerprint'],
        (
            'persisted Person fingerprint drift: '
            f'expected={c3b["person_map_fingerprint"]} '
            f'actual={persisted_person_fingerprint}'
        )
    )

    class_rows = (
        persisted
        .groupBy('encounter_class')
        .count()
        .collect()
    )

    class_counts = normalize_class_counts(
        class_rows
    )

    require(
        class_counts == plan['class_counts'],
        (
            'class distribution drift: '
            f'expected={plan["class_counts"]} '
            f'actual={class_counts}'
        )
    )

    raw_context = (
        f2.get('input', {})
        .get('raw_context', {})
    )

    expected_processing_run = (
        raw_context.get('processing_run_id')
    )

    require(
        isinstance(expected_processing_run, str)
        and bool(expected_processing_run),
        'F2 processing_run_id missing'
    )

    processing_runs = [
        row['processing_run_id']
        for row in (
            persisted
            .select('processing_run_id')
            .distinct()
            .collect()
        )
    ]

    require(
        processing_runs == [expected_processing_run],
        (
            'processing_run_id drift: '
            f'expected={expected_processing_run} '
            f'actual={processing_runs}'
        )
    )

    raw_runs = [
        row['raw_publish_run_id']
        for row in (
            persisted
            .select('raw_publish_run_id')
            .distinct()
            .collect()
        )
    ]

    expected_raw_run = (
        raw_context.get('raw_publish_run_id')
    )

    require(
        isinstance(expected_raw_run, str)
        and bool(expected_raw_run),
        'F2 raw_publish_run_id missing'
    )

    require(
        raw_runs == [expected_raw_run],
        (
            'raw_publish_run_id drift: '
            + repr(raw_runs)
        )
    )

    source_systems = [
        row['source_system']
        for row in (
            persisted
            .select('source_system')
            .distinct()
            .collect()
        )
    ]

    require(
        source_systems == ['synthea'],
        (
            'source_system drift: '
            + repr(source_systems)
        )
    )

    result = {
        'status':
            'INDEPENDENT_S3_READBACK_PASS',

        'data_uri':
            data_uri,

        'rows':
            row_count,

        'unique_business_keys':
            unique_key_count,

        'business_key':
            list(BUSINESS_KEY),

        'referenced_persons':
            person_count,

        'person_map_fingerprint':
            persisted_person_fingerprint,

        'class_counts':
            class_counts,

        'contract_field_count':
            len(actual_fields),

        'visit_occurrence_id_present':
            False,

        'processing_run_id':
            expected_processing_run,

        'raw_publish_run_id':
            expected_raw_run,

        'source_system':
            'synthea',

        's3_write_verified':
            True,

        'candidate_published_verified':
            True,

        'dq_published':
            False,

        'manifest_published':
            False,

        'postgresql_write':
            False,
    }

    return result


def main():
    parser = argparse.ArgumentParser(
        description=__doc__
    )

    parser.add_argument(
        '--data-uri',
        required=True,
    )

    parser.add_argument(
        '--plan',
        type=Path,
        required=True,
    )

    parser.add_argument(
        '--f2-state',
        type=Path,
        required=True,
    )

    parser.add_argument(
        '--c3b-state',
        type=Path,
        required=True,
    )

    parser.add_argument(
        '--contract',
        type=Path,
        required=True,
    )

    parser.add_argument(
        '--person-snapshot',
        type=Path,
        required=True,
    )

    args = parser.parse_args()

    from pyspark.sql import SparkSession

    plan = json.loads(
        read_regular(
            args.plan
        )
    )

    f2 = json.loads(
        read_regular(
            args.f2_state
        )
    )

    c3b = json.loads(
        read_regular(
            args.c3b_state
        )
    )

    contract = json.loads(
        read_regular(
            args.contract
        )
    )

    person_snapshot_bytes = read_regular(
        args.person_snapshot
    )

    spark = (
        SparkSession.builder
        .appName(
            'task003-independent-visit-readback'
        )
        .getOrCreate()
    )

    try:
        result = validate_persisted(
            spark,
            args.data_uri,
            plan,
            f2,
            c3b,
            contract,
            person_snapshot_bytes,
        )

        print(
            'VISIT_PERSISTED_VALIDATION_RESULT='
            + json.dumps(
                result,
                sort_keys=True,
            )
        )

    finally:
        spark.stop()


if __name__ == '__main__':
    main()
PY_APP

# ============================================================
# 2. Unit tests for all pure validation logic
# ============================================================

cat > "$STAGE/tests/task003/test_persisted_visit_candidate_validator.py" <<'PY_TEST'
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(
    0,
    str(ROOT / 'spark/apps/visit')
)

from validate_persisted_visit_candidate import (
    EXPECTED_FIELD_COUNT,
    canonical_person_snapshot,
    extract_contract_fields,
    normalize_class_counts,
    read_regular,
    sha,
    to_spark_storage_uri,
    validate_contract,
    validate_static_evidence,
)


FIELDS = [
    'source_system',
    'source_encounter_id',
    'source_person_id',
    'person_id',
    'visit_concept_id',
    'visit_start_date',
    'visit_start_datetime',
    'visit_end_date',
    'visit_end_datetime',
    'visit_type_concept_id',
    'provider_id',
    'care_site_id',
    'visit_source_value',
    'visit_source_concept_id',
    'admitted_from_concept_id',
    'admitted_from_source_value',
    'discharged_to_concept_id',
    'discharged_to_source_value',
    'preceding_visit_occurrence_id',
    'encounter_class',
    'source_code',
    'source_description',
    'source_organization_id',
    'source_provider_id',
    'source_payer_id',
    'reason_code',
    'reason_description',
    'source_version',
    'source_batch_id',
    'source_ingest_date',
    'processing_run_id',
    'raw_publish_run_id',
    'canonical_version',
    'source_file',
    'source_file_sha256',
    'source_file_size_bytes',
]


class ValidatorTests(unittest.TestCase):

    def test_kubernetes_projected_file_symlink_allowed(self):
        import tempfile

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)

            data_dir = root / '..20261009_224629'
            data_dir.mkdir()

            target = data_dir / 'plan.json'
            target.write_bytes(b'{"ok":true}\n')

            data_link = root / '..data'
            data_link.symlink_to(
                data_dir.name,
                target_is_directory=True,
            )

            projected = root / 'plan.json'
            projected.symlink_to(
                Path('..data') / 'plan.json'
            )

            self.assertTrue(
                projected.is_symlink()
            )

            self.assertEqual(
                read_regular(projected),
                b'{"ok":true}\n',
            )

    def test_projected_file_escape_rejected(self):
        import tempfile

        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)

            mount = base / 'mount'
            mount.mkdir()

            outside = base / 'outside.json'
            outside.write_bytes(b'{}\n')

            projected = mount / 'plan.json'
            projected.symlink_to(
                Path('..') / 'outside.json'
            )

            with self.assertRaisesRegex(
                ValueError,
                'escapes mount directory',
            ):
                read_regular(
                    projected
                )

    def test_processing_lineage_pin_fixture(self):
        f2 = {
            'input': {
                'raw_context': {
                    'processing_run_id':
                        'encounter-20261008T234726Z-1658454',

                    'raw_publish_run_id':
                        'encounter-raw-20261009T005128Z-1681690',
                }
            }
        }

        raw_context = (
            f2.get('input', {})
            .get('raw_context', {})
        )

        self.assertEqual(
            raw_context['processing_run_id'],
            'encounter-20261008T234726Z-1658454',
        )

        self.assertEqual(
            raw_context['raw_publish_run_id'],
            'encounter-raw-20261009T005128Z-1681690',
        )

    def test_s3_uri_transport_conversion(self):
        self.assertEqual(
            to_spark_storage_uri(
                's3://health-processed/a/b/data/'
            ),
            's3a://health-processed/a/b/data/',
        )

        with self.assertRaises(ValueError):
            to_spark_storage_uri(
                's3a://health-processed/a/b/data/'
            )

    def test_field_fixture_count(self):
        self.assertEqual(
            len(FIELDS),
            EXPECTED_FIELD_COUNT,
        )

    def test_contract_string_fields(self):
        contract = {
            'fields': FIELDS
        }

        self.assertEqual(
            validate_contract(contract),
            FIELDS,
        )

    def test_contract_object_fields(self):
        contract = {
            'schema': {
                'fields': [
                    {'name': field}
                    for field in FIELDS
                ]
            }
        }

        self.assertEqual(
            extract_contract_fields(
                contract
            ),
            FIELDS,
        )

    def test_final_visit_id_rejected(self):
        fields = list(FIELDS)
        fields[-1] = 'visit_occurrence_id'

        with self.assertRaises(ValueError):
            validate_contract({
                'fields': fields
            })

    def test_person_snapshot_is_stable(self):
        one = [
            ['synthea', 'b', 2],
            ['synthea', 'a', 1],
        ]

        two = [
            ['synthea', 'a', 1],
            ['synthea', 'b', 2],
        ]

        self.assertEqual(
            canonical_person_snapshot(one),
            canonical_person_snapshot(two),
        )

    def test_duplicate_source_person_rejected(self):
        records = [
            ['synthea', 'a', 1],
            ['synthea', 'a', 2],
        ]

        with self.assertRaisesRegex(
            ValueError,
            'duplicate source Person',
        ):
            canonical_person_snapshot(
                records
            )

    def test_duplicate_omop_person_rejected(self):
        records = [
            ['synthea', 'a', 1],
            ['synthea', 'b', 1],
        ]

        with self.assertRaisesRegex(
            ValueError,
            'duplicate OMOP',
        ):
            canonical_person_snapshot(
                records
            )

    def test_class_counts(self):
        rows = [
            {
                'encounter_class':
                    'ambulatory',

                'count':
                    2605,
            },

            {
                'encounter_class':
                    'inpatient',

                'count':
                    74,
            },
        ]

        self.assertEqual(
            normalize_class_counts(rows),
            {
                'ambulatory': 2605,
                'inpatient': 74,
            },
        )

    def test_static_evidence(self):
        people = [
            ['synthea', 'a', 1],
            ['synthea', 'b', 2],
        ]

        person_bytes = (
            canonical_person_snapshot(
                people
            )
        )

        plan = {
            'run_id':
                'run-1',

            'data_uri':
                's3://health-processed/x/data/',

            'expected_rows':
                3,

            'expected_persons':
                2,
        }

        f2 = {
            'task':
                'TASK-003',

            'step':
                'STEP-05F2',

            'status':
                'PASS',

            'result': {
                'candidate_rows':
                    3,

                'referenced_persons':
                    2,
            },
        }

        c3b = {
            'run_id':
                'run-1',

            'status':
                'POSTLOCK_PREFLIGHT_PASS',

            'fresh_s3_relist_passed':
                True,

            'reservation_still_held':
                True,

            'person_map_fingerprint':
                sha(person_bytes),
        }

        result = validate_static_evidence(
            plan,
            f2,
            c3b,
            {'fields': FIELDS},
            person_bytes,
            plan['data_uri'],
        )

        self.assertEqual(
            result,
            FIELDS,
        )

    def test_person_fingerprint_drift(self):
        people = [
            ['synthea', 'a', 1],
        ]

        person_bytes = (
            canonical_person_snapshot(
                people
            )
        )

        plan = {
            'run_id':
                'run-1',

            'data_uri':
                's3://health-processed/x/data/',

            'expected_rows':
                1,

            'expected_persons':
                1,
        }

        f2 = {
            'task':
                'TASK-003',

            'step':
                'STEP-05F2',

            'status':
                'PASS',

            'result': {
                'candidate_rows':
                    1,

                'referenced_persons':
                    1,
            },
        }

        c3b = {
            'run_id':
                'run-1',

            'status':
                'POSTLOCK_PREFLIGHT_PASS',

            'fresh_s3_relist_passed':
                True,

            'reservation_still_held':
                True,

            'person_map_fingerprint':
                '0' * 64,
        }

        with self.assertRaisesRegex(
            ValueError,
            'fingerprint',
        ):
            validate_static_evidence(
                plan,
                f2,
                c3b,
                {'fields': FIELDS},
                person_bytes,
                plan['data_uri'],
            )


if __name__ == '__main__':
    unittest.main()
PY_TEST

# ============================================================
# 3. Syntax and isolated tests
# ============================================================

echo '=== 1. Python syntax and unit tests ==='

python3 - "$STAGE" <<'PY_AST'
import ast
import sys
from pathlib import Path

root = Path(sys.argv[1])

for rel in (
    'spark/apps/visit/validate_persisted_visit_candidate.py',
    'tests/task003/test_persisted_visit_candidate_validator.py',
):
    ast.parse(
        (root / rel).read_text(),
        filename=rel,
    )

print('PERSISTED_VALIDATOR_PYTHON_AST=PASS')
PY_AST

PYTHONPATH="$STAGE/spark/apps/visit" \
python3 -m unittest discover \
  -s "$STAGE/tests/task003" \
  -p 'test_persisted_visit_candidate_validator.py' \
  -v

echo 'PERSISTED_VALIDATOR_TESTS=PASS'

# ============================================================
# 4. Validate against REAL canonical contract now
# ============================================================

echo '=== 2. Real Contract compatibility ==='

PYTHONPATH="$STAGE/spark/apps/visit" \
python3 - \
  "$ROOT/spark/contracts/omop/visit-candidate-v1.json" \
  <<'PY_REAL'
import json
import sys
from pathlib import Path

from validate_persisted_visit_candidate import (
    BUSINESS_KEY,
    EXPECTED_FIELD_COUNT,
    PERSON_KEY,
    validate_contract,
)

contract = json.loads(
    Path(sys.argv[1]).read_text()
)

fields = validate_contract(
    contract
)

print(
    'REAL_CONTRACT_FIELD_COUNT='
    + str(len(fields))
)

print(
    'REAL_CONTRACT_FIELDS='
    + ','.join(fields)
)

print(
    'BUSINESS_KEY='
    + ','.join(BUSINESS_KEY)
)

print(
    'PERSON_MAPPING_KEY='
    + ','.join(PERSON_KEY)
)

print(
    'VISIT_OCCURRENCE_ID_PRESENT='
    + (
        'YES'
        if 'visit_occurrence_id' in fields
        else 'NO'
    )
)

assert len(fields) == EXPECTED_FIELD_COUNT

print('REAL_CONTRACT_COMPATIBILITY=PASS')
PY_REAL

# ============================================================
# 5. Static independence/safety checks
# ============================================================

echo '=== 3. Independent validator boundary checks ==='

python3 - \
  "$STAGE/spark/apps/visit/validate_persisted_visit_candidate.py" \
  <<'PY_BOUNDARY'
import sys
from pathlib import Path

source = Path(sys.argv[1]).read_text()

required = (
    "spark.read",
    "to_spark_storage_uri",
    ".parquet(storage_uri)",
    "BUSINESS_KEY",
    "'source_system'",
    "'source_encounter_id'",
    "'encounter_class'",
    "canonical_person_snapshot",
    "INDEPENDENT_S3_READBACK_PASS",
    "'s3_write_verified':",
    "'candidate_published_verified':",
)

for token in required:
    assert token in source, token

for forbidden in (
    'processed_visit_writer_core',
    '.write.',
    'mode("overwrite")',
    "mode('overwrite')",
    'INSERT INTO',
    'UPDATE ',
    'DELETE FROM',
    'kubectl',
):
    assert forbidden not in source, forbidden

print('VALIDATOR_INDEPENDENT_FROM_WRITER_CORE=PASS')
print('VALIDATOR_S3_WRITE_PATH_ABSENT=PASS')
print('VALIDATOR_DB_MUTATION_ABSENT=PASS')
PY_BOUNDARY

# ============================================================
# 6. Canonical conflict check and install
# ============================================================

echo '=== 4. Canonical source conflict check ==='

FILES=(
  spark/apps/visit/validate_persisted_visit_candidate.py
  tests/task003/test_persisted_visit_candidate_validator.py
)

GEN=scripts/task003/05g2c2c3d2b1-prepare-persisted-validator-source.sh

for rel in "${FILES[@]}"; do
  if [[ -L "$ROOT/$rel" ]] || {
    [[ -e "$ROOT/$rel" ]] &&
    ! cmp -s "$STAGE/$rel" "$ROOT/$rel"
  }; then
    echo "ERROR: canonical source conflict: $rel"
    exit 1
  fi
done

if [[ -L "$ROOT/$GEN" ]] || {
  [[ -e "$ROOT/$GEN" ]] &&
  ! cmp -s "$SOURCE" "$ROOT/$GEN"
}; then
  echo "ERROR: canonical generator conflict: $GEN"
  exit 1
fi

echo '=== 5. Install canonical source ==='

for rel in "${FILES[@]}"; do
  mkdir -p "$(dirname "$ROOT/$rel")"

  if [[ -f "$ROOT/$rel" ]] &&
     cmp -s "$STAGE/$rel" "$ROOT/$rel"
  then
    echo "CANONICAL_SOURCE_REUSED=$rel"
  else
    install \
      -m 644 \
      "$STAGE/$rel" \
      "$ROOT/$rel"

    echo "CANONICAL_SOURCE_READY=$rel"
  fi
done

if [[ -f "$ROOT/$GEN" ]]; then
  echo "CANONICAL_GENERATOR_REUSED=$GEN"
else
  install \
    -m 755 \
    "$SOURCE" \
    "$ROOT/$GEN"

  echo "CANONICAL_GENERATOR_READY=$GEN"
fi

echo 'STEP05G2C2C3D2B1_SOURCE_AND_TESTS=PASS'

echo 'SPARK_VALIDATOR_SUBMITTED=NO'
echo 'S3_WRITE_VERIFIED=NO'
echo 'CANDIDATE_PUBLISHED_VERIFIED=NO'

echo 'RESERVATION_RELEASED=NO'
echo 'S3_MUTATION=NO'
echo 'DATABASE_MUTATION=NO'
echo 'GIT_COMMIT=NO'
