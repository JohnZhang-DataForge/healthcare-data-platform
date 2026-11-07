"""One local-only physical HL7 Delta staging table from an immutable verified manifest.

The parser is hl7apy-based and accepts only the reviewed OIE V2 source profile.
We DO NOT perform Azure GET, OIE POST, Fabric Capacity, Silver or Gold I/O.
All listed raw objects are verified before the first Delta write. An existing
identical Delta table is replay-skipped; any changed bytes/metadata fail closed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlparse

from landing_intake import verified_seed_rows
from parse_oie_v2 import COLUMNS

TABLE = "hl7_staging.hl7_events"
DATE_COLS = ("source_ingest_date",)
TIMESTAMP_COLS = ("event_datetime_utc", "processed_at")
LONG_COLS = ("source_file_size_bytes",)


def _warehouse(uri: str) -> str:
    if not isinstance(uri, str) or not uri.startswith("file:/"):
        raise ValueError("HL7_LOCAL_ONLY_WAREHOUSE_FILE_URI_REQUIRED")
    url = urlparse(uri)
    if (url.scheme != "file" or url.netloc or url.query or url.fragment
            or not url.path or not Path(url.path).is_absolute()
            or Path(url.path).is_symlink()):
        raise ValueError("HL7_LOCAL_WAREHOUSE_PATH_HOLD")
    path = Path(url.path)
    if path == Path("/") or path == Path("/tmp") or ".." in path.parts:
        raise ValueError("HL7_LOCAL_WAREHOUSE_ROOT_HOLD")
    path.mkdir(parents=True, exist_ok=True)
    return uri


def _spark(warehouse_uri: str):
    from pyspark.sql import SparkSession

    return (
        SparkSession.builder.master("local[2]")
        .appName("healthcare-hl7-verified-local-staging")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.warehouse.dir", warehouse_uri)
        .config("spark.jars.packages", "io.delta:delta-spark_2.12:3.3.2")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog",
                "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .enableHiveSupport()
        .getOrCreate()
    )


def _frame(spark, rows):
    from pyspark.sql import functions as F
    from pyspark.sql.types import StructField, StructType, StringType

    if not rows or set().union(*(r.keys() for r in rows)) != set(COLUMNS):
        raise ValueError("HL7_STAGING_SCHEMA_HOLD")
    schema = StructType([StructField(name, StringType(), False) for name in COLUMNS])
    df = spark.createDataFrame(
        [tuple(row[name] for name in COLUMNS) for row in rows], schema=schema)
    for name in DATE_COLS:
        df = df.withColumn(name, F.to_date(F.col(name), "yyyy-MM-dd"))
    for name in TIMESTAMP_COLS:
        df = df.withColumn(name, F.to_timestamp(F.col(name), "yyyy-MM-dd HH:mm:ss"))
    for name in LONG_COLS:
        df = df.withColumn(name, F.col(name).cast("long"))
    if any(df.where(F.col(name).isNull()).limit(1).count()
           for name in DATE_COLS + TIMESTAMP_COLS + LONG_COLS):
        raise ValueError("HL7_STAGING_TYPED_FACT_HOLD")
    return df


def publish_local_delta(rows: list[dict], *, warehouse_uri: str) -> dict:
    """Local-only Delta table create-or-verify with no overwrite or append."""
    _warehouse(warehouse_uri)
    spark = _spark(warehouse_uri)
    try:
        df = _frame(spark, rows)
        spark.sql("CREATE DATABASE IF NOT EXISTS hl7_staging")
        if spark.catalog.tableExists(TABLE):
            prior = spark.table(TABLE)
            # Delta persists different nullable metadata from the Python
            # in-memory StructType. Compare semantic columns/types, then exact
            # row multisets in both directions; do not reject safe replay for
            # storage-only nullability canonicalization.
            old_fields = [(v.name, v.dataType.simpleString()) for v in prior.schema.fields]
            new_fields = [(v.name, v.dataType.simpleString()) for v in df.schema.fields]
            if (old_fields != new_fields or prior.count() != len(rows)
                    or prior.exceptAll(df).limit(1).count()
                    or df.exceptAll(prior).limit(1).count()):
                raise ValueError("HL7_EXISTING_DELTA_BATCH_CONFLICT_HOLD")
            state = "ALREADY_MATCHING_REPLAY_SKIP"
        else:
            df.write.format("delta").mode("errorifexists").saveAsTable(TABLE)
            state = "CREATED"
        record = spark.sql(f"DESCRIBE DETAIL {TABLE}").first().asDict()
        if record.get("format") != "delta":
            raise ValueError("HL7_STAGING_NOT_PHYSICAL_DELTA")
        parsed = urlparse(record["location"])
        if parsed.scheme not in ("", "file"):
            raise ValueError("HL7_STAGING_NOT_LOCAL")
        log = Path(parsed.path) / "_delta_log"
        if not log.is_dir() or spark.table(TABLE).count() != len(rows):
            raise ValueError("HL7_STAGING_DELTA_READBACK_HOLD")
        return {"status": state, "table": TABLE, "rows": len(rows),
                "format": "delta", "scope": "LOCAL_CANDIDATE_NOT_SILVER"}
    finally:
        spark.stop()


def main() -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--manifest", type=Path, required=True)
    cli.add_argument("--blob-root", type=Path, required=True)
    cli.add_argument("--manifest-sha256", required=True)
    cli.add_argument("--source-sha256", required=True)
    cli.add_argument("--request-id", required=True)
    cli.add_argument("--ingest-date", required=True)
    cli.add_argument("--processing-run-id", required=True)
    cli.add_argument("--processed-at", required=True)
    cli.add_argument("--warehouse-uri", required=True)
    args = cli.parse_args()
    try:
        rows = verified_seed_rows(
            args.manifest.read_bytes(), args.blob_root,
            manifest_sha256=args.manifest_sha256,
            source_sha256=args.source_sha256,
            request_id=args.request_id, ingest_date=args.ingest_date,
            processing_run_id=args.processing_run_id, processed_at=args.processed_at)
        result = publish_local_delta(rows, warehouse_uri=args.warehouse_uri)
    except (ValueError, OSError) as exc:
        code = str(exc)
        if not (code.startswith("HL7_") and len(code) < 115
                and all(c.isupper() or c.isdigit() or c == "_" for c in code)):
            code = "HL7_STAGING_INPUT_OR_RUNTIME_HOLD"
        raise SystemExit(code) from None
    print("HL7_PARSER_TO_LOCAL_STAGING_DELTA=" + result["status"])
    print("HL7_STAGING_ROW_COUNT=" + str(result["rows"]))
    print("HL7_FORMAL_FABRIC_SILVER_APPROVED=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
