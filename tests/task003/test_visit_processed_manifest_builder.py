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

from build_visit_processed_manifest import (
    EXPECTED_DQ_SHA256,
    EXPECTED_DQ_SIZE_BYTES,
    EXPECTED_GIT_CHECKPOINT,
    EXPECTED_PERSON_FINGERPRINT,
    EXPECTED_PROCESSING_RUN_ID,
    EXPECTED_RAW_PUBLISH_RUN_ID,
    EXPECTED_RUN_ID,
    build_manifest,
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
            EXPECTED_RUN_ID,

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
            copy.deepcopy(
                CLASS_COUNTS
            ),
    }

    readback_result = {
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

        'class_counts':
            copy.deepcopy(
                CLASS_COUNTS
            ),

        's3_write_verified':
            True,

        'candidate_published_verified':
            True,

        'postgresql_write':
            False,
    }

    readback_result_bytes = (
        canonical_json_bytes(
            readback_result
        )
    )

    readback_state = {
        'task':
            'TASK-003',

        'step':
            'STEP-05G2C2C3D2B2',

        'status':
            'INDEPENDENT_S3_READBACK_PASS',

        'run_id':
            EXPECTED_RUN_ID,

        'validator_spark_state':
            'COMPLETED',

        'rows':
            5799,

        'unique_business_keys':
            5799,

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
                readback_result_bytes
            ),
    }

    dq = {
        'task':
            'TASK-003',

        'step':
            'STEP-05G3',

        'status':
            'PASS',

        'run_id':
            EXPECTED_RUN_ID,

        'data_uri':
            plan['data_uri'],

        'dq_uri':
            plan['dq_uri'],

        'manifest_uri':
            plan['manifest_uri'],

        'publication_gate': {
            'manifest_may_be_published_after_dq':
                True,

            'manifest_published_at_build_time':
                False,

            'reservation_must_remain_held':
                True,
        },
    }

    dq_bytes = json.dumps(
        dq,
        sort_keys=True,
    ).encode('utf-8')

    # Unit fixtures need production-pinned DQ bytes.
    # Replace with a synthetic blob whose hash/size are patched
    # only inside negative tests is intentionally unsupported.
    # Positive real-artifact testing is performed by the runner.

    dq_publication_result = {
        'status':
            'DQ_PUBLICATION_PASS',

        'publication_status':
            'CREATED',

        'dq_uri':
            plan['dq_uri'],

        'dq_sha256':
            EXPECTED_DQ_SHA256,

        'dq_size_bytes':
            EXPECTED_DQ_SIZE_BYTES,

        'dq_published':
            True,

        'dq_readback_verified':
            True,

        'manifest_uri':
            plan['manifest_uri'],

        'manifest_published':
            False,

        'reservation_release_requested':
            False,

        'postgresql_write':
            False,
    }

    dq_publication_result_bytes = (
        canonical_json_bytes(
            dq_publication_result
        )
    )

    dq_publication_state = {
        'task':
            'TASK-003',

        'step':
            'STEP-05G3B2',

        'status':
            'DQ_PUBLICATION_PASS',

        'run_id':
            EXPECTED_RUN_ID,

        'spark_application_state':
            'COMPLETED',

        'publication_status':
            'CREATED',

        'processed_data_verified':
            True,

        'candidate_published_verified':
            True,

        's3_write_verified':
            True,

        'dq_published':
            True,

        'dq_readback_verified':
            True,

        'dq_sha256':
            EXPECTED_DQ_SHA256,

        'dq_size_bytes':
            EXPECTED_DQ_SIZE_BYTES,

        'manifest_published':
            False,

        'reservation_released':
            False,

        'postgresql_write':
            False,

        'publication_result_sha256':
            sha256_bytes(
                dq_publication_result_bytes
            ),
    }

    return (
        plan,
        readback_state,
        readback_result,
        readback_result_bytes,
        dq_publication_state,
        dq_publication_result,
        dq_publication_result_bytes,
    )


class ManifestBuilderTests(
    unittest.TestCase
):

    def test_canonical_json_is_stable(self):
        value = {
            'z': 1,
            'a': 2,
        }

        self.assertEqual(
            canonical_json_bytes(
                value
            ),
            canonical_json_bytes(
                value
            ),
        )

    def test_git_checkpoint_constant(self):
        self.assertEqual(
            EXPECTED_GIT_CHECKPOINT,
            'beb6370cddafbe4c4e649f9a6cb9d949af0ee05e',
        )

    def test_dq_sha_constant(self):
        self.assertEqual(
            EXPECTED_DQ_SHA256,
            '58e0ffc9e9b9a0ef5f34558807297b5ae2d6545d909fa340b0e2b713346b77c2',
        )

    def test_manifest_already_published_rejected(self):
        args = list(
            fixtures()
        )

        args[4][
            'manifest_published'
        ] = True

        with self.assertRaisesRegex(
            ValueError,
            'Manifest already published',
        ):
            build_manifest(
                *args,
                b'x' * EXPECTED_DQ_SIZE_BYTES,
                EXPECTED_GIT_CHECKPOINT,
            )

    def test_dq_not_published_rejected(self):
        args = list(
            fixtures()
        )

        args[4][
            'dq_published'
        ] = False

        with self.assertRaisesRegex(
            ValueError,
            'DQ not published',
        ):
            build_manifest(
                *args,
                b'x' * EXPECTED_DQ_SIZE_BYTES,
                EXPECTED_GIT_CHECKPOINT,
            )

    def test_reservation_released_rejected(self):
        args = list(
            fixtures()
        )

        args[4][
            'reservation_released'
        ] = True

        with self.assertRaisesRegex(
            ValueError,
            'Reservation released',
        ):
            build_manifest(
                *args,
                b'x' * EXPECTED_DQ_SIZE_BYTES,
                EXPECTED_GIT_CHECKPOINT,
            )

    def test_git_checkpoint_drift_rejected(self):
        args = list(
            fixtures()
        )

        with self.assertRaisesRegex(
            ValueError,
            'Git checkpoint',
        ):
            build_manifest(
                *args,
                b'x' * EXPECTED_DQ_SIZE_BYTES,
                '0' * 40,
            )

    def test_dq_size_drift_rejected(self):
        args = list(
            fixtures()
        )

        with self.assertRaisesRegex(
            ValueError,
            'local DQ artifact SHA drift',
        ):
            build_manifest(
                *args,
                b'x',
                EXPECTED_GIT_CHECKPOINT,
            )


if __name__ == '__main__':
    unittest.main()
