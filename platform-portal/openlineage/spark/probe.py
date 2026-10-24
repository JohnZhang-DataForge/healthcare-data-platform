"""Independent Spark OpenLineage proof with isolated synthetic Parquet output.

This application must run only after the Portal/TASK004 human coordination gate.
CSV comes from a per-run ConfigMap; Parquet output uses a per-run PVC shared by driver/executor.
"""
from __future__ import annotations

import argparse
import re


_TOKEN = re.compile(r"[a-z][a-z0-9-]{0,20}[a-z0-9]\Z")
_INPUT = "file:///opt/spark/portal-a4/input.csv"
_OUTPUT_PREFIX = "file:///opt/spark/portal-a4-output/"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only Spark lineage probe")
    parser.add_argument("--run-token", required=True)
    parser.add_argument("--input-uri", required=True)
    parser.add_argument("--output-uri", required=True)
    args = parser.parse_args(argv)
    if not _TOKEN.fullmatch(args.run_token):
        parser.error("Invalid isolated Portal A4 run token")
    if args.input_uri != _INPUT:
        parser.error("Only mounted, immutable Portal fixture CSV may be read")
    if args.output_uri != f"{_OUTPUT_PREFIX}{args.run_token}/summary.parquet":
        parser.error("Only the run-scoped mounted Portal PVC Parquet output is allowed")
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
        result = (
            df.groupBy("category")
            .sum("amount")
            .withColumnRenamed("sum(amount)", "total")
        )
        summary = {row["category"]: row["total"] for row in result.collect()}
        assert summary == {"alpha": 40, "beta": 20}, summary
        # The per-run PVC is intentionally persistent until explicit cleanup.
        # errorifexists prevents accidentally replaying over old evidence.
        result.coalesce(1).write.mode("errorifexists").parquet(args.output_uri)
        persisted = spark.read.parquet(args.output_uri)
        actual = {row["category"]: row["total"] for row in persisted.collect()}
        assert actual == summary, (summary, actual)
        assert persisted.count() == 2, "PORTAL_P3_PERSISTED_ROWS_MISMATCH"
        print("PORTAL_A4_SPARK_READONLY_CSV_ROWS=3")
        print("PORTAL_A4_SPARK_READONLY_AGGREGATION=PASS")
        print("PORTAL_P3_SPARK_PARQUET_PVC_READBACK=PASS")
        print("PORTAL_P3_OUTPUT_URI=" + args.output_uri)
        print("PORTAL_A4_NO_S3_OMOP_WRITES=YES")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
