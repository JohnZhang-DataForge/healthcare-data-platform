"""Bounded in-memory Spark 3.5 / Fabric Spark 4.x compatibility probe.

No external data sources, mutations, or OpenLineage side effects.  Both runtimes
execute this exact code; the platform execution adapter may capture the result.
"""
import hashlib
import json
from pyspark.sql import SparkSession, functions as F


def transform_patients(frame):
    """Pure DataFrame transformation; no Fabric-specific APIs."""
    return (
        frame.select(
            F.trim(F.col("patient_id")).alias("patient_id"),
            F.lower(F.trim(F.col("gender"))).alias("gender"),
            F.year(F.to_date(F.col("birthDate"), "yyyy-MM-dd")).alias("birth_year"),
        )
        .filter(F.col("patient_id").isNotNull() & (F.length("patient_id") > 0))
        .dropDuplicates(["patient_id"])
        .orderBy("patient_id")
    )


def run_smoke(session):
    """Run against five anonymous fictional records; assert the full output."""
    fixtures = [
        ("p-001", " Female ", "1980-01-02"),
        ("p-002", "MALE", "1991-12-11"),
        ("p-003", "female", "2001-05-10"),
        ("p-004", "other", "1985-08-30"),
        ("p-005", "male", "1975-02-04"),
        ("p-001", " Female ", "1980-01-02"),  # deliberate exact duplicate
    ]
    frame = session.createDataFrame(
        fixtures, schema="patient_id string, gender string, birthDate string"
    )
    actual = [
        [row["patient_id"], row["gender"], row["birth_year"]]
        for row in transform_patients(frame).collect()
    ]
    expected = [
        ["p-001", "female", 1980],
        ["p-002", "male", 1991],
        ["p-003", "female", 2001],
        ["p-004", "other", 1985],
        ["p-005", "male", 1975],
    ]
    assert actual == expected, ("PATIENT_TRANSFORM_MISMATCH", actual)
    encoded = json.dumps(actual, separators=(",", ":"), ensure_ascii=True)
    return {
        "status": "PASS",
        "rows": len(actual),
        "sha256": hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
        "spark": session.version,
    }


if __name__ == "__main__":
    result = run_smoke(SparkSession.builder.appName("healthcare-portable-patient-smoke").getOrCreate())
    print("PORTABLE_SPARK_COMPAT_RESULT=" + json.dumps(result, sort_keys=True))
