import copy
import importlib.util
import sys
from pathlib import Path
import unittest

file = Path(__file__).resolve().parents[1] / "publisher.py"
spec = importlib.util.spec_from_file_location("publisher", file)
p = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = p
spec.loader.exec_module(p)

class FakeBlob:
    def __init__(self):
        self.data = {}
        self.creates = []
        self.fail_key = None
    def create(self, key, payload):
        self.creates.append(key)
        if self.fail_key and self.fail_key in key:
            raise ConnectionError("injected failure")
        if key in self.data:
            raise p.BlobExists(key)
        self.data[key] = payload
    def read(self, key):
        return self.data[key]

def event(kind="COMPLETE"):
    return {"schemaURL": "https://openlineage.io/spec/1-0-5/OpenLineage.json",
            "eventType": kind, "eventTime": "2026-10-27T10:00:00Z",
            "run": {"runId": "123e4567-e89b-42d3-a456-426614174000"},
            "job": {"namespace": "fabric", "name": "patient-core"},
            "inputs": [{"namespace": "abfss://landing", "name": "in.csv"}],
            "outputs": [{"namespace": "abfss://lakehouse", "name": "out",
                         "facets": {"schema": {"fields": [{"name": "id", "type": "string"}]}}}]}

class PublisherTests(unittest.TestCase):
    def publish(self, blob, events=None):
        return p.publish(blob, batch_id="atlanta-001", runtime="fabric",
                         source_manifest_sha256="a"*64, events=events or [event()])

    def test_immutable_commit_replay(self):
        b = FakeBlob()
        key = self.publish(b)
        self.assertEqual(key, self.publish(b))
        self.assertEqual(2, len(b.data))
        self.assertTrue(b.creates[-1].endswith("manifest.json"))
        self.assertEqual(b"\n", b.data[key][-1:])

    def test_partial_failure_no_manifest_then_recover(self):
        b = FakeBlob()
        b.fail_key = "/events/"
        with self.assertRaises(ConnectionError):
            self.publish(b)
        self.assertFalse(any(x.endswith("manifest.json") for x in b.data))
        b.fail_key = None
        self.publish(b)
        self.assertEqual(2, len(b.data))

    def test_mutated_event_conflicts_same_key(self):
        b = FakeBlob()
        self.publish(b)
        changed = event()
        changed["outputs"][0]["name"] = "changed"
        with self.assertRaises(p.IntegrityError):
            self.publish(b, [changed])

    def test_invalid_events_have_no_writes(self):
        b = FakeBlob()
        for change in (lambda e: e.update({"sql": "select * from x"}),
                       lambda e: e["run"].update({"runId": "bad"}),
                       lambda e: e.update({"inputs": "not-a-list"})):
            e = copy.deepcopy(event())
            change(e)
            with self.assertRaises(p.IntegrityError):
                self.publish(b, [e])
        self.assertEqual({}, b.data)

    def test_duplicate_logical_identity_conflict(self):
        a, b = event(), event()
        b["outputs"][0]["name"] = "another"
        with self.assertRaises(p.IntegrityError):
            self.publish(FakeBlob(), [a,b])

    def test_fake_azure_sdk_conditional_create(self):
        store = FakeBlob()
        class ResourceExistsError(Exception):
            pass
        class Client:
            def __init__(self,key): self.key=key
            def upload_blob(self, data, *, blob_type, overwrite):
                assert blob_type == "BlockBlob" and overwrite is False
                try: store.create(self.key, data)
                except p.BlobExists: raise ResourceExistsError()
            def download_blob(self): return self
            def readall(self): return store.read(self.key)
        class Container:
            def get_blob_client(self, key): return Client(key)
        azure = p.AzureBlobStore(Container())
        key = self.publish(azure)
        self.assertEqual(key, self.publish(azure))
        self.assertEqual(2, len(store.data))
