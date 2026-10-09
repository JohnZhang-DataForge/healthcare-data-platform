#!/usr/bin/env python3
"""Build TASK-003 Raw evidence from verified lineage and Spark output."""
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n",
                         encoding="utf-8")
    os.replace(temporary, path)


def env(name):
    value = os.environ.get(name, "")
    if not value or "\n" in value or "\r" in value:
        raise ValueError(f"Missing or invalid {name}")
    return value


def context():
    names = (
        "BATCH_ID PROCESSING_RUN_ID PROCESSING_DATA_URI STEP03_STATE_FILE "
        "SOURCE SOURCE_VERSION INGEST_DATE SOURCE_FILE SOURCE_FILE_SHA256 "
        "SOURCE_FILE_SIZE_BYTES INPUT_MANIFEST_S3 INPUT_MANIFEST_SHA256 "
        "EXPECTED_ROWS RAW_ROWS RAW_UNIQUE_KEYS RAW_RUN_ID RAW_BASE_S3 "
        "RAW_DATA_S3 DQ_URI RAW_MANIFEST_URI DRIVER_LOG DQ_FILE "
        "REMOTE_DQ_FILE MANIFEST_FILE REMOTE_MANIFEST_FILE STATE_FILE "
        "APP_NAME CONFIGMAP_NAME CONTRACT"
    ).split()
    c = {name: env(name) for name in names}
    for name in ("EXPECTED_ROWS", "RAW_ROWS", "RAW_UNIQUE_KEYS",
                 "SOURCE_FILE_SIZE_BYTES"):
        c[name] = int(c[name])
        if c[name] < 0:
            raise ValueError(f"Negative {name}")
    if not (c["EXPECTED_ROWS"] == c["RAW_ROWS"] == c["RAW_UNIQUE_KEYS"] > 0):
        raise ValueError("Raw counts do not match verified source")
    for name in ("SOURCE_FILE_SHA256", "INPUT_MANIFEST_SHA256"):
        value = c[name]
        if len(value) != 64 or any(x not in "0123456789abcdef" for x in value):
            raise ValueError(f"Invalid checksum {name}")
    state = read(c["STEP03_STATE_FILE"])
    fixed = {"task": "TASK-003", "step": "STEP-03", "status": "PASS",
             "entity": "encounter", "canonical_version": "v1",
             "raw_published": False, "postgresql_write": False}
    pairs = {
        "batch_id": "BATCH_ID", "run_id": "PROCESSING_RUN_ID",
        "processing_data_uri": "PROCESSING_DATA_URI", "source": "SOURCE",
        "source_version": "SOURCE_VERSION", "ingest_date": "INGEST_DATE",
        "source_file": "SOURCE_FILE", "source_file_sha256": "SOURCE_FILE_SHA256",
        "source_file_size_bytes": "SOURCE_FILE_SIZE_BYTES",
        "intake_manifest_uri": "INPUT_MANIFEST_S3",
        "intake_manifest_sha256": "INPUT_MANIFEST_SHA256",
        "canonical_rows": "EXPECTED_ROWS"}
    for key, expected in fixed.items():
        if state.get(key) != expected:
            raise ValueError(f"STEP03 no longer verified: {key}")
    for key, name in pairs.items():
        if state.get(key) != c[name]:
            raise ValueError(f"STEP03 lineage mismatch: {key}")
    expected_base = (
        "s3://health-raw/canonical_version=v1/entity=encounter/"
        f"source={c['SOURCE']}/source_version={c['SOURCE_VERSION']}/"
        f"ingest_date={c['INGEST_DATE']}/batch_id={c['BATCH_ID']}/"
        f"run_id={c['RAW_RUN_ID']}")
    if c["RAW_BASE_S3"] != expected_base:
        raise ValueError("Unexpected Raw prefix")
    for key, suffix in (("RAW_DATA_S3", "/data/"),
                        ("DQ_URI", "/dq/result.json"),
                        ("RAW_MANIFEST_URI", "/manifest.json")):
        if c[key] != expected_base + suffix:
            raise ValueError(f"Unexpected {key}")
    markers = Path(c["DRIVER_LOG"]).read_text(encoding="utf-8").splitlines()
    required = ["INPUT_MANIFEST_STATUS=INTAKE_VERIFIED",
                f"SOURCE_FILE_SHA256={c['SOURCE_FILE_SHA256']}",
                "CANONICAL_SCHEMA=PASS", "CANONICAL_REQUIRED_FIELDS=PASS",
                "CANONICAL_METADATA=PASS", "CANONICAL_GATE=PASS",
                "RAW_WRITE=PASS", "RAW_READBACK=PASS",
                "RAW_DATA_PUBLISHED=PASS", "RAW_MANIFEST_PUBLISHED=NO",
                "POSTGRESQL_WRITE=NO", "GENERIC_CANONICAL_PUBLISHER=PASS"]
    for key in ("EXPECTED_ROWS", "CANONICAL_GATE_ROWS",
                "CANONICAL_GATE_UNIQUE_KEYS", "RAW_ROWS", "RAW_UNIQUE_KEYS"):
        values = [line.split("=", 1)[1] for line in markers if line.startswith(key + "=")]
        if values != [str(c["EXPECTED_ROWS"])]:
            raise ValueError(f"Missing, ambiguous or wrong Spark count: {key}")
    if any(marker not in markers for marker in required):
        raise ValueError("Missing required Spark verification marker")
    c["contract_sha256"] = sha(c["CONTRACT"])
    return c


def base(c):
    return {
        "task": "TASK-003", "step": "STEP-04", "entity": "encounter",
        "canonical_version": "v1", "source": c["SOURCE"],
        "source_version": c["SOURCE_VERSION"], "batch_id": c["BATCH_ID"],
        "ingest_date": c["INGEST_DATE"],
        "processing_run_id": c["PROCESSING_RUN_ID"],
        "raw_publish_run_id": c["RAW_RUN_ID"],
        "source_file": c["SOURCE_FILE"],
        "source_file_sha256": c["SOURCE_FILE_SHA256"],
        "source_file_size_bytes": c["SOURCE_FILE_SIZE_BYTES"],
        "intake_manifest_uri": c["INPUT_MANIFEST_S3"],
        "intake_manifest_sha256": c["INPUT_MANIFEST_SHA256"],
        "processing_data_uri": c["PROCESSING_DATA_URI"],
        "contract_sha256": c["contract_sha256"],
        "expected_rows": c["EXPECTED_ROWS"], "raw_rows": c["RAW_ROWS"],
        "raw_unique_keys": c["RAW_UNIQUE_KEYS"]}


def dq(c):
    return dict(base(c), status="PASS", checks={
        name: "PASS" for name in (
            "canonical_schema", "canonical_required_fields", "canonical_metadata",
            "canonical_primary_key", "raw_write", "raw_readback")})


def verify_pair(local, remote, expected):
    if Path(local).read_bytes() != Path(remote).read_bytes():
        raise ValueError(f"S3 readback differs: {local}")
    if read(remote) != expected:
        raise ValueError(f"Evidence content differs: {remote}")


def manifest(c):
    verify_pair(c["DQ_FILE"], c["REMOTE_DQ_FILE"], dq(c))
    return dict(base(c), manifest_version="1.0", status="APPROVED",
                adapter_name="synthea_encounter_adapter", adapter_version="v1",
                input={"intake_manifest_uri": c["INPUT_MANIFEST_S3"],
                       "intake_manifest_sha256": c["INPUT_MANIFEST_SHA256"],
                       "source_file": c["SOURCE_FILE"],
                       "size_bytes": c["SOURCE_FILE_SIZE_BYTES"],
                       "sha256": c["SOURCE_FILE_SHA256"],
                       "expected_rows": c["EXPECTED_ROWS"],
                       "processing_data_uri": c["PROCESSING_DATA_URI"]},
                data={"uri": c["RAW_DATA_S3"], "format": "parquet",
                      "row_count": c["RAW_ROWS"],
                      "primary_key": ["source_system", "source_encounter_id"],
                      "unique_primary_keys": c["RAW_UNIQUE_KEYS"]},
                dq={"status": "PASS", "uri": c["DQ_URI"],
                    "sha256": sha(c["DQ_FILE"]), "readback_sha256": "PASS"})


def main():
    mode = sys.argv[1]
    if mode == "empty-listing":
        listing = json.load(sys.stdin)
        if not isinstance(listing, dict):
            raise ValueError("Invalid S3 listing type")
        if not any(k in listing for k in ("Contents", "KeyCount", "RequestCharged")):
            raise ValueError("Unrecognized S3 listing response")
        contents = listing.get("Contents", [])
        prefixes = listing.get("CommonPrefixes", [])
        if (not isinstance(contents, list) or contents
                or not isinstance(prefixes, list) or prefixes
                or ("KeyCount" in listing and listing["KeyCount"] != 0)
                or listing.get("IsTruncated", False) is not False
                or listing.get("NextContinuationToken") not in (None, "")
                or "Error" in listing):
            raise ValueError("Metadata key exists or S3 listing is invalid")
        return
    c = context()
    if mode == "dq":
        write(c["DQ_FILE"], dq(c))
    elif mode == "manifest":
        write(c["MANIFEST_FILE"], manifest(c))
    elif mode == "state":
        expected = manifest(c)
        verify_pair(c["MANIFEST_FILE"], c["REMOTE_MANIFEST_FILE"], expected)
        result = dict(base(c), status="PASS", run_id=c["RAW_RUN_ID"],
                      raw_status="APPROVED", raw_published=True,
                      raw_data_uri=c["RAW_DATA_S3"],
                      raw_manifest_uri=c["RAW_MANIFEST_URI"],
                      raw_manifest_sha256=sha(c["MANIFEST_FILE"]),
                      raw_manifest_readback="PASS", raw_readback="PASS",
                      dq_status="PASS", dq_uri=c["DQ_URI"],
                      dq_sha256=sha(c["DQ_FILE"]), dq_readback="PASS",
                      spark_application=c["APP_NAME"],
                      spark_application_state="COMPLETED", configmap=c["CONFIGMAP_NAME"],
                      postgresql_write=False, phase3c_touched=False,
                      completed_at=datetime.now(timezone.utc).isoformat())
        write(c["STATE_FILE"], result)
    else:
        raise ValueError(f"Unknown mode {mode}")


if __name__ == "__main__":
    main()
