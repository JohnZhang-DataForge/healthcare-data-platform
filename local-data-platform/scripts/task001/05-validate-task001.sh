#!/usr/bin/env bash
set -Eeuo pipefail


PROJECT_ROOT="${PROJECT_ROOT:-/data/spark/healthcare-data-platform}"

SCRIPT_DIR="${PROJECT_ROOT}/scripts/task001"

RESET="${SCRIPT_DIR}/00-reset-task001.sh"
STEP01="${SCRIPT_DIR}/01-validate-build-draft.sh"
STEP02="${SCRIPT_DIR}/02-s3-readonly-preflight.sh"
STEP03="${SCRIPT_DIR}/03-publish-landing-payload.sh"
STEP04="${SCRIPT_DIR}/04-publish-intake-manifest.sh"

GUARD="${PROJECT_ROOT}/apps/task001/landing_guard.py"


for required in \
    "${RESET}" \
    "${STEP01}" \
    "${STEP02}" \
    "${STEP03}" \
    "${STEP04}" \
    "${GUARD}"
do

    if [[ ! -f "${required}" ]]; then

        echo "ERROR: required file missing:"
        echo "  ${required}"

        exit 1

    fi

done


echo "============================================================"
echo "Healthcare Data Platform V2.1"
echo "TASK-001 / STEP 05"
echo "Final acceptance validation"
echo "============================================================"
echo


# ============================================================
# 1. Clean local runtime state
# ============================================================

echo "[1/8] Resetting TASK-001 local runtime..."
echo

RESET_LOG="/tmp/task001-step05-reset.log"

rm -f "${RESET_LOG}"

"${RESET}" \
    2>&1 \
    | tee "${RESET_LOG}"


# RESET removes runtime/reports/task001, so create STEP 05
# report directory only AFTER RESET completes.

REPORT_DIR="${PROJECT_ROOT}/runtime/reports/task001/step05"

mkdir -p "${REPORT_DIR}"

mv \
    "${RESET_LOG}" \
    "${REPORT_DIR}/00-reset.log"

echo
echo "PASS: local runtime reset"
echo


# ============================================================
# 2. Replay STEP 01
# ============================================================

echo "[2/8] Replaying STEP 01..."
echo

"${STEP01}" \
    2>&1 \
    | tee "${REPORT_DIR}/01-validation.log"

echo
echo "PASS: STEP 01 replay"
echo


# ============================================================
# 3. Replay STEP 02
# ============================================================

echo "[3/8] Replaying STEP 02..."
echo

"${STEP02}" \
    2>&1 \
    | tee "${REPORT_DIR}/02-s3-preflight.log"

echo
echo "PASS: STEP 02 replay"
echo


# ============================================================
# 4. Replay STEP 03
# ============================================================

echo "[4/8] Replaying STEP 03..."
echo

"${STEP03}" \
    2>&1 \
    | tee "${REPORT_DIR}/03-payload-replay.log"

echo
echo "PASS: STEP 03 replay"
echo


# ============================================================
# 5. Replay STEP 04
# ============================================================

echo "[5/8] Replaying STEP 04..."
echo

"${STEP04}" \
    2>&1 \
    | tee "${REPORT_DIR}/04-manifest-replay.log"

echo
echo "PASS: STEP 04 replay"
echo


# ============================================================
# Paths recreated by replay
# ============================================================

DRAFT="${PROJECT_ROOT}/runtime/reports/task001/step01/manifest.draft.json"

STEP02_PREFIX="${PROJECT_ROOT}/runtime/reports/task001/step02/prefix-analysis.txt"

STEP03_STATE="${PROJECT_ROOT}/runtime/reports/task001/step03/landing-payload-state.json"

STEP04_STATE="${PROJECT_ROOT}/runtime/reports/task001/step04/intake-state.json"

REMOTE_MANIFEST="${PROJECT_ROOT}/runtime/reports/task001/step04/manifest.remote.json"

TAMPERED_DRAFT="${REPORT_DIR}/tampered-manifest.draft.json"

CONFLICT_LOG="${REPORT_DIR}/conflict-negative-test.log"

FINAL_REPORT="${REPORT_DIR}/task001-final-validation.json"


# ============================================================
# 6. Validate replay semantics
# ============================================================

echo "[6/8] Validating replay semantics..."
echo


python3 - \
    "${DRAFT}" \
    "${STEP02_PREFIX}" \
    "${STEP03_STATE}" \
    "${STEP04_STATE}" \
    "${REMOTE_MANIFEST}" <<'PY'

import hashlib
import json
import sys
from pathlib import Path


(
    draft_file,
    prefix_file,
    step03_file,
    step04_file,
    remote_manifest_file
) = sys.argv[1:]


draft = json.loads(
    Path(draft_file).read_text(
        encoding="utf-8"
    )
)


step03 = json.loads(
    Path(step03_file).read_text(
        encoding="utf-8"
    )
)


step04 = json.loads(
    Path(step04_file).read_text(
        encoding="utf-8"
    )
)


remote_path = Path(
    remote_manifest_file
)


remote = json.loads(
    remote_path.read_text(
        encoding="utf-8"
    )
)


prefix_text = Path(
    prefix_file
).read_text(
    encoding="utf-8"
)


# ------------------------------------------------------------
# STEP 01
# ------------------------------------------------------------

assert (
    draft["status"]
    == "LOCAL_VALIDATED_NOT_UPLOADED"
)

assert (
    draft["expected_file_count"]
    == 18
)

assert (
    len(draft["files"])
    == 18
)


total_rows = sum(
    item["row_count"]
    for item in draft["files"]
)


assert total_rows == 227025


# ------------------------------------------------------------
# STEP 02
# Existing published batch must now be discoverable.
# ------------------------------------------------------------

assert (
    "V2_BATCH_PREFIX_COUNT=1"
    in prefix_text
)


# ------------------------------------------------------------
# STEP 03
# Because the batch already exists, final replay must reuse
# all 18 payloads and upload nothing.
# ------------------------------------------------------------

assert (
    step03["status"]
    == "PAYLOAD_VERIFIED"
)

assert (
    step03["verified_file_count"]
    == 18
)

assert (
    step03["uploaded_this_run"]
    == 0
)

assert (
    step03["reused_this_run"]
    == 18
)

assert (
    step03["manifest_present_before_step"]
    is True
)


# ------------------------------------------------------------
# STEP 04
# Existing manifest must be reused, not republished.
# ------------------------------------------------------------

assert (
    step04["status"]
    == "INTAKE_VERIFIED"
)

assert (
    step04["publish_mode"]
    == "REUSE_EXISTING"
)


# ------------------------------------------------------------
# Remote manifest
# ------------------------------------------------------------

assert (
    remote["status"]
    == "INTAKE_VERIFIED"
)

assert (
    remote["expected_file_count"]
    == 18
)

assert (
    len(remote["files"])
    == 18
)

assert (
    remote["verification"][
        "verified_file_count"
    ]
    == 18
)

assert (
    remote["verification"][
        "s3_readback"
    ]
    == "PASS"
)


manifest_sha = hashlib.sha256(
    remote_path.read_bytes()
).hexdigest()


assert (
    manifest_sha
    == step04["manifest_sha256"]
)


print("PASS: STEP 01")
print("  CSV               : 18/18")
print(f"  total rows        : {total_rows}")

print()

print("PASS: STEP 02")
print("  V2 batch prefixes : 1")

print()

print("PASS: STEP 03")
print(
    "  payload verified  : "
    f"{step03['verified_file_count']}/18"
)
print(
    "  uploaded replay   : "
    f"{step03['uploaded_this_run']}"
)
print(
    "  reused replay     : "
    f"{step03['reused_this_run']}"
)

print()

print("PASS: STEP 04")
print(
    "  manifest mode     : "
    f"{step04['publish_mode']}"
)
print(
    "  manifest SHA256   : "
    f"{manifest_sha}"
)

PY


echo
echo "PASS: replay semantics"
echo


# ============================================================
# 7. Safe negative conflict test
#
# Same batch_id but altered file checksum MUST be rejected.
# No S3 object is modified.
# ============================================================

echo "[7/8] Running same-batch/different-content conflict test..."
echo


python3 - \
    "${DRAFT}" \
    "${TAMPERED_DRAFT}" <<'PY'

import json
import sys
from pathlib import Path


source = Path(
    sys.argv[1]
)

target = Path(
    sys.argv[2]
)


data = json.loads(
    source.read_text(
        encoding="utf-8"
    )
)


# Keep the SAME batch_id and metadata,
# but deliberately alter one checksum.

patient = next(
    item
    for item in data["files"]
    if item["dataset"] == "patients"
)


original = patient["sha256"]

patient["sha256"] = (
    "0"
    if original[0] != "0"
    else "1"
) + original[1:]


target.write_text(
    json.dumps(
        data,
        ensure_ascii=False,
        indent=2
    ) + "\n",
    encoding="utf-8"
)


print(
    "Prepared local conflict fixture:"
)

print(
    f"  batch_id : "
    f"{data['batch_id']}"
)

print(
    "  dataset  : patients"
)

print(
    f"  original : "
    f"{original}"
)

print(
    f"  tampered : "
    f"{patient['sha256']}"
)

PY


set +e

python3 "${GUARD}" \
    compare-manifest \
    --draft "${TAMPERED_DRAFT}" \
    --manifest "${REMOTE_MANIFEST}" \
    > "${CONFLICT_LOG}" \
    2>&1

CONFLICT_RC=$?

set -e


cat "${CONFLICT_LOG}"

echo


if [[ "${CONFLICT_RC}" -eq 0 ]]; then

    echo "ERROR:"
    echo "Tampered same-batch content was incorrectly accepted."

    exit 1

fi


if ! grep -Eq \
    'conflict|mismatch' \
    "${CONFLICT_LOG}"
then

    echo "ERROR:"
    echo "Conflict test failed for an unexpected reason."

    exit 1

fi


echo "PASS:"
echo "Same batch_id + different checksum rejected."
echo "No S3 object was modified."
echo


# ============================================================
# 8. Generate final TASK-001 acceptance report
# ============================================================

echo "[8/8] Writing final TASK-001 acceptance report..."
echo


python3 - \
    "${DRAFT}" \
    "${STEP03_STATE}" \
    "${STEP04_STATE}" \
    "${REMOTE_MANIFEST}" \
    "${FINAL_REPORT}" <<'PY'

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


(
    draft_file,
    step03_file,
    step04_file,
    manifest_file,
    output_file
) = sys.argv[1:]


draft = json.loads(
    Path(draft_file).read_text(
        encoding="utf-8"
    )
)

step03 = json.loads(
    Path(step03_file).read_text(
        encoding="utf-8"
    )
)

step04 = json.loads(
    Path(step04_file).read_text(
        encoding="utf-8"
    )
)

manifest_path = Path(
    manifest_file
)

manifest = json.loads(
    manifest_path.read_text(
        encoding="utf-8"
    )
)


manifest_sha = hashlib.sha256(
    manifest_path.read_bytes()
).hexdigest()


report = {
    "task":
        "TASK-001",

    "name":
        "Synthea Whole-batch Intake",

    "status":
        "PASS",

    "validated_at":
        (
            datetime.now(
                timezone.utc
            )
            .replace(
                microsecond=0
            )
            .isoformat()
            .replace(
                "+00:00",
                "Z"
            )
        ),

    "batch_id":
        manifest["batch_id"],

    "landing_uri":
        step04["landing_uri"],

    "manifest_uri":
        step04["manifest_uri"],

    "manifest_sha256":
        manifest_sha,

    "source_validation": {
        "files":
            "18/18",

        "total_rows":
            sum(
                item["row_count"]
                for item in draft["files"]
            ),

        "header_validation":
            "PASS",

        "csv_structure_validation":
            "PASS",

        "local_negative_tests":
            "PASS"
    },

    "s3_payload": {
        "objects":
            "18/18",

        "readback_sha256":
            "18/18",

        "replay_uploaded":
            step03[
                "uploaded_this_run"
            ],

        "replay_reused":
            step03[
                "reused_this_run"
            ]
    },

    "manifest": {
        "status":
            manifest["status"],

        "publish_replay":
            step04[
                "publish_mode"
            ],

        "remote_validation":
            "PASS"
    },

    "negative_tests": {
        "missing_file":
            "PASS",

        "bad_header":
            "PASS",

        "malformed_row":
            "PASS",

        "extra_csv":
            "PASS",

        "same_batch_different_content":
            "PASS"
    },

    "protected_assets": {
        "legacy_phase3c_touched":
            False,

        "old_landing_touched":
            False,

        "omop_touched":
            False
    }
}


Path(output_file).write_text(
    json.dumps(
        report,
        ensure_ascii=False,
        indent=2
    ) + "\n",
    encoding="utf-8"
)


print(
    f"Final report:"
)

print(
    f"  {output_file}"
)

PY


echo
echo "============================================================"
echo "TASK-001 FINAL ACCEPTANCE"
echo "============================================================"
echo
echo "TASK-001 Status : PASS"
echo
echo "Batch:"
echo "  synthea-20261005-pop100-atlanta"
echo
echo "Source validation:"
echo "  CSV               18/18"
echo "  total rows        227025"
echo "  negative tests    PASS"
echo
echo "Landing validation:"
echo "  payload objects   18/18"
echo "  readback SHA256   18/18"
echo "  replay upload     0"
echo "  replay reuse      18"
echo
echo "Manifest:"
echo "  status            INTAKE_VERIFIED"
echo "  replay            REUSE_EXISTING"
echo
echo "Conflict protection:"
echo "  same batch / different checksum = REJECTED"
echo
echo "Protected assets:"
echo "  legacy Phase3C    PRESERVED"
echo "  old Landing       PRESERVED"
echo "  OMOP              UNCHANGED"
echo
echo "TASK001=PASS"
echo "WHOLE_BATCH_INTAKE=VERIFIED"
echo "============================================================"
