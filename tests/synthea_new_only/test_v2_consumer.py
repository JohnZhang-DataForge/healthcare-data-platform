"""V2 consumer compatibility and strict rejection; zero synthetic source claims."""
import copy
import csv
import hashlib
import io
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/"apps/task004"),str(ROOT/"apps/landing_discovery"),str(ROOT/"apps/synthea/new_only")]
from validate_new_only_v2_manifest import validate_v2_manifest,V2ContractError,source_contract,CONTRACT_RELATIVE,PINNED_COMMIT
from resolve_verified_landing_file import validate_manifest,resolve_from_bytes,ResolverError
from scan_ready_batches import discover_ready_batches
from verify_v1_ready import DiscoveryAdapter

REQUEST="gh-v2-test-001"
BATCH="synthea-new-only-"+REQUEST
PREFIX="source=synthea/source_version=v3.3.0/ingest_date=2026-10-14/batch_id="+BATCH+"/"
URI="s3://health-landing/"+PREFIX+"manifest.json"


def fixture():
    contract,sha=source_contract()
    objects={}
    files=[]
    for spec in contract["files"]:
        name=spec["filename"]
        h=spec["header"]
        buff=io.StringIO(newline="")
        w=csv.writer(buff)
        w.writerow(h)
        row_count=0
        if name in ("patients.csv","encounters.csv"):
            row=[""]*len(h)
            row[h.index("Id")]="p-new" if name=="patients.csv" else "enc-new"
            if name=="encounters.csv": row[h.index("PATIENT")]="p-new"
            w.writerow(row)
            row_count=1
        raw=buff.getvalue().encode()
        key=PREFIX+"payload/csv/"+name
        objects[key]=raw
        files.append({"path":"payload/csv/"+name,"dataset":spec["dataset"],
                      "header":h,"row_count":row_count,"size_bytes":len(raw),
                      "sha256":hashlib.sha256(raw).hexdigest()})
    fingerprint=hashlib.sha256()
    for f in sorted(files,key=lambda x:x["path"]):
        fingerprint.update((f["path"].rsplit("/",1)[-1]+"|"+f["sha256"]+"\n").encode())
    doc={"manifest_version":"2.0","status":"INTAKE_VERIFIED",
         "source":"synthea","source_version":"v3.3.0",
         "batch_id":BATCH,"ingest_date":"2026-10-14",
         "landing_uri":"s3://health-landing/"+PREFIX,
         "payload_format":"csv",
         "source_parameters":{"generation_mode":"NEW_ONLY","generation_request_id":REQUEST,
                              "population_size":1},
         "source_provenance":{"synthea_version":"v3.3.0","synthea_commit":PINNED_COMMIT},
         "contract":{"path":CONTRACT_RELATIVE,"sha256":sha},
         "expected_file_count":18,
         "files":files,
         "verification":{"s3_readback":"PASS","verified_file_count":18,"checksum_algorithm":"SHA256"},
         "payload_fingerprint":fingerprint.hexdigest()}
    objects[PREFIX+"manifest.json"]=json.dumps(doc,sort_keys=True).encode()
    return doc,objects


class StubReadOnlyS3:
    def __init__(self,objects):self.objects=objects
    def list_keys(self,prefix):return sorted(k for k in self.objects if k.startswith(prefix))
    def get_object(self,key):return self.objects[key]


class V2ConsumerTests(unittest.TestCase):
    def test_header_only_auxiliary_is_ready_under_explicit_v2(self):
        doc,objects=fixture()
        result=validate_manifest(doc,BATCH,URI)
        self.assertEqual(len(result),18)
        self.assertEqual(sum(f["row_count"]==0 for f in result),16)
        raw=objects[PREFIX+"manifest.json"]
        selected=resolve_from_bytes(raw,"patients",BATCH,URI,hashlib.sha256(raw).hexdigest())
        self.assertEqual(selected["row_count"],1)
        self.assertEqual(selected["manifest_version"],"2.0")
        zero=resolve_from_bytes(raw,"claims",BATCH,URI,hashlib.sha256(raw).hexdigest())
        self.assertEqual(zero["row_count"],0)
        self.assertEqual(zero["size_bytes"],len(objects[PREFIX+zero["path"]]))

    def test_discovery_v2_does_not_claim_and_v1_same_scanner(self):
        doc,objects=fixture()
        result=discover_ready_batches(DiscoveryAdapter(StubReadOnlyS3(objects)))
        self.assertEqual(result["ready_count"],1)
        self.assertFalse(result["processing_authorized"])
        self.assertEqual(result["ready_batches"][0]["batch_id"],BATCH)
        self.assertEqual(result["ready_batches"][0]["manifest_sha256"],
                         hashlib.sha256(objects[PREFIX+"manifest.json"]).hexdigest())

    def test_fail_closed_negative_cases(self):
        original,_=fixture()
        cases=[
          ("unknown version",lambda d:d.update(manifest_version="2.1")),
          ("legacy spoofed batch",lambda d:d.update(batch_id="task004-airflow-fake")),
          ("wrong mode",lambda d:d["source_parameters"].update(generation_mode="UPDATE_ONLY")),
          ("wrong request",lambda d:d["source_parameters"].update(generation_request_id="gh-tampered-001")),
          ("wrong contract hash",lambda d:d["contract"].update(sha256="0"*64)),
          ("wrong contract path",lambda d:d["contract"].update(path="contracts/synthea/v3.3.0/csv-contract.json")),
          ("wrong header",lambda d:d["files"][0].update(header=["Id"])),
          ("empty patients",lambda d:next(f for f in d["files"] if f["dataset"]=="patients").update(row_count=0)),
          ("empty encounters",lambda d:next(f for f in d["files"] if f["dataset"]=="encounters").update(row_count=0)),
          ("negative optional",lambda d:next(f for f in d["files"] if f["dataset"]=="claims").update(row_count=-1)),
          ("forged size",lambda d:d["files"][0].update(size_bytes=0)),
          ("forged sha",lambda d:d["files"][0].update(sha256="zzz")),
          ("duplicate path",lambda d:d["files"][1].update(path=d["files"][0]["path"])),
          ("fingerprint",lambda d:d.update(payload_fingerprint="0"*64)),
          ("readback flag",lambda d:d["verification"].update(s3_readback="SKIP")),
          ("status",lambda d:d.update(status="LOCAL_VALIDATED_NOT_UPLOADED")),
        ]
        for name,mutate in cases:
            with self.subTest(name=name):
                doc=copy.deepcopy(original);mutate(doc)
                with self.assertRaises((ResolverError,V2ContractError)):
                    validate_manifest(doc,BATCH,URI)

    def test_v1_does_not_acquire_zero_row_permission(self):
        doc,_=fixture()
        doc["manifest_version"]="1.0"
        with self.assertRaisesRegex(ResolverError,"row_count must be > 0"):
            validate_manifest(doc,BATCH,URI)
        doc["manifest_version"]="2.0"
        doc["files"][0]["row_count"]=True
        with self.assertRaises(ResolverError):
            validate_manifest(doc,BATCH,URI)


if __name__=="__main__":unittest.main()
