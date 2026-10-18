#!/usr/bin/env bash
set -Eeuo pipefail
echo "#### TASK003 STEP04 PREPARE OUTPUT BEGIN ####"
trap 'rc=$?; echo "PREPARE_EXIT_CODE=${rc}"; echo "#### TASK003 STEP04 PREPARE OUTPUT END ####"; exit "${rc}"' EXIT
ROOT="/data/spark/healthcare-data-platform"
mkdir -p "${ROOT}/apps/task003" "${ROOT}/scripts/task003"
cat > "${ROOT}/apps/task003/build_encounter_raw_evidence.py" <<'TASK003_FROZEN_BUILDER'
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
TASK003_FROZEN_BUILDER
chmod +x "${ROOT}/apps/task003/build_encounter_raw_evidence.py"
cat > "${ROOT}/apps/task003/resolve_encounter_raw_resume.py" <<'TASK003_RESUME_HELPER_PY'
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
TASK003_RESUME_HELPER_PY
chmod +x "${ROOT}/apps/task003/resolve_encounter_raw_resume.py"
cat > "${ROOT}/scripts/task003/04-publish-canonical-encounter.sh" <<'TASK003_FROZEN_RUNNER'
#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="/data/spark/healthcare-data-platform"
# TASK003_RESUME_ENTRY
if [[ "$#" -gt 0 ]]; then
    if [[ "$#" -eq 2 && "$1" == "--resume-run" ]]; then
        exec "${ROOT}/scripts/task003/04-resume-canonical-encounter-publish.sh" "$2"
    fi
    echo "Usage: $0 [--resume-run encounter-raw-YYYYMMDDTHHMMSSZ-PID]"
    exit 2
fi

STEP03_ROOT="${ROOT}/runtime/reports/task003/step03"
STEP04_ROOT="${ROOT}/runtime/reports/task003/step04"

RESOLVER="${ROOT}/apps/resolve_verified_intake_file.py"

APP_SOURCE="${ROOT}/spark/apps/publish_canonical_entity.py"
COMMON_MANIFEST="${ROOT}/spark/common/batch_manifest.py"
COMMON_GATE="${ROOT}/spark/common/canonical_gate.py"

CONTRACT="${ROOT}/spark/contracts/canonical/encounter-v1.json"
TEMPLATE="${ROOT}/spark/manifests/common/canonical-raw-publish.yaml.tpl"

NS="dw-spark"

S3_ENDPOINT="http://dw-seaweedfs-s3.dw-seaweedfs.svc.cluster.local:8333"

mkdir -p "${STEP04_ROOT}"

UTILITY_POD=""

cleanup() {
    if [[ -n "${UTILITY_POD}" ]]; then
        kubectl delete pod \
          "${UTILITY_POD}" \
          -n "${NS}" \
          --ignore-not-found \
          --wait=false \
          >/dev/null 2>&1 \
          || true
    fi
}

echo "#### TASK003 STEP04 RUN OUTPUT BEGIN ####"
step04_finish() {
    rc=$?
    trap - EXIT
    cleanup
    echo "RUN_EXIT_CODE=${rc}"
    echo "#### TASK003 STEP04 RUN OUTPUT END ####"
    exit "${rc}"
}
trap step04_finish EXIT


echo "============================================================"
echo "TASK-003 / STEP 04"
echo "Canonical Encounter Gate -> health-raw"
echo "============================================================"
echo


# ============================================================
# 1. Runtime prerequisites
# ============================================================

echo "[1/9] Runtime prerequisites..."

for file in \
  "${RESOLVER}" \
  "${APP_SOURCE}" \
  "${COMMON_MANIFEST}" \
  "${COMMON_GATE}" \
  "${CONTRACT}" \
  "${TEMPLATE}"
do
    [[ -s "${file}" ]] || {
        echo "ERROR: missing required file:"
        echo "  ${file}"
        exit 1
    }
done

kubectl get secret \
  dw-spark-s3-secret \
  -n "${NS}" \
  >/dev/null

kubectl get serviceaccount \
  spark-job \
  -n "${NS}" \
  >/dev/null

echo "PASS"
echo


# ============================================================
# 2. Resolve latest verified STEP03 Encounter run
# ============================================================

echo "[2/9] Resolve latest verified STEP03..."

readarray -t STEP03_VALUES < <(
python3 - "${STEP03_ROOT}" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])

candidates = []

for path in root.glob("*/run-state.json"):
    try:
        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        continue

    if not (
        data.get("task") == "TASK-003"
        and data.get("step") == "STEP-03"
        and data.get("status") == "PASS"
        and data.get("entity") == "encounter"
        and data.get("canonical_version") == "v1"
        and data.get("raw_published") is False
        and data.get("postgresql_write") is False
    ):
        continue

    candidates.append(
        (
            path.stat().st_mtime,
            path,
            data,
        )
    )

if not candidates:
    raise SystemExit(
        "No verified TASK-003 STEP03 "
        "Encounter run-state found."
    )

candidates.sort(
    key=lambda x: x[0],
    reverse=True,
)

_, path, data = candidates[0]

required = [
    "batch_id",
    "run_id",
    "processing_data_uri",
    "canonical_rows",
    "source",
    "source_version",
    "ingest_date",
    "source_file",
    "source_file_sha256",
    "source_file_size_bytes",
    "intake_manifest_uri",
    "intake_manifest_sha256",
]

for name in required:
    if name not in data:
        raise SystemExit(
            f"STEP03 state missing {name}"
        )

values = [
    data["batch_id"],
    data["run_id"],
    data["processing_data_uri"],
    data["canonical_rows"],
    data["source"],
    data["source_version"],
    data["ingest_date"],
    data["source_file"],
    data["source_file_sha256"],
    data["source_file_size_bytes"],
    data["intake_manifest_uri"],
    data["intake_manifest_sha256"],
    str(path),
]

for value in values:
    print(value)
PY
)

BATCH_ID="${STEP03_VALUES[0]}"
PROCESSING_RUN_ID="${STEP03_VALUES[1]}"
PROCESSING_DATA_URI="${STEP03_VALUES[2]}"
STEP03_ROWS="${STEP03_VALUES[3]}"

STEP03_SOURCE="${STEP03_VALUES[4]}"
STEP03_SOURCE_VERSION="${STEP03_VALUES[5]}"
STEP03_INGEST_DATE="${STEP03_VALUES[6]}"

STEP03_SOURCE_FILE="${STEP03_VALUES[7]}"
STEP03_SOURCE_SHA="${STEP03_VALUES[8]}"
STEP03_SOURCE_SIZE="${STEP03_VALUES[9]}"

STEP03_MANIFEST_URI="${STEP03_VALUES[10]}"
STEP03_MANIFEST_SHA="${STEP03_VALUES[11]}"

STEP03_STATE_FILE="${STEP03_VALUES[12]}"

echo "BATCH_ID=${BATCH_ID}"
echo "PROCESSING_RUN_ID=${PROCESSING_RUN_ID}"
echo "PROCESSING_DATA_URI=${PROCESSING_DATA_URI}"
echo "STEP03_ROWS=${STEP03_ROWS}"
echo "STEP03_STATE_FILE=${STEP03_STATE_FILE}"

echo "PASS"
echo


# ============================================================
# 3. Re-resolve authoritative TASK001 lineage
# ============================================================

echo "[3/9] Revalidate TASK-001 Encounter lineage..."

readarray -t SOURCE_VALUES < <(
    "${RESOLVER}" \
      encounters \
      --format json \
    | python3 -c '
import json
import sys

d = json.load(sys.stdin)

for value in [
    d["manifest_status"],
    d["manifest_uri"],
    d["manifest_sha256"],
    d["source"],
    d["source_version"],
    d["batch_id"],
    d["ingest_date"],
    d["path"],
    d["row_count"],
    d["size_bytes"],
    d["sha256"],
]:
    print(value)
'
)

MANIFEST_STATUS="${SOURCE_VALUES[0]}"
INPUT_MANIFEST_S3="${SOURCE_VALUES[1]}"
INPUT_MANIFEST_SHA256="${SOURCE_VALUES[2]}"

SOURCE="${SOURCE_VALUES[3]}"
SOURCE_VERSION="${SOURCE_VALUES[4]}"
SOURCE_BATCH_ID="${SOURCE_VALUES[5]}"
INGEST_DATE="${SOURCE_VALUES[6]}"

SOURCE_FILE="${SOURCE_VALUES[7]}"
EXPECTED_ROWS="${SOURCE_VALUES[8]}"
SOURCE_FILE_SIZE_BYTES="${SOURCE_VALUES[9]}"
SOURCE_FILE_SHA256="${SOURCE_VALUES[10]}"

INPUT_MANIFEST_S3A="$(
    printf '%s' "${INPUT_MANIFEST_S3}" \
    | sed 's#^s3://#s3a://#'
)"

[[ "${MANIFEST_STATUS}" == "INTAKE_VERIFIED" ]] || {
    echo "ERROR: intake manifest not verified."
    exit 1
}

[[ "${SOURCE_BATCH_ID}" == "${BATCH_ID}" ]] || {
    echo "ERROR: STEP03/TASK001 batch mismatch."
    exit 1
}

[[ "${SOURCE}" == "${STEP03_SOURCE}" ]] || {
    echo "ERROR: source mismatch."
    exit 1
}

[[ "${SOURCE_VERSION}" == "${STEP03_SOURCE_VERSION}" ]] || {
    echo "ERROR: source_version mismatch."
    exit 1
}

[[ "${INGEST_DATE}" == "${STEP03_INGEST_DATE}" ]] || {
    echo "ERROR: ingest_date mismatch."
    exit 1
}

[[ "${SOURCE_FILE}" == "${STEP03_SOURCE_FILE}" ]] || {
    echo "ERROR: source_file mismatch."
    exit 1
}

[[ "${SOURCE_FILE_SHA256}" == "${STEP03_SOURCE_SHA}" ]] || {
    echo "ERROR: source SHA mismatch."
    exit 1
}

[[ "${SOURCE_FILE_SIZE_BYTES}" == "${STEP03_SOURCE_SIZE}" ]] || {
    echo "ERROR: source size mismatch."
    exit 1
}

[[ "${EXPECTED_ROWS}" == "${STEP03_ROWS}" ]] || {
    echo "ERROR: row count mismatch."
    exit 1
}

[[ "${INPUT_MANIFEST_S3}" == "${STEP03_MANIFEST_URI}" ]] || {
    echo "ERROR: manifest URI mismatch."
    exit 1
}

[[ "${INPUT_MANIFEST_SHA256}" == "${STEP03_MANIFEST_SHA}" ]] || {
    echo "ERROR: manifest SHA mismatch."
    exit 1
}

echo "MANIFEST_STATUS=${MANIFEST_STATUS}"
echo "EXPECTED_ROWS=${EXPECTED_ROWS}"
echo "SOURCE_FILE_SHA256=${SOURCE_FILE_SHA256}"
echo "LINEAGE_REVALIDATION=PASS"
echo


# ============================================================
# 4. Allocate isolated Raw publish run
# ============================================================

echo "[4/9] Allocate immutable Raw publish run..."

UTC_STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

RAW_RUN_ID="encounter-raw-${UTC_STAMP}-$$"

APP_NAME="task003-encounter-raw-${UTC_STAMP,,}-$$"

CONFIGMAP_NAME="task003-encounter-raw-app-${UTC_STAMP,,}-$$"

RAW_BASE_KEY="canonical_version=v1/entity=encounter/source=${SOURCE}/source_version=${SOURCE_VERSION}/ingest_date=${INGEST_DATE}/batch_id=${BATCH_ID}/run_id=${RAW_RUN_ID}"

RAW_BASE_S3="s3://health-raw/${RAW_BASE_KEY}"

RAW_DATA_S3="${RAW_BASE_S3}/data/"
RAW_DATA_S3A="s3a://health-raw/${RAW_BASE_KEY}/data/"

DQ_URI="${RAW_BASE_S3}/dq/result.json"
RAW_MANIFEST_URI="${RAW_BASE_S3}/manifest.json"

RUN_DIR="${STEP04_ROOT}/${RAW_RUN_ID}"

RENDERED="${RUN_DIR}/sparkapplication.yaml"
DRIVER_LOG="${RUN_DIR}/driver.log"

DQ_FILE="${RUN_DIR}/dq-result.json"
MANIFEST_FILE="${RUN_DIR}/manifest.json"

REMOTE_DQ_FILE="${RUN_DIR}/dq-result.remote.json"
REMOTE_MANIFEST_FILE="${RUN_DIR}/manifest.remote.json"

STATE_FILE="${RUN_DIR}/run-state.json"

mkdir -p "${RUN_DIR}"

echo "RAW_PUBLISH_RUN_ID=${RAW_RUN_ID}"
echo "RAW_DATA_URI=${RAW_DATA_S3}"
echo "DQ_URI=${DQ_URI}"
echo "RAW_MANIFEST_URI=${RAW_MANIFEST_URI}"

echo "PASS"
echo


# ============================================================
# 5. Start S3 utility Pod + Raw prefix guard
# ============================================================

echo "[5/9] Raw prefix guard..."

UTILITY_POD="task003-raw-publisher-${UTC_STAMP,,}-$$"

cat <<YAML \
| kubectl apply -f - >/dev/null
apiVersion: v1
kind: Pod
metadata:
  name: ${UTILITY_POD}
  namespace: ${NS}
  labels:
    healthcare-task: task003
    healthcare-purpose: raw-publisher
spec:
  restartPolicy: Never

  containers:
    - name: aws
      image: amazon/aws-cli:2.15.57
      imagePullPolicy: IfNotPresent

      command:
        - /bin/sh
        - -c
        - sleep 3600

      envFrom:
        - secretRef:
            name: dw-spark-s3-secret
YAML


kubectl wait \
  --for=condition=Ready \
  "pod/${UTILITY_POD}" \
  -n "${NS}" \
  --timeout=180s \
  >/dev/null


EXISTING_KEYS="$(
    kubectl exec \
      -n "${NS}" \
      "${UTILITY_POD}" \
      -- \
      aws \
        --endpoint-url "${S3_ENDPOINT}" \
        s3api list-objects-v2 \
        --bucket health-raw \
        --prefix "${RAW_BASE_KEY}/" \
        --query 'Contents[].Key' \
        --output text \
    | tr -d '\r'
)"


if [[ -n "${EXISTING_KEYS}" ]] \
   && [[ "${EXISTING_KEYS}" != "None" ]]
then
    echo "ERROR:"
    echo "Raw run prefix already contains objects:"
    echo "${EXISTING_KEYS}"
    exit 1
fi


echo "RAW_PREFIX_EMPTY=PASS"
echo


# ============================================================
# 6. ConfigMap + render generic SparkApplication
# ============================================================

echo "[6/9] Build Canonical Gate SparkApplication..."


kubectl create configmap \
    "${CONFIGMAP_NAME}" \
    -n "${NS}" \
    --from-file=publish_canonical_entity.py="${APP_SOURCE}" \
    --from-file=batch_manifest.py="${COMMON_MANIFEST}" \
    --from-file=canonical_gate.py="${COMMON_GATE}" \
    --from-file=encounter-v1.json="${CONTRACT}" \
    --dry-run=client \
    -o yaml \
| kubectl apply -f - \
    >/dev/null


python3 - \
    "${TEMPLATE}" \
    "${RENDERED}" \
    "${APP_NAME}" \
    "${CONFIGMAP_NAME}" \
    "${INPUT_MANIFEST_S3A}" \
    "${BATCH_ID}" \
    "${PROCESSING_RUN_ID}" \
    "${PROCESSING_DATA_URI}" \
    "${RAW_DATA_S3A}" <<'PY'

import sys
from pathlib import Path


(
    source,
    destination,
    app_name,
    configmap_name,
    manifest_uri,
    batch_id,
    processing_run_id,
    processing_uri,
    raw_uri,
) = sys.argv[1:]


text = Path(source).read_text(
    encoding="utf-8"
)


replacements = {
    "__APP_NAME__":
        app_name,

    "__TASK_LABEL__":
        "task003",

    "__CONFIGMAP_NAME__":
        configmap_name,

    "__INPUT_MANIFEST_URI__":
        manifest_uri,

    "__BATCH_ID__":
        batch_id,

    "__PROCESSING_RUN_ID__":
        processing_run_id,

    "__PROCESSING_DATA_URI__":
        processing_uri,

    "__RAW_DATA_URI__":
        raw_uri,

    "__CONTRACT_FILE__":
        "encounter-v1.json",

    "__ENTITY__":
        "encounter",

    "__DATASET__":
        "encounters",

    "__SOURCE_FILE_NAME__":
        "encounters.csv",

    "__EXPECTED_ADAPTER_NAME__":
        "synthea_encounter_adapter",

    "__ADAPTER_VERSION__":
        "v1",

    "__CANONICAL_VERSION__":
        "v1",
}


for old, new in replacements.items():
    text = text.replace(
        old,
        new,
    )


unresolved = [
    line
    for line in text.splitlines()
    if "__" in line
]


if unresolved:
    raise SystemExit(
        "Unresolved template placeholders:\n"
        + "\n".join(unresolved)
    )


Path(destination).write_text(
    text,
    encoding="utf-8",
)
PY


kubectl apply \
  --dry-run=client \
  -f "${RENDERED}" \
  >/dev/null


echo "CONFIGMAP=${CONFIGMAP_NAME}"
echo "SPARKAPPLICATION_RENDER=PASS"
echo


# ============================================================
# 7. Submit generic Canonical Gate SparkApplication
# ============================================================

echo "[7/9] Submit Canonical Gate SparkApplication..."


kubectl apply \
  -f "${RENDERED}"


FINAL_STATE=""


for _ in $(seq 1 180)
do
    FINAL_STATE="$(
        kubectl get sparkapplication \
          "${APP_NAME}" \
          -n "${NS}" \
          -o jsonpath='{.status.applicationState.state}' \
          2>/dev/null \
        || true
    )"


    case "${FINAL_STATE}" in
        COMPLETED)
            break
            ;;

        FAILED|FAILING|UNKNOWN)
            break
            ;;
    esac


    sleep 5
done


echo "FINAL_STATE=${FINAL_STATE}"


kubectl logs \
  -n "${NS}" \
  "${APP_NAME}-driver" \
  > "${DRIVER_LOG}" \
  2>&1 \
  || true


if [[ "${FINAL_STATE}" != "COMPLETED" ]]
then
    echo
    tail -300 "${DRIVER_LOG}" || true

    echo
    echo "ERROR:"
    echo "Canonical Gate SparkApplication failed."

    exit 1
fi


REQUIRED_MARKERS=(
    "INPUT_MANIFEST_STATUS=INTAKE_VERIFIED"

    "EXPECTED_ROWS=${EXPECTED_ROWS}"

    "SOURCE_FILE_SHA256=${SOURCE_FILE_SHA256}"

    "CANONICAL_SCHEMA=PASS"

    "CANONICAL_REQUIRED_FIELDS=PASS"

    "CANONICAL_METADATA=PASS"

    "CANONICAL_GATE_ROWS=${EXPECTED_ROWS}"

    "CANONICAL_GATE_UNIQUE_KEYS=${EXPECTED_ROWS}"

    "CANONICAL_GATE=PASS"

    "RAW_WRITE=PASS"

    "RAW_READBACK=PASS"

    "RAW_ROWS=${EXPECTED_ROWS}"

    "RAW_UNIQUE_KEYS=${EXPECTED_ROWS}"

    "RAW_DATA_PUBLISHED=PASS"

    "RAW_MANIFEST_PUBLISHED=NO"

    "POSTGRESQL_WRITE=NO"

    "GENERIC_CANONICAL_PUBLISHER=PASS"
)


for marker in "${REQUIRED_MARKERS[@]}"
do
    if ! grep -Fxq \
      "${marker}" \
      "${DRIVER_LOG}"
    then
        echo
        echo "ERROR:"
        echo "Missing Spark marker:"
        echo "  ${marker}"
        echo
        tail -300 "${DRIVER_LOG}" || true
        exit 1
    fi
done


RAW_ROWS="$(
    grep '^RAW_ROWS=' \
      "${DRIVER_LOG}" \
    | tail -1 \
    | cut -d= -f2
)"


RAW_UNIQUE_KEYS="$(
    grep '^RAW_UNIQUE_KEYS=' \
      "${DRIVER_LOG}" \
    | tail -1 \
    | cut -d= -f2
)"


if [[ "${RAW_ROWS}" != "${EXPECTED_ROWS}" ]]
then
    echo "ERROR:"
    echo "Raw row count mismatch."
    exit 1
fi


if [[ "${RAW_UNIQUE_KEYS}" != "${EXPECTED_ROWS}" ]]
then
    echo "ERROR:"
    echo "Raw unique key count mismatch."
    exit 1
fi


echo "SPARK_CANONICAL_GATE=PASS"
echo "RAW_ROWS=${RAW_ROWS}"
echo "RAW_UNIQUE_KEYS=${RAW_UNIQUE_KEYS}"
echo

# TASK003_STEP04B1C_BEGIN
# ============================================================
# 8. Build + publish DQ, verify S3 bytes before approval
# ============================================================
echo "[8/9] Build + publish DQ..."
EVIDENCE_BUILDER="${ROOT}/apps/task003/build_encounter_raw_evidence.py"
[[ -s "${EVIDENCE_BUILDER}" ]] || { echo "ERROR: missing evidence builder"; exit 1; }

export BATCH_ID PROCESSING_RUN_ID PROCESSING_DATA_URI STEP03_STATE_FILE
export SOURCE SOURCE_VERSION INGEST_DATE SOURCE_FILE SOURCE_FILE_SHA256
export SOURCE_FILE_SIZE_BYTES INPUT_MANIFEST_S3 INPUT_MANIFEST_SHA256
export EXPECTED_ROWS RAW_ROWS RAW_UNIQUE_KEYS RAW_RUN_ID RAW_BASE_S3
export RAW_DATA_S3 DQ_URI RAW_MANIFEST_URI DRIVER_LOG DQ_FILE
export REMOTE_DQ_FILE MANIFEST_FILE REMOTE_MANIFEST_FILE STATE_FILE
export APP_NAME CONFIGMAP_NAME CONTRACT

# Single writer, isolated run prefix. Never reuse or overwrite a metadata key.
publish_json_once() {
    local local_file="$1" uri="$2" remote_file="$3" label="$4"
    local key="${uri#s3://health-raw/}" found local_sha remote_sha
    [[ "${uri}" == "${RAW_BASE_S3}/"* ]] || {
        echo "ERROR: unexpected publication target: ${uri}"; return 1;
    }
    if ! found="$(kubectl exec -n "${NS}" "${UTILITY_POD}" -- \
        aws --endpoint-url "${S3_ENDPOINT}" s3api list-objects-v2 \
        --bucket health-raw --prefix "${key}" --output json)"; then
        echo "ERROR: ${label} existence check failed"; return 1
    fi
    printf '%s' "${found}" | python3 "${EVIDENCE_BUILDER}" empty-listing
    kubectl exec -i -n "${NS}" "${UTILITY_POD}" -- \
        aws --endpoint-url "${S3_ENDPOINT}" s3 cp - "${uri}" \
        --content-type application/json --only-show-errors < "${local_file}"
    kubectl exec -n "${NS}" "${UTILITY_POD}" -- \
        aws --endpoint-url "${S3_ENDPOINT}" s3 cp "${uri}" - \
        --only-show-errors > "${remote_file}"
    local_sha="$(sha256sum "${local_file}")"
    remote_sha="$(sha256sum "${remote_file}")"
    [[ "${local_sha%% *}" == "${remote_sha%% *}" ]] || {
        echo "ERROR: ${label} S3 readback SHA256 mismatch"; return 1;
    }
    echo "${label}_PUBLISHED=PASS"
    echo "${label}_READBACK_SHA256=PASS"
}

python3 "${EVIDENCE_BUILDER}" dq
publish_json_once "${DQ_FILE}" "${DQ_URI}" "${REMOTE_DQ_FILE}" DQ
echo

# ============================================================
# 9. Publish Raw manifest LAST, then local acceptance state
# ============================================================
echo "[9/9] Publish approved Raw manifest LAST..."
# Builder refuses to approve if the remote DQ is missing or different.
python3 "${EVIDENCE_BUILDER}" manifest
publish_json_once "${MANIFEST_FILE}" "${RAW_MANIFEST_URI}" \
    "${REMOTE_MANIFEST_FILE}" RAW_MANIFEST
# Recheck both remote JSON documents before atomically writing PASS state.
python3 "${EVIDENCE_BUILDER}" state

echo "STEP04=PASS"
echo "SPARK_APPLICATION=COMPLETED"
echo "CANONICAL_GATE=PASS"
echo "RAW_ROWS=${RAW_ROWS}"
echo "RAW_UNIQUE_KEYS=${RAW_UNIQUE_KEYS}"
echo "RAW_STATUS=APPROVED"
echo "RAW_PUBLISH_RUN_ID=${RAW_RUN_ID}"
echo "RAW_DATA_URI=${RAW_DATA_S3}"
echo "RAW_MANIFEST_URI=${RAW_MANIFEST_URI}"
echo "RUN_STATE=${STATE_FILE}"
echo "POSTGRESQL_WRITE=NO"
echo "PHASE3C_TOUCHED=NO"
# TASK003_STEP04B1C_END
TASK003_FROZEN_RUNNER
chmod +x "${ROOT}/scripts/task003/04-publish-canonical-encounter.sh"
bash -n "${ROOT}/scripts/task003/04-publish-canonical-encounter.sh"
cat > "${ROOT}/scripts/task003/04-resume-canonical-encounter-publish.sh" <<'TASK003_RESUME_RUNNER_SH'
#!/usr/bin/env bash
set -Eeuo pipefail
echo "#### TASK003 STEP04 RESUME OUTPUT BEGIN ####"
ROOT="/data/spark/healthcare-data-platform"
NS="dw-spark"
S3_ENDPOINT="http://dw-seaweedfs-s3.dw-seaweedfs.svc.cluster.local:8333"
UTILITY_POD=""
SESSION=""

finish() {
    rc=$?
    trap - EXIT
    if [[ -n "${UTILITY_POD}" ]]; then
        kubectl delete pod "${UTILITY_POD}" -n "${NS}" --ignore-not-found \
          --wait=false >/dev/null 2>&1 || true
    fi
    echo "RESUME_EXIT_CODE=${rc}"
    echo "RESUME_EVIDENCE=${SESSION}"
    echo "#### TASK003 STEP04 RESUME OUTPUT END ####"
    exit "${rc}"
}
trap finish EXIT

[[ "$#" -eq 1 && "$1" =~ ^encounter-raw-[0-9]{8}T[0-9]{6}Z-[0-9]+$ ]] || {
    echo "Usage: $0 encounter-raw-YYYYMMDDTHHMMSSZ-PID"; exit 2;
}
RAW_RUN_ID="$1"
RUN_DIR="${ROOT}/runtime/reports/task003/step04/${RAW_RUN_ID}"
[[ -s "${RUN_DIR}/dq-result.json" ]] || { echo "ERROR: draft DQ missing"; exit 1; }

STAMP="$(date -u +%Y%m%dT%H%M%SZ)-$$"
SESSION="${RUN_DIR}/resume-${STAMP}"
mkdir -p "${SESSION}"
exec 8>"${RUN_DIR}/resume.lock"
flock -n 8 || { echo "ERROR: another recovery is running"; exit 1; }

EVIDENCE_BUILDER="${ROOT}/apps/task003/build_encounter_raw_evidence.py"
RECOVERY_HELPER="${ROOT}/apps/task003/resolve_encounter_raw_resume.py"
APP_NAME="task003-encounter-raw-${RAW_RUN_ID#encounter-raw-}"
APP_NAME="${APP_NAME,,}"

echo "[1/4] Revalidate original completed Spark run and TASK001 lineage..."
kubectl get sparkapplication "${APP_NAME}" -n "${NS}" -o json > "${SESSION}/sparkapplication.json"
kubectl logs -n "${NS}" "${APP_NAME}-driver" > "${SESSION}/driver.log"
"${ROOT}/apps/resolve_verified_intake_file.py" encounters --format json > "${SESSION}/intake.json"
python3 "${RECOVERY_HELPER}" context "${ROOT}" "${RAW_RUN_ID}" "${SESSION}" > "${SESSION}/verified.env"
source "${SESSION}/verified.env"
echo "RESUME_LINEAGE_AND_SPARK_GATE=PASS"

echo "[2/4] Verify original Raw objects remain unchanged..."
UTILITY_POD="task003-raw-resume-${STAMP,,}"
cat <<YAML | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: ${UTILITY_POD}
  namespace: ${NS}
  labels:
    healthcare-task: task003
    healthcare-purpose: raw-resume
spec:
  restartPolicy: Never
  containers:
    - name: aws
      image: amazon/aws-cli:2.15.57
      imagePullPolicy: IfNotPresent
      command: ["/bin/sh", "-c", "sleep 600"]
      envFrom:
        - secretRef:
            name: dw-spark-s3-secret
YAML

kubectl wait --for=condition=Ready "pod/${UTILITY_POD}" -n "${NS}" --timeout=180s
RAW_KEY="${RAW_BASE_S3#s3://health-raw/}"
kubectl exec -n "${NS}" "${UTILITY_POD}" -- aws --endpoint-url "${S3_ENDPOINT}" \
  s3api list-objects-v2 --bucket health-raw --prefix "${RAW_KEY}/data/" \
  --output json > "${SESSION}/data-inventory.json"
python3 "${RECOVERY_HELPER}" inventory "${ROOT}" "${RAW_RUN_ID}" "${SESSION}"

publish_or_reuse_json() {
    local local_file="$1" uri="$2" remote_file="$3" label="$4"
    local key="${uri#s3://health-raw/}" listing="${remote_file}.listing" count
    [[ "${uri}" == "${RAW_BASE_S3}/"* ]] || return 1

    kubectl exec -n "${NS}" "${UTILITY_POD}" -- aws --endpoint-url "${S3_ENDPOINT}" \
      s3api list-objects-v2 --bucket health-raw --prefix "${key}" --output json > "${listing}"
    count="$(python3 "${RECOVERY_HELPER}" metadata-count "${listing}" "${key}")"

    if [[ "${count}" == "0" ]]; then
        python3 "${EVIDENCE_BUILDER}" empty-listing < "${listing}"
        kubectl exec -i -n "${NS}" "${UTILITY_POD}" -- aws --endpoint-url "${S3_ENDPOINT}" \
          s3 cp - "${uri}" --content-type application/json --only-show-errors < "${local_file}"
    fi

    kubectl exec -n "${NS}" "${UTILITY_POD}" -- aws --endpoint-url "${S3_ENDPOINT}" \
      s3 cp "${uri}" - --only-show-errors > "${remote_file}"

    cmp -s "${local_file}" "${remote_file}" || {
        echo "ERROR: ${label} content conflict or readback mismatch"; return 1;
    }
    echo "${label}_PUBLISHED=PASS"
    echo "${label}_READBACK_SHA256=PASS"
    echo "${label}_EXISTING_OBJECTS_REUSED=${count}"
}

echo "[3/4] Publish or verify DQ..."
python3 "${EVIDENCE_BUILDER}" dq
publish_or_reuse_json "${DQ_FILE}" "${DQ_URI}" "${REMOTE_DQ_FILE}" DQ

echo "[4/4] Publish approved manifest LAST and validate state..."
python3 "${EVIDENCE_BUILDER}" manifest
publish_or_reuse_json "${MANIFEST_FILE}" "${RAW_MANIFEST_URI}" "${REMOTE_MANIFEST_FILE}" RAW_MANIFEST
python3 "${EVIDENCE_BUILDER}" state

echo "STEP04=PASS"
echo "SPARK_APPLICATION=COMPLETED"
echo "CANONICAL_GATE=PASS"
echo "RAW_ROWS=${RAW_ROWS}"
echo "RAW_UNIQUE_KEYS=${RAW_UNIQUE_KEYS}"
echo "RAW_STATUS=APPROVED"
echo "RAW_PUBLISH_RUN_ID=${RAW_RUN_ID}"
echo "RUN_STATE=${STATE_FILE}"
echo "SPARK_APPLICATION_SUBMITTED=NO"
echo "RAW_PARQUET_REWRITTEN=NO"
echo "POSTGRESQL_WRITE=NO"
echo "PHASE3C_TOUCHED=NO"
TASK003_RESUME_RUNNER_SH
chmod +x "${ROOT}/scripts/task003/04-resume-canonical-encounter-publish.sh"
bash -n "${ROOT}/scripts/task003/04-resume-canonical-encounter-publish.sh"
python3 - "${ROOT}" <<'VERIFY_PY'
import ast, sys
from pathlib import Path
for name in ('build_encounter_raw_evidence.py', 'resolve_encounter_raw_resume.py'):
    ast.parse((Path(sys.argv[1]) / 'apps/task003' / name).read_bytes())
VERIFY_PY
echo 'STEP04_PREPARE=PASS'
echo 'RUNNER_EXECUTED=NO'
