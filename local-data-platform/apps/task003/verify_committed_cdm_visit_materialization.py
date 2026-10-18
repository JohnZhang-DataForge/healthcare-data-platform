#!/usr/bin/env python3

import argparse
import json
from pathlib import Path


EXPECTED_STATE = {
    "TARGET_COLUMN_COUNT": "17",
    "TARGET_CONSTRAINT_COUNT": "10",
    "TARGET_INDEX_COUNT": "3",
    "TARGET_USER_TRIGGER_COUNT": "0",
    "CDM_STATE": "5799|5799|2|5800",
    "MAP_STATE": "5799|5799|2|5800",
    "PERSON_MAP_ROWS": "113",
    "SEQUENCE_STATE": "5800|true",
    "MAPPING_SHA256":
        "7e74c9c0a179e6222a7c4ded2993b8cf61a20d9b"
        "06b1d6349d7f21f6a0c03c9f",
    "PERSON_MAP_SHA256":
        "f52f95120b8a9bd80d33029d04d9abf4cb1c5920"
        "6d00b745b59e39b5a89c9a98",
    "CDM_ROW_SHAPE_SHA256":
        "995724ba282f443892074d9b189be134fde8819b2"
        "afda05f021729323b0ebce1",
    "TARGET_MAP_ID_MISMATCH": "0",
    "REQUIRED_NULL_ROWS": "0",
    "MISSING_PERSON_FK": "0",
    "MISSING_CONCEPT_FK": "0",
    "MISSING_PROVIDER_FK": "0",
    "MISSING_CARE_SITE_FK": "0",
    "MISSING_PRECEDING_VISIT_FK": "0",
    "TRANSACTION_READ_ONLY": "on",
}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def parse_state_text(text):
    values = {}

    for raw in text.splitlines():
        line = raw.strip()

        if not line:
            continue

        if line in {
            "BEGIN",
            "SET",
            "ROLLBACK",
        }:
            continue

        if "=" not in line:
            continue

        key, value = line.split(
            "=",
            1,
        )

        values[key] = value

    return values


def validate_state(values):
    for key, expected in EXPECTED_STATE.items():
        actual = values.get(key)

        require(
            actual == expected,
            (
                f"{key}: expected {expected!r}, "
                f"got {actual!r}"
            ),
        )


def validate_contract(obj):
    require(
        obj["task"] == "TASK-003",
        "task",
    )

    require(
        obj["step"] == "STEP-06C4E",
        "step",
    )

    require(
        obj["status"]
        == "CDM_VISIT_MATERIALIZATION_COMMITTED_FROZEN",
        "status",
    )

    require(
        obj["target"]["table"]
        == "cdm.visit_occurrence",
        "target table",
    )

    require(
        obj["target"]["row_count"] == 5799,
        "target row count",
    )

    require(
        obj["target"]["unique_visit_occurrence_ids"]
        == 5799,
        "target unique IDs",
    )

    require(
        obj["target"]["visit_occurrence_id_min"] == 2,
        "target min ID",
    )

    require(
        obj["target"]["visit_occurrence_id_max"] == 5800,
        "target max ID",
    )

    require(
        obj["target"]["column_count"] == 17,
        "target columns",
    )

    require(
        obj["target"]["row_shape_sha256"]
        == EXPECTED_STATE["CDM_ROW_SHAPE_SHA256"],
        "row shape SHA",
    )

    require(
        obj["lineage"]["authoritative_mapping_sha256"]
        == EXPECTED_STATE["MAPPING_SHA256"],
        "mapping SHA",
    )

    require(
        obj["lineage"]["person_map_sha256"]
        == EXPECTED_STATE["PERSON_MAP_SHA256"],
        "person map SHA",
    )

    require(
        obj["lineage"]["visit_id_map_rows"] == 5799,
        "Visit map rows",
    )

    require(
        obj["lineage"]["person_map_rows"] == 113,
        "Person map rows",
    )

    require(
        obj["sequence"]["last_value"] == 5800,
        "sequence value",
    )

    require(
        obj["sequence"]["is_called"] is True,
        "sequence called",
    )

    require(
        obj["sequence"]["mutated_by_materialization"]
        is False,
        "sequence mutation",
    )

    require(
        obj["execution"]["psql_exit_code"] == 0,
        "psql exit",
    )

    require(
        obj["execution"]["insert_rows"] == 5799,
        "insert rows",
    )

    require(
        obj["execution"]["commit_returned_successfully"]
        is True,
        "commit marker",
    )

    require(
        obj["execution"]["automatic_retry_performed"]
        is False,
        "retry",
    )

    require(
        obj["reconciliation"]["status"]
        == "PASS",
        "reconciliation",
    )

    for name, value in obj["foreign_key_gates"].items():
        require(
            value == "PASS",
            f"FK gate {name}",
        )

    require(
        obj["terminal_policy"]["materialization_rerun"]
        == "FORBIDDEN",
        "terminal rerun policy",
    )

    require(
        obj["terminal_policy"]["visit_id_reallocation"]
        == "FORBIDDEN",
        "Visit reallocation policy",
    )


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
        "--output-json",
        required=True,
    )

    args = parser.parse_args()

    contract = json.loads(
        Path(args.contract).read_bytes()
    )

    validate_contract(contract)

    state_text = Path(
        args.state
    ).read_text(
        encoding="utf-8",
    )

    values = parse_state_text(
        state_text
    )

    validate_state(
        values
    )

    result = {
        "task":
            "TASK-003",

        "step":
            "STEP-06C4E",

        "status":
            "COMMITTED_CDM_VISIT_CANONICAL_VERIFY_PASS",

        "cdm_visit_rows":
            5799,

        "cdm_visit_unique_ids":
            5799,

        "visit_occurrence_id_min":
            2,

        "visit_occurrence_id_max":
            5800,

        "cdm_row_shape_sha256":
            EXPECTED_STATE["CDM_ROW_SHAPE_SHA256"],

        "authoritative_mapping_sha256":
            EXPECTED_STATE["MAPPING_SHA256"],

        "person_map_sha256":
            EXPECTED_STATE["PERSON_MAP_SHA256"],

        "sequence_last_value":
            5800,

        "sequence_is_called":
            True,

        "target_map_id_mismatch":
            0,

        "required_null_rows":
            0,

        "database_access":
            "READ_ONLY",

        "database_mutation":
            False,

        "ready_for_git_checkpoint":
            True,
    }

    Path(
        args.output_json
    ).write_text(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    print(
        "STEP06C4E_COMMITTED_CDM_VISIT_VERIFY=PASS"
    )

    print(
        "CDM_VISIT_ROWS=5799"
    )

    print(
        "CDM_VISIT_UNIQUE_IDS=5799"
    )

    print(
        "CDM_VISIT_ID_RANGE=2..5800"
    )

    print(
        "CDM_ROW_SHAPE_SHA256="
        + EXPECTED_STATE["CDM_ROW_SHAPE_SHA256"]
    )

    print(
        "AUTHORITATIVE_MAPPING_SHA256="
        + EXPECTED_STATE["MAPPING_SHA256"]
    )

    print(
        "PERSON_MAP_SHA256="
        + EXPECTED_STATE["PERSON_MAP_SHA256"]
    )

    print(
        "SEQUENCE_STATE=5800|true"
    )

    print(
        "TARGET_MAP_ID_MISMATCH=0"
    )

    print(
        "ALL_DATABASE_FK_GATES=PASS"
    )

    print(
        "DATABASE_ACCESS=READ_ONLY"
    )

    print(
        "DATABASE_MUTATION=NO"
    )

    print(
        "READY_FOR_GIT_CHECKPOINT=YES"
    )


if __name__ == "__main__":
    main()
