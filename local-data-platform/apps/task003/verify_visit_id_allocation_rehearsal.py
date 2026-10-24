#!/usr/bin/env python3

import argparse
import hashlib
import json
import re
from pathlib import Path


EXPECTED_HEAD = (
    "0fab643417dd3922f8adc8041014d352430c233f"
)

EXPECTED_CONTRACT_SHA = (
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

EXPECTED_SQL_SHA = (
    "21e00285ce0ebaf43c0c38b57be74bf3"
    "2204236ae7af8d9c1170143b757d31e1"
)

EXPECTED_OUTPUT_SHA = (
    "7d26cf9f34bb39b445e2ff53171f4f34"
    "5eb6c2818a2a39b0692756c5fb48e92b"
)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def validate(
    state_path,
    sql_path,
    output_path,
    postcheck_path,
):
    state = json.loads(
        Path(state_path).read_bytes()
    )

    require(
        state["status"]
        == "VISIT_ID_ALLOCATION_REHEARSAL_PASS",
        "B4A status",
    )

    require(
        state["git_checkpoint"]
        == EXPECTED_HEAD,
        "B4A checkpoint",
    )

    require(
        state["mutation_contract_sha256"]
        == EXPECTED_CONTRACT_SHA,
        "B4A contract lineage",
    )

    require(
        state["snapshot_metadata_sha256"]
        == EXPECTED_META_SHA,
        "B4A metadata lineage",
    )

    require(
        state["candidate_business_key_sha256"]
        == EXPECTED_KEY_SHA,
        "B4A key lineage",
    )

    require(
        sha(sql_path)
        == EXPECTED_SQL_SHA,
        "rehearsal SQL SHA",
    )

    require(
        sha(output_path)
        == EXPECTED_OUTPUT_SHA,
        "rehearsal output SHA",
    )

    require(
        state["candidate_temp_rows"]
        == 5799,
        "TEMP rows",
    )

    require(
        state["candidate_temp_sha256"]
        == EXPECTED_KEY_SHA,
        "TEMP fingerprint",
    )

    require(
        state["existing_candidate_mappings"]
        == 0,
        "existing mappings",
    )

    require(
        state["advisory_lock_acquired"]
        is True,
        "advisory lock",
    )

    require(
        state["table_locks_acquired"]
        is True,
        "table locks",
    )

    require(
        state["transaction_rolled_back"]
        is True,
        "rollback",
    )

    require(
        state["advisory_lock_released"]
        is True,
        "lock release",
    )

    require(
        state["irreversible_boundary_crossed"]
        is False,
        "irreversible boundary",
    )

    for field in (
        "nextval_called",
        "setval_called",
        "visit_id_allocation_started",
        "visit_id_map_mutated",
        "sequence_advanced",
        "cdm_visit_occurrence_write",
    ):
        require(
            state[field] is False,
            field,
        )

    sql = Path(
        sql_path
    ).read_text()

    require(
        not re.search(
            r"\bnextval\s*\(",
            sql,
            re.IGNORECASE,
        ),
        "sequence allocation in rehearsal SQL",
    )

    require(
        not re.search(
            r"\bsetval\s*\(",
            sql,
            re.IGNORECASE,
        ),
        "setval in rehearsal SQL",
    )

    output = Path(
        output_path
    ).read_text()

    for token in (
        "ADVISORY_LOCK_ACQUIRED",
        "TABLE_LOCKS_ACQUIRED",
        "COPY 5799",
        "TEMP_TABLE_REVALIDATION_PASS",
        "IRREVERSIBLE_BOUNDARY_NOT_CROSSED",
        "REHEARSAL_ROLLBACK_COMPLETE",
    ):
        require(
            token in output,
            token,
        )

    post = [
        x.strip()
        for x in Path(
            postcheck_path
        ).read_text().splitlines()
        if x.strip()
        and x.strip() not in {
            "BEGIN",
            "SET",
            "ROLLBACK",
        }
    ]

    require(
        post
        == [
            "0|0|113",
            "1|f",
            "0",
            "on",
        ],
        "post-rehearsal DB state",
    )

    return {
        "task":
            "TASK-003",

        "step":
            "STEP-06B4A",

        "status":
            "VISIT_ID_ALLOCATION_REHEARSAL_VERIFIED",

        "candidate_rows":
            5799,

        "candidate_business_key_sha256":
            EXPECTED_KEY_SHA,

        "advisory_lock_key":
            5947676943154735385,

        "copy_temp_rows":
            5799,

        "transaction_rolled_back":
            True,

        "irreversible_boundary_crossed":
            False,

        "nextval_called":
            False,

        "visit_id_map_mutated":
            False,

        "sequence_advanced":
            False,

        "ready_for_first_mutation":
            True,
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--state",
        required=True,
    )

    parser.add_argument(
        "--sql",
        required=True,
    )

    parser.add_argument(
        "--psql-output",
        required=True,
    )

    parser.add_argument(
        "--postcheck",
        required=True,
    )

    parser.add_argument(
        "--output",
        required=True,
    )

    args = parser.parse_args()

    result = validate(
        args.state,
        args.sql,
        args.psql_output,
        args.postcheck,
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
        "STEP06B4A_CANONICAL_EVIDENCE_VERIFY=PASS"
    )

    print(
        "IRREVERSIBLE_BOUNDARY_CROSSED=NO"
    )

    print(
        "READY_FOR_FIRST_VISIT_ID_MUTATION=YES"
    )


if __name__ == "__main__":
    main()
