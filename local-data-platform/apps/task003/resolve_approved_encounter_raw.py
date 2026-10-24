#!/usr/bin/env python3
"""Resolve an explicit Encounter Raw run from local publication evidence.

This does not validate live S3 objects or authorize a database write.
The consumer must revalidate the remote manifest/DQ against the returned hashes.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path.name}")
    return value


def require(actual, expected, label):
    if type(actual) is not type(expected) or actual != expected:
        raise ValueError(f"Evidence mismatch: {label}")
    if isinstance(expected, dict):
        for key in expected:
            require(actual[key], expected[key], label + "." + key)
    elif isinstance(expected, list):
        for index, value in enumerate(expected):
            require(actual[index], value, f"{label}[{index}]")


def resolve(root, raw_run_id):
    root = Path(root)
    if not re.fullmatch(r"encounter-raw-[A-Za-z0-9_-]+", raw_run_id):
        raise ValueError("Invalid raw_run_id")

    run = root / "runtime/reports/task003/step04" / raw_run_id
    state = read(run / "run-state.json")
    manifest = read(run / "manifest.json")
    dq = read(run / "dq-result.json")

    for name, key in (
        ("manifest.json", "raw_manifest_sha256"),
        ("dq-result.json", "dq_sha256"),
    ):
        require(sha(run / name), state.get(key), key)

    fixed = dict(
        task="TASK-003", step="STEP-04", status="PASS",
        entity="encounter", canonical_version="v1", source="synthea",
        source_version="v3.3.0", raw_publish_run_id=raw_run_id,
        raw_status="APPROVED", raw_published=True,
        raw_manifest_readback="PASS", raw_readback="PASS",
        dq_status="PASS", dq_readback="PASS",
        spark_application_state="COMPLETED", postgresql_write=False,
    )
    for key, value in fixed.items():
        require(state.get(key), value, "state." + key)

    shared = (
        "task step entity canonical_version source source_version batch_id ingest_date "
        "processing_run_id raw_publish_run_id source_file source_file_sha256 "
        "source_file_size_bytes intake_manifest_uri intake_manifest_sha256 "
        "processing_data_uri contract_sha256 expected_rows raw_rows raw_unique_keys"
    ).split()
    for key in shared:
        if key not in state:
            raise ValueError("Missing state field: " + key)
        require(manifest.get(key), state[key], "manifest." + key)
        require(dq.get(key), state[key], "dq." + key)

    for key in ("expected_rows", "raw_rows", "raw_unique_keys", "source_file_size_bytes"):
        if type(state[key]) is not int or state[key] <= 0:
            raise ValueError("Invalid positive integer: " + key)

    rows = state["expected_rows"]
    require(state["raw_rows"], rows, "raw_rows")
    require(state["raw_unique_keys"], rows, "raw_unique_keys")

    for key in ("source_file_sha256", "intake_manifest_sha256", "contract_sha256"):
        if not isinstance(state[key], str) or not re.fullmatch(r"[a-f0-9]{64}", state[key]):
            raise ValueError("Invalid checksum: " + key)

    for key in ("source", "source_version", "ingest_date", "batch_id", "processing_run_id"):
        if not isinstance(state[key], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", state[key]):
            raise ValueError("Invalid path component: " + key)

    partition = (
        f"source={state['source']}/source_version={state['source_version']}/"
        f"ingest_date={state['ingest_date']}/batch_id={state['batch_id']}"
    )
    base = f"s3://health-raw/canonical_version=v1/entity=encounter/{partition}/run_id={raw_run_id}"

    for key, suffix in (
        ("raw_data_uri", "/data/"),
        ("raw_manifest_uri", "/manifest.json"),
        ("dq_uri", "/dq/result.json"),
    ):
        require(state.get(key), base + suffix, key)

    require(
        state["intake_manifest_uri"],
        f"s3://health-landing/{partition}/manifest.json",
        "intake URI",
    )
    require(state["source_file"], "payload/csv/encounters.csv", "source_file")

    canonical = root / "spark/contracts/canonical/encounter-v1.json"
    mapping = root / "spark/contracts/omop/visit-class-v1.json"
    require(sha(canonical), state["contract_sha256"], "canonical contract SHA256")

    processing = state["processing_run_id"]
    step03 = read(root / "runtime/reports/task003/step03" / processing / "run-state.json")

    for key, value in dict(
        task="TASK-003", step="STEP-03", status="PASS",
        entity="encounter", canonical_version="v1", run_id=processing,
        raw_published=False, postgresql_write=False,
    ).items():
        require(step03.get(key), value, "step03." + key)

    for key in (
        "source", "source_version", "batch_id", "ingest_date", "source_file",
        "source_file_sha256", "source_file_size_bytes", "intake_manifest_uri",
        "intake_manifest_sha256", "processing_data_uri",
    ):
        require(step03.get(key), state[key], "step03." + key)

    require(step03.get("canonical_rows"), rows, "step03 rows")
    require(step03.get("canonical_unique_encounters"), rows, "step03 unique keys")

    for key, value in dict(
        manifest_version="1.0", status="APPROVED",
        adapter_name="synthea_encounter_adapter", adapter_version="v1",
    ).items():
        require(manifest.get(key), value, "manifest." + key)

    require(
        manifest.get("data"),
        dict(
            uri=base + "/data/", format="parquet", row_count=rows,
            primary_key=["source_system", "source_encounter_id"],
            unique_primary_keys=rows,
        ),
        "manifest.data",
    )
    require(
        manifest.get("dq"),
        dict(
            status="PASS", uri=base + "/dq/result.json",
            sha256=state["dq_sha256"], readback_sha256="PASS",
        ),
        "manifest.dq",
    )
    require(
        manifest.get("input"),
        dict(
            intake_manifest_uri=state["intake_manifest_uri"],
            intake_manifest_sha256=state["intake_manifest_sha256"],
            source_file=state["source_file"],
            size_bytes=state["source_file_size_bytes"],
            sha256=state["source_file_sha256"],
            expected_rows=rows,
            processing_data_uri=state["processing_data_uri"],
        ),
        "manifest.input",
    )

    require(dq.get("status"), "PASS", "dq.status")
    checks = (
        "canonical_schema canonical_required_fields canonical_metadata "
        "canonical_primary_key raw_write raw_readback"
    ).split()
    require(dq.get("checks"), {key: "PASS" for key in checks}, "dq.checks")

    rule = read(mapping)
    require(rule.get("source_system"), state["source"], "mapping source")
    require(rule.get("source_version"), state["source_version"], "mapping source version")
    require(rule.get("mapping_version"), "v1", "mapping version")

    result = {key: state[key] for key in (
        "source source_version batch_id ingest_date processing_run_id raw_publish_run_id "
        "raw_manifest_uri raw_manifest_sha256 raw_data_uri dq_uri dq_sha256 expected_rows"
    ).split()}

    return dict(
        result, task="TASK-003", step="STEP-05A", status="PASS",
        validation_scope="local_evidence", remote_verified=False,
        canonical_contract_sha256=state["contract_sha256"],
        mapping_contract_sha256=sha(mapping), postgresql_write=False,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--raw-run-id", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    result = resolve(args.project_root, args.raw_run_id)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    with args.output.open("x", encoding="utf-8") as handle:
        handle.write(text)
    print(text, end="")


if __name__ == "__main__":
    main()
