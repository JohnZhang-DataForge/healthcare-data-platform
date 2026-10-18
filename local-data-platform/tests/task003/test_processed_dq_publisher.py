import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(
    0,
    str(ROOT / 'spark/apps/visit')
)

from publish_processed_dq import (
    EXPECTED_DQ_SHA256,
    EXPECTED_DQ_SIZE_BYTES,
    EXPECTED_RUN_ID,
    canonical_to_s3a,
    read_mounted_file,
    validate_publication_inputs,
)


def fixture():
    # Fixed-size synthetic bytes are not used for the
    # successful validation test, because production constants
    # intentionally pin the real G3A artifact.
    plan = {
        'run_id':
            EXPECTED_RUN_ID,

        'dq_uri':
            's3://health-processed/x/dq/result.json',

        'manifest_uri':
            's3://health-processed/x/manifest.json',
    }

    state = {
        'task':
            'TASK-003',

        'step':
            'STEP-05G3A',

        'status':
            'DQ_BUILT_NOT_PUBLISHED',

        'run_id':
            EXPECTED_RUN_ID,

        'processed_data_verified':
            True,

        's3_write_verified':
            True,

        'candidate_published_verified':
            True,

        'dq_published':
            False,

        'manifest_published':
            False,

        'reservation_released':
            False,

        'postgresql_write':
            False,

        'dq_result_sha256':
            EXPECTED_DQ_SHA256,

        'dq_result_size_bytes':
            EXPECTED_DQ_SIZE_BYTES,

        'dq_uri':
            plan['dq_uri'],

        'manifest_uri':
            plan['manifest_uri'],
    }

    return plan, state


class DQPublisherTests(
    unittest.TestCase
):

    def test_s3_write_uses_create_stream_not_copy_from_local(self):
        source = (
            ROOT
            / 'spark/apps/visit/publish_processed_dq.py'
        ).read_text()

        self.assertIn(
            'output = fs.create(',
            source,
        )

        self.assertIn(
            'bytearray(',
            source,
        )

        self.assertIn(
            'dq_bytes',
            source,
        )

        self.assertNotIn(
            'fs.copyFromLocalFile(',
            source,
        )

    def test_uri_conversion(self):
        self.assertEqual(
            canonical_to_s3a(
                's3://health-processed/a'
            ),
            's3a://health-processed/a',
        )

    def test_noncanonical_uri_rejected(self):
        with self.assertRaises(
            ValueError
        ):
            canonical_to_s3a(
                's3a://health-processed/a'
            )

    def test_kubernetes_projected_file_allowed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)

            version = (
                root
                / '..20261009_230000'
            )

            version.mkdir()

            target = (
                version
                / 'dq-result.json'
            )

            target.write_bytes(
                b'hello\n'
            )

            (
                root
                / '..data'
            ).symlink_to(
                version.name,
                target_is_directory=True,
            )

            projected = (
                root
                / 'dq-result.json'
            )

            projected.symlink_to(
                Path('..data')
                / 'dq-result.json'
            )

            self.assertEqual(
                read_mounted_file(
                    projected
                ),
                b'hello\n',
            )

    def test_projected_file_escape_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)

            mount = base / 'mount'
            mount.mkdir()

            outside = (
                base
                / 'outside.json'
            )

            outside.write_bytes(
                b'{}\n'
            )

            link = (
                mount
                / 'dq-result.json'
            )

            link.symlink_to(
                Path('..')
                / 'outside.json'
            )

            with self.assertRaisesRegex(
                ValueError,
                'escapes directory',
            ):
                read_mounted_file(
                    link
                )

    def test_manifest_published_rejected_before_sha(self):
        plan, state = fixture()

        state['manifest_published'] = True

        with self.assertRaisesRegex(
            ValueError,
            'Manifest already published',
        ):
            validate_publication_inputs(
                plan,
                state,
                b'x',
            )

    def test_reservation_released_rejected_before_sha(self):
        plan, state = fixture()

        state['reservation_released'] = True

        with self.assertRaisesRegex(
            ValueError,
            'Reservation released',
        ):
            validate_publication_inputs(
                plan,
                state,
                b'x',
            )

    def test_dq_marked_published_rejected_before_sha(self):
        plan, state = fixture()

        state['dq_published'] = True

        with self.assertRaisesRegex(
            ValueError,
            'DQ already marked published',
        ):
            validate_publication_inputs(
                plan,
                state,
                b'x',
            )

    def test_sha_drift_rejected(self):
        plan, state = fixture()

        with self.assertRaisesRegex(
            ValueError,
            'DQ SHA256 drift',
        ):
            validate_publication_inputs(
                plan,
                state,
                b'x' * EXPECTED_DQ_SIZE_BYTES,
            )

    def test_constants_match_real_artifact(self):
        path = (
            ROOT
            / 'runtime/reports/task003/step05/'
            'processed-dq-builds/'
            'visit-proc-20261009t192437z-2081886/'
            'dq-result.json'
        )

        if not path.is_file():
            self.skipTest(
                'real runtime artifact unavailable'
            )

        blob = path.read_bytes()

        self.assertEqual(
            len(blob),
            EXPECTED_DQ_SIZE_BYTES,
        )

        self.assertEqual(
            hashlib.sha256(
                blob
            ).hexdigest(),
            EXPECTED_DQ_SHA256,
        )


if __name__ == '__main__':
    unittest.main()
