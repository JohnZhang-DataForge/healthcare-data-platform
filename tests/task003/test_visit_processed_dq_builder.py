import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(
    0,
    str(ROOT / 'apps/task003')
)

from build_visit_processed_dq import (
    EXPECTED_GIT_CHECKPOINT,
    EXPECTED_PERSON_FINGERPRINT,
    EXPECTED_PROCESSING_RUN_ID,
    EXPECTED_RAW_PUBLISH_RUN_ID,
    build_dq,
    canonical_json_bytes,
    sha256_bytes,
)


CLASS_COUNTS = {
    'ambulatory': 2605,
    'emergency': 334,
    'home': 18,
    'hospice': 10,
    'inpatient': 74,
    'outpatient': 992,
    'snf': 12,
    'urgentcare': 350,
    'virtual': 27,
    'wellness': 1377,
}


def fixtures():
    plan = {
        'run_id':
            'visit-proc-test',

        'data_uri':
            's3://health-processed/x/data/',

        'dq_uri':
            's3://health-processed/x/dq/result.json',

        'manifest_uri':
            's3://health-processed/x/manifest.json',

        'expected_rows':
            5799,

        'expected_persons':
            113,

        'class_counts':
            CLASS_COUNTS,
    }

    result = {
        'status':
            'INDEPENDENT_S3_READBACK_PASS',

        'data_uri':
            plan['data_uri'],

        'rows':
            5799,

        'unique_business_keys':
            5799,

        'business_key': [
            'source_system',
            'source_encounter_id',
        ],

        'referenced_persons':
            113,

        'contract_field_count':
            36,

        'visit_occurrence_id_present':
            False,

        'person_map_fingerprint':
            EXPECTED_PERSON_FINGERPRINT,

        'processing_run_id':
            EXPECTED_PROCESSING_RUN_ID,

        'raw_publish_run_id':
            EXPECTED_RAW_PUBLISH_RUN_ID,

        'source_system':
            'synthea',

        'class_counts':
            CLASS_COUNTS,

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

    result_bytes = canonical_json_bytes(
        result
    )

    state = {
        'task':
            'TASK-003',

        'step':
            'STEP-05G2C2C3D2B2',

        'status':
            'INDEPENDENT_S3_READBACK_PASS',

        'run_id':
            plan['run_id'],

        'validator_spark_state':
            'COMPLETED',

        'candidate_published_verified':
            True,

        's3_write_verified':
            True,

        'dq_published':
            False,

        'manifest_published':
            False,

        'postgresql_write':
            False,

        'reservation_released':
            False,

        'validation_result_sha256':
            sha256_bytes(
                result_bytes
            ),
    }

    return (
        plan,
        state,
        result,
        result_bytes,
    )


class DQBuilderTests(
    unittest.TestCase
):

    def test_valid_dq(self):
        (
            plan,
            state,
            result,
            result_bytes,
        ) = fixtures()

        dq = build_dq(
            plan,
            state,
            result,
            result_bytes,
            EXPECTED_GIT_CHECKPOINT,
        )

        self.assertEqual(
            dq['status'],
            'PASS',
        )

        self.assertEqual(
            dq['metrics']['rows'],
            5799,
        )

        self.assertTrue(
            dq['verification']
            ['s3_write_verified']
        )

        self.assertFalse(
            dq['publication_gate']
            ['manifest_published_at_build_time']
        )

    def test_stable_output(self):
        args = fixtures()

        one = build_dq(
            *args,
            EXPECTED_GIT_CHECKPOINT,
        )

        two = build_dq(
            *args,
            EXPECTED_GIT_CHECKPOINT,
        )

        self.assertEqual(
            canonical_json_bytes(one),
            canonical_json_bytes(two),
        )

    def test_git_checkpoint_drift(self):
        args = fixtures()

        with self.assertRaisesRegex(
            ValueError,
            'Git checkpoint',
        ):
            build_dq(
                *args,
                '0' * 40,
            )

    def test_row_drift(self):
        (
            plan,
            state,
            result,
            _,
        ) = fixtures()

        result['rows'] = 5798

        result_bytes = canonical_json_bytes(
            result
        )

        state[
            'validation_result_sha256'
        ] = sha256_bytes(
            result_bytes
        )

        with self.assertRaisesRegex(
            ValueError,
            'row count',
        ):
            build_dq(
                plan,
                state,
                result,
                result_bytes,
                EXPECTED_GIT_CHECKPOINT,
            )

    def test_person_fingerprint_drift(self):
        (
            plan,
            state,
            result,
            _,
        ) = fixtures()

        result[
            'person_map_fingerprint'
        ] = '0' * 64

        result_bytes = canonical_json_bytes(
            result
        )

        state[
            'validation_result_sha256'
        ] = sha256_bytes(
            result_bytes
        )

        with self.assertRaisesRegex(
            ValueError,
            'Person map fingerprint',
        ):
            build_dq(
                plan,
                state,
                result,
                result_bytes,
                EXPECTED_GIT_CHECKPOINT,
            )

    def test_class_drift(self):
        (
            plan,
            state,
            result,
            _,
        ) = fixtures()

        result['class_counts'] = (
            copy.deepcopy(
                CLASS_COUNTS
            )
        )

        result[
            'class_counts'
        ]['ambulatory'] -= 1

        result_bytes = canonical_json_bytes(
            result
        )

        state[
            'validation_result_sha256'
        ] = sha256_bytes(
            result_bytes
        )

        with self.assertRaisesRegex(
            ValueError,
            'class distribution',
        ):
            build_dq(
                plan,
                state,
                result,
                result_bytes,
                EXPECTED_GIT_CHECKPOINT,
            )

    def test_manifest_already_published_rejected(self):
        (
            plan,
            state,
            result,
            result_bytes,
        ) = fixtures()

        state[
            'manifest_published'
        ] = True

        with self.assertRaisesRegex(
            ValueError,
            'Manifest already',
        ):
            build_dq(
                plan,
                state,
                result,
                result_bytes,
                EXPECTED_GIT_CHECKPOINT,
            )

    def test_final_visit_id_rejected(self):
        (
            plan,
            state,
            result,
            _,
        ) = fixtures()

        result[
            'visit_occurrence_id_present'
        ] = True

        result_bytes = canonical_json_bytes(
            result
        )

        state[
            'validation_result_sha256'
        ] = sha256_bytes(
            result_bytes
        )

        with self.assertRaisesRegex(
            ValueError,
            'visit_occurrence_id',
        ):
            build_dq(
                plan,
                state,
                result,
                result_bytes,
                EXPECTED_GIT_CHECKPOINT,
            )


if __name__ == '__main__':
    unittest.main()
