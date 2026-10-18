#!/usr/bin/env python3

import argparse
import hashlib
import json
from pathlib import Path


EXPECTED_PARENT = (
    "6d8ef90ac50b4ce96cbde16b7b3c0a68a7574d4a"
)

EXPECTED_B1_SHA = (
    "58cd44b22eaf15674a7277c51c66418c"
    "305bd3743b403c7612d458453d87f9f0"
)

EXPECTED_META_SHA = (
    "21ac6b5af6f74d3b078b4fbf7fb8ce21"
    "b5d5d32af1aaccc5e495e595fc90dbaa"
)

EXPECTED_KEY_SHA = (
    "aa5be446a3fe0ce4688594db45db19a33"
    "ad9bb182cca61e6a19cdb69ff74f72e"
)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def load_json(path):
    return json.loads(
        Path(path).read_bytes()
    )


def sha256_file(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def validate(
    canonical_contract_path,
    canonical_meta_path,
    runtime_contract_path,
    snapshot_path,
    runtime_meta_path,
    b2_result_path,
    b2_state_path,
):
    canonical_contract = load_json(
        canonical_contract_path
    )

    canonical_meta = load_json(
        canonical_meta_path
    )

    runtime_contract = load_json(
        runtime_contract_path
    )

    runtime_meta = load_json(
        runtime_meta_path
    )

    b2_result = load_json(
        b2_result_path
    )

    b2_state = load_json(
        b2_state_path
    )

    require(
        sha256_file(
            canonical_contract_path
        )
        == EXPECTED_B1_SHA,
        "canonical B1 contract SHA",
    )

    require(
        sha256_file(
            runtime_contract_path
        )
        == EXPECTED_B1_SHA,
        "runtime B1 contract SHA",
    )

    require(
        canonical_contract
        == runtime_contract,
        "canonical/runtime B1 contract mismatch",
    )

    require(
        sha256_file(
            canonical_meta_path
        )
        == EXPECTED_META_SHA,
        "canonical B2 metadata SHA",
    )

    require(
        sha256_file(
            runtime_meta_path
        )
        == EXPECTED_META_SHA,
        "runtime B2 metadata SHA",
    )

    require(
        canonical_meta
        == runtime_meta,
        "canonical/runtime B2 metadata mismatch",
    )

    require(
        sha256_file(
            snapshot_path
        )
        == EXPECTED_KEY_SHA,
        "business-key snapshot SHA",
    )

    contract = canonical_contract

    require(
        contract["task"]
        == "TASK-003",
        "B1 task",
    )

    require(
        contract["step"]
        == "STEP-06B1",
        "B1 step",
    )

    require(
        contract["status"]
        == "VISIT_ID_MUTATION_CONTRACT_READY",
        "B1 status",
    )

    require(
        contract["git_checkpoint"]
        == EXPECTED_PARENT,
        "B1 parent checkpoint",
    )

    scope = contract["scope"]

    require(
        scope["mutation_target"]
        == "etl.visit_occurrence_id_map",
        "mutation target",
    )

    require(
        scope["cdm_visit_occurrence_write"]
        is False,
        "CDM write scope",
    )

    require(
        scope["s3_write"]
        is False,
        "S3 write scope",
    )

    require(
        scope["candidate_rows"]
        == 5799,
        "candidate rows",
    )

    require(
        scope["candidate_unique_business_keys"]
        == 5799,
        "candidate keys",
    )

    require(
        scope["candidate_business_key_sha256"]
        == EXPECTED_KEY_SHA,
        "candidate fingerprint",
    )

    serialization = contract[
        "serialization"
    ]

    lock = serialization[
        "advisory_lock"
    ]

    require(
        lock["function"]
        == "pg_advisory_xact_lock(bigint)",
        "advisory function",
    )

    require(
        lock["key"]
        == 5947676943154735385,
        "advisory lock key",
    )

    require(
        lock["scope"]
        == "transaction",
        "advisory lock scope",
    )

    transport = contract[
        "candidate_key_transport"
    ]

    require(
        transport["producer_step"]
        == "STEP-06B2",
        "snapshot producer",
    )

    require(
        transport["expected_rows"]
        == 5799,
        "transport rows",
    )

    require(
        transport["expected_unique_rows"]
        == 5799,
        "transport unique rows",
    )

    require(
        transport[
            "expected_business_key_sha256"
        ]
        == EXPECTED_KEY_SHA,
        "transport fingerprint",
    )

    require(
        transport[
            "database_ingest"
        ]
        == "COPY temporary table FROM STDIN",
        "database transport",
    )

    policy = contract[
        "allocation_policy"
    ]

    require(
        policy[
            "existing_mapping_reassignment"
        ]
        == "FORBIDDEN",
        "existing mapping policy",
    )

    require(
        policy[
            "sequence_gap_policy"
        ]
        == "ACCEPT_GAPS_NEVER_REWIND",
        "sequence gap policy",
    )

    require(
        policy[
            "setval_backward"
        ]
        == "FORBIDDEN",
        "setval policy",
    )

    require(
        policy[
            "predicted_range_authoritative"
        ]
        is False,
        "predicted range authority",
    )

    failure = contract[
        "failure_policy"
    ]

    require(
        failure[
            "after_first_nextval_before_commit"
        ][
            "blind_retry"
        ]
        is False,
        "blind retry policy",
    )

    safety = contract[
        "safety"
    ]

    require(
        safety[
            "advisory_lock_acquired"
        ]
        is False,
        "B1 advisory state",
    )

    require(
        safety["nextval_called"]
        is False,
        "B1 nextval state",
    )

    require(
        safety["setval_called"]
        is False,
        "B1 setval state",
    )

    require(
        safety[
            "visit_id_allocation_started"
        ]
        is False,
        "B1 allocation state",
    )

    meta = canonical_meta

    require(
        meta["task"]
        == "TASK-003",
        "B2 metadata task",
    )

    require(
        meta["step"]
        == "STEP-06B2",
        "B2 metadata step",
    )

    require(
        meta["status"]
        == "VISIT_BUSINESS_KEY_SNAPSHOT_FROZEN",
        "B2 metadata status",
    )

    require(
        meta["git_checkpoint"]
        == EXPECTED_PARENT,
        "B2 parent checkpoint",
    )

    require(
        meta["rows"]
        == 5799,
        "B2 rows",
    )

    require(
        meta["unique_business_keys"]
        == 5799,
        "B2 unique rows",
    )

    require(
        meta["business_key_sha256"]
        == EXPECTED_KEY_SHA,
        "B2 fingerprint",
    )

    require(
        meta["snapshot_file_sha256"]
        == EXPECTED_KEY_SHA,
        "B2 snapshot file fingerprint",
    )

    require(
        meta[
            "lineage"
        ][
            "step06b1_mutation_contract_sha256"
        ]
        == EXPECTED_B1_SHA,
        "B2 -> B1 lineage",
    )

    payload = Path(
        snapshot_path
    ).read_bytes()

    require(
        payload.endswith(b"\n"),
        "snapshot final LF",
    )

    require(
        b"\r" not in payload,
        "snapshot CR forbidden",
    )

    lines = payload.decode(
        "utf-8"
    ).splitlines()

    require(
        len(lines)
        == 5799,
        "snapshot line count",
    )

    require(
        len(set(lines))
        == 5799,
        "snapshot unique count",
    )

    require(
        lines
        == sorted(lines),
        "snapshot deterministic ordering",
    )

    for line in lines:
        fields = line.split(
            "\t"
        )

        require(
            len(fields)
            == 2,
            "snapshot TSV schema",
        )

        require(
            fields[0]
            == "synthea",
            "snapshot source_system",
        )

        require(
            bool(fields[1]),
            "snapshot encounter ID",
        )

    for doc in (
        b2_result,
        b2_state,
    ):
        require(
            doc["task"]
            == "TASK-003",
            "B2 evidence task",
        )

        require(
            doc["step"]
            == "STEP-06B2",
            "B2 evidence step",
        )

        require(
            doc["status"]
            == "VISIT_BUSINESS_KEY_SNAPSHOT_BUILD_PASS",
            "B2 evidence status",
        )

        require(
            doc["rows"]
            == 5799,
            "B2 evidence rows",
        )

        require(
            doc[
                "unique_business_keys"
            ]
            == 5799,
            "B2 evidence unique",
        )

        require(
            doc[
                "business_key_sha256"
            ]
            == EXPECTED_KEY_SHA,
            "B2 evidence fingerprint",
        )

        require(
            doc[
                "snapshot_metadata_sha256"
            ]
            == EXPECTED_META_SHA,
            "B2 metadata lineage",
        )

    require(
        b2_state[
            "database_access"
        ]
        == "NONE",
        "B2 database access",
    )

    require(
        b2_state[
            "s3_access"
        ]
        == "READ_ONLY",
        "B2 S3 access",
    )

    require(
        b2_state[
            "nextval_called"
        ]
        is False,
        "B2 nextval state",
    )

    require(
        b2_state[
            "setval_called"
        ]
        is False,
        "B2 setval state",
    )

    require(
        b2_state[
            "visit_id_map_mutated"
        ]
        is False,
        "B2 map mutation",
    )

    require(
        b2_state[
            "sequence_advanced"
        ]
        is False,
        "B2 sequence state",
    )

    return {
        "task":
            "TASK-003",

        "step":
            "STEP-06B3",

        "status":
            "VISIT_ID_PRE_MUTATION_GATE_FROZEN",

        "parent_git_checkpoint":
            EXPECTED_PARENT,

        "mutation_contract_sha256":
            EXPECTED_B1_SHA,

        "snapshot_metadata_sha256":
            EXPECTED_META_SHA,

        "candidate_business_key_sha256":
            EXPECTED_KEY_SHA,

        "candidate_rows":
            5799,

        "candidate_unique_business_keys":
            5799,

        "advisory_lock_key":
            5947676943154735385,

        "database_transport":
            "COPY temporary table FROM STDIN",

        "sequence_gap_policy":
            "ACCEPT_GAPS_NEVER_REWIND",

        "predicted_visit_id_range": [
            1,
            5799
        ],

        "predicted_range_authoritative":
            False,

        "advisory_lock_acquired":
            False,

        "nextval_called":
            False,

        "setval_called":
            False,

        "visit_id_allocation_started":
            False,

        "visit_id_map_mutated":
            False,

        "sequence_advanced":
            False,

        "cdm_visit_occurrence_write":
            False,
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--canonical-contract",
        required=True,
    )

    parser.add_argument(
        "--canonical-snapshot-meta",
        required=True,
    )

    parser.add_argument(
        "--runtime-contract",
        required=True,
    )

    parser.add_argument(
        "--snapshot",
        required=True,
    )

    parser.add_argument(
        "--runtime-snapshot-meta",
        required=True,
    )

    parser.add_argument(
        "--b2-result",
        required=True,
    )

    parser.add_argument(
        "--b2-state",
        required=True,
    )

    parser.add_argument(
        "--output",
        required=True,
    )

    args = parser.parse_args()

    result = validate(
        args.canonical_contract,
        args.canonical_snapshot_meta,
        args.runtime_contract,
        args.snapshot,
        args.runtime_snapshot_meta,
        args.b2_result,
        args.b2_state,
    )

    Path(
        args.output
    ).write_text(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    print(
        "STEP06B_PRE_MUTATION_GATE=PASS"
    )

    print(
        "MUTATION_CONTRACT_SHA256="
        + result[
            "mutation_contract_sha256"
        ]
    )

    print(
        "SNAPSHOT_METADATA_SHA256="
        + result[
            "snapshot_metadata_sha256"
        ]
    )

    print(
        "CANDIDATE_BUSINESS_KEY_SHA256="
        + result[
            "candidate_business_key_sha256"
        ]
    )


if __name__ == "__main__":
    main()
