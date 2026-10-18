import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'apps/task003'))
from verify_encounter_remote_metadata import verify_metadata


class RemoteMetadataTests(unittest.TestCase):
    def setUp(self):
        self.context = dict(
            source='synthea', source_version='v3.3.0',
            batch_id='test', ingest_date='2026-10-08',
            processing_run_id='processing-test',
            raw_publish_run_id='raw-test', expected_rows=3,
            raw_data_uri='s3://health-raw/test/data/',
            dq_uri='s3://health-raw/test/dq/result.json',
        )
        common = {k: self.context[k] for k in (
            'source', 'source_version', 'batch_id', 'ingest_date',
            'processing_run_id', 'raw_publish_run_id',
        )}
        common.update(
            entity='encounter', canonical_version='v1',
            expected_rows=3, raw_rows=3, raw_unique_keys=3,
        )
        checks = (
            'canonical_schema canonical_required_fields canonical_metadata '
            'canonical_primary_key raw_write raw_readback'
        ).split()
        self.dq = dict(
            common, status='PASS', checks={k: 'PASS' for k in checks}
        )
        self.manifest = dict(common, status='APPROVED', data=dict(
            uri=self.context['raw_data_uri'], format='parquet', row_count=3,
            primary_key=['source_system', 'source_encounter_id'],
            unique_primary_keys=3,
        ))
        self.seal()

    def seal(self):
        self.db = json.dumps(self.dq).encode()
        self.context['dq_sha256'] = hashlib.sha256(self.db).hexdigest()
        self.manifest['dq'] = dict(
            status='PASS', uri=self.context['dq_uri'],
            sha256=self.context['dq_sha256'], readback_sha256='PASS',
        )
        self.mb = json.dumps(self.manifest).encode()
        self.context['raw_manifest_sha256'] = hashlib.sha256(self.mb).hexdigest()

    def test_valid_metadata(self):
        verify_metadata(self.context, self.mb, self.db)

    def test_tampered_download(self):
        with self.assertRaises(ValueError):
            verify_metadata(self.context, self.mb + b' ', self.db)
        with self.assertRaises(ValueError):
            verify_metadata(self.context, self.mb, self.db + b' ')

    def test_reject_semantic_changes_even_with_matching_hashes(self):
        for doc, key, value in (
            ('manifest', 'status', 'DRAFT'),
            ('manifest', 'raw_publish_run_id', 'other-run'),
            ('manifest', 'raw_rows', True),
            ('dq', 'status', 'FAIL'),
        ):
            with self.subTest(doc=doc, key=key):
                self.setUp()
                getattr(self, doc)[key] = value
                self.seal()
                with self.assertRaises(ValueError):
                    verify_metadata(self.context, self.mb, self.db)


if __name__ == '__main__':
    unittest.main()
