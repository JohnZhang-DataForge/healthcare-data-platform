"""Independent Spark OpenLineage proof-of-execution. No business data or writes.

This application must run only after the Portal/TASK004 human coordination gate.
CSV comes from a per-run ConfigMap mounted at the same path on driver/executor.
"""
from __future__ import annotations

import argparse
import re


_TOKEN = re.compile(r"[a-z][a-z0-9-]{0,20}[a-z0-9]\Z")
_INPUT = "file:///opt/spark/portal-a4/input.csv"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only Spark lineage probe")
    parser.add_argument("--run-token", required=True)
    parser.add_argument("--input-uri", required=True)
    args = parser.parse_args(argv)
    if not _TOKEN.fullmatch(args.run_token):
        parser.error("Invalid isolated Portal A4 run token")
    if args.input_uri != _INPUT:
        parser.error("Only mounted, immutable Portal fixture CSV may be read")
    return args


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    # Defer PySpark import so parse_args and the module itself can be tested
    # without a Spark installation and without importing TASK004 modules.
    from pyspark.sql import SparkSession
    from pyspark.sql.types import IntegerType, StringType, StructField, StructType

    spark = (
        SparkSession.builder.appName("portal-a4-" + args.run_token)
        .getOrCreate()
    )
    try:
        schema = StructType(
            [
                StructField("record_id", StringType(), False),
                StructField("category", StringType(), False),
                StructField("amount", IntegerType(), False),
            ]
        )
        df = spark.read.option("header", "true").schema(schema).csv(args.input_uri)
        assert df.count() == 3, "PORTAL_A4_FIXTURE_COUNT_MISMATCH"
        summary = {
            row["category"]: row["total"]
            for row in df.groupBy("category").sum("amount").withColumnRenamed(
                "sum(amount)", "total"
            ).collect()
        }
        assert summary == {"alpha": 40, "beta": 20}, summary
        print("PORTAL_A4_SPARK_READONLY_CSV_ROWS=3")
        print("PORTAL_A4_SPARK_READONLY_AGGREGATION=PASS")
        print("PORTAL_A4_NO_S3_OMOP_WRITES=YES")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
