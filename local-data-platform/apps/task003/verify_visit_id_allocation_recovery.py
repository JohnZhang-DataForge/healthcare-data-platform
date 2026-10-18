#!/usr/bin/env python3

import argparse
import hashlib
import json
from pathlib import Path


EXPECTED_HEAD = (
    "a4d4381dfa6541b10f8e22dd01cb3b8f50ab0a62"
)

EXPECTED_KEY_SHA = (
    "aa5be446a3fe0ce4688594db45db19a33"
    "ad9bb182cca61e6a19cdb69ff74f72e"
)

EXPECTED_FAILED_SQL_SHA = (
    "46ba2f9f1ffad0fbbe1415f27122c04c"
    "23b2422c34e93ab836dcdf87e00570f6"
)

EXPECTED_FAILED_INTENT_SHA = (
    "e089d6a7d4adb00f2af4095715f92614"
    "1611dd2315d9f4b8b3a99a9b5136b664"
)

EXPECTED_FAILED_OUTPUT_SHA = (
    "bea7b2bbaa61de00accbc6f181782f257"
    "c6fe846d618c747b6790514b600c997"
)

EXPECTED_RECOVERY_SHA = (
    "c34f6682f5a4482f1ef33f8a085463c4"
    "714fe858cd72c14bc03d75be3608dcc2"
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
    amendment_path,
    recovery_path,
    failed_sql_path,
    failed_intent_path,
    failed_output_path,
    identity_state_path,
    db_state_path,
    map_readback_path,
):
    amendment = load(
        amendment_path
    )

    recovery = load(
        recovery_path
    )

    require(
        amendment["task"]
        == "TASK-003",
        "amendment task",
    )

    require(
        amendment["step"]
        == "STEP-06B4B-R1",
        "amendment step",
    )

    require(
        amendment["status"]
        == "VISIT_ID_ALLOCATION_RECOVERY_AMENDMENT_READY",
        "amendment status",
    )

    require(
        amendment["git_checkpoint"]
        == EXPECTED_HEAD,
        "amendment checkpoint",
    )

    require(
        amendment["recovery_state_sha256"]
        == EXPECTED_RECOVERY_SHA,
        "amendment recovery SHA",
    )

    require(
        sha(recovery_path)
        == EXPECTED_RECOVERY_SHA,
        "runtime recovery SHA",
    )

    require(
        sha(failed_sql_path)
        == EXPECTED_FAILED_SQL_SHA,
        "failed SQL SHA",
    )

    require(
        sha(failed_intent_path)
        == EXPECTED_FAILED_INTENT_SHA,
        "failed intent SHA",
    )

    require(
        sha(failed_output_path)
        == EXPECTED_FAILED_OUTPUT_SHA,
        "failed output SHA",
    )

    identity = amendment["identity"]

    require(
        identity["is_identity"]
        is True,
        "identity flag",
    )

    require(
        identity["identity_generation"]
        == "ALWAYS",
        "identity generation",
    )

    require(
        identity["ordinary_column_default"]
        is None,
        "ordinary default",
    )

    require(
        identity["dependency_type"]
        == "i",
        "identity dependency",
    )

    require(
        identity["sequence"]
        == "etl.visit_occurrence_id_map_visit_occurrence_id_seq",
        "identity sequence",
    )

    baseline = amendment[
        "recovery_baseline"
    ]

    require(
        baseline[
            "candidate_business_key_sha256"
        ]
        == EXPECTED_KEY_SHA,
        "candidate fingerprint",
    )

    require(
        baseline[
            "committed_visit_map_rows"
        ]
        == 0,
        "map baseline",
    )

    require(
        baseline[
            "cdm_visit_rows"
        ]
        == 0,
        "CDM baseline",
    )

    require(
        baseline[
            "person_map_rows"
        ]
        == 113,
        "Person baseline",
    )

    require(
        baseline[
            "sequence_last_value"
        ]
        == 1,
        "sequence last",
    )

    require(
        baseline[
            "sequence_is_called"
        ]
        is True,
        "sequence is_called",
    )

    require(
        baseline[
            "sequence_value_1_consumed"
        ]
        is True,
        "consumed ID 1",
    )

    require(
        baseline[
            "predicted_next_sequence_value"
        ]
        == 2,
        "predicted next",
    )

    require(
        baseline[
            "predicted_next_value_authoritative"
        ]
        is False,
        "prediction authority",
    )

    correction = amendment[
        "corrected_mutation_requirements"
    ]

    require(
        correction[
            "explicit_identity_insert"
        ][
            "required_clause"
        ]
        == "OVERRIDING SYSTEM VALUE",
        "override clause",
    )

    require(
        correction[
            "old_b4b_rerun_allowed"
        ]
        is False,
        "old retry",
    )

    require(
        correction[
            "setval_backward_allowed"
        ]
        is False,
        "setval policy",
    )

    require(
        correction[
            "sequence_gap_policy"
        ]
        == "ACCEPT_GAPS_NEVER_REWIND",
        "gap policy",
    )

    require(
        correction[
            "fresh_locked_revalidation_required"
        ]
        is True,
        "fresh lock gate",
    )

    require(
        recovery["status"]
        == "FAILED_ALLOCATION_RECONCILED",
        "runtime recovery status",
    )

    require(
        recovery["sequence_last_value"]
        == 1,
        "runtime sequence last",
    )

    require(
        recovery["sequence_is_called"]
        is True,
        "runtime sequence called",
    )

    require(
        recovery["sequence_value_1_consumed"]
        is True,
        "runtime consumed value",
    )

    identity_text = Path(
        identity_state_path
    ).read_text()

    require(
        "YES|ALWAYS|1|1|NO|NONE"
        in identity_text,
        "identity metadata",
    )

    require(
        "1|t"
        in identity_text,
        "identity sequence state",
    )

    db_text = Path(
        db_state_path
    ).read_text()

    require(
        "0|0|113"
        in db_text,
        "recovery DB counts",
    )

    require(
        "0|0|0|0"
        in db_text,
        "recovery map state",
    )

    map_lines = [
        line
        for line in Path(
            map_readback_path
        ).read_text().splitlines()
        if line.strip()
        and line.strip() not in {
            "BEGIN",
            "SET",
            "ROLLBACK",
        }
    ]

    require(
        map_lines == [],
        "recovery map readback",
    )

    return {
        "task":
            "TASK-003",

        "step":
            "STEP-06B4B-R1A",

        "status":
            "VISIT_ID_ALLOCATION_RECOVERY_CANONICAL_GATE_PASS",

        "candidate_business_key_sha256":
            EXPECTED_KEY_SHA,

        "committed_visit_map_rows":
            0,

        "sequence_last_value":
            1,

        "sequence_is_called":
            True,

        "sequence_value_1_consumed":
            True,

        "predicted_next_sequence_value":
            2,

        "predicted_next_value_authoritative":
            False,

        "identity_generation":
            "ALWAYS",

        "explicit_id_insert_requirement":
            "OVERRIDING SYSTEM VALUE",

        "old_b4b_rerun_allowed":
            False,

        "setval_backward_allowed":
            False,

        "ready_for_corrected_mutation_design":
            True,
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--amendment",
        required=True,
    )

    parser.add_argument(
        "--recovery",
        required=True,
    )

    parser.add_argument(
        "--failed-sql",
        required=True,
    )

    parser.add_argument(
        "--failed-intent",
        required=True,
    )

    parser.add_argument(
        "--failed-output",
        required=True,
    )

    parser.add_argument(
        "--identity-state",
        required=True,
    )

    parser.add_argument(
        "--db-state",
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
        args.amendment,
        args.recovery,
        args.failed_sql,
        args.failed_intent,
        args.failed_output,
        args.identity_state,
        args.db_state,
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
        "STEP06B4B_R1_CANONICAL_RECOVERY_VERIFY=PASS"
    )

    print(
        "RECOVERY_SEQUENCE_STATE=1|TRUE"
    )

    print(
        "SEQUENCE_VALUE_1_CONSUMED=YES"
    )

    print(
        "EXPLICIT_ID_INSERT_REQUIRES="
        "OVERRIDING_SYSTEM_VALUE"
    )

    print(
        "READY_FOR_CORRECTED_MUTATION_DESIGN=YES"
    )


if __name__ == "__main__":
    main()
