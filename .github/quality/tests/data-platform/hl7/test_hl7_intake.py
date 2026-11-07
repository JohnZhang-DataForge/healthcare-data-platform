"""No-cloud source contract checks from actual OIE v2 Mapper synthetic input."""
import hashlib,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]
sys.path[:0]=[str(ROOT/"local-data-platform/spark/apps/hl7"),str(ROOT/".github/quality/fixtures/hl7")]
from generate_oie_v2_sample import generate,REQUEST,SOURCE_SHA
from landing_intake import verified_seed_rows
from write_staging_delta import _warehouse

class HL7SourceContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.manifest,self.blobs,self.sha=generate(Path(self.tmp.name))
        self.opts=dict(manifest_sha256=self.sha,source_sha256=SOURCE_SHA,
            request_id=REQUEST,ingest_date="2026-11-07",
            processing_run_id="synthetic-v2-001",processed_at="2026-11-07 13:00:00")
    def rows(self):
        return verified_seed_rows(self.manifest.read_bytes(),self.blobs,**self.opts)
    def change(self,obj):
        raw=json.dumps(obj,sort_keys=True).encode()
        self.manifest.write_bytes(raw)
        self.opts["manifest_sha256"]=hashlib.sha256(raw).hexdigest()
    def test_real_mapper_a01_a03_fields_and_replay(self):
        rows=self.rows()
        self.assertEqual([x["event_type"] for x in rows],["A01","A03"])
        self.assertEqual({x["source_system"] for x in rows},{"johns-creek-hl7"})
        self.assertEqual({x["race_code"] for x in rows},{"2028-9"})
        self.assertEqual({x["ethnicity_code"] for x in rows},{"2135-2"})
        self.assertEqual(self.rows(),rows)
    def test_manifest_sha_rejects(self):
        self.opts["manifest_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"MANIFEST_SHA256"): self.rows()
    def test_changed_bytes_reject(self):
        key=json.loads(self.manifest.read_text())["objects"][0]["blob_key"]
        path=self.blobs/key
        path.write_bytes(path.read_bytes().replace(b"Synthetic",b"Modified!"))
        with self.assertRaisesRegex(ValueError,"OBJECT_SHA256"): self.rows()
    def test_duplicate_event_reject(self):
        m=json.loads(self.manifest.read_text())
        m["objects"].append(dict(m["objects"][0]))
        self.change(m)
        with self.assertRaisesRegex(ValueError,"DUPLICATE_BLOB_KEY"): self.rows()
    def test_missing_a01_reject(self):
        m=json.loads(self.manifest.read_text())
        m["objects"]=[m["objects"][1]]
        self.change(m)
        with self.assertRaisesRegex(ValueError,"INCOMPLETE_ADT_EVENT_SET"): self.rows()
    def test_wrong_hospital_reject(self):
        m=json.loads(self.manifest.read_text())
        m["hospital_id"]="other"
        self.change(m)
        with self.assertRaisesRegex(ValueError,"MANIFEST_CONTRACT"): self.rows()
    def test_warehouse_rejects_remote_or_root(self):
        for v in ("abfss://one-lake","https://blob","file:/","file:/tmp"):
            with self.subTest(uri=v),self.assertRaises(ValueError): _warehouse(v)

if __name__=="__main__": unittest.main()
