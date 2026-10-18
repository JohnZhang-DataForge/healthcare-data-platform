import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "apps/task003"))
import build_encounter_raw_evidence as publisher
from resolve_approved_encounter_raw import resolve, sha


class ApprovedEncounterInputTests(unittest.TestCase):
    def write(self, path, value):
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

        for name in ("canonical/encounter-v1.json", "omop/visit-class-v1.json"):
            target = self.root / "spark/contracts" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO / "spark/contracts" / name, target)

        self.run_id = "encounter-raw-test-1"
        self.run = self.root / "runtime/reports/task003/step04" / self.run_id
        self.run.mkdir(parents=True)
        self.step03 = self.root / "runtime/reports/task003/step03/encounter-test-1/run-state.json"
        self.step03.parent.mkdir(parents=True)

        partition = "source=synthea/source_version=v3.3.0/ingest_date=2026-10-08/batch_id=test-batch"
        base = "s3://health-raw/canonical_version=v1/entity=encounter/" + partition + "/run_id=" + self.run_id

        c = dict(
            BATCH_ID="test-batch", PROCESSING_RUN_ID="encounter-test-1",
            RAW_RUN_ID=self.run_id, SOURCE="synthea", SOURCE_VERSION="v3.3.0",
            INGEST_DATE="2026-10-08", SOURCE_FILE="payload/csv/encounters.csv",
            SOURCE_FILE_SHA256="a" * 64, SOURCE_FILE_SIZE_BYTES=100,
            INPUT_MANIFEST_S3="s3://health-landing/" + partition + "/manifest.json",
            INPUT_MANIFEST_SHA256="b" * 64,
            PROCESSING_DATA_URI="s3a://health-processing/test/data/",
            EXPECTED_ROWS=3, RAW_ROWS=3, RAW_UNIQUE_KEYS=3,
            RAW_DATA_S3=base + "/data/", DQ_URI=base + "/dq/result.json",
            DQ_FILE=str(self.run / "dq-result.json"),
            REMOTE_DQ_FILE=str(self.run / "dq-result.json"),
            contract_sha256=sha(self.root / "spark/contracts/canonical/encounter-v1.json"),
        )

        # Generate fixtures using the existing STEP04 publisher.
        self.write(self.run / "dq-result.json", publisher.dq(c))
        self.write(self.run / "manifest.json", publisher.manifest(c))

        self.state = dict(
            publisher.base(c), status="PASS", raw_status="APPROVED",
            raw_published=True, raw_manifest_readback="PASS", raw_readback="PASS",
            dq_status="PASS", dq_readback="PASS", spark_application_state="COMPLETED",
            postgresql_write=False, raw_data_uri=base + "/data/",
            raw_manifest_uri=base + "/manifest.json", dq_uri=c["DQ_URI"],
        )
        step03 = dict(
            publisher.base(c), step="STEP-03", status="PASS",
            run_id=c["PROCESSING_RUN_ID"],
            canonical_rows=3, canonical_unique_encounters=3,
            raw_published=False, postgresql_write=False,
        )
        self.write(self.step03, step03)
        self.reseal()

    def reseal(self):
        self.state["dq_sha256"] = sha(self.run / "dq-result.json")
        m = json.loads((self.run / "manifest.json").read_text())
        m["dq"]["sha256"] = self.state["dq_sha256"]
        self.write(self.run / "manifest.json", m)
        self.state["raw_manifest_sha256"] = sha(self.run / "manifest.json")
        self.write(self.run / "run-state.json", self.state)

    def change(self, path, key, value):
        obj = json.loads(path.read_text())
        obj[key] = value
        self.write(path, obj)

    def reject(self):
        with self.assertRaises(ValueError):
            resolve(self.root, self.run_id)

    def test_accept_existing_publisher_format(self):
        result = resolve(self.root, self.run_id)
        self.assertEqual(result["expected_rows"], 3)
        self.assertEqual(result["raw_manifest_sha256"], self.state["raw_manifest_sha256"])
        self.assertFalse(result["remote_verified"])

    def test_reject_unapproved_manifest_even_with_new_hash(self):
        self.change(self.run / "manifest.json", "status", "DRAFT")
        self.reseal()
        self.reject()

    def test_reject_damaged_bytes(self):
        with (self.run / "manifest.json").open("a") as f:
            f.write(" ")
        self.reject()

    def test_reject_foreign_run_uri(self):
        m = json.loads((self.run / "manifest.json").read_text())
        m["data"]["uri"] = "s3://health-raw/another-run/data/"
        self.write(self.run / "manifest.json", m)
        self.reseal()
        self.reject()

    def test_reject_failed_dq_even_with_new_hashes(self):
        self.change(self.run / "dq-result.json", "status", "FAIL")
        self.reseal()
        self.reject()

    def test_reject_changed_lineage(self):
        self.change(self.step03, "source_file_sha256", "c" * 64)
        self.reject()

    def test_reject_changed_contract(self):
        path = self.root / "spark/contracts/canonical/encounter-v1.json"
        path.write_text(path.read_text() + "\n")
        self.reject()

    def test_reject_boolean_publication_flag(self):
        self.state["raw_published"] = 1
        self.reseal()
        self.reject()

    def test_reject_path_traversal(self):
        with self.assertRaises(ValueError):
            resolve(self.root, "../../step03")


if __name__ == "__main__":
    unittest.main()
