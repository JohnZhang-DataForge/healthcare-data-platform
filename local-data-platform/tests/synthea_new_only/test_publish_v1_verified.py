"""Immutable NEW_ONLY -> legacy strict-v1 publisher compatibility tests."""
import csv
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/"apps/task004"),str(ROOT/"apps/synthea/new_only")]
import publish_v1_verified as pub

CONTRACT=ROOT/"contracts/synthea/v3.3.0/csv-contract.json"
VALIDATOR=ROOT/"apps/task004/validate_generated_synthea_batch.py"

def fixture(directory):
    state=directory/"state"
    request="gh-38484300008"
    folder=state/"new-only"/"requests"/request
    csv_dir=folder/"csv"
    csv_dir.mkdir(parents=True)
    spec=json.loads(CONTRACT.read_text())
    for item in spec["files"]:
        with (csv_dir/item["filename"]).open("w",newline="") as f:
            w=csv.writer(f)
            h=item["header"]
            w.writerow(h)
            row=[""]*len(h)
            if "Id" in h:
                row[h.index("Id")]=("person-new-only" if item["filename"]=="patients.csv" else "encounter-unique-"+item["filename"])
            if "PATIENT" in h:
                row[h.index("PATIENT")]="person-new-only"
            w.writerow(row)
    params={
        "generation_request_id":request,
        "batch_id":"synthea-new-only-"+request,
        "synthea_commit":pub.COMMIT,
        "synthea_version":"v3.3.0",
        "target_population":1,
        "seed":987654,"clinician_seed":3579,
        "reference_date":"20261013",
        "state":"Georgia",
    }
    pp=folder/"params.json"
    pp.write_text(json.dumps(params))
    pid=hashlib.sha256("synthea-source:person-new-only".encode()).hexdigest()
    marker={
        "generation_request_id":request,"batch_id":params["batch_id"],
        "state":"LOCAL_CSV_VALIDATED_NOT_PUBLISHED",
        "params_sha256":pub.file_sha(pp),
        "publication_eligible":False,
        "legacy_18_csv_nonempty_contract_applied":False,
        "actual_persons":1,
        "actual_encounters":1,
        "person_id_hashes":[pid],
    }
    (folder/"validated.json").write_text(json.dumps(marker))
    return state,request,folder

class PublisherTests(unittest.TestCase):
    def test_frozen_v1_draft_has_new_only_provenance_and_no_source_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            state,request,folder=fixture(p)
            draft,marker,csvdir=pub.prepare(state,request,VALIDATOR,CONTRACT,p/"scratch")
            self.assertEqual(len(draft["files"]),18)
            self.assertEqual(draft["manifest_version"],"1.0")
            self.assertEqual(draft["source_parameters"]["generation_mode"],"NEW_ONLY")
            self.assertEqual(draft["source_parameters"]["generation_request_id"],request)
            self.assertEqual(draft["source_parameters"]["population_size"],1)
            self.assertEqual(draft["source_provenance"]["generator_params_sha256"],pub.file_sha(folder/"params.json"))
            self.assertEqual(draft["source_provenance"]["generator_local_validation_sha256"],pub.file_sha(folder/"validated.json"))
            self.assertEqual(marker["actual_persons"],1)
            self.assertEqual(len(list(csvdir.iterdir())),18)

    def test_no_generated_request_no_publish_and_no_forged_request_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with self.assertRaisesRegex(pub.NewOnlyBlocked,"REQUEST_ID_INVALID"):
                pub.frozen_request(root,"../../unsafe")
            with self.assertRaisesRegex(pub.NewOnlyBlocked,"REQUEST_NOT_ON_PVC"):
                pub.frozen_request(root,"gh-38484300008")

    def test_tampered_parameters_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            state,request,folder=fixture(root)
            p=folder/"params.json"
            d=json.loads(p.read_text());d["seed"]=111;p.write_text(json.dumps(d))
            with self.assertRaisesRegex(pub.NewOnlyBlocked,"FROZEN_REQUEST_IDENTITY_DRIFT"):
                pub.frozen_request(state,request)

    def test_tampered_person_source_id_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            state,request,folder=fixture(root)
            p=folder/"csv"/"patients.csv"
            data=p.read_text().replace("person-new-only","forged-person-id")
            p.write_text(data)
            with self.assertRaisesRegex(pub.NewOnlyBlocked,"PERSON_SOURCE_REGISTRY_DRIFT"):
                pub.frozen_request(state,request)

    def test_v1_strict_contract_blocks_optional_zero_row_tables(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            state,request,folder=fixture(root)
            target=folder/"csv"/"claims_transactions.csv"
            data=target.read_text()
            target.write_text(data.splitlines(keepends=True)[0])
            with self.assertRaisesRegex(pub.NewOnlyBlocked,"STRICT_V1_VALIDATOR_REJECTED"):
                pub.prepare(state,request,VALIDATOR,CONTRACT,root/"scratch")

if __name__=="__main__":
    unittest.main()
