#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1 GIT_PAGER=cat

ROOT="${HEALTHCARE_PROJECT_ROOT:-/data/spark/healthcare-data-platform}"
STAGE=''

echo '#### TASK003 STEP05G2C2A RESERVATION SOURCE OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT
  [[ -z "$STAGE" ]] || rm -rf -- "$STAGE"
  echo "INSTALL_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G2C2A RESERVATION SOURCE OUTPUT END ####'
  exit "$rc"
}
trap finish EXIT

for rel in \
  apps/task003/prepare_visit_processed_write_intent.py \
  apps/task003/inspect_visit_processed_prefix.py \
  apps/task003/plan_visit_processed.py \
  spark/contracts/processed/visit-writer-safety-v1.json
do
  [[ -s "$ROOT/$rel" && ! -L "$ROOT/$rel" ]] || {
    echo "ERROR: missing prerequisite $rel"
    exit 1
  }
done

STAGE=$(mktemp -d /data/spark/temp_shell/05g2c2a-stage.XXXXXXXX)

mkdir -p \
  "$STAGE/apps/task003" \
  "$STAGE/tests/task003" \
  "$STAGE/scripts/task003"

# ========================================================
# 1. Reservation Resource Builder
# ========================================================

cat > "$STAGE/apps/task003/build_visit_writer_reservation.py" <<'PY_APP'
"""Build a deterministic Kubernetes ConfigMap reservation request.

No Kubernetes API calls are made here.
This is a PREPARED resource, not an acquired lock.
"""

import argparse
import hashlib
import json
from pathlib import Path

from inspect_visit_processed_prefix import get_prefix
from prepare_visit_processed_write_intent import POLICY as WRITER_POLICY
from plan_visit_processed import save_once


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(actual, expected, name):
    if type(actual) is not type(expected) or actual != expected:
        raise ValueError("RESERVATION_CONFLICT: " + name)


def build_resource(intent_bytes, plan_bytes, policy_bytes):
    intent = json.loads(intent_bytes)
    plan = json.loads(plan_bytes)
    policy = json.loads(policy_bytes)

    require(policy, WRITER_POLICY, "writer safety policy")

    require(
        intent.get("writer_safety_policy"),
        policy,
        "intent writer policy",
    )

    require(
        intent.get("writer_safety_policy_sha256"),
        sha(policy_bytes),
        "writer policy checksum",
    )

    require(
        intent.get("plan_sha256"),
        sha(plan_bytes),
        "immutable plan checksum",
    )

    for key, value in {
        "task": "TASK-003",
        "step": "STEP-05G2C1",
        "status": "PREFLIGHT_SNAPSHOT_ONLY",
        "writer_reservation_acquired": False,
        "fresh_s3_relist_passed": False,
        "write_authorized": False,
        "spark_submitted": False,
        "s3_write": False,
        "postgresql_write": False,
        "candidate_published": False,
    }.items():
        require(intent.get(key), value, "write intent " + key)

    for key, value in {
        "task": "TASK-003",
        "step": "STEP-05G1",
        "status": "PLANNED",
        "persisted": False,
        "published": False,
        "s3_write": False,
        "postgresql_write": False,
        "visit_ids_allocated": 0,
    }.items():
        require(plan.get(key), value, "plan " + key)

    bucket, prefix = get_prefix(plan)

    for intent_key, plan_key in (
        ("run_id", "run_id"),
        ("base_uri", "base_uri"),
        ("data_uri", "data_uri"),
        ("expected_rows", "expected_rows"),
        ("expected_persons", "expected_persons"),
        ("expected_class_counts", "class_counts"),
    ):
        require(
            intent.get(intent_key),
            plan.get(plan_key),
            intent_key + " against plan",
        )

    source_sha = intent.get("source_sha256")

    if not isinstance(source_sha, dict) or not source_sha:
        raise ValueError("RESERVATION_CONFLICT: missing source hashes")

    for key, value in source_sha.items():
        if (
            not isinstance(key, str)
            or not isinstance(value, str)
            or len(value) != 64
            or any(c not in "0123456789abcdef" for c in value)
        ):
            raise ValueError("RESERVATION_CONFLICT: invalid source SHA")

    if (
        type(intent["expected_rows"]) is not int
        or intent["expected_rows"] <= 0
    ):
        raise ValueError("RESERVATION_CONFLICT: invalid row count")

    # Stable lock name scoped to this exact S3 prefix.
    scope = (bucket + "/" + prefix).encode("utf-8")
    name = "visit-proc-lock-" + sha(scope)[:32]

    record = {
        "reservation_schema":
            "task003.visit_processed.writer_reservation.v1",
        "run_id": intent["run_id"],
        "bucket": bucket,
        "prefix": prefix,
        "write_intent_sha256": sha(intent_bytes),
        "plan_sha256": sha(plan_bytes),
        "writer_policy_sha256": sha(policy_bytes),
        "mode": "EXCLUSIVE_CREATE_ONLY",
        "on_existing_reservation":
            "STOP_MANUAL_RECONCILIATION",
        "release_policy": "NO_AUTOMATIC_DELETE",
        "s3_prefix_must_be_relisted_after_create": True,
        "write_authorized": False,
    }

    return {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {
            "name": name,
            "namespace": "dw-spark",
            "labels": {
                "healthcare-task": "task003",
                "healthcare-purpose":
                    "visit-processed-writer-lock",
            },
        },
        "immutable": True,
        "data": {
            "reservation.json": json.dumps(
                record,
                sort_keys=True,
                separators=(",", ":"),
            ),
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()

    root = args.root.resolve()
    base = root / "runtime/reports/task003/step05"

    intent_path = (
        base / "processed-intents"
        / args.run_id / "write-intent.json"
    )

    plan_path = (
        base / "processed-plans"
        / args.run_id / "plan.json"
    )

    policy_path = (
        root
        / "spark/contracts/processed/visit-writer-safety-v1.json"
    )

    for path in (intent_path, plan_path, policy_path):
        if path.is_symlink() or not path.is_file():
            raise ValueError("Missing or unsafe input: " + str(path))

    resource = build_resource(
        intent_path.read_bytes(),
        plan_path.read_bytes(),
        policy_path.read_bytes(),
    )

    target = (
        base / "writer-reservations" / args.run_id
        / "reservation-create.json"
    )

    status = save_once(target, resource)

    print("RESERVATION_SPEC_STATUS=" + status)
    print("RESERVATION_NAME=" + resource["metadata"]["name"])
    print("RESERVATION_SPEC_SHA256=" + sha(target.read_bytes()))
    print("RESERVATION_SPEC_FILE=" + str(target))
    print("RESERVATION_ACQUIRED=NO")
    print("FRESH_S3_RELIST_PASSED=NO")
    print("WRITE_AUTHORIZED=NO")
    print("K8S_WRITE=NO")
    print("S3_WRITE=NO")
    print("DATABASE_WRITE=NO")


if __name__ == "__main__":
    main()
PY_APP

# ========================================================
# 2. Unit and negative tests
# ========================================================

cat > "$STAGE/tests/task003/test_visit_writer_reservation.py" <<'PY_TEST'
import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps/task003"))

from build_visit_writer_reservation import build_resource
from prepare_visit_processed_write_intent import POLICY


def pack(value):
    return (json.dumps(value, sort_keys=True) + "\n").encode()


class ReservationTests(unittest.TestCase):

    def setUp(self):
        base = (
            "s3://health-processed/contract_version=v1/"
            "entity=visit_occurrence/source=synthea/"
            "source_version=v3.3.0/ingest_date=2026-10-08/"
            "batch_id=batch-test/raw_publish_run_id=raw-test/"
            "run_id=run-test"
        )

        self.plan = {
            "task": "TASK-003",
            "step": "STEP-05G1",
            "status": "PLANNED",
            "run_id": "run-test",
            "base_uri": base,
            "data_uri": base + "/data/",
            "dq_uri": base + "/dq/result.json",
            "manifest_uri": base + "/manifest.json",
            "publication_policy": {
                "output_bucket": "health-processed",
                "publication_gate": "APPROVED_manifest_last",
                "same_run_conflict": "STOP_WITHOUT_OVERWRITE",
                "same_run_replay":
                    "REUSE_ONLY_IF_VERIFIED_IDENTICAL",
                "objects": [
                    "data/",
                    "dq/result.json",
                    "manifest.json",
                ],
            },
            "persisted": False,
            "published": False,
            "s3_write": False,
            "postgresql_write": False,
            "visit_ids_allocated": 0,
            "expected_rows": 3,
            "expected_persons": 2,
            "class_counts": {
                "emergency": 1,
                "ambulatory": 2,
            },
        }

        self.policy_bytes = pack(POLICY)
        self.plan_bytes = pack(self.plan)

        self.intent = {
            "task": "TASK-003",
            "step": "STEP-05G2C1",
            "status": "PREFLIGHT_SNAPSHOT_ONLY",
            "run_id": "run-test",
            "base_uri": base,
            "data_uri": base + "/data/",
            "expected_rows": 3,
            "expected_persons": 2,
            "expected_class_counts": self.plan["class_counts"],
            "plan_sha256":
                hashlib.sha256(self.plan_bytes).hexdigest(),
            "writer_safety_policy": POLICY,
            "writer_safety_policy_sha256":
                hashlib.sha256(self.policy_bytes).hexdigest(),
            "writer_reservation_acquired": False,
            "fresh_s3_relist_passed": False,
            "write_authorized": False,
            "spark_submitted": False,
            "s3_write": False,
            "postgresql_write": False,
            "candidate_published": False,
            "source_sha256": {
                "mapper": "a" * 64
            },
        }

    def build(self):
        return build_resource(
            pack(self.intent),
            self.plan_bytes,
            self.policy_bytes,
        )

    def test_deterministic_request_not_acquired(self):
        first = self.build()
        second = self.build()

        self.assertEqual(first, second)
        self.assertEqual(first["kind"], "ConfigMap")
        self.assertTrue(first["immutable"])
        self.assertEqual(
            first["metadata"]["namespace"],
            "dw-spark",
        )
        self.assertLessEqual(
            len(first["metadata"]["name"]), 63
        )

        record = json.loads(
            first["data"]["reservation.json"]
        )
        self.assertFalse(record["write_authorized"])
        self.assertEqual(
            record["mode"], "EXCLUSIVE_CREATE_ONLY"
        )
        self.assertEqual(
            record["release_policy"], "NO_AUTOMATIC_DELETE"
        )

    def test_plan_drift_rejected(self):
        self.plan["expected_rows"] += 1
        self.plan_bytes = pack(self.plan)

        with self.assertRaises(ValueError):
            self.build()

    def test_intent_cannot_claim_lock(self):
        self.intent["writer_reservation_acquired"] = True

        with self.assertRaises(ValueError):
            self.build()

    def test_intent_cannot_claim_write(self):
        self.intent["write_authorized"] = True

        with self.assertRaises(ValueError):
            self.build()

    def test_source_hash_required(self):
        self.intent["source_sha256"] = {}

        with self.assertRaises(ValueError):
            self.build()

    def test_policy_weakening_rejected(self):
        weaker = copy.deepcopy(POLICY)
        weaker["exclusive_writer_reservation_required"] = False
        self.intent["writer_safety_policy"] = weaker

        with self.assertRaises(ValueError):
            self.build()

    def test_run_identity_drift_rejected(self):
        self.intent["run_id"] = "other-run"

        with self.assertRaises(ValueError):
            self.build()

    def test_wrong_s3_prefix_rejected(self):
        self.intent["base_uri"] = (
            self.intent["base_uri"].replace(
                "health-processed", "health-raw"
            )
        )

        with self.assertRaises(ValueError):
            self.build()

    def test_distinct_run_has_distinct_lock(self):
        first = self.build()["metadata"]["name"]

        self.plan["run_id"] = "run-test-2"
        self.plan["base_uri"] = (
            self.plan["base_uri"].replace(
                "run-test", "run-test-2"
            )
        )

        self.plan["data_uri"] = (
            self.plan["base_uri"] + "/data/"
        )
        self.plan["dq_uri"] = (
            self.plan["base_uri"] + "/dq/result.json"
        )
        self.plan["manifest_uri"] = (
            self.plan["base_uri"] + "/manifest.json"
        )

        self.plan_bytes = pack(self.plan)

        self.intent["run_id"] = "run-test-2"
        self.intent["base_uri"] = self.plan["base_uri"]
        self.intent["data_uri"] = self.plan["data_uri"]
        self.intent["plan_sha256"] = (
            hashlib.sha256(self.plan_bytes).hexdigest()
        )

        self.assertNotEqual(
            first,
            self.build()["metadata"]["name"],
        )


if __name__ == "__main__":
    unittest.main()
PY_TEST

# ========================================================
# 3. Permanent preparation runner
# ========================================================

cat > "$STAGE/scripts/task003/05g2c2a-prepare-writer-reservation.sh" <<'SH_RUN'
#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo '#### TASK003 STEP05G2C2A RESERVATION PREPARATION OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT
  echo "PREPARE_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G2C2A RESERVATION PREPARATION OUTPUT END ####'
  exit "$rc"
}
trap finish EXIT

[[ $# -eq 1 ]] || {
  echo 'Usage: $0 PROCESSED_RUN_ID'
  exit 2
}

[[ "$1" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$ && \
   "$1" != '.' && "$1" != '..' ]] || {
  echo 'ERROR: unsafe run ID'
  exit 2
}

python3 "$ROOT/apps/task003/build_visit_writer_reservation.py" \
  --root "$ROOT" \
  --run-id "$1"

echo 'STEP05G2C2A_RESERVATION_PREPARED=PASS'
echo 'K8S_RESOURCE_CREATED=NO'
echo 'SPARK_APPLICATION_SUBMITTED=NO'
echo 'S3_WRITE=NO'
echo 'DATABASE_WRITE=NO'
SH_RUN

# ========================================================
# 4. Validate generated source
# ========================================================

echo '=== 1. Static validation ==='

python3 - "$STAGE" <<'PY_AST'
import ast
import sys
from pathlib import Path

root = Path(sys.argv[1])

for rel in (
    "apps/task003/build_visit_writer_reservation.py",
    "tests/task003/test_visit_writer_reservation.py",
):
    ast.parse(
        (root / rel).read_text(),
        filename=rel,
    )

print("PYTHON_AST=PASS")
PY_AST

bash -n "$STAGE/scripts/task003/05g2c2a-prepare-writer-reservation.sh"

# Copy existing dependencies for isolated tests.
cp "$ROOT/apps/task003/inspect_visit_processed_prefix.py" \
   "$STAGE/apps/task003/"

cp "$ROOT/apps/task003/prepare_visit_processed_write_intent.py" \
   "$STAGE/apps/task003/"

cp "$ROOT/apps/task003/plan_visit_processed.py" \
   "$STAGE/apps/task003/"

cp "$ROOT/apps/task003/verify_visit_processed_plan.py" \
   "$STAGE/apps/task003/"

PYTHONPATH="$STAGE/apps/task003" \
python3 -m unittest discover \
  -s "$STAGE/tests/task003" \
  -p 'test_visit_writer_reservation.py' -v

echo 'RESERVATION_UNIT_TESTS=PASS'

# ========================================================
# 5. Install canonical files
# ========================================================

echo '=== 2. Canonical source conflict check ==='

FILES=(
  apps/task003/build_visit_writer_reservation.py
  tests/task003/test_visit_writer_reservation.py
  scripts/task003/05g2c2a-prepare-writer-reservation.sh
)

GEN=scripts/task003/05g2c2a-prepare-writer-reservation-source.sh

for rel in "${FILES[@]}"; do
  if [[ -L "$ROOT/$rel" ]] || {
    [[ -e "$ROOT/$rel" ]] &&
    ! cmp -s "$STAGE/$rel" "$ROOT/$rel"
  }; then
    echo "ERROR: canonical source conflict: $rel"
    exit 1
  fi
done

if [[ -L "$ROOT/$GEN" ]] || {
  [[ -e "$ROOT/$GEN" ]] &&
  ! cmp -s "${BASH_SOURCE[0]}" "$ROOT/$GEN"
}; then
  echo "ERROR: canonical generator conflict: $GEN"
  exit 1
fi

echo '=== 3. Install canonical sources ==='

for rel in "${FILES[@]}"; do
  mkdir -p "$(dirname "$ROOT/$rel")"

  mode=644
  [[ "$rel" != *.sh ]] || mode=755

  install -m "$mode" "$STAGE/$rel" "$ROOT/$rel"
  echo "CANONICAL_SOURCE_READY=$rel"
done

if [[ "${BASH_SOURCE[0]}" -ef "$ROOT/$GEN" ]]; then
  echo "CANONICAL_GENERATOR_REUSED=$GEN"
else
  install -m 755 "${BASH_SOURCE[0]}" "$ROOT/$GEN"
  echo "CANONICAL_GENERATOR_READY=$GEN"
fi

echo 'STEP05G2C2A_SOURCE_AND_TESTS=PASS'
echo 'K8S_WRITE=NO'
echo 'S3_WRITE=NO'
echo 'DATABASE_WRITE=NO'
echo 'GIT_COMMIT=NO'
