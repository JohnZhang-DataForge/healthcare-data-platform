"""Multi-part Spark Parquet dataset reader contract; all S3 objects are in memory."""
import hashlib
import io
import json
import sys
import unittest
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
for folder in ("airflow/dags", "apps/omop_writer"):
    sys.path.insert(0, str(ROOT / folder))

from build_s3_rollback_plan import build
from task004_cdm_dynamic_source import read

BATCH = "synthea-new-only-gh-multi-part-regression"
DAY = "2026-10-21"
PREFIX = ("source=synthea/source_version=v3.3.0/ingest_date=" + DAY
          + "/batch_id=" + BATCH + "/")
MANIFEST = b'{"batch_status":"READY"}'


def context():
    return build(
        batch_id=BATCH,
        manifest_uri="s3://health-landing/" + PREFIX + "manifest.json",
        manifest_sha256=hashlib.sha256(MANIFEST).hexdigest(),
        person_processing_uri="s3a://health-processing/" + PREFIX
            + "entity=patient/run_id=task004-person-test/work/normalized/data/",
        visit_processing_uri="s3a://health-processing/" + PREFIX
            + "entity=encounter/run_id=task004-encounter-test/work/normalized/data/",
        person_rows=2, visit_rows=3, source_version="v3.3.0",
        writer_identity_version="synthea-new-only-v1",
    )


def canonical(kind, key):
    common = dict(source_system="synthea", source_version="v3.3.0",
                  source_batch_id=BATCH, source_ingest_date=DAY)
    if kind == "visit":
        return dict(common, source_encounter_id=key, source_person_id="p-1",
                    encounter_class="ambulatory",
                    start_datetime="2026-10-20T12:00:00+00:00",
                    end_datetime="2026-10-20T12:30:00+00:00")
    return dict(common, source_record_id=key, gender_code="M",
                race_code="white", ethnicity_code="nonhispanic",
                birth_date="1980-01-01")


def as_parquet_payload(rows):
    # The injected decoder stands in for PyArrow; actual Parquet is E2E-tested.
    return json.dumps(rows).encode("utf-8")


class FakeS3:
    def __init__(self, objects, pages=None, manifest=MANIFEST):
        self.objects = objects
        self.pages = pages if pages is not None else [list(objects)]
        self.manifest = manifest
        self.read_keys = []
        self.prefixes = []

    def get_paginator(self, operation):
        assert operation == "list_objects_v2"
        return self

    def paginate(self, *, Bucket, Prefix):
        assert Bucket == "health-processing"
        self.prefixes.append(Prefix)
        return [{"Contents": [{"Key": key} for key in keys]} for keys in self.pages]

    def get_object(self, *, Bucket, Key):
        self.read_keys.append(Key)
        if Bucket == "health-landing" and Key == PREFIX + "manifest.json":
            return {"Body": io.BytesIO(self.manifest)}
        assert Bucket == "health-processing", Bucket
        return {"Body": io.BytesIO(self.objects[Key])}


def decode(data):
    return json.loads(data.decode("utf-8"))


def keys(context_data, entity):
    prefix = urlsplit(context_data[entity + "_processing_uri"]).path.lstrip("/")
    return prefix + "part-00000.snappy.parquet", prefix + "part-00001.snappy.parquet"


class ParquetShardTests(unittest.TestCase):
    def test_two_visit_parts_combined_once_sorted_and_validated(self):
        p = context()
        k0, k1 = keys(p, "visit")
        s3 = FakeS3({k0: as_parquet_payload([canonical("visit", "v-2"),
                                           canonical("visit", "v-3")]),
                     k1: as_parquet_payload([canonical("visit", "v-1")])},
                    pages=[[k1], [k0]])
        result = read(s3, p, "visit", decode)
        self.assertEqual([row["source_key"] for row in result], ["v-1", "v-2", "v-3"])
        self.assertEqual(s3.read_keys, [PREFIX + "manifest.json", k0, k1])
        self.assertEqual(s3.prefixes, [urlsplit(p["visit_processing_uri"]).path.lstrip("/")])

    def test_one_person_part_remains_supported(self):
        p = context()
        k0, _ = keys(p, "person")
        s3 = FakeS3({k0: as_parquet_payload(
            [canonical("person", "p-2"), canonical("person", "p-1")])})
        rows = read(s3, p, "person", decode)
        self.assertEqual([r["source_key"] for r in rows], ["p-1", "p-2"])

    def test_missing_part_rejected_by_global_row_count(self):
        p = context()
        k0, _ = keys(p, "visit")
        s3 = FakeS3({k0: as_parquet_payload([canonical("visit", "v-1")])})
        with self.assertRaisesRegex(ValueError, "BLOCKED=row_count"):
            read(s3, p, "visit", decode)

    def test_duplicate_id_across_parts_rejected(self):
        p = context()
        k0, k1 = keys(p, "visit")
        s3 = FakeS3({k0: as_parquet_payload([canonical("visit", "v-1"),
                                           canonical("visit", "v-2")]),
                     k1: as_parquet_payload([canonical("visit", "v-1")])})
        with self.assertRaisesRegex(ValueError, "BLOCKED=duplicate_or_missing_key"):
            read(s3, p, "visit", decode)

    def test_wrong_batch_in_second_part_rejected(self):
        p = context()
        k0, k1 = keys(p, "visit")
        bad = canonical("visit", "v-3")
        bad["source_batch_id"] = "synthea-new-only-gh-other"
        s3 = FakeS3({k0: as_parquet_payload([canonical("visit", "v-1"),
                                           canonical("visit", "v-2")]),
                     k1: as_parquet_payload([bad])})
        with self.assertRaisesRegex(ValueError, "BLOCKED=mixed_batch"):
            read(s3, p, "visit", decode)

    def test_missing_parquet_objects_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "BLOCKED=parquet_cardinality"):
            read(FakeS3({}, pages=[[], []]), context(), "visit", decode)

    def test_duplicate_listing_fails_closed(self):
        p = context()
        k0, _ = keys(p, "visit")
        obj = {k0: as_parquet_payload([canonical("visit", "v-1")])}
        with self.assertRaisesRegex(ValueError, "BLOCKED=parquet_cardinality"):
            read(FakeS3(obj, pages=[[k0], [k0]]), p, "visit", decode)

    def test_empty_second_parquet_rejected(self):
        p = context()
        k0, k1 = keys(p, "visit")
        s3 = FakeS3({k0: as_parquet_payload([canonical("visit", "v-1")]),
                     k1: b""})
        with self.assertRaisesRegex(ValueError, "BLOCKED=empty_parquet"):
            read(s3, p, "visit", decode)

    def test_invalid_decoded_shard_rejected(self):
        p = context()
        k0, _ = keys(p, "visit")
        with self.assertRaisesRegex(ValueError, "BLOCKED=parquet_decode"):
            read(FakeS3({k0: as_parquet_payload({"not": "a list"})}), p,
                 "visit", decode)

    def test_bad_manifest_rejected_before_reading_shards(self):
        p = context()
        k0, _ = keys(p, "visit")
        s3 = FakeS3({k0: as_parquet_payload([canonical("visit", "v-1")])},
                    manifest=b"tampered")
        with self.assertRaisesRegex(ValueError, "BLOCKED=manifest_sha_mismatch"):
            read(s3, p, "visit", decode)
        self.assertEqual(s3.read_keys, [PREFIX + "manifest.json"])


if __name__ == "__main__":
    unittest.main()
