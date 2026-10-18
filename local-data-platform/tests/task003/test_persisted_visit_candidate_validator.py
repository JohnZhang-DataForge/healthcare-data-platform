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
