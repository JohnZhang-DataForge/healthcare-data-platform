"""NEW_ONLY prepublication fail-closed contract and identity tests."""
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"apps/synthea/new_only"))
from prepublish_gate import audit_local,audit_historical_landing,load_contract,PublishGateBlocked,source_hash
CONTRACT=ROOT/"contracts/synthea/new-only/csv-contract-v2.json"

def write_csvs(root,person="new-uuid",visit="enc-new",parent=None):
    d=load_contract(CONTRACT)
    for item in d["files"]:
        h=item["header"]
        with (root/item["filename"]).open("w",newline="") as f:
            w=csv.writer(f);w.writerow(h)
            if item["filename"]=="patients.csv":
                row=[""]*len(h);row[h.index("Id")]=person;w.writerow(row)
            if item["filename"]=="encounters.csv":
                row=[""]*len(h);row[h.index("Id")]=visit
                row[h.index("PATIENT")]=parent or person
                w.writerow(row)
class FakeS3:
    def __init__(self,files):self.files=files
    def list_keys(self,prefix):return sorted(k for k in self.files if k.startswith(prefix))
    def get_object(self,key):return self.files[key]

class GateTests(unittest.TestCase):
    def test_real_v2_contract_is_distinct_and_18_header_preserving(self):
        d=load_contract(CONTRACT)
        old=json.loads((ROOT/"contracts/synthea/v3.3.0/csv-contract.json").read_text())
        self.assertEqual(d["files"],old["files"])
        self.assertTrue(old["require_nonempty_data_rows"])
        self.assertFalse(d["require_nonempty_data_rows"])
        self.assertNotEqual(d["contract_version"],old["contract_version"])
        self.assertEqual(d["consumer_compatibility"],"NOT_YET_DEPLOYED_DO_NOT_PUBLISH_READY")

    def test_one_person_accepts_optional_empty_without_publishing(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);write_csvs(p)
            result=audit_local(p,CONTRACT)
            self.assertEqual(result["person_rows"],1)
            self.assertEqual(result["visit_rows"],1)
            self.assertEqual(result["csv_file_count"],18)
            self.assertGreater(len(result["zero_row_optional_files"]),0)
            self.assertTrue(result["batch_not_published"])
            self.assertEqual(result["person_source_hashes"],[source_hash("new-uuid")])

    def test_duplicate_patient_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);write_csvs(p)
            with (p/"patients.csv").open("a",newline="") as f:
                w=csv.writer(f)
                h=next(x["header"] for x in load_contract(CONTRACT)["files"] if x["filename"]=="patients.csv")
                row=[""]*len(h);row[h.index("Id")]="new-uuid";w.writerow(row)
            with self.assertRaises(PublishGateBlocked):
                audit_local(p,CONTRACT)

    def test_orphan_encounter_and_empty_required_are_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);write_csvs(p,parent="missing")
            with self.assertRaisesRegex(PublishGateBlocked,"ENCOUNTER_ORPHAN"):
                audit_local(p,CONTRACT)
            write_csvs(p)
            h=next(x["header"] for x in load_contract(CONTRACT)["files"] if x["filename"]=="patients.csv")
            with (p/"patients.csv").open("w",newline="") as f:
                csv.writer(f).writerow(h)
            with self.assertRaises(PublishGateBlocked):
                audit_local(p,CONTRACT)

    def test_remote_collision_and_candidate_batch_exists_are_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);write_csvs(p)
            a=audit_local(p,CONTRACT)
            headers={x["filename"]:x["header"] for x in load_contract(CONTRACT)["files"]}
            prefix="source=synthea/source_version=v3.3.0/ingest_date=2026-10-11/batch_id=old/"
            contents=(p/"patients.csv").read_bytes()
            old=FakeS3({prefix+"payload/csv/patients.csv":contents})
            info=audit_historical_landing(old,"source=synthea/source_version=v3.3.0/",dict(a,headers=headers),"synthea-new-only-future")
            self.assertEqual(info["s3_person_source_collisions"],1)
            self.assertFalse(info["s3_collision_free"])
            with self.assertRaisesRegex(PublishGateBlocked,"CANDIDATE_BATCH_PREFIX_ALREADY_EXISTS"):
                audit_historical_landing(old,"source=synthea/source_version=v3.3.0/",dict(a,headers=headers),"old")

    def test_s3_checksum_drift_blocks_before_publishing(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);write_csvs(p)
            a=audit_local(p,CONTRACT)
            prefix="source=synthea/source_version=v3.3.0/ingest_date=2026-10-11/batch_id=old/"
            key=prefix+"payload/csv/patients.csv"
            manifest=prefix+"manifest.json"
            remote=FakeS3({key:(p/"patients.csv").read_bytes(),manifest:json.dumps({
                "status":"INTAKE_VERIFIED","files":[{"path":"payload/csv/patients.csv","sha256":"0"*64}]
            }).encode()})
            headers={x["filename"]:x["header"] for x in load_contract(CONTRACT)["files"]}
            with self.assertRaisesRegex(PublishGateBlocked,"HISTORICAL_S3_CHECKSUM_DRIFT"):
                audit_historical_landing(remote,"source=synthea/source_version=v3.3.0/",dict(a,headers=headers),"future")

if __name__=="__main__":
    unittest.main()
