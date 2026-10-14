"""NEW_ONLY separate v2 routing and independent 18-object S3 readback tests."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/"apps/synthea/new_only"),str(ROOT/"apps/task004"),str(ROOT/"apps/landing_discovery")]
from test_publish_v2_verified import prepared,InMemoryS3,CONTRACT,DATE
from publish_v2_verified import build_draft,publish
from verify_v2_ready import verify,V2ReadyBlocked
import entrypoint

class V2ReaderPublisherTests(unittest.TestCase):
    def test_v2_runtime_has_explicit_distinct_phases(self):
        for phase,script in (("validate-v2","publish_v2_verified.py"),
                              ("publish-v2","publish_v2_verified.py"),
                              ("replay-v2","publish_v2_verified.py"),
                              ("verify-v2","verify_v2_ready.py")):
            argv=entrypoint.command(phase,"gh-38484300008")
            self.assertTrue(any(part.endswith(script) for part in argv))
            self.assertIn("gh-38484300008",argv)
        self.assertTrue(any(x.endswith("/publish_v1_verified.py") for x in entrypoint.command("publish","gh-38484300008")))

    def test_independent_v2_reader_matches_frozen_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            state,request,_=prepared(Path(tmp))
            draft,csv=build_draft(state,request,CONTRACT)
            s3=InMemoryS3()
            with patch.dict(os.environ,{"NEW_ONLY_READONLY_SOURCE_AUDIT":"PASS",
                                       "NEW_ONLY_PG_SOURCE_AUDIT":"PASS"}):
                result=publish(s3,draft,csv,CONTRACT,ingest_date=DATE)
            verified=verify(s3,request,state,CONTRACT)
            self.assertEqual(verified["manifest_sha256"],result["manifest_sha256"])
            self.assertEqual(verified["person_rows"],1)
            self.assertEqual(verified["encounter_rows"],1)
            self.assertEqual(verified["zero_auxiliary_count"],16)
            self.assertFalse(verified["db_mutation"])

    def test_independent_reader_rejects_corrupt_s3_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            state,request,_=prepared(Path(tmp))
            draft,csv=build_draft(state,request,CONTRACT)
            s3=InMemoryS3()
            with patch.dict(os.environ,{"NEW_ONLY_READONLY_SOURCE_AUDIT":"PASS",
                                       "NEW_ONLY_PG_SOURCE_AUDIT":"PASS"}):
                publish(s3,draft,csv,CONTRACT,ingest_date=DATE)
            corrupt=next(key for key in s3.objects if key.endswith("/patients.csv"))
            s3.bad_read=corrupt
            with self.assertRaisesRegex(V2ReadyBlocked,"V2_REMOTE_OBJECT_SHA"):
                verify(s3,request,state,CONTRACT)

if __name__=="__main__":unittest.main()
