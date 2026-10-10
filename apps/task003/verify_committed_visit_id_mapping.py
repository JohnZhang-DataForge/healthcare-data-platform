#!/usr/bin/env python3

import argparse
import hashlib
import json
from pathlib import Path


EXPECTED_MAPPING_SHA = (
    "7e74c9c0a179e6222a7c4ded2993b8cf"
    "61a20d9b06b1d6349d7f21f6a0c03c9f"
)

EXPECTED_KEY_SHA = (
    "aa5be446a3fe0ce4688594db45db19a33"
    "ad9bb182cca61e6a19cdb69ff74f72e"
)

EXPECTED_SQL_SHA = (
    "4e0f7ba8c81639d601df832781515d1b"
    "2e6084706f9e96f1829ec12a2937bf7e"
)

EXPECTED_PSQL_SHA = (
    "db7add87ae7185dc2127b21230ce7756"
    "e2ec3c11bb80676c023fed0e066c59a3"
)

EXPECTED_RECOVERY_SHA = (
    "c34f6682f5a4482f1ef33f8a085463c4"
    "714fe858cd72c14bc03d75be3608dcc2"
)

EXPECTED_AMENDMENT_SHA = (
    "f3f81af4effadc65e73255837f5cf79f"
    "e74050f2bf3f4685385f360b20a76a03"
)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def load(path):
    return json.loads(
        Path(path).read_bytes()
    )


def validate(
    contract_path,
    state_path,
    post_verify_path,
    tx_path,
    sql_path,
    psql_path,
    map_path,
):
    contract = load(
        contract_path
    )

    state = load(
        state_path
    )

    post = load(
        post_verify_path
    )

    tx = load(
        tx_path
    )

    require(
        contract["status"]
        == "VISIT_ID_ALLOCATION_COMMITTED_AND_FROZEN",
        "contract status",
    )

    require(
        contract[
            "candidate_business_key_sha256"
        ]
        == EXPECTED_KEY_SHA,
        "candidate key SHA",
    )

    committed = contract[
        "committed_mapping"
    ]

    require(
        committed["rows"]
        == 5799,
        "mapping rows",
    )

    require(
        committed[
            "unique_visit_occurrence_ids"
        ]
        == 5799,
        "unique IDs",
    )

    require(
        committed[
            "min_visit_occurrence_id"
        ]
        == 2,
        "min ID",
    )

    require(
        committed[
            "max_visit_occurrence_id"
        ]
        == 5800,
        "max ID",
    )

    require(
        committed[
            "mapping_sha256"
        ]
        == EXPECTED_MAPPING_SHA,
        "mapping SHA",
    )

    require(
        committed[
            "visit_ids_contiguous_2_through_5800"
        ]
        is True,
        "contiguous IDs",
    )

    require(
        contract[
            "cdm_visit_rows_after_allocation"
        ]
        == 0,
        "CDM rows",
    )

    require(
        contract[
            "cdm_visit_occurrence_write"
        ]
        is False,
        "CDM write",
    )

    recovery = contract[
        "recovery_lineage"
    ]

    require(
        recovery[
            "recovery_state_sha256"
        ]
        == EXPECTED_RECOVERY_SHA,
        "recovery SHA",
    )

    require(
        recovery[
            "recovery_amendment_sha256"
        ]
        == EXPECTED_AMENDMENT_SHA,
        "amendment SHA",
    )

    require(
        recovery[
            "sequence_value_1_consumed_gap"
        ]
        is True,
        "gap lineage",
    )

    correction = contract[
        "corrected_allocation"
    ]

    require(
        correction[
            "allocation_sql_sha256"
        ]
        == EXPECTED_SQL_SHA,
        "SQL SHA",
    )

    require(
        correction[
            "psql_output_sha256"
        ]
        == EXPECTED_PSQL_SHA,
        "psql SHA",
    )

    require(
        correction[
            "explicit_identity_insert"
        ]
        == "OVERRIDING SYSTEM VALUE",
        "identity override",
    )

    require(
        correction[
            "identity_generation"
        ]
        == "ALWAYS",
        "identity generation",
    )

    require(
        correction[
            "transaction_committed"
        ]
        is True,
        "transaction commit",
    )

    require(
        correction[
            "independent_post_commit_verification"
        ]
        is True,
        "independent verify",
    )

    sequence = contract[
        "sequence"
    ]

    require(
        sequence["last_value"]
        == 5800,
        "sequence last",
    )

    require(
        sequence["is_called"]
        is True,
        "sequence called",
    )

    require(
        sequence["gap_policy"]
        == "ACCEPT_GAPS_NEVER_REWIND",
        "gap policy",
    )

    require(
        sequence[
            "setval_backward_used"
        ]
        is False,
        "setval policy",
    )

    require(
        sha(sql_path)
        == EXPECTED_SQL_SHA,
        "runtime SQL SHA",
    )

    require(
        sha(psql_path)
        == EXPECTED_PSQL_SHA,
        "runtime psql SHA",
    )

    require(
        state["mapping_sha256"]
        == EXPECTED_MAPPING_SHA,
        "state mapping SHA",
    )

    require(
        state["committed_map_rows"]
        == 5799,
        "state rows",
    )

    require(
        state[
            "min_visit_occurrence_id"
        ]
        == 2,
        "state min",
    )

    require(
        state[
            "max_visit_occurrence_id"
        ]
        == 5800,
        "state max",
    )

    require(
        state["transaction_committed"]
        is True,
        "state commit",
    )

    require(
        state[
            "independent_post_commit_verification"
        ]
        is True,
        "state independent verify",
    )

    require(
        state[
            "cdm_visit_occurrence_write"
        ]
        is False,
        "state CDM write",
    )

    require(
        post["mapping_sha256"]
        == EXPECTED_MAPPING_SHA,
        "post mapping SHA",
    )

    require(
        post["committed_map_rows"]
        == 5799,
        "post rows",
    )

    require(
        post["candidate_coverage"]
        == 5799,
        "candidate coverage",
    )

    require(
        post[
            "unique_visit_occurrence_ids"
        ]
        == 5799,
        "post unique IDs",
    )

    require(
        post["cdm_visit_rows"]
        == 0,
        "post CDM rows",
    )

    require(
        tx["mapping_sha256"]
        == EXPECTED_MAPPING_SHA,
        "tx mapping SHA",
    )

    require(
        tx["map_rows"]
        == 5799,
        "tx rows",
    )

    require(
        tx[
            "min_visit_occurrence_id"
        ]
        == 2,
        "tx min",
    )

    require(
        tx[
            "max_visit_occurrence_id"
        ]
        == 5800,
        "tx max",
    )

    map_lines = [
        line
        for line in Path(
            map_path
        ).read_text().splitlines()
        if line
        and line not in {
            "BEGIN",
            "SET",
            "ROLLBACK",
        }
    ]

    require(
        len(map_lines)
        == 5799,
        "map readback rows",
    )

    parsed = []

    for line in map_lines:
        fields = line.split("\t")

        require(
            len(fields)
            == 3,
            "map TSV schema",
        )

        parsed.append(
            (
                fields[0],
                fields[1],
                int(fields[2]),
            )
        )

    ids = [
        row[2]
        for row in parsed
    ]

    require(
        ids
        == list(
            range(
                2,
                5801,
            )
        ),
        "authoritative ID sequence",
    )

    payload = "".join(
        source_system
        + "\t"
        + encounter_id
        + "\t"
        + str(visit_id)
        + "\n"
        for (
            source_system,
            encounter_id,
            visit_id
        )
        in parsed
    ).encode(
        "utf-8"
    )

    require(
        hashlib.sha256(
            payload
        ).hexdigest()
        == EXPECTED_MAPPING_SHA,
        "readback mapping SHA",
    )

    return {
        "task":
            "TASK-003",

        "step":
            "STEP-06B4C",

        "status":
            "COMMITTED_VISIT_ID_MAPPING_CANONICAL_GATE_PASS",

        "committed_map_rows":
            5799,

        "candidate_coverage":
            5799,

        "unique_visit_occurrence_ids":
            5799,

        "min_visit_occurrence_id":
            2,

        "max_visit_occurrence_id":
            5800,

        "mapping_sha256":
            EXPECTED_MAPPING_SHA,

        "sequence_last_value":
            5800,

        "sequence_is_called":
            True,

        "sequence_value_1_consumed_gap":
            True,

        "cdm_visit_rows":
            0,

        "cdm_visit_occurrence_write":
            False,

        "ready_for_git_checkpoint":
            True,
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--contract",
        required=True,
    )

    parser.add_argument(
        "--state",
        required=True,
    )

    parser.add_argument(
        "--post-verify",
        required=True,
    )

    parser.add_argument(
        "--transaction-summary",
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
        "--map-readback",
        required=True,
    )

    parser.add_argument(
        "--output",
        required=True,
    )

    args = parser.parse_args()

    result = validate(
        args.contract,
        args.state,
        args.post_verify,
        args.transaction_summary,
        args.sql,
        args.psql_output,
        args.map_readback,
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
        "STEP06B4C_COMMITTED_MAPPING_VERIFY=PASS"
    )

    print(
        "COMMITTED_VISIT_MAP_ROWS=5799"
    )

    print(
        "COMMITTED_VISIT_ID_RANGE=2..5800"
    )

    print(
        "AUTHORITATIVE_MAPPING_SHA256="
        + EXPECTED_MAPPING_SHA
    )

    print(
        "CDM_VISIT_ROWS=0"
    )

    print(
        "READY_FOR_GIT_CHECKPOINT=YES"
    )


if __name__ == "__main__":
    main()
