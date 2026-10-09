"""Build deterministic TASK-003 Processed Visit APPROVED manifest.

The Manifest is the final publication gate.

This builder:
- validates independently verified Processed data;
- validates published and readback-verified DQ;
- pins lineage and Git checkpoint;
- produces deterministic manifest bytes;
- does NOT publish manifest.json;
- does NOT mutate PostgreSQL;
- does NOT release the Writer Reservation.
"""

import hashlib
import json


EXPECTED_GIT_CHECKPOINT = (
    'beb6370cddafbe4c4e649f9a6cb9d949af0ee05e'
)

EXPECTED_RUN_ID = (
    'visit-proc-20261009t192437z-2081886'
)

EXPECTED_ROWS = 5799
EXPECTED_PERSONS = 113
EXPECTED_FIELDS = 36

EXPECTED_DQ_SHA256 = (
    '58e0ffc9e9b9a0ef5f34558807297b5a'
    'e2d6545d909fa340b0e2b713346b77c2'
)

EXPECTED_DQ_SIZE_BYTES = 2607

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

EXPECTED_CONTRACT_SHA256 = (
    '473ae45225c9063a7560b0092ed7914d'
    '71a43623f593d4959c66294e942a5837'
)

BUSINESS_KEY = [
    'source_system',
    'source_encounter_id',
]


def require(condition, message):
    if not condition:
        raise ValueError(
            'PROCESSED_MANIFEST_BUILD_FAILED: '
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
    dq_publication_state,
    dq_publication_result,
    dq_publication_result_bytes,
    dq_bytes,
    git_checkpoint,
):
    require(
        git_checkpoint == EXPECTED_GIT_CHECKPOINT,
        'Git checkpoint drift'
    )

    require(
        plan.get('run_id') == EXPECTED_RUN_ID,
        'Plan run identity drift'
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
        readback_state.get('run_id')
        == EXPECTED_RUN_ID,
        'readback run identity drift'
    )

    require(
        readback_state.get(
            'validator_spark_state'
        )
        == 'COMPLETED',
        'independent Spark readback not completed'
    )

    require(
        readback_state.get('rows')
        == EXPECTED_ROWS,
        'readback row count drift'
    )

    require(
        readback_state.get(
            'unique_business_keys'
        )
        == EXPECTED_ROWS,
        'readback business-key count drift'
    )

    require(
        readback_state.get(
            'referenced_persons'
        )
        == EXPECTED_PERSONS,
        'readback Person count drift'
    )

    require(
        readback_state.get(
            'contract_field_count'
        )
        == EXPECTED_FIELDS,
        'readback Contract field count drift'
    )

    require(
        readback_state.get(
            'visit_occurrence_id_present'
        )
        is False,
        'final visit_occurrence_id appeared early'
    )

    require(
        readback_state.get(
            'person_map_fingerprint'
        )
        == EXPECTED_PERSON_FINGERPRINT,
        'Person map fingerprint drift'
    )

    require(
        readback_state.get(
            'processing_run_id'
        )
        == EXPECTED_PROCESSING_RUN_ID,
        'processing_run_id drift'
    )

    require(
        readback_state.get(
            'raw_publish_run_id'
        )
        == EXPECTED_RAW_PUBLISH_RUN_ID,
        'raw_publish_run_id drift'
    )

    require(
        readback_state.get(
            'candidate_published_verified'
        )
        is True,
        'Candidate data not verified'
    )

    require(
        readback_state.get(
            's3_write_verified'
        )
        is True,
        'Processed data S3 write not verified'
    )

    require(
        readback_state.get(
            'dq_published'
        )
        is False,
        'historical readback state changed'
    )

    require(
        readback_state.get(
            'manifest_published'
        )
        is False,
        'historical readback state claims Manifest publication'
    )

    require(
        readback_state.get(
            'postgresql_write'
        )
        is False,
        'unexpected PostgreSQL write in readback'
    )

    require(
        readback_state.get(
            'reservation_released'
        )
        is False,
        'Reservation released in readback evidence'
    )

    require(
        sha256_bytes(
            readback_result_bytes
        )
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
        'Processed data URI drift'
    )

    require(
        readback_result.get('rows')
        == EXPECTED_ROWS,
        'result row count drift'
    )

    require(
        readback_result.get(
            'unique_business_keys'
        )
        == EXPECTED_ROWS,
        'result business-key count drift'
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
        == EXPECTED_PERSONS,
        'result Person count drift'
    )

    require(
        readback_result.get(
            'contract_field_count'
        )
        == EXPECTED_FIELDS,
        'result Contract field count drift'
    )

    require(
        readback_result.get(
            'visit_occurrence_id_present'
        )
        is False,
        'result contains final visit_occurrence_id'
    )

    require(
        readback_result.get(
            'person_map_fingerprint'
        )
        == EXPECTED_PERSON_FINGERPRINT,
        'result Person fingerprint drift'
    )

    require(
        readback_result.get(
            'processing_run_id'
        )
        == EXPECTED_PROCESSING_RUN_ID,
        'result processing lineage drift'
    )

    require(
        readback_result.get(
            'raw_publish_run_id'
        )
        == EXPECTED_RAW_PUBLISH_RUN_ID,
        'result Raw publication lineage drift'
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
        'result S3 verification missing'
    )

    require(
        readback_result.get(
            'candidate_published_verified'
        )
        is True,
        'result Candidate verification missing'
    )

    require(
        readback_result.get(
            'postgresql_write'
        )
        is False,
        'result PostgreSQL write drift'
    )

    require(
        (
            dq_publication_state.get('task'),
            dq_publication_state.get('step'),
            dq_publication_state.get('status'),
        )
        == (
            'TASK-003',
            'STEP-05G3B2',
            'DQ_PUBLICATION_PASS',
        ),
        'DQ publication state'
    )

    require(
        dq_publication_state.get('run_id')
        == EXPECTED_RUN_ID,
        'DQ publication run identity drift'
    )

    require(
        dq_publication_state.get(
            'spark_application_state'
        )
        == 'COMPLETED',
        'DQ Publisher SparkApplication not completed'
    )

    require(
        dq_publication_state.get(
            'publication_status'
        )
        in (
            'CREATED',
            'REUSED_IDENTICAL',
        ),
        'invalid DQ publication status'
    )

    require(
        dq_publication_state.get(
            'processed_data_verified'
        )
        is True,
        'DQ state lost Processed data verification'
    )

    require(
        dq_publication_state.get(
            'candidate_published_verified'
        )
        is True,
        'DQ state lost Candidate verification'
    )

    require(
        dq_publication_state.get(
            's3_write_verified'
        )
        is True,
        'DQ state lost data S3 verification'
    )

    require(
        dq_publication_state.get(
            'dq_published'
        )
        is True,
        'DQ not published'
    )

    require(
        dq_publication_state.get(
            'dq_readback_verified'
        )
        is True,
        'DQ readback not verified'
    )

    require(
        dq_publication_state.get(
            'dq_sha256'
        )
        == EXPECTED_DQ_SHA256,
        'published DQ SHA drift'
    )

    require(
        dq_publication_state.get(
            'dq_size_bytes'
        )
        == EXPECTED_DQ_SIZE_BYTES,
        'published DQ size drift'
    )

    require(
        dq_publication_state.get(
            'manifest_published'
        )
        is False,
        'Manifest already published'
    )

    require(
        dq_publication_state.get(
            'reservation_released'
        )
        is False,
        'Reservation released before Manifest'
    )

    require(
        dq_publication_state.get(
            'postgresql_write'
        )
        is False,
        'unexpected PostgreSQL write in DQ state'
    )

    require(
        sha256_bytes(
            dq_publication_result_bytes
        )
        == dq_publication_state.get(
            'publication_result_sha256'
        ),
        'DQ publication result SHA drift'
    )

    require(
        dq_publication_result.get('status')
        == 'DQ_PUBLICATION_PASS',
        'DQ publication result status'
    )

    require(
        dq_publication_result.get(
            'publication_status'
        )
        in (
            'CREATED',
            'REUSED_IDENTICAL',
        ),
        'DQ publication result mode'
    )

    require(
        dq_publication_result.get(
            'dq_uri'
        )
        == plan.get('dq_uri'),
        'DQ URI drift'
    )

    require(
        dq_publication_result.get(
            'dq_sha256'
        )
        == EXPECTED_DQ_SHA256,
        'DQ result SHA drift'
    )

    require(
        dq_publication_result.get(
            'dq_size_bytes'
        )
        == EXPECTED_DQ_SIZE_BYTES,
        'DQ result size drift'
    )

    require(
        dq_publication_result.get(
            'dq_published'
        )
        is True,
        'DQ result not published'
    )

    require(
        dq_publication_result.get(
            'dq_readback_verified'
        )
        is True,
        'DQ result readback not verified'
    )

    require(
        dq_publication_result.get(
            'manifest_uri'
        )
        == plan.get('manifest_uri'),
        'Manifest URI drift'
    )

    require(
        dq_publication_result.get(
            'manifest_published'
        )
        is False,
        'DQ result claims Manifest already published'
    )

    require(
        dq_publication_result.get(
            'reservation_release_requested'
        )
        is False,
        'DQ result requested Reservation release'
    )

    require(
        dq_publication_result.get(
            'postgresql_write'
        )
        is False,
        'DQ result PostgreSQL write drift'
    )

    actual_dq_sha = sha256_bytes(
        dq_bytes
    )

    require(
        actual_dq_sha
        == EXPECTED_DQ_SHA256,
        'local DQ artifact SHA drift'
    )

    require(
        len(dq_bytes)
        == EXPECTED_DQ_SIZE_BYTES,
        'local DQ artifact size drift'
    )

    dq = json.loads(
        dq_bytes
    )

    require(
        (
            dq.get('task'),
            dq.get('step'),
            dq.get('status'),
        )
        == (
            'TASK-003',
            'STEP-05G3',
            'PASS',
        ),
        'DQ content status'
    )

    require(
        dq.get('run_id')
        == EXPECTED_RUN_ID,
        'DQ content run identity'
    )

    require(
        dq.get('data_uri')
        == plan.get('data_uri'),
        'DQ data URI drift'
    )

    require(
        dq.get('dq_uri')
        == plan.get('dq_uri'),
        'DQ content URI drift'
    )

    require(
        dq.get('manifest_uri')
        == plan.get('manifest_uri'),
        'DQ Manifest URI drift'
    )

    require(
        dq['publication_gate']
        ['manifest_may_be_published_after_dq']
        is True,
        'DQ does not approve Manifest progression'
    )

    require(
        dq['publication_gate']
        ['manifest_published_at_build_time']
        is False,
        'DQ content claims Manifest already published'
    )

    require(
        dq['publication_gate']
        ['reservation_must_remain_held']
        is True,
        'DQ Reservation policy drift'
    )

    plan_contract_sha = plan.get(
        'canonical_contract_sha256'
    )

    if plan_contract_sha is not None:
        require(
            plan_contract_sha
            == EXPECTED_CONTRACT_SHA256,
            'Canonical Contract SHA drift'
        )

    return {
        'readback_result_sha256':
            sha256_bytes(
                readback_result_bytes
            ),

        'dq_publication_result_sha256':
            sha256_bytes(
                dq_publication_result_bytes
            ),

        'dq_sha256':
            actual_dq_sha,
    }


def build_manifest(
    plan,
    readback_state,
    readback_result,
    readback_result_bytes,
    dq_publication_state,
    dq_publication_result,
    dq_publication_result_bytes,
    dq_bytes,
    git_checkpoint,
):
    evidence_hashes = validate_inputs(
        plan,
        readback_state,
        readback_result,
        readback_result_bytes,
        dq_publication_state,
        dq_publication_result,
        dq_publication_result_bytes,
        dq_bytes,
        git_checkpoint,
    )

    manifest = {
        'schema_version':
            'task003-visit-processed-manifest-v1',

        'task':
            'TASK-003',

        'step':
            'STEP-05G4',

        'status':
            'APPROVED',

        'publication_policy':
            'APPROVED_manifest_last',

        'run_id':
            EXPECTED_RUN_ID,

        'entity':
            'visit_occurrence',

        'source_system':
            'synthea',

        'uris': {
            'data':
                plan['data_uri'],

            'dq':
                plan['dq_uri'],

            'manifest':
                plan['manifest_uri'],
        },

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

            'canonical_contract_sha256':
                EXPECTED_CONTRACT_SHA256,

            'processed_data_verified_git_commit':
                git_checkpoint,
        },

        'artifacts': {
            'data': {
                'verified':
                    True,

                'independent_spark_readback':
                    True,
            },

            'dq': {
                'published':
                    True,

                'readback_verified':
                    True,

                'sha256':
                    EXPECTED_DQ_SHA256,

                'size_bytes':
                    EXPECTED_DQ_SIZE_BYTES,
            },
        },

        'approval_gate': {
            'processed_data_verified':
                True,

            'independent_s3_readback_passed':
                True,

            'candidate_published_verified':
                True,

            'dq_published':
                True,

            'dq_readback_verified':
                True,

            'manifest_must_be_last':
                True,

            'ready_for_manifest_publication':
                True,

            'reservation_must_remain_held_until_manifest_verification':
                True,

            'postgresql_write':
                False,
        },

        'evidence': {
            'independent_validation_result_sha256':
                evidence_hashes[
                    'readback_result_sha256'
                ],

            'dq_publication_result_sha256':
                evidence_hashes[
                    'dq_publication_result_sha256'
                ],

            'dq_sha256':
                evidence_hashes[
                    'dq_sha256'
                ],
        },
    }

    return manifest
