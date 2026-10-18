"""Independent NEW_ONLY v2 Publisher contract and last-object safety tests."""
import copy
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/"apps/synthea/new_only"),str(ROOT/"apps/task004")]
from test_publish_v1_verified import fixture
from publish_v2_verified import build_draft,publish,V2PublishBlocked
from prepublish_gate import audit_local
from validate_new_only_v2_manifest import source_contract,validate_v2_manifest
from publish_synthea_landing import PublishError
CONTRACT=ROOT/"contracts/synthea/new-only/csv-contract-v2.json"
REQ="gh-38484300008"
DATE="2026-10-14"


class InMemoryS3:
    def __init__(self):
        self.objects={}
        self.put_order=[]
        self.bad_read=None
    def head_bucket(self):return None
    def list_keys(self,prefix):
        return sorted(k for k in self.objects if k.startswith(prefix))
    def head_object(self,key):return key in self.objects
    def get_object(self,key):
        result=self.objects[key]
        if key==self.bad_read:return b"SHA-CORRUPTED"+result
        return result
    def put_object(self,key,body):
        if key in self.objects:
            raise AssertionError("overwrite forbidden "+key)
        self.objects[key]=bytes(body)
        self.put_order.append(key)


def prepared(root):
    state,request,folder=fixture(root)
    contract,_=source_contract(CONTRACT)
    for obj in contract["files"]:
        if obj["dataset"] in ("patients","encounters"):
            continue
        file=folder/"csv"/obj["filename"]
        file.write_text(",".join(obj["header"])+"\n")
    measured=audit_local(folder/"csv",CONTRACT)
    marker_file=folder/"validated.json"
    marker=json.loads(marker_file.read_text())
    marker["files"]={key:{"rows":v["row_count"],"sha256":v["sha256"]}
                     for key,v in measured["files"].items()}
    marker_file.write_text(json.dumps(marker))
    return state,request,folder


class V2PublisherTests(unittest.TestCase):
    def test_header_only_auxiliaries_real_csv_bytes_draft(self):
        with tempfile.TemporaryDirectory() as tmp:
            state,request,folder=prepared(Path(tmp))
            draft,local=build_draft(state,request,CONTRACT)
            self.assertEqual(draft["manifest_version"],"2.0")
            self.assertEqual(sum(x["row_count"]==0 for x in draft["files"]),16)
            self.assertEqual(sum(x["row_count"]>0 for x in draft["files"]),2)
            self.assertTrue(all(x["size_bytes"]>0 for x in draft["files"]))
            self.assertEqual(local,folder/"csv")

    def test_manifest_last_readback_and_exact_sha_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            state,request,_=prepared(Path(tmp))
            draft,directory=build_draft(state,request,CONTRACT)
            remote=InMemoryS3()
            with patch.dict(os.environ,{"NEW_ONLY_READONLY_SOURCE_AUDIT":"PASS",
                                       "NEW_ONLY_PG_SOURCE_AUDIT":"PASS"}):
                result=publish(remote,draft,directory,CONTRACT,ingest_date=DATE)
            self.assertEqual(result["publish_mode"],"PUBLISHED_NEW")
            self.assertEqual(len(remote.objects),19)
            self.assertEqual(len(remote.put_order),19)
            self.assertTrue(remote.put_order[-1].endswith("/manifest.json"))
            raw=remote.objects[remote.put_order[-1]]
            self.assertEqual(hashlib.sha256(raw).hexdigest(),result["manifest_sha256"])
            self.assertEqual(len(validate_v2_manifest(json.loads(raw),draft["batch_id"],
                            result["manifest_uri"],CONTRACT)),18)
            result2=publish(remote,draft,directory,CONTRACT,replay=True,ingest_date=DATE)
            self.assertEqual(result2["publish_mode"],"REUSE_EXISTING")
            self.assertEqual(result2["manifest_sha256"],result["manifest_sha256"])
            self.assertEqual(len(remote.put_order),19)

    def test_fresh_without_audits_refuses_any_s3_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            state,request,_=prepared(Path(tmp))
            draft,directory=build_draft(state,request,CONTRACT)
            remote=InMemoryS3()
            with patch.dict(os.environ,{"NEW_ONLY_READONLY_SOURCE_AUDIT":"DENY",
                                       "NEW_ONLY_PG_SOURCE_AUDIT":"DENY"}):
                with self.assertRaisesRegex(V2PublishBlocked,"HISTORIC_S3_AUDIT_MISSING"):
                    publish(remote,draft,directory,CONTRACT,ingest_date=DATE)
            self.assertFalse(remote.objects)

    def test_incomplete_existing_ready_manifest_does_not_repair(self):
        with tempfile.TemporaryDirectory() as tmp:
            state,request,_=prepared(Path(tmp))
            draft,directory=build_draft(state,request,CONTRACT)
            s3=InMemoryS3()
            with patch.dict(os.environ,{"NEW_ONLY_READONLY_SOURCE_AUDIT":"PASS",
                                       "NEW_ONLY_PG_SOURCE_AUDIT":"PASS"}):
                good=publish(s3,draft,directory,CONTRACT,ingest_date=DATE)
            to_delete=next(k for k in s3.objects if k.endswith("/patients.csv"))
            s3.objects.pop(to_delete)
            n=len(s3.put_order)
            with self.assertRaisesRegex(V2PublishBlocked,"MANIFEST_HAS_MISSING_PAYLOADS"):
                publish(s3,draft,directory,CONTRACT,replay=True)
            self.assertEqual(len(s3.put_order),n)

    def test_payload_conflict_and_corrupt_readback_no_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            state,request,_=prepared(Path(tmp))
            draft,directory=build_draft(state,request,CONTRACT)
            prefix="source=synthea/source_version=v3.3.0/ingest_date="+DATE+"/batch_id="+draft["batch_id"]+"/"
            with patch.dict(os.environ,{"NEW_ONLY_READONLY_SOURCE_AUDIT":"PASS",
                                       "NEW_ONLY_PG_SOURCE_AUDIT":"PASS"}):
                s3=InMemoryS3()
                s3.objects[prefix+"payload/csv/patients.csv"]=b"collision"
                with self.assertRaisesRegex(V2PublishBlocked,"PREEXISTING_PAYLOAD_CONFLICT"):
                    publish(s3,draft,directory,CONTRACT,ingest_date=DATE)
                self.assertFalse(any(x.endswith("/manifest.json") for x in s3.objects))
                s3=InMemoryS3()
                s3.bad_read=prefix+"payload/csv/patients.csv"
                with self.assertRaisesRegex(V2PublishBlocked,"REMOTE_SHA256_READBACK"):
                    publish(s3,draft,directory,CONTRACT,ingest_date=DATE)
                self.assertFalse(any(x.endswith("/manifest.json") for x in s3.objects))

    def test_wrong_frozen_source_sha_fails_before_s3(self):
        with tempfile.TemporaryDirectory() as tmp:
            state,request,folder=prepared(Path(tmp))
            file=folder/"csv"/"claims.csv"
            file.write_text("wrong,header\n")
            with self.assertRaises(Exception):
                build_draft(state,request,CONTRACT)


if __name__=="__main__":
    unittest.main()
