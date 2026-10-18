#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT="${HEALTHCARE_PROJECT_ROOT:-/data/spark/healthcare-data-platform}"
SOURCE="${BASH_SOURCE[0]:-}"
STAGE=''

echo '#### TASK003 STEP05G4A PROCESSED MANIFEST BUILDER SOURCE OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  [[ -z "$STAGE" ]] || rm -rf -- "$STAGE"

  echo "INSTALL_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G4A PROCESSED MANIFEST BUILDER SOURCE OUTPUT END ####'
  exit "$rc"
}

trap finish EXIT

[[ -n "$SOURCE" && -f "$SOURCE" ]] || {
  echo 'ERROR: installer must run from saved Bash file'
  exit 2
}

cd "$ROOT"

STAGE=$(
  mktemp -d \
    /data/spark/temp_shell/g4a.XXXXXXXX
)

mkdir -p \
  "$STAGE/apps/task003" \
  "$STAGE/tests/task003" \
  "$STAGE/scripts/task003"

# ============================================================
# 1. Deterministic final Manifest builder
# ============================================================

cat > "$STAGE/apps/task003/build_visit_processed_manifest.py" <<'PY_APP'
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
PY_APP

# ============================================================
# 2. Unit tests
# ============================================================

cat > "$STAGE/tests/task003/test_visit_processed_manifest_builder.py" <<'PY_TEST'
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
PY_TEST

# ============================================================
# 3. Local immutable Manifest build runner
# ============================================================

cat > "$STAGE/scripts/task003/05g4a-build-processed-manifest.sh" <<'RUNNER'
#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

EXPECTED_CHECKPOINT=beb6370cddafbe4c4e649f9a6cb9d949af0ee05e
EXPECTED_DQ_SHA=58e0ffc9e9b9a0ef5f34558807297b5ae2d6545d909fa340b0e2b713346b77c2
EXPECTED_DQ_SIZE=2607

echo '#### TASK003 STEP05G4A PROCESSED MANIFEST BUILD OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  echo "MANIFEST_BUILD_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G4A PROCESSED MANIFEST BUILD OUTPUT END ####'
  exit "$rc"
}

trap finish EXIT

[[ $# -eq 7 ]] || {
  echo "Usage:"
  echo "$0 PLAN READBACK_STATE READBACK_RESULT DQ_PUBLICATION_STATE DQ_PUBLICATION_RESULT DQ_FILE GIT_CHECKPOINT"
  exit 2
}

PLAN="$1"
READBACK_STATE="$2"
READBACK_RESULT="$3"
DQ_STATE="$4"
DQ_RESULT="$5"
DQ_FILE="$6"
CHECKPOINT="$7"

for path in \
  "$PLAN" \
  "$READBACK_STATE" \
  "$READBACK_RESULT" \
  "$DQ_STATE" \
  "$DQ_RESULT" \
  "$DQ_FILE"
do
  [[ -s "$path" && ! -L "$path" ]] || {
    echo "ERROR: missing or unsafe input: $path"
    exit 2
  }
done

cd "$ROOT"

echo '=== 1. Verify exact DQ-published Git checkpoint ==='

HEAD=$(git rev-parse HEAD)

echo "CURRENT_HEAD=$HEAD"
echo "EXPECTED_HEAD=$EXPECTED_CHECKPOINT"

[[ "$CHECKPOINT" == "$EXPECTED_CHECKPOINT" ]] || {
  echo 'ERROR: supplied Git checkpoint drift'
  exit 1
}

[[ "$HEAD" == "$EXPECTED_CHECKPOINT" ]] || {
  echo 'ERROR: repository HEAD drifted after DQ-published checkpoint'
  exit 1
}

git cat-file -e \
  "${CHECKPOINT}^{commit}"

echo 'DQ_PUBLISHED_GIT_CHECKPOINT=PASS'

echo '=== 2. Verify local DQ artifact remains exact ==='

DQ_SHA=$(
  sha256sum "$DQ_FILE" |
  awk '{print $1}'
)

DQ_SIZE=$(
  wc -c < "$DQ_FILE" |
  tr -d ' '
)

echo "DQ_SHA256=$DQ_SHA"
echo "DQ_SIZE_BYTES=$DQ_SIZE"

[[ "$DQ_SHA" == "$EXPECTED_DQ_SHA" ]] || {
  echo 'ERROR: local DQ SHA drift'
  exit 1
}

[[ "$DQ_SIZE" == "$EXPECTED_DQ_SIZE" ]] || {
  echo 'ERROR: local DQ size drift'
  exit 1
}

echo 'LOCAL_DQ_ARTIFACT=PASS'

RUN_ID=$(
  python3 -c '
import json,sys
print(json.load(open(sys.argv[1]))["run_id"])
' "$PLAN"
)

[[ "$RUN_ID" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$ ]] || {
  echo 'ERROR: unsafe run ID'
  exit 2
}

OUTDIR="$ROOT/runtime/reports/task003/step05/processed-manifest-builds/$RUN_ID"

mkdir -p "$OUTDIR"

MANIFEST_FILE="$OUTDIR/manifest.json"
STATE_FILE="$OUTDIR/run-state.json"

TMP_MANIFEST=$(
  mktemp \
    "$OUTDIR/.manifest.XXXXXXXX"
)

TMP_STATE=$(
  mktemp \
    "$OUTDIR/.run-state.XXXXXXXX"
)

cleanup() {
  [[ -z "${TMP_MANIFEST:-}" ]] || rm -f "$TMP_MANIFEST"
  [[ -z "${TMP_STATE:-}" ]] || rm -f "$TMP_STATE"
}

trap 'cleanup; finish' EXIT

echo '=== 3. Build deterministic APPROVED Manifest ==='

PYTHONPATH="$ROOT/apps/task003" \
python3 - \
  "$PLAN" \
  "$READBACK_STATE" \
  "$READBACK_RESULT" \
  "$DQ_STATE" \
  "$DQ_RESULT" \
  "$DQ_FILE" \
  "$CHECKPOINT" \
  "$TMP_MANIFEST" \
  <<'PY_BUILD'
import json
import sys
from pathlib import Path

from build_visit_processed_manifest import (
    build_manifest,
    canonical_json_bytes,
)

plan_path = Path(sys.argv[1])
readback_state_path = Path(sys.argv[2])
readback_result_path = Path(sys.argv[3])
dq_state_path = Path(sys.argv[4])
dq_result_path = Path(sys.argv[5])
dq_path = Path(sys.argv[6])

checkpoint = sys.argv[7]
target = Path(sys.argv[8])

plan = json.loads(
    plan_path.read_bytes()
)

readback_state = json.loads(
    readback_state_path.read_bytes()
)

readback_result_bytes = (
    readback_result_path.read_bytes()
)

readback_result = json.loads(
    readback_result_bytes
)

dq_state = json.loads(
    dq_state_path.read_bytes()
)

dq_result_bytes = (
    dq_result_path.read_bytes()
)

dq_result = json.loads(
    dq_result_bytes
)

dq_bytes = dq_path.read_bytes()

manifest = build_manifest(
    plan,
    readback_state,
    readback_result,
    readback_result_bytes,
    dq_state,
    dq_result,
    dq_result_bytes,
    dq_bytes,
    checkpoint,
)

target.write_bytes(
    canonical_json_bytes(
        manifest
    )
)

print('MANIFEST_CONTENT_BUILD=PASS')
print('MANIFEST_STATUS=' + manifest['status'])
print(
    'MANIFEST_PUBLICATION_POLICY='
    + manifest['publication_policy']
)
print('MANIFEST_RUN_ID=' + manifest['run_id'])
print(
    'MANIFEST_URI='
    + manifest['uris']['manifest']
)
print(
    'READY_FOR_MANIFEST_PUBLICATION='
    + str(
        manifest['approval_gate']
        ['ready_for_manifest_publication']
    ).upper()
)
PY_BUILD

MANIFEST_SHA=$(
  sha256sum "$TMP_MANIFEST" |
  awk '{print $1}'
)

MANIFEST_SIZE=$(
  wc -c < "$TMP_MANIFEST" |
  tr -d ' '
)

echo "MANIFEST_SHA256=$MANIFEST_SHA"
echo "MANIFEST_SIZE_BYTES=$MANIFEST_SIZE"

echo '=== 4. Install/reuse immutable local Manifest artifact ==='

if [[ -e "$MANIFEST_FILE" ]]; then

  [[ -f "$MANIFEST_FILE" && ! -L "$MANIFEST_FILE" ]] || {
    echo 'ERROR: unsafe existing Manifest artifact'
    exit 1
  }

  if cmp -s "$TMP_MANIFEST" "$MANIFEST_FILE"; then
    echo 'MANIFEST_LOCAL_ARTIFACT=REUSED_IDENTICAL'
  else
    echo 'ERROR: conflicting immutable local Manifest artifact'
    exit 4
  fi

else
  mv "$TMP_MANIFEST" "$MANIFEST_FILE"
  TMP_MANIFEST=''
  echo 'MANIFEST_LOCAL_ARTIFACT=CREATED'
fi

echo '=== 5. Build local G4A state ==='

python3 - \
  "$PLAN" \
  "$READBACK_STATE" \
  "$READBACK_RESULT" \
  "$DQ_STATE" \
  "$DQ_RESULT" \
  "$DQ_FILE" \
  "$MANIFEST_FILE" \
  "$CHECKPOINT" \
  "$TMP_STATE" \
  <<'PY_STATE'
import hashlib
import json
import sys
from pathlib import Path

plan = Path(sys.argv[1])
readback_state = Path(sys.argv[2])
readback_result = Path(sys.argv[3])
dq_state = Path(sys.argv[4])
dq_result = Path(sys.argv[5])
dq_file = Path(sys.argv[6])
manifest = Path(sys.argv[7])

checkpoint = sys.argv[8]
target = Path(sys.argv[9])


def sha(path):
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


manifest_obj = json.loads(
    manifest.read_bytes()
)

state = {
    'task':
        'TASK-003',

    'step':
        'STEP-05G4A',

    'status':
        'MANIFEST_BUILT_NOT_PUBLISHED',

    'run_id':
        manifest_obj['run_id'],

    'git_checkpoint':
        checkpoint,

    'plan_sha256':
        sha(plan),

    'independent_readback_state_sha256':
        sha(readback_state),

    'independent_validation_result_sha256':
        sha(readback_result),

    'dq_publication_state_sha256':
        sha(dq_state),

    'dq_publication_result_sha256':
        sha(dq_result),

    'dq_sha256':
        sha(dq_file),

    'manifest_sha256':
        sha(manifest),

    'manifest_size_bytes':
        manifest.stat().st_size,

    'data_uri':
        manifest_obj['uris']['data'],

    'dq_uri':
        manifest_obj['uris']['dq'],

    'manifest_uri':
        manifest_obj['uris']['manifest'],

    'approval_status':
        manifest_obj['status'],

    'publication_policy':
        manifest_obj['publication_policy'],

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

    'manifest_built':
        True,

    'manifest_published':
        False,

    'manifest_readback_verified':
        False,

    'reservation_released':
        False,

    'postgresql_write':
        False,
}

target.write_text(
    json.dumps(
        state,
        indent=2,
        sort_keys=True,
    )
    + '\n'
)

print('MANIFEST_BUILD_STATE=PASS')
PY_STATE

if [[ -e "$STATE_FILE" ]]; then

  [[ -f "$STATE_FILE" && ! -L "$STATE_FILE" ]] || {
    echo 'ERROR: unsafe existing Manifest build state'
    exit 1
  }

  if cmp -s "$TMP_STATE" "$STATE_FILE"; then
    echo 'MANIFEST_BUILD_STATE_ARTIFACT=REUSED_IDENTICAL'
  else
    echo 'ERROR: conflicting immutable Manifest build state'
    exit 4
  fi

else
  mv "$TMP_STATE" "$STATE_FILE"
  TMP_STATE=''
  echo 'MANIFEST_BUILD_STATE_ARTIFACT=CREATED'
fi

echo '=== 6. Validate final Manifest semantic gate ==='

python3 - \
  "$MANIFEST_FILE" \
  <<'PY_VERIFY'
import json
import sys
from pathlib import Path

manifest = json.loads(
    Path(sys.argv[1]).read_bytes()
)

assert manifest['status'] == 'APPROVED'

assert (
    manifest['publication_policy']
    == 'APPROVED_manifest_last'
)

gate = manifest['approval_gate']

assert gate['processed_data_verified'] is True
assert gate['independent_s3_readback_passed'] is True
assert gate['candidate_published_verified'] is True
assert gate['dq_published'] is True
assert gate['dq_readback_verified'] is True

assert gate['manifest_must_be_last'] is True
assert gate['ready_for_manifest_publication'] is True

assert (
    gate[
        'reservation_must_remain_held_until_manifest_verification'
    ]
    is True
)

assert gate['postgresql_write'] is False

assert manifest['metrics']['rows'] == 5799

assert (
    manifest['metrics']['unique_business_keys']
    == 5799
)

assert (
    manifest['metrics']['referenced_persons']
    == 113
)

assert (
    manifest['metrics']['contract_field_count']
    == 36
)

assert (
    manifest['metrics']['visit_occurrence_id_present']
    is False
)

assert (
    manifest['artifacts']['dq']['sha256']
    == '58e0ffc9e9b9a0ef5f34558807297b5ae2d6545d909fa340b0e2b713346b77c2'
)

assert (
    manifest['artifacts']['dq']['size_bytes']
    == 2607
)

print('FINAL_MANIFEST_APPROVAL_GATE=PASS')
print('MANIFEST_STATUS=APPROVED')
print('MANIFEST_MUST_BE_LAST=YES')
print('READY_FOR_MANIFEST_PUBLICATION=YES')
PY_VERIFY

echo "MANIFEST_LOCAL_FILE=$MANIFEST_FILE"
echo "MANIFEST_BUILD_STATE_FILE=$STATE_FILE"

echo 'STEP05G4A_PROCESSED_MANIFEST_BUILD=PASS'

echo 'PROCESSED_DATA_VERIFIED=YES'
echo 'DQ_PUBLISHED=YES'
echo 'DQ_READBACK_VERIFIED=YES'

echo 'MANIFEST_BUILT=YES'
echo 'MANIFEST_APPROVED=YES'
echo 'MANIFEST_PUBLISHED=NO'
echo 'MANIFEST_READBACK_VERIFIED=NO'

echo 'RESERVATION_STILL_HELD=YES'

echo 'S3_MUTATION=NO'
echo 'DATABASE_WRITE=NO'
RUNNER

# ============================================================
# 4. Static syntax/tests
# ============================================================

echo '=== 1. Syntax validation ==='

python3 - "$STAGE" <<'PY_AST'
import ast
import sys
from pathlib import Path

root = Path(sys.argv[1])

for rel in (
    'apps/task003/build_visit_processed_manifest.py',
    'tests/task003/test_visit_processed_manifest_builder.py',
):
    ast.parse(
        (root / rel).read_text(),
        filename=rel,
    )

print('PROCESSED_MANIFEST_PYTHON_AST=PASS')
PY_AST

bash -n \
  "$STAGE/scripts/task003/05g4a-build-processed-manifest.sh"

echo 'PROCESSED_MANIFEST_RUNNER_BASH_SYNTAX=PASS'

echo '=== 2. Run Manifest builder unit tests ==='

PYTHONPATH="$STAGE/apps/task003" \
python3 -m unittest discover \
  -s "$STAGE/tests/task003" \
  -p 'test_visit_processed_manifest_builder.py' \
  -v

echo 'PROCESSED_MANIFEST_TESTS=PASS'

echo '=== 3. Static Manifest-last boundary ==='

python3 - "$STAGE" <<'PY_STATIC'
import sys
from pathlib import Path

root = Path(sys.argv[1])

app = (
    root
    / 'apps/task003/build_visit_processed_manifest.py'
).read_text()

runner = (
    root
    / 'scripts/task003/05g4a-build-processed-manifest.sh'
).read_text()

required = (
    "'status':\n            'APPROVED'",
    "'publication_policy':\n            'APPROVED_manifest_last'",
    "'manifest_must_be_last':",
    "'ready_for_manifest_publication':",
    "'reservation_must_remain_held_until_manifest_verification':",
)

for token in required:
    assert token in app, token

for source in (
    app,
    runner,
):
    for forbidden in (
        'aws s3 cp',
        'aws s3api put-object',
        'fs.create(',
        'copyFromLocalFile',
        'kubectl create',
        'kubectl apply',
        'kubectl delete',
        'INSERT INTO',
        'UPDATE ',
        'DELETE FROM',
    ):
        assert forbidden not in source, forbidden

assert 'MANIFEST_PUBLISHED=NO' in runner
assert 'S3_MUTATION=NO' in runner
assert 'DATABASE_WRITE=NO' in runner

print('MANIFEST_BUILD_ONLY_BOUNDARY=PASS')
print('MANIFEST_LAST_POLICY=PASS')
print('S3_MUTATION_PATH_ABSENT=PASS')
print('DATABASE_MUTATION_PATH_ABSENT=PASS')
PY_STATIC

# ============================================================
# 5. Canonical conflict/install
# ============================================================

echo '=== 4. Canonical conflict check ==='

FILES=(
  apps/task003/build_visit_processed_manifest.py
  tests/task003/test_visit_processed_manifest_builder.py
  scripts/task003/05g4a-build-processed-manifest.sh
)

GEN=scripts/task003/05g4a-prepare-processed-manifest-builder.sh

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

  mkdir -p \
    "$(dirname "$ROOT/$rel")"

  if [[ -f "$ROOT/$rel" ]] &&
     cmp -s "$STAGE/$rel" "$ROOT/$rel"
  then
    echo "CANONICAL_SOURCE_REUSED=$rel"
  else
    install \
      -m 755 \
      "$STAGE/$rel" \
      "$ROOT/$rel"

    case "$rel" in
      *.py)
        chmod 644 "$ROOT/$rel"
        ;;
    esac

    echo "CANONICAL_SOURCE_READY=$rel"
  fi

done

mkdir -p \
  "$ROOT/scripts/task003"

if [[ -f "$ROOT/$GEN" ]]; then
  echo "CANONICAL_GENERATOR_REUSED=$GEN"
else
  install \
    -m 755 \
    "$SOURCE" \
    "$ROOT/$GEN"

  echo "CANONICAL_GENERATOR_READY=$GEN"
fi

echo 'STEP05G4A_SOURCE_AND_TESTS=PASS'

echo 'MANIFEST_PUBLISHER_EXECUTED=NO'
echo 'MANIFEST_PUBLISHED=NO'
echo 'RESERVATION_RELEASED=NO'

echo 'K8S_MUTATION=NO'
echo 'S3_MUTATION=NO'
echo 'DATABASE_MUTATION=NO'
echo 'GIT_COMMIT=NO'
