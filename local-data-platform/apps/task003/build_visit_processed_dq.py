"""Build deterministic TASK-003 Processed Visit Candidate DQ result.

This module does not write S3 or PostgreSQL.

The DQ artifact is derived only from:
- the immutable Processed publication Plan;
- the independently verified persisted-data state/result;
- the approved Git data-verification checkpoint.

Publication of dq/result.json is a separate step.
"""

import hashlib
import json


EXPECTED_GIT_CHECKPOINT = (
    '16b264cd5260b7d4a155e9ffc4d61d165b7c4d21'
)

EXPECTED_ROWS = 5799
EXPECTED_PERSONS = 113
EXPECTED_FIELDS = 36

EXPECTED_PERSON_FINGERPRINT = (
    'e4f63203932043bd7a2a64a5241740'
    'faf93494b7e7421699b5b462583ba5dbb8'
)

EXPECTED_PROCESSING_RUN_ID = (
    'encounter-20261008T234726Z-1658454'
)

EXPECTED_RAW_PUBLISH_RUN_ID = (
    'encounter-raw-20261009T005128Z-1681690'
)

BUSINESS_KEY = [
    'source_system',
    'source_encounter_id',
]


def require(condition, message):
    if not condition:
        raise ValueError(
            'PROCESSED_DQ_BUILD_FAILED: '
            + message
        )


def canonical_json_bytes(value):
    return (
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
        )
        + '\n'
    ).encode('utf-8')


def sha256_bytes(blob):
    return hashlib.sha256(
        blob
    ).hexdigest()


def validate_inputs(
    plan,
    readback_state,
    readback_result,
    readback_result_bytes,
    git_checkpoint,
):
    require(
        git_checkpoint
        == EXPECTED_GIT_CHECKPOINT,
        'Git checkpoint drift'
    )

    require(
        plan.get('run_id')
        == readback_state.get('run_id'),
        'Plan/readback run identity drift'
    )

    require(
        (
            readback_state.get('task'),
            readback_state.get('step'),
            readback_state.get('status'),
        )
        == (
            'TASK-003',
            'STEP-05G2C2C3D2B2',
            'INDEPENDENT_S3_READBACK_PASS',
        ),
        'independent readback state'
    )

    require(
        readback_state.get(
            'validator_spark_state'
        )
        == 'COMPLETED',
        'Validator Spark state'
    )

    require(
        readback_state.get(
            'candidate_published_verified'
        )
        is True,
        'Candidate publication not verified'
    )

    require(
        readback_state.get(
            's3_write_verified'
        )
        is True,
        'S3 write not verified'
    )

    require(
        readback_state.get(
            'dq_published'
        )
        is False,
        'DQ already marked published'
    )

    require(
        readback_state.get(
            'manifest_published'
        )
        is False,
        'Manifest already marked published'
    )

    require(
        readback_state.get(
            'postgresql_write'
        )
        is False,
        'unexpected PostgreSQL write'
    )

    require(
        readback_state.get(
            'reservation_released'
        )
        is False,
        'Reservation already released'
    )

    result_sha = sha256_bytes(
        readback_result_bytes
    )

    require(
        result_sha
        == readback_state.get(
            'validation_result_sha256'
        ),
        'independent validation result SHA drift'
    )

    require(
        readback_result.get('status')
        == 'INDEPENDENT_S3_READBACK_PASS',
        'independent validation result status'
    )

    require(
        readback_result.get('data_uri')
        == plan.get('data_uri'),
        'data URI drift'
    )

    require(
        readback_result.get('rows')
        == EXPECTED_ROWS
        == plan.get('expected_rows'),
        'row count drift'
    )

    require(
        readback_result.get(
            'unique_business_keys'
        )
        == EXPECTED_ROWS,
        'business-key uniqueness drift'
    )

    require(
        readback_result.get(
            'business_key'
        )
        == BUSINESS_KEY,
        'business key drift'
    )

    require(
        readback_result.get(
            'referenced_persons'
        )
        == EXPECTED_PERSONS
        == plan.get('expected_persons'),
        'Person count drift'
    )

    require(
        readback_result.get(
            'contract_field_count'
        )
        == EXPECTED_FIELDS,
        'Contract field count drift'
    )

    require(
        readback_result.get(
            'visit_occurrence_id_present'
        )
        is False,
        'final visit_occurrence_id appeared early'
    )

    require(
        readback_result.get(
            'person_map_fingerprint'
        )
        == EXPECTED_PERSON_FINGERPRINT,
        'Person map fingerprint drift'
    )

    require(
        readback_result.get(
            'processing_run_id'
        )
        == EXPECTED_PROCESSING_RUN_ID,
        'processing_run_id drift'
    )

    require(
        readback_result.get(
            'raw_publish_run_id'
        )
        == EXPECTED_RAW_PUBLISH_RUN_ID,
        'raw_publish_run_id drift'
    )

    require(
        readback_result.get(
            'source_system'
        )
        == 'synthea',
        'source_system drift'
    )

    require(
        readback_result.get(
            'class_counts'
        )
        == plan.get('class_counts'),
        'class distribution drift'
    )

    require(
        readback_result.get(
            's3_write_verified'
        )
        is True,
        'result S3 verification'
    )

    require(
        readback_result.get(
            'candidate_published_verified'
        )
        is True,
        'result Candidate verification'
    )

    require(
        readback_result.get(
            'dq_published'
        )
        is False,
        'result prematurely claims DQ publication'
    )

    require(
        readback_result.get(
            'manifest_published'
        )
        is False,
        'result prematurely claims Manifest publication'
    )

    require(
        readback_result.get(
            'postgresql_write'
        )
        is False,
        'result PostgreSQL write drift'
    )

    dq_uri = plan.get('dq_uri')
    manifest_uri = plan.get(
        'manifest_uri'
    )

    require(
        isinstance(dq_uri, str)
        and dq_uri.endswith(
            '/dq/result.json'
        ),
        'invalid DQ URI'
    )

    require(
        isinstance(manifest_uri, str)
        and manifest_uri.endswith(
            '/manifest.json'
        ),
        'invalid Manifest URI'
    )

    require(
        dq_uri != manifest_uri,
        'DQ/Manifest URI collision'
    )

    return result_sha


def build_dq(
    plan,
    readback_state,
    readback_result,
    readback_result_bytes,
    git_checkpoint,
):
    result_sha = validate_inputs(
        plan,
        readback_state,
        readback_result,
        readback_result_bytes,
        git_checkpoint,
    )

    dq = {
        'schema_version':
            'task003-visit-processed-dq-v1',

        'task':
            'TASK-003',

        'step':
            'STEP-05G3',

        'status':
            'PASS',

        'run_id':
            plan['run_id'],

        'entity':
            'visit_occurrence',

        'source_system':
            'synthea',

        'data_uri':
            plan['data_uri'],

        'dq_uri':
            plan['dq_uri'],

        'manifest_uri':
            plan['manifest_uri'],

        'metrics': {
            'rows':
                EXPECTED_ROWS,

            'unique_business_keys':
                EXPECTED_ROWS,

            'business_key':
                BUSINESS_KEY,

            'referenced_persons':
                EXPECTED_PERSONS,

            'contract_field_count':
                EXPECTED_FIELDS,

            'visit_occurrence_id_present':
                False,

            'class_counts':
                readback_result[
                    'class_counts'
                ],
        },

        'lineage': {
            'processing_run_id':
                EXPECTED_PROCESSING_RUN_ID,

            'raw_publish_run_id':
                EXPECTED_RAW_PUBLISH_RUN_ID,

            'person_map_fingerprint':
                EXPECTED_PERSON_FINGERPRINT,
        },

        'verification': {
            'independent_s3_readback':
                True,

            'candidate_published_verified':
                True,

            's3_write_verified':
                True,

            'writer_database_write':
                False,

            'postgresql_write':
                False,
        },

        'publication_gate': {
            'dq_result_status':
                'PASS',

            'manifest_may_be_published_after_dq':
                True,

            'manifest_published_at_build_time':
                False,

            'reservation_must_remain_held':
                True,
        },

        'evidence': {
            'processed_data_verified_git_commit':
                git_checkpoint,

            'independent_validation_result_sha256':
                result_sha,

            'independent_readback_state_sha256':
                sha256_bytes(
                    canonical_json_bytes(
                        readback_state
                    )
                ),
        },
    }

    return dq
