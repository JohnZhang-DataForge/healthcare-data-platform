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
