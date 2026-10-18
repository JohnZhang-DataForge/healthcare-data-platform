import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(
    0,
    str(ROOT / 'spark/apps/visit')
)

from publish_processed_manifest import (
    EXPECTED_DQ_SHA256,
    EXPECTED_DQ_SIZE_BYTES,
    EXPECTED_MANIFEST_SHA256,
    EXPECTED_MANIFEST_SIZE_BYTES,
    EXPECTED_RUN_ID,
    canonical_to_s3a,
    read_mounted_file,
    validate_publication_inputs,
)


def fixture():
    plan = {
        'run_id':
            EXPECTED_RUN_ID,

        'data_uri':
            's3://health-processed/x/data/',

        'dq_uri':
            's3://health-processed/x/dq/result.json',

        'manifest_uri':
            's3://health-processed/x/manifest.json',
    }

    state = {
        'task':
            'TASK-003',

        'step':
            'STEP-05G4A',

        'status':
            'MANIFEST_BUILT_NOT_PUBLISHED',

        'run_id':
            EXPECTED_RUN_ID,

        'approval_status':
            'APPROVED',

        'publication_policy':
            'APPROVED_manifest_last',

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

        'dq_uri':
            plan['dq_uri'],

        'manifest_built':
            True,

        'manifest_published':
            False,

        'manifest_readback_verified':
            False,

        'manifest_sha256':
            EXPECTED_MANIFEST_SHA256,

        'manifest_size_bytes':
            EXPECTED_MANIFEST_SIZE_BYTES,

        'manifest_uri':
            plan['manifest_uri'],

        'reservation_released':
            False,

        'postgresql_write':
            False,
    }

    return plan, state


class ManifestPublisherTests(
    unittest.TestCase
):

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
                / '..20261009_231500'
            )

            version.mkdir()

            target = (
                version
                / 'manifest.json'
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
                / 'manifest.json'
            )

            projected.symlink_to(
                Path('..data')
                / 'manifest.json'
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
                / 'manifest.json'
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

    def test_manifest_already_marked_published_rejected(self):
        plan, state = fixture()

        state[
            'manifest_published'
        ] = True

        with self.assertRaisesRegex(
            ValueError,
            'already marked published',
        ):
            validate_publication_inputs(
                plan,
                state,
                b'x',
            )

    def test_dq_not_published_rejected(self):
        plan, state = fixture()

        state[
            'dq_published'
        ] = False

        with self.assertRaisesRegex(
            ValueError,
            'DQ not published',
        ):
            validate_publication_inputs(
                plan,
                state,
                b'x',
            )

    def test_dq_readback_not_verified_rejected(self):
        plan, state = fixture()

        state[
            'dq_readback_verified'
        ] = False

        with self.assertRaisesRegex(
            ValueError,
            'DQ readback not verified',
        ):
            validate_publication_inputs(
                plan,
                state,
                b'x',
            )

    def test_reservation_released_rejected(self):
        plan, state = fixture()

        state[
            'reservation_released'
        ] = True

        with self.assertRaisesRegex(
            ValueError,
            'Reservation released',
        ):
            validate_publication_inputs(
                plan,
                state,
                b'x',
            )

    def test_manifest_sha_drift_rejected(self):
        plan, state = fixture()

        blob = (
            b'x'
            * EXPECTED_MANIFEST_SIZE_BYTES
        )

        with self.assertRaisesRegex(
            ValueError,
            'Manifest SHA256 drift',
        ):
            validate_publication_inputs(
                plan,
                state,
                blob,
            )

    def test_s3_write_uses_create_stream(self):
        source = (
            ROOT
            / 'spark/apps/visit/'
            'publish_processed_manifest.py'
        ).read_text()

        self.assertIn(
            'output = fs.create(',
            source,
        )

        self.assertIn(
            'bytearray(',
            source,
        )

        self.assertNotIn(
            'fs.copyFromLocalFile(',
            source,
        )

    def test_manifest_constants_match_real_artifact(self):
        path = (
            ROOT
            / 'runtime/reports/task003/step05/'
            'processed-manifest-builds/'
            'visit-proc-20261009t192437z-2081886/'
            'manifest.json'
        )

        if not path.is_file():
            self.skipTest(
                'real runtime artifact unavailable'
            )

        blob = path.read_bytes()

        self.assertEqual(
            len(blob),
            EXPECTED_MANIFEST_SIZE_BYTES,
        )

        self.assertEqual(
            hashlib.sha256(
                blob
            ).hexdigest(),
            EXPECTED_MANIFEST_SHA256,
        )

    def test_dq_constants(self):
        self.assertEqual(
            EXPECTED_DQ_SIZE_BYTES,
            2607,
        )

        self.assertEqual(
            EXPECTED_DQ_SHA256,
            '58e0ffc9e9b9a0ef5f34558807297b5ae2d6545d909fa340b0e2b713346b77c2',
        )


if __name__ == '__main__':
    unittest.main()
