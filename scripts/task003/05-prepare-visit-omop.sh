#!/usr/bin/env bash
set -Eeuo pipefail
export GIT_PAGER=cat

echo "#### TASK003 STEP05A SOURCE INSTALL OUTPUT BEGIN ####"
WORK=""
finish() {
    rc=$?
    trap - EXIT
    if [[ -n "${WORK}" ]]; then rm -rf -- "${WORK}"; fi
    echo "INSTALL_EXIT_CODE=${rc}"
    echo "#### TASK003 STEP05A SOURCE INSTALL OUTPUT END ####"
    exit "${rc}"
}
trap finish EXIT

ROOT="${HEALTHCARE_PROJECT_ROOT:-/data/spark/healthcare-data-platform}"
[[ -f "${ROOT}/apps/task003/build_encounter_raw_evidence.py" ]]
WORK="$(mktemp -d)"
mkdir -p "${WORK}/apps/task003" "${WORK}/tests/task003" "${WORK}/scripts/task003"

cat > "${WORK}/apps/task003/resolve_approved_encounter_raw.py" <<'SOURCE_0'
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
SOURCE_0

cat > "${WORK}/tests/task003/test_approved_encounter_raw.py" <<'SOURCE_1'
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "apps/task003"))
import build_encounter_raw_evidence as publisher
from resolve_approved_encounter_raw import resolve, sha


class ApprovedEncounterInputTests(unittest.TestCase):
    def write(self, path, value):
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

        for name in ("canonical/encounter-v1.json", "omop/visit-class-v1.json"):
            target = self.root / "spark/contracts" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO / "spark/contracts" / name, target)

        self.run_id = "encounter-raw-test-1"
        self.run = self.root / "runtime/reports/task003/step04" / self.run_id
        self.run.mkdir(parents=True)
        self.step03 = self.root / "runtime/reports/task003/step03/encounter-test-1/run-state.json"
        self.step03.parent.mkdir(parents=True)

        partition = "source=synthea/source_version=v3.3.0/ingest_date=2026-10-08/batch_id=test-batch"
        base = "s3://health-raw/canonical_version=v1/entity=encounter/" + partition + "/run_id=" + self.run_id

        c = dict(
            BATCH_ID="test-batch", PROCESSING_RUN_ID="encounter-test-1",
            RAW_RUN_ID=self.run_id, SOURCE="synthea", SOURCE_VERSION="v3.3.0",
            INGEST_DATE="2026-10-08", SOURCE_FILE="payload/csv/encounters.csv",
            SOURCE_FILE_SHA256="a" * 64, SOURCE_FILE_SIZE_BYTES=100,
            INPUT_MANIFEST_S3="s3://health-landing/" + partition + "/manifest.json",
            INPUT_MANIFEST_SHA256="b" * 64,
            PROCESSING_DATA_URI="s3a://health-processing/test/data/",
            EXPECTED_ROWS=3, RAW_ROWS=3, RAW_UNIQUE_KEYS=3,
            RAW_DATA_S3=base + "/data/", DQ_URI=base + "/dq/result.json",
            DQ_FILE=str(self.run / "dq-result.json"),
            REMOTE_DQ_FILE=str(self.run / "dq-result.json"),
            contract_sha256=sha(self.root / "spark/contracts/canonical/encounter-v1.json"),
        )

        # Generate fixtures using the existing STEP04 publisher.
        self.write(self.run / "dq-result.json", publisher.dq(c))
        self.write(self.run / "manifest.json", publisher.manifest(c))

        self.state = dict(
            publisher.base(c), status="PASS", raw_status="APPROVED",
            raw_published=True, raw_manifest_readback="PASS", raw_readback="PASS",
            dq_status="PASS", dq_readback="PASS", spark_application_state="COMPLETED",
            postgresql_write=False, raw_data_uri=base + "/data/",
            raw_manifest_uri=base + "/manifest.json", dq_uri=c["DQ_URI"],
        )
        step03 = dict(
            publisher.base(c), step="STEP-03", status="PASS",
            run_id=c["PROCESSING_RUN_ID"],
            canonical_rows=3, canonical_unique_encounters=3,
            raw_published=False, postgresql_write=False,
        )
        self.write(self.step03, step03)
        self.reseal()

    def reseal(self):
        self.state["dq_sha256"] = sha(self.run / "dq-result.json")
        m = json.loads((self.run / "manifest.json").read_text())
        m["dq"]["sha256"] = self.state["dq_sha256"]
        self.write(self.run / "manifest.json", m)
        self.state["raw_manifest_sha256"] = sha(self.run / "manifest.json")
        self.write(self.run / "run-state.json", self.state)

    def change(self, path, key, value):
        obj = json.loads(path.read_text())
        obj[key] = value
        self.write(path, obj)

    def reject(self):
        with self.assertRaises(ValueError):
            resolve(self.root, self.run_id)

    def test_accept_existing_publisher_format(self):
        result = resolve(self.root, self.run_id)
        self.assertEqual(result["expected_rows"], 3)
        self.assertEqual(result["raw_manifest_sha256"], self.state["raw_manifest_sha256"])
        self.assertFalse(result["remote_verified"])

    def test_reject_unapproved_manifest_even_with_new_hash(self):
        self.change(self.run / "manifest.json", "status", "DRAFT")
        self.reseal()
        self.reject()

    def test_reject_damaged_bytes(self):
        with (self.run / "manifest.json").open("a") as f:
            f.write(" ")
        self.reject()

    def test_reject_foreign_run_uri(self):
        m = json.loads((self.run / "manifest.json").read_text())
        m["data"]["uri"] = "s3://health-raw/another-run/data/"
        self.write(self.run / "manifest.json", m)
        self.reseal()
        self.reject()

    def test_reject_failed_dq_even_with_new_hashes(self):
        self.change(self.run / "dq-result.json", "status", "FAIL")
        self.reseal()
        self.reject()

    def test_reject_changed_lineage(self):
        self.change(self.step03, "source_file_sha256", "c" * 64)
        self.reject()

    def test_reject_changed_contract(self):
        path = self.root / "spark/contracts/canonical/encounter-v1.json"
        path.write_text(path.read_text() + "\n")
        self.reject()

    def test_reject_boolean_publication_flag(self):
        self.state["raw_published"] = 1
        self.reseal()
        self.reject()

    def test_reject_path_traversal(self):
        with self.assertRaises(ValueError):
            resolve(self.root, "../../step03")


if __name__ == "__main__":
    unittest.main()
SOURCE_1

cat > "${WORK}/scripts/task003/05a-verify-visit-omop-input.sh" <<'SOURCE_2'
#!/usr/bin/env bash
set -Eeuo pipefail

echo "#### TASK003 STEP05A INPUT VERIFY OUTPUT BEGIN ####"
trap 'rc=$?; echo "VERIFY_EXIT_CODE=${rc}"; echo "#### TASK003 STEP05A INPUT VERIFY OUTPUT END ####"; exit "${rc}"' EXIT

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
[[ "$#" -eq 1 ]] || {
    echo "Usage: $0 RAW_RUN_ID"
    exit 2
}

mkdir -p "${ROOT}/runtime/reports/task003/step05"
REPORT="$(mktemp -d "${ROOT}/runtime/reports/task003/step05/input.XXXXXX")"

python3 "${ROOT}/apps/task003/resolve_approved_encounter_raw.py" \
    --project-root "${ROOT}" \
    --raw-run-id "$1" \
    --output "${REPORT}/input-context.json"

echo "LOCAL_APPROVED_RAW_INPUT=PASS"
echo "REMOTE_RAW_REVALIDATION=PENDING"
echo "INPUT_CONTEXT=${REPORT}/input-context.json"
echo "SPARK_APPLICATION_SUBMITTED=NO"
echo "S3_WRITE=NO"
echo "DATABASE_WRITE=NO"
SOURCE_2

cp -- "$(realpath "${BASH_SOURCE[0]}")" \
    "${WORK}/scripts/task003/05-prepare-visit-omop.sh"

bash -n "${WORK}/scripts/task003/05-prepare-visit-omop.sh"
bash -n "${WORK}/scripts/task003/05a-verify-visit-omop-input.sh"

python3 - "${WORK}" "${ROOT}" <<'INSTALL_PY'
from pathlib import Path
import shutil
import sys

work, root = map(Path, sys.argv[1:])
files = sorted(p for p in work.rglob("*") if p.is_file())

for p in files:
    if p.suffix == ".py":
        compile(p.read_text(encoding="utf-8"), str(p), "exec")

    target = root / p.relative_to(work)
    if target.is_symlink() or (
        target.exists()
        and (
            not target.is_file()
            or target.read_bytes() != p.read_bytes()
        )
    ):
        raise SystemExit("ERROR: existing source differs: " + str(target))

for p in files:
    target = root / p.relative_to(work)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        shutil.copyfile(p, target)
        target.chmod(0o755 if p.suffix == ".sh" else 0o644)
    print("SOURCE_READY=" + str(target))
INSTALL_PY

cd "${ROOT}"
python3 -m unittest discover \
    -s tests/task003 \
    -p test_approved_encounter_raw.py \
    -v

echo "STEP05A_SOURCE_AND_TESTS=PASS"
echo "GIT_COMMIT_CREATED=NO"
echo "S3_WRITE=NO"
echo "DATABASE_WRITE=NO"
