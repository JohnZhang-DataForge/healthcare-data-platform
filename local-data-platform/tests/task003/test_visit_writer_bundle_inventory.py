import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(
    0,
    str(ROOT / 'apps/task003')
)

from prepare_visit_writer_bundle_inventory import (
    SOURCE_PATHS,
    build_inventory,
    sha,
)


def pack(value):
    return (
        json.dumps(value, sort_keys=True) + '\n'
    ).encode()


class TestBundleInventory(unittest.TestCase):

    def setUp(self):
        self.sources = {
            key: (key + '\n').encode()
            for key in SOURCE_PATHS
        }

        self.sources['run_visit_processed_writer.py'] = (
            b'MOUNTED_SOURCES = '
            + repr(tuple(SOURCE_PATHS)).encode()
            + b'\n'
            + b'ARTIFACTS = ('
            + b'"processed-plan.json", '
            + b'"processed-write-intent.json", '
            + b'"reservation-create.json", '
            + b'"fresh-s3-listing.json", '
            + b'"write-permit.json", '
            + b'"step05f2-run-state.json")\n'
        )

        self.sources['processed_visit_writer_core.py'] = (
            b'# safe library\n'
        )

        self.f2 = {
            'task': 'TASK-003',
            'step': 'STEP-05F2',
            'status': 'PASS',
            'input': {
                'mounted_file_sha256': {
                    key: sha(self.sources[key])
                    for key in SOURCE_PATHS
                }
            },
            'result': {
                'candidate_rows': 3,
                'referenced_persons': 2,
            },
        }

        self.f2bytes = pack(self.f2)

        self.plan = {
            'task': 'TASK-003',
            'step': 'STEP-05G1',
            'status': 'PLANNED',
            'run_id': 'test-run',
            'source_f2_evidence_sha256':
                sha(self.f2bytes),
            'expected_rows': 3,
            'expected_persons': 2,
            'data_uri':
                's3://health-processed/test-run/data/',
            'published': False,
            'persisted': False,
        }

        self.planbytes = pack(self.plan)

        self.intent = {
            'task': 'TASK-003',
            'step': 'STEP-05G2C1',
            'status': 'PREFLIGHT_SNAPSHOT_ONLY',
            'run_id': 'test-run',
            'step05f2_sha256':
                sha(self.f2bytes),
            'plan_sha256':
                sha(self.planbytes),
            'expected_rows': 3,
            'expected_persons': 2,
            'write_authorized': False,
            'writer_reservation_acquired': False,
            'source_sha256': {
                path: sha(self.sources[key])
                for key, path in SOURCE_PATHS.items()
            },
        }

        self.intentbytes = pack(self.intent)

        self.lock = {
            'apiVersion': 'v1',
            'kind': 'ConfigMap',
            'immutable': True,
            'metadata': {
                'namespace': 'dw-spark',
                'name': 'visit-proc-lock-test',
            },
            'data': {
                'reservation.json': json.dumps({
                    'run_id': 'test-run',
                    'plan_sha256':
                        sha(self.planbytes),
                    'write_intent_sha256':
                        sha(self.intentbytes),
                    'mode': 'EXCLUSIVE_CREATE_ONLY',
                    'write_authorized': False,
                })
            },
        }

        self.lockbytes = pack(self.lock)

    def check(self):
        return build_inventory(
            'test-run',
            self.f2bytes,
            self.planbytes,
            self.intentbytes,
            self.lockbytes,
            self.sources,
        )

    def test_valid_inventory_no_authorization(self):
        result = self.check()

        self.assertEqual(
            len(result['source_files']), 11
        )
        self.assertEqual(
            len(result['static_artifacts']), 4
        )
        self.assertFalse(
            result['write_authorized']
        )
        self.assertFalse(
            result['configmap_created']
        )

    def test_stable(self):
        self.assertEqual(
            self.check(),
            self.check(),
        )

    def test_source_drift(self):
        self.sources['canonical_gate.py'] = b'changed'

        with self.assertRaisesRegex(
            ValueError, 'source SHA'
        ):
            self.check()

    def test_intent_drift(self):
        self.intent['expected_rows'] = 42
        self.intentbytes = pack(self.intent)

        self.lock['data']['reservation.json'] = (
            json.dumps({
                'run_id': 'test-run',
                'plan_sha256': sha(self.planbytes),
                'write_intent_sha256':
                    sha(self.intentbytes),
                'mode': 'EXCLUSIVE_CREATE_ONLY',
                'write_authorized': False,
            })
        )

        self.lockbytes = pack(self.lock)

        with self.assertRaisesRegex(
            ValueError, 'intent counts'
        ):
            self.check()

    def test_f2_drift(self):
        self.f2['result']['candidate_rows'] = 4
        self.f2bytes = pack(self.f2)

        with self.assertRaisesRegex(
            ValueError, 'plan F2 pin'
        ):
            self.check()

    def test_fake_lock(self):
        self.lock['immutable'] = False
        self.lockbytes = pack(self.lock)

        with self.assertRaisesRegex(
            ValueError, 'reservation definition'
        ):
            self.check()

    def test_early_authorization(self):
        self.intent['write_authorized'] = True
        self.intentbytes = pack(self.intent)

        with self.assertRaises(ValueError):
            self.check()

    def test_missing_file(self):
        del self.sources['visit-class-v1.json']

        with self.assertRaisesRegex(
            ValueError, 'source inventory'
        ):
            self.check()

    def test_driver_mount_drift(self):
        self.sources['run_visit_processed_writer.py'] = (
            b'MOUNTED_SOURCES=("x",)\n'
            b'ARTIFACTS=("y",)\n'
        )

        with self.assertRaisesRegex(
            ValueError, 'driver mount drift'
        ):
            self.check()

    def test_future_permit_is_required(self):
        self.assertEqual(
            self.check()['future_artifacts_required'],
            [
                'fresh-s3-listing.json',
                'write-permit.json',
            ],
        )


if __name__ == '__main__':
    unittest.main()
