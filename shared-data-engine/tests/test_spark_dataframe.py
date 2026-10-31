"""Actual PySpark DataFrame schema/rows; must run in pinned CI Spark environment."""
from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import unittest

from pyspark.sql import SparkSession
from pyspark.sql.types import DateType, StringType, TimestampType, LongType

from healthcare_data_engine import (
    BatchContext, SourceObject, parse_fhir_resources,
    normalize_fhir_patient, normalize_fhir_encounter, load_pinned_contract)
from healthcare_data_engine.canonical.validation import accepted_dataframe

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).resolve().parent / "fixtures/fhir_r4/patient_encounters_bundle.json"


class CanonicalSparkSchemaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spark = (SparkSession.builder.master("local[1]").appName("synthetic-fhir-contract-test")
                     .config("spark.ui.enabled", "false")
                     .config("spark.sql.session.timeZone", "UTC")
                     .getOrCreate())

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop()

    def test_patient_encounter_pyspark_schema_and_fk(self):
        context = BatchContext(
            hospital_id="hospital-a", feed_id="fhir-r4", source_system="synthetic",
            request_id="offline-pyspark", manifest_sha256=hashlib.sha256(b"manifest").hexdigest(),
            processing_version="0.1.0:canonical-v1", processing_run_id="spark-offline",
            source_version="R4", source_ingest_date=date(2026, 10, 31),
            processed_at=datetime(2026, 10, 31, 12, tzinfo=timezone.utc))
        raw = FIXTURE.read_bytes()
        parsed = parse_fhir_resources((SourceObject.from_bytes("synthetic.json", raw),), context)
        pc = load_pinned_contract((ROOT / "local-data-platform/spark/contracts/canonical/patient-v1.json").read_bytes(), "patient")
        ec = load_pinned_contract((ROOT / "local-data-platform/spark/contracts/canonical/encounter-v1.json").read_bytes(), "encounter")
        p = normalize_fhir_patient(parsed, pc, context)
        e = normalize_fhir_encounter(parsed, ec, context)
        pdf = accepted_dataframe(self.spark, p.accepted, pc)
        edf = accepted_dataframe(self.spark, e.accepted, ec)
        self.assertEqual(pdf.count(), 1)
        self.assertEqual(edf.count(), 2)
        self.assertEqual(pdf.schema.fieldNames(), [f["name"] for f in pc["fields"]])
        self.assertEqual(edf.schema.fieldNames(), [f["name"] for f in ec["fields"]])
        self.assertIsInstance(pdf.schema["birth_date"].dataType, DateType)
        self.assertIsInstance(pdf.schema["source_file_size_bytes"].dataType, LongType)
        self.assertIsInstance(edf.schema["start_datetime"].dataType, TimestampType)
        self.assertIsInstance(edf.schema["source_person_id"].dataType, StringType)
        accepted_ids = {row.source_record_id for row in pdf.select("source_record_id").collect()}
        fk_ids = {row.source_person_id for row in edf.select("source_person_id").collect()}
        self.assertEqual(fk_ids, accepted_ids)
        self.assertEqual(edf.select("source_encounter_id").distinct().count(), 2)

    def test_empty_results_still_preserve_exact_local_schema(self):
        ec = load_pinned_contract((ROOT / "local-data-platform/spark/contracts/canonical/encounter-v1.json").read_bytes(), "encounter")
        df = accepted_dataframe(self.spark, (), ec)
        self.assertEqual(df.count(), 0)
        self.assertEqual(df.schema.fieldNames(), [f["name"] for f in ec["fields"]])


if __name__ == "__main__":
    unittest.main()
