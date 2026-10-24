#!/usr/bin/env python3

import argparse
import hashlib
import json
from pathlib import Path


EXPECTED_HEAD = (
    "8595a2dd46092517ec8fde40408172b1dfb76c09"
)

EXPECTED_ENCOUNTER_SHA = (
    "473ae45225c9063a7560b0092ed7914d71a43623"
    "f593d4959c66294e942a5837"
)

EXPECTED_KEY_SHA = (
    "aa5be446a3fe0ce4688594db45db19a33ad9bb182"
    "cca61e6a19cdb69ff74f72e"
)

EXPECTED_MAPPING_SHA = (
    "7e74c9c0a179e6222a7c4ded2993b8cf61a20d9b"
    "06b1d6349d7f21f6a0c03c9f"
)

EXPECTED_PERSON_SHA = (
    "f52f95120b8a9bd80d33029d04d9abf4cb1c5920"
    "6d00b745b59e39b5a89c9a98"
)

EXPECTED_ROW_SHAPE_SHA = (
    "995724ba282f443892074d9b189be134fde8819b2"
    "afda05f021729323b0ebce1"
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
    c1_summary_path,
    c2_result_path,
    c2_app_path,
    c2_driver_path,
    c2_post_db_path,
    c2_sparkapp_path,
):
    contract = load(
        contract_path
    )

    c1 = load(
        c1_summary_path
    )

    c2 = load(
        c2_result_path
    )

    require(
        contract["task"] == "TASK-003",
        "task",
    )

    require(
        contract["step"] == "STEP-06C3",
        "step",
    )

    require(
        contract["status"]
        == "CDM_VISIT_MATERIALIZATION_PREFLIGHT_FROZEN",
        "status",
    )

    require(
        contract[
            "git_checkpoint_before_preflight"
        ]
        == EXPECTED_HEAD,
        "Git checkpoint",
    )

    target = contract[
        "target_schema"
    ]

    require(
        target["column_count"] == 17,
        "target columns",
    )

    require(
        target[
            "required_insert_column_count"
        ]
        == 6,
        "required columns",
    )

    require(
        target["identity_column_count"]
        == 0,
        "identity columns",
    )

    require(
        target["constraint_count"]
        == 10,
        "constraints",
    )

    source = contract[
        "source_lineage"
    ]

    require(
        source[
            "canonical_encounter_contract_sha256"
        ]
        == EXPECTED_ENCOUNTER_SHA,
        "Encounter contract SHA",
    )

    require(
        source[
            "candidate_business_key_sha256"
        ]
        == EXPECTED_KEY_SHA,
        "business key SHA",
    )

    require(
        source["candidate_rows"]
        == 5799,
        "candidate rows",
    )

    require(
        source["candidate_column_count"]
        == 36,
        "candidate columns",
    )

    mapping = contract[
        "authoritative_visit_id_mapping"
    ]

    require(
        mapping["rows"] == 5799,
        "mapping rows",
    )

    require(
        mapping["min_visit_occurrence_id"]
        == 2,
        "mapping min",
    )

    require(
        mapping["max_visit_occurrence_id"]
        == 5800,
        "mapping max",
    )

    require(
        mapping["mapping_sha256"]
        == EXPECTED_MAPPING_SHA,
        "mapping SHA",
    )

    person = contract[
        "person_mapping"
    ]

    require(
        person["rows"] == 113,
        "person rows",
    )

    require(
        person["person_map_sha256"]
        == EXPECTED_PERSON_SHA,
        "person SHA",
    )

    shape = contract[
        "prepared_cdm_row_shape"
    ]

    require(
        shape["rows"] == 5799,
        "shape rows",
    )

    require(
        shape["column_count"] == 17,
        "shape columns",
    )

    require(
        shape[
            "unique_visit_occurrence_ids"
        ]
        == 5799,
        "shape unique IDs",
    )

    require(
        shape["row_shape_sha256"]
        == EXPECTED_ROW_SHAPE_SHA,
        "row shape SHA",
    )

    for key in (
        "required_null_violations",
        "cast_violations",
        "varchar_length_violations",
        "date_order_violations",
        "datetime_order_violations",
        "date_datetime_consistency_violations",
    ):
        require(
            shape[key] == 0,
            key,
        )

    fk = contract[
        "foreign_key_feasibility"
    ]

    for key in (
        "person",
        "concept",
        "provider",
        "care_site",
        "preceding_visit",
    ):
        require(
            fk[key] == "PASS",
            "FK " + key,
        )

    database = contract[
        "database_baseline"
    ]

    require(
        database["cdm_visit_rows"]
        == 0,
        "CDM rows",
    )

    require(
        database["visit_id_map_rows"]
        == 5799,
        "Visit map rows",
    )

    require(
        database["person_map_rows"]
        == 113,
        "Person map rows",
    )

    require(
        database["sequence_last_value"]
        == 5800,
        "sequence last",
    )

    require(
        database["sequence_is_called"]
        is True,
        "sequence called",
    )

    evidence = contract[
        "runtime_evidence"
    ]

    require(
        sha(c1_summary_path)
        == evidence[
            "c1_summary_sha256"
        ],
        "C1 summary SHA",
    )

    require(
        sha(c2_result_path)
        == evidence[
            "c2_result_sha256"
        ],
        "C2 result SHA",
    )

    require(
        sha(c2_app_path)
        == evidence[
            "c2_verified_spark_application_sha256"
        ],
        "C2 app SHA",
    )

    require(
        sha(c2_driver_path)
        == evidence[
            "c2_driver_log_sha256"
        ],
        "driver SHA",
    )

    require(
        sha(c2_post_db_path)
        == evidence[
            "c2_post_database_state_sha256"
        ],
        "post DB SHA",
    )

    require(
        sha(c2_sparkapp_path)
        == evidence[
            "c2_sparkapplication_manifest_sha256"
        ],
        "SparkApplication SHA",
    )

    require(
        c1["column_count"] == 17,
        "C1 column count",
    )

    require(
        c1["cdm_visit_rows"] == 0,
        "C1 CDM rows",
    )

    require(
        c1[
            "authoritative_mapping_sha256"
        ]
        == EXPECTED_MAPPING_SHA,
        "C1 mapping SHA",
    )

    require(
        c2["candidate_rows"] == 5799,
        "C2 candidate rows",
    )

    require(
        c2[
            "candidate_business_key_sha256"
        ]
        == EXPECTED_KEY_SHA,
        "C2 key SHA",
    )

    require(
        c2[
            "authoritative_mapping_sha256"
        ]
        == EXPECTED_MAPPING_SHA,
        "C2 mapping SHA",
    )

    require(
        c2["person_map_sha256"]
        == EXPECTED_PERSON_SHA,
        "C2 person SHA",
    )

    require(
        c2["cdm_row_shape_sha256"]
        == EXPECTED_ROW_SHAPE_SHA,
        "C2 shape SHA",
    )

    require(
        c2[
            "final_cdm_row_shape_rows"
        ]
        == 5799,
        "C2 shape rows",
    )

    require(
        c2["cdm_visit_rows_before"]
        == 0,
        "C2 CDM rows",
    )

    require(
        c2["database_mutation"]
        is False,
        "C2 database mutation",
    )

    require(
        c2["s3_mutation"]
        is False,
        "C2 S3 mutation",
    )

    post_rows = [
        line.strip()
        for line in Path(
            c2_post_db_path
        ).read_text().splitlines()
        if line.strip()
        and line.strip() not in {
            "BEGIN",
            "SET",
            "ROLLBACK",
        }
    ]

    require(
        post_rows
        == [
            "5799|0|113",
            "5799|2|5800",
            "5800|t",
            EXPECTED_MAPPING_SHA,
            "on",
        ],
        "post-Spark DB state",
    )

    policy = contract[
        "materialization_policy"
    ]

    require(
        policy[
            "cdm_visit_occurrence_mutated"
        ]
        is False,
        "CDM mutation",
    )

    require(
        policy[
            "row_shape_is_authoritative_pre_mutation_payload"
        ]
        is True,
        "payload authority",
    )

    require(
        policy[
            "fresh_database_revalidation_before_mutation"
        ]
        == "REQUIRED",
        "fresh revalidation",
    )

    require(
        policy[
            "materialization_transaction_required"
        ]
        is True,
        "transaction policy",
    )

    return {
        "task":
            "TASK-003",

        "step":
            "STEP-06C3",

        "status":
            "CDM_MATERIALIZATION_PREFLIGHT_CANONICAL_GATE_PASS",

        "candidate_rows":
            5799,

        "target_columns":
            17,

        "cdm_row_shape_rows":
            5799,

        "cdm_row_shape_sha256":
            EXPECTED_ROW_SHAPE_SHA,

        "authoritative_mapping_sha256":
            EXPECTED_MAPPING_SHA,

        "person_map_sha256":
            EXPECTED_PERSON_SHA,

        "cdm_visit_rows":
            0,

        "database_mutation":
            False,

        "s3_mutation":
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
        "--c1-summary",
        required=True,
    )

    parser.add_argument(
        "--c2-result",
        required=True,
    )

    parser.add_argument(
        "--c2-app",
        required=True,
    )

    parser.add_argument(
        "--c2-driver",
        required=True,
    )

    parser.add_argument(
        "--c2-post-db",
        required=True,
    )

    parser.add_argument(
        "--c2-sparkapp",
        required=True,
    )

    parser.add_argument(
        "--output",
        required=True,
    )

    args = parser.parse_args()

    result = validate(
        args.contract,
        args.c1_summary,
        args.c2_result,
        args.c2_app,
        args.c2_driver,
        args.c2_post_db,
        args.c2_sparkapp,
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
        "STEP06C3_PREFLIGHT_VERIFY=PASS"
    )

    print(
        "CDM_ROW_SHAPE_SHA256="
        + EXPECTED_ROW_SHAPE_SHA
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
