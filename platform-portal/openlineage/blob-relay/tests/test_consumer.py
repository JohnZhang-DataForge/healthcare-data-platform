import importlib.util
import sys
import tempfile
from pathlib import Path
import unittest

file = Path(__file__).resolve().parents[1] / "consumer.py"
spec = importlib.util.spec_from_file_location("consumer", file)
c = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = c
spec.loader.exec_module(c)

class Blob:
    def __init__(self): self.data = {}
    def read(self, key): return self.data[key]

class Marquez:
    def __init__(self): self.posts = []; self.gets = 0; self.fail = False
    def ingest(self, event): self.posts.append(event)
    def verify(self, event):
        self.gets += 1
        if self.fail:
            raise ConnectionError("Marquez GET temporarily down")

def fixture():
    event = {"schemaURL": "https://openlineage.io/spec/1-0-5/OpenLineage.json",
             "eventType": "COMPLETE", "eventTime": "2026-10-27T10:00:00Z",
             "job": {"namespace": "fabric", "name": "transform"},
             "run": {"runId": "123e4567-e89b-42d3-a456-426614174000"},
             "inputs": [{"namespace": "abfss://landing", "name": "source"}],
             "outputs": [{"namespace": "abfss://out", "name": "output"}]}
    eid = c.logical_id(event)
    root = "openlineage/v1/batches/atlanta-001"
    key = f"{root}/events/{eid}.json"
    manifest = {"schema_version": "openlineage.blob-manifest.v1",
                "state": "COMMITTED", "batch_id": "atlanta-001", "runtime": "fabric",
                "source_manifest_sha256": "a"*64, "event_count": 1,
                "events": [{"event_id": eid, "key": key, "sha256": c.digest(c.canonical(event))}]}
    blob = Blob()
    blob.data[key] = c.canonical(event)
    blob.data[root + "/manifest.json"] = c.canonical(manifest)
    return blob, root + "/manifest.json", key

class ConsumerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.cp = c.Checkpoint(str(Path(self.temp.name) / "checkpoint.sqlite"))
    def tearDown(self):
        self.cp.close()
        self.temp.cleanup()

    def test_replay_idempotent_and_durable_restart(self):
        blob, marker, _ = fixture()
        m = Marquez()
        self.assertEqual(1, c.consume(blob, marker, m, self.cp))
        self.assertEqual(0, c.consume(blob, marker, m, self.cp))
        self.assertEqual(1, len(m.posts))
        self.cp.close()
        self.cp = c.Checkpoint(str(Path(self.temp.name) / "checkpoint.sqlite"))
        self.assertEqual(0, c.consume(blob, marker, m, self.cp))

    def test_failed_readback_replays_only_lineage(self):
        blob, marker, _ = fixture()
        m = Marquez(); m.fail = True
        with self.assertRaises(ConnectionError):
            c.consume(blob, marker, m, self.cp)
        m.fail = False
        self.assertEqual(1, c.consume(blob, marker, m, self.cp))
        self.assertEqual(2, len(m.posts))

    def test_partial_and_tampered_manifest_fail_closed(self):
        blob, marker, key = fixture()
        m = Marquez()
        x = c.parse_json(blob.data[marker])
        x["state"] = "PENDING"
        blob.data[marker] = c.canonical(x)
        with self.assertRaises(c.RelayError):
            c.consume(blob, marker, m, self.cp)
        blob, marker, key = fixture()
        blob.data[key] = b"{}\n"
        with self.assertRaises(c.RelayError):
            c.consume(blob, marker, m, self.cp)
        self.assertEqual([], m.posts)

    def test_reject_path_traversal_and_unauthorized_manifest(self):
        blob, marker, _ = fixture()
        x = c.parse_json(blob.data[marker])
        x["events"][0]["key"] = "openlineage/v1/batches/another/secret"
        blob.data[marker] = c.canonical(x)
        with self.assertRaises(c.RelayError):
            c.consume(blob, marker, Marquez(), self.cp)

    def test_no_commit_marker_no_consumption(self):
        blob, marker, _ = fixture()
        del blob.data[marker]
        with self.assertRaises(KeyError):
            c.consume(blob, marker, Marquez(), self.cp)

    def test_marquez_readback_error_no_checkpoint(self):
        blob, marker, _ = fixture()
        class Bad(Marquez):
            def verify(self, event): raise c.RelayError("GET mismatch")
        with self.assertRaises(c.RelayError):
            c.consume(blob, marker, Bad(), self.cp)
        self.assertEqual(1, c.consume(blob, marker, Marquez(), self.cp))

    def test_private_only_marquez(self):
        with self.assertRaises(c.RelayError):
            c.MarquezHttp("https://public.example.com")
        c.MarquezHttp("http://marquez-api.default.svc.cluster.local:5000")

    def test_get_job_run_and_exact_dataset_identities(self):
        class Fake(c.MarquezHttp):
            def __init__(self): self.paths = []
            def request(self, method, path, event=None):
                self.paths.append((method,path))
                if path.startswith("/jobs/runs/"):
                    return {"id": "123e4567-e89b-42d3-a456-426614174000", "state": "COMPLETED"}
                if path.startswith("/namespaces/fabric/jobs/"):
                    return {"namespace": "fabric", "name": "transform"}
                if path.startswith("/namespaces/abfss%3A%2F%2Flanding/"):
                    return {"namespace": "abfss://landing", "name": "source"}
                return {"namespace": "abfss://out", "name": "output"}
        blob, _, key = fixture()
        m = Fake()
        m.verify(c.parse_json(blob.data[key]))
        self.assertEqual(4, len(m.paths))

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(c.RelayError):
            c.parse_json(b'{"state":"COMMITTED","state":"PENDING"}')
