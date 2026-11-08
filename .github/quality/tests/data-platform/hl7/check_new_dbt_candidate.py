"""Read back isolated local Delta Candidate; prepare mutation-only negative fixtures.

No live Azure, Fabric, OIE POST, Silver/Gold, or shared runtime.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "local-data-platform/spark/apps/hl7"))
from write_staging_delta import _spark, _warehouse

CANDIDATE = "hl7_candidate"


def physical_delta(spark, name):
    detail = spark.sql(f"DESCRIBE DETAIL {name}").first().asDict()
    uri = urlparse(detail["location"])
    assert detail["format"] == "delta" and uri.scheme in ("", "file") and not uri.netloc, name
    assert (Path(uri.path) / "_delta_log").is_dir(), name
    return spark.table(name)


def verify(spark, baseline):
    staging = physical_delta(spark, "hl7_staging.hl7_events")
    patient = physical_delta(spark, f"{CANDIDATE}.canonical_patient")
    encounter = physical_delta(spark, f"{CANDIDATE}.canonical_encounter")
    assert (staging.count(), patient.count(), encounter.count()) == (2, 1, 1)
    for entity, frame in (("patient", patient), ("encounter", encounter)):
        path = ROOT / f"local-data-platform/spark/contracts/canonical/{entity}-v1.json"
        contract = json.loads(path.read_text())
        expected = [(x["name"], x["type"]) for x in contract["fields"]]
        actual = [(x.name, x.dataType.simpleString()) for x in frame.schema.fields]
        assert actual == expected, (entity, expected, actual)
        for field in contract["fields"]:
            if not field["nullable"]:
                assert frame.where(frame[field["name"]].isNull()).count() == 0
        assert frame.count() == frame.dropDuplicates(contract["primary_key"]).count()
    assert tuple(patient.select("source_system", "source_record_id", "race_code",
                                "ethnicity_code").first()) == (
                                    "johns-creek-hl7", "patient-one", "2028-9", "2135-2")
    assert tuple(encounter.select("source_system", "source_person_id",
                                  "source_encounter_id", "source_code").first()) == (
                                      "johns-creek-hl7", "patient-one", "visit-one", "IMP")
    assert encounter.where("start_datetime > end_datetime").count() == 0
    assert encounter.join(patient,
        (encounter.source_system == patient.source_system)
        & (encounter.source_person_id == patient.source_record_id),
        "left_anti").count() == 0
    content = {name: [r.asDict(recursive=True) for r in df.orderBy(
        *df.columns).collect()] for name, df in (
            ("patient", patient), ("encounter", encounter))}
    digest = hashlib.sha256(json.dumps(content, sort_keys=True,
                                      default=str).encode()).hexdigest()
    if baseline.exists():
        assert baseline.read_text().strip() == digest, "HL7_P3_LOGICAL_REPLAY_MISMATCH"
        print("HL7_P3_LOGICAL_REPLAY=PASS")
    else:
        baseline.write_text(digest + "\n")
        print("HL7_P3_BASELINE_SAVED=YES")
    print("HL7_P3_PHYSICAL_LOCAL_DELTA_CONTRACT_18_27=PASS")
    print("HL7_P3_APPROVED_SILVER_GOLD=NO")


def negatives(spark):
    from pyspark.sql import functions as F
    src = physical_delta(spark, "hl7_staging.hl7_events")
    admit = src.where("event_type='A01'")
    discharge = src.where("event_type='A03'")
    cases = {
        "hl7_negative_unmatched": discharge,
        "hl7_negative_reversed": admit.unionByName(discharge.withColumn(
            "event_datetime_utc", F.expr("event_datetime_utc - INTERVAL 7 DAYS"))),
        "hl7_negative_collision": admit.unionByName(discharge.withColumn(
            "source_person_id", F.lit("foreign-patient"))),
        "hl7_negative_duplicate": src.unionByName(admit),
    }
    for schema, frame in cases.items():
        spark.sql(f"CREATE DATABASE IF NOT EXISTS {schema}")
        frame.write.format("delta").mode("errorifexists").saveAsTable(
            f"{schema}.hl7_events")
        assert physical_delta(spark, f"{schema}.hl7_events").count() > 0
    print("HL7_P3_NEGATIVE_LOCAL_FIXTURES=4")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("readback", "prepare-negative"))
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()
    spark = _spark(_warehouse(os.environ["HL7_LOCAL_WAREHOUSE_URI"]))
    try:
        if args.mode == "readback":
            if not args.baseline:
                raise ValueError("HL7_P3_BASELINE_PATH_REQUIRED")
            verify(spark, args.baseline)
        else:
            negatives(spark)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
