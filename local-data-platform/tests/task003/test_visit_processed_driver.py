"""Pure negative tests for the future Spark driver. No Spark imports/execution."""
import ast
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'spark/apps/visit'))
from run_visit_processed_writer import (
    MOUNTED_SOURCES, ARTIFACTS, digest, verify_bundle,
    verify_live_lock_payload, verify_schema,
)


class DriverTests(unittest.TestCase):
    def setUp(self):
        self.request = {
            'kind': 'ConfigMap', 'immutable': True,
            'metadata': {
                'name': 'visit-proc-lock-abc', 'namespace': 'dw-spark',
                'labels': {'healthcare-task': 'task003'},
            },
            'data': {'reservation.json': '{}'},
        }
        self.permit = {
            'reservation_uid': 'abc-123',
            'reservation_resource_version': '25',
        }
        self.live = copy.deepcopy(self.request)
        self.live['metadata'].update(uid='abc-123', resourceVersion='25')

    def test_live_lock_payload(self):
        self.assertTrue(verify_live_lock_payload(self.live, self.request, self.permit))

    def test_live_uid_drift_rejected(self):
        self.live['metadata']['uid'] = 'another'
        with self.assertRaisesRegex(ValueError, 'UID'):
            verify_live_lock_payload(self.live, self.request, self.permit)

    def test_live_version_drift_rejected(self):
        self.live['metadata']['resourceVersion'] = '26'
        with self.assertRaisesRegex(ValueError, 'resourceVersion'):
            verify_live_lock_payload(self.live, self.request, self.permit)

    def test_live_data_drift_rejected(self):
        self.live['data']['reservation.json'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'changed'):
            verify_live_lock_payload(self.live, self.request, self.permit)

    def test_live_mutable_rejected(self):
        self.live['immutable'] = False
        with self.assertRaisesRegex(ValueError, 'mutable'):
            verify_live_lock_payload(self.live, self.request, self.permit)

    def test_live_labels_drift_rejected(self):
        self.live['metadata']['labels'] = {}
        with self.assertRaisesRegex(ValueError, 'labels'):
            verify_live_lock_payload(self.live, self.request, self.permit)

    def test_schema_contract(self):
        fields = [{'name': 'source_system', 'type': 'string'},
                  {'name': 'person_id', 'type': 'integer'}]
        self.assertEqual(verify_schema([('source_system', 'string'), ('person_id', 'int')],
                                       fields), [('source_system', 'string'), ('person_id', 'int')])

    def test_schema_drift_rejected(self):
        with self.assertRaisesRegex(ValueError, 'schema'):
            verify_schema([('x', 'string')], [{'name': 'y', 'type': 'string'}])

    def test_visit_id_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Visit ID'):
            verify_schema([('visit_occurrence_id', 'int')],
                          [{'name': 'visit_occurrence_id', 'type': 'integer'}])

    def test_no_automatic_import_side_effects(self):
        src = (ROOT / 'spark/apps/visit/run_visit_processed_writer.py').read_text()
        tree = ast.parse(src)
        self.assertFalse(any(isinstance(n, ast.Call) for n in tree.body))
        self.assertNotIn('mode("overwrite")', src)
        self.assertNotIn("mode('overwrite')", src)

    def test_source_inventory(self):
        self.assertEqual(len(MOUNTED_SOURCES), 9)
        self.assertEqual(len(ARTIFACTS), 6)


if __name__ == '__main__':
    unittest.main()
