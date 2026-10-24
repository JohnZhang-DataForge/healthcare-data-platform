#!/usr/bin/env python3
"""Restore and verify one interrupted Encounter Raw publication."""
import json
import os
import re
import shlex
import sys
from pathlib import Path
from build_encounter_raw_evidence import context, dq, read


def inventory(document, prefix):
    items = document.get("Contents", [])
    if not isinstance(items, list):
        raise ValueError("Invalid data inventory")
    result = {}
    for item in items:
        key = item["Key"]
        if not key.startswith(prefix):
            continue
        if key in result or not isinstance(item.get("Size"), int):
            raise ValueError("Duplicate key or invalid object size")
        result[key] = (item["Size"], item["ETag"])
    if prefix + "_SUCCESS" not in result:
        raise ValueError("Raw _SUCCESS missing")
    if not any(k.endswith(".parquet") and size > 0 for k, (size, _) in result.items()):
        raise ValueError("Raw Parquet missing")
    return result


def main():
    if sys.argv[1] == "metadata-count":
        document, key = read(sys.argv[2]), sys.argv[3]
        if (not isinstance(document, dict)
                or not any(k in document for k in ("Contents", "KeyCount", "RequestCharged"))
                or document.get("IsTruncated", False) is not False
                or document.get("NextContinuationToken") not in (None, "")
                or "Error" in document):
            raise ValueError("Invalid metadata listing")
        items = document.get("Contents", [])
        if (not isinstance(items, list) or len(items) > 1
                or any(item.get("Key") != key for item in items)
                or document.get("CommonPrefixes", []) != []
                or ("KeyCount" in document and document["KeyCount"] != len(items))):
            raise ValueError("Unexpected metadata objects")
        print(len(items))
        return

    mode, root_text, run_id, session_text = sys.argv[1:]
    root, session = Path(root_text), Path(session_text)
    if root_text != "/data/spark/healthcare-data-platform":
        raise ValueError("Unexpected project root")
    if not re.fullmatch(r"encounter-raw-\d{8}T\d{6}Z-\d+", run_id):
        raise ValueError("Invalid Raw run ID")
    run_dir = root / "runtime/reports/task003/step04" / run_id

    if mode == "inventory":
        draft = read(run_dir / "dq-result.json")
        base_key = (f"canonical_version=v1/entity=encounter/source={draft['source']}/"
                    f"source_version={draft['source_version']}/ingest_date={draft['ingest_date']}/"
                    f"batch_id={draft['batch_id']}/run_id={run_id}")
        prior = sorted(run_dir.glob("diag-*/whole-run.listing.json"),
                       key=lambda p: p.stat().st_mtime, reverse=True)
        if not prior:
            raise ValueError("Verified diagnostic inventory required for recovery")
        prefix = base_key + "/data/"
        if inventory(read(prior[0]), prefix) != inventory(read(session / "data-inventory.json"), prefix):
            raise ValueError("Raw data objects differ from diagnostic evidence")
        print("RAW_OBJECT_INVENTORY_UNCHANGED=PASS")
        return

    if mode != "context":
        raise ValueError("Unknown recovery mode")
    draft = read(run_dir / "dq-result.json")
    current = read(session / "intake.json")
    app = read(session / "sparkapplication.json")
    if current["manifest_status"] != "INTAKE_VERIFIED":
        raise ValueError("TASK001 intake no longer verified")
    if app["status"]["applicationState"]["state"] != "COMPLETED":
        raise ValueError("Original SparkApplication is not COMPLETED")

    processing_id = draft["processing_run_id"]
    if not re.fullmatch(r"encounter-\d{8}T\d{6}Z-\d+", processing_id):
        raise ValueError("Invalid processing run ID")
    lineage = {"source": "source", "source_version": "source_version",
               "batch_id": "batch_id", "ingest_date": "ingest_date",
               "source_file": "path", "source_file_sha256": "sha256",
               "source_file_size_bytes": "size_bytes", "expected_rows": "row_count",
               "intake_manifest_uri": "manifest_uri", "intake_manifest_sha256": "manifest_sha256"}
    for key, intake_key in lineage.items():
        if draft[key] != current[intake_key]:
            raise ValueError(f"Current TASK001 lineage differs: {key}")
    if draft["raw_publish_run_id"] != run_id:
        raise ValueError("Draft DQ belongs to another Raw run")

    raw_base = (f"s3://health-raw/canonical_version=v1/entity=encounter/source={current['source']}/"
                f"source_version={current['source_version']}/ingest_date={current['ingest_date']}/"
                f"batch_id={current['batch_id']}/run_id={run_id}")
    tail = run_id.removeprefix("encounter-raw-").lower()
    values = {
        "BATCH_ID": current["batch_id"], "PROCESSING_RUN_ID": processing_id,
        "PROCESSING_DATA_URI": draft["processing_data_uri"],
        "STEP03_STATE_FILE": str(root / "runtime/reports/task003/step03" / processing_id / "run-state.json"),
        "SOURCE": current["source"], "SOURCE_VERSION": current["source_version"],
        "INGEST_DATE": current["ingest_date"], "SOURCE_FILE": current["path"],
        "SOURCE_FILE_SHA256": current["sha256"], "SOURCE_FILE_SIZE_BYTES": current["size_bytes"],
        "INPUT_MANIFEST_S3": current["manifest_uri"], "INPUT_MANIFEST_SHA256": current["manifest_sha256"],
        "EXPECTED_ROWS": current["row_count"], "RAW_ROWS": draft["raw_rows"],
        "RAW_UNIQUE_KEYS": draft["raw_unique_keys"], "RAW_RUN_ID": run_id,
        "RAW_BASE_S3": raw_base, "RAW_DATA_S3": raw_base + "/data/",
        "DQ_URI": raw_base + "/dq/result.json", "RAW_MANIFEST_URI": raw_base + "/manifest.json",
        "DRIVER_LOG": str(session / "driver.log"), "DQ_FILE": str(run_dir / "dq-result.json"),
        "REMOTE_DQ_FILE": str(session / "dq.remote.json"), "MANIFEST_FILE": str(run_dir / "manifest.json"),
        "REMOTE_MANIFEST_FILE": str(session / "manifest.remote.json"), "STATE_FILE": str(run_dir / "run-state.json"),
        "APP_NAME": "task003-encounter-raw-" + tail,
        "CONFIGMAP_NAME": "task003-encounter-raw-app-" + tail,
        "CONTRACT": str(root / "spark/contracts/canonical/encounter-v1.json")}

    if app["metadata"]["name"] != values["APP_NAME"]:
        raise ValueError("Unexpected SparkApplication identity")

    def scalars(value):
        if isinstance(value, dict):
            for v in value.values():
                yield from scalars(v)
        elif isinstance(value, list):
            for v in value:
                yield from scalars(v)
        elif isinstance(value, str):
            yield value

    parameters = set(scalars(app["spec"]))
    for expected in (current["manifest_uri"].replace("s3://", "s3a://", 1),
                     values["BATCH_ID"], processing_id, values["PROCESSING_DATA_URI"],
                     values["RAW_DATA_S3"].replace("s3://", "s3a://", 1)):
        if expected not in parameters:
            raise ValueError(f"Spark configuration does not bind expected input/output: {expected}")

    os.environ.update({k: str(v) for k, v in values.items()})
    verified = context()
    if draft != dq(verified):
        raise ValueError("Draft DQ differs from freshly verified evidence")
    for name, value in values.items():
        print(f"export {name}={shlex.quote(str(value))}")


if __name__ == "__main__":
    main()
