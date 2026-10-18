#!/usr/bin/env python3

import argparse
import hashlib
import json
from pathlib import Path


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_bytes())


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def validate(
    contract_path,
    baseline_path,
    plan_path,
    reconciliation_state_path,
    reconciliation_result_path,
):
    contract = load(contract_path)
    baseline = load(baseline_path)
    plan = load(plan_path)
    recon_state = load(reconciliation_state_path)
    recon_result = load(reconciliation_result_path)

    expected_git = contract["git_checkpoint"]
    run_id = contract["run_id"]

    require(contract["task"] == "TASK-003", "contract task")
    require(contract["step"] == "STEP-06A", "contract step")

    # STEP06A1
    require(baseline["task"] == "TASK-003", "A1 task")
    require(baseline["step"] == "STEP-06A1", "A1 step")
    require(
        baseline["status"] == "VISIT_ID_ALLOCATION_BASELINE_DISCOVERED",
        "A1 status",
    )
    require(baseline["git_checkpoint"] == expected_git, "A1 git checkpoint")
    require(baseline["processed_publication_complete"] is True, "A1 processed complete")
    require(baseline["processed_prefix_frozen"] is True, "A1 processed frozen")
    require(baseline["processed_reservation_present"] is False, "A1 reservation")
    require(baseline["transaction_read_only"] is True, "A1 read only")
    require(baseline["visit_id_allocation_started"] is False, "A1 allocation")
    require(baseline["visit_id_map_mutated"] is False, "A1 map mutation")
    require(baseline["sequence_advanced"] is False, "A1 sequence")
    require(baseline["cdm_visit_occurrence_write"] is False, "A1 CDM write")
    require(baseline["s3_mutation"] is False, "A1 S3")

    # STEP06A2
    plan_sha = sha256_file(plan_path)
    require(
        plan_sha == contract["fingerprints"]["allocation_plan_sha256"],
        "A2 plan SHA",
    )
    require(plan["task"] == "TASK-003", "A2 task")
    require(plan["step"] == "STEP-06A2", "A2 step")
    require(plan["status"] == "VISIT_ID_ALLOCATION_PLAN_READY", "A2 status")
    require(plan["run_id"] == run_id, "A2 run")
    require(plan["git_checkpoint"] == expected_git, "A2 git")

    candidate = plan["source_candidate"]
    expected_candidate = contract["candidate"]

    require(candidate["rows"] == expected_candidate["rows"], "candidate rows")
    require(
        candidate["unique_business_keys"]
        == expected_candidate["unique_business_keys"],
        "candidate keys",
    )
    require(
        candidate["referenced_persons"]
        == expected_candidate["referenced_persons"],
        "candidate persons",
    )
    require(candidate["frozen"] is True, "candidate frozen")

    db = plan["database_snapshot"]
    expected_db = contract["database_baseline"]

    require(db["visit_map_rows"] == expected_db["visit_map_rows"], "map rows")
    require(db["cdm_visit_rows"] == expected_db["cdm_visit_rows"], "cdm rows")
    require(db["person_map_rows"] == expected_db["person_map_rows"], "person rows")

    seq = plan["sequence"]
    expected_seq = contract["sequence"]

    require(seq["name"] == expected_seq["name"], "sequence name")
    require(seq["last_value_direct"] == expected_seq["last_value"], "sequence value")
    require(seq["is_called"] == expected_seq["is_called"], "sequence is_called")
    require(
        seq["pg_get_serial_sequence_binding"]
        == expected_seq["pg_get_serial_sequence_binding"],
        "sequence binding",
    )
    require(seq["column_default"] is None, "sequence column default")
    require(seq["automatic_default_nextval"] is False, "automatic nextval")
    require(seq["explicit_allocation_required"] is True, "explicit allocation")

    preview = plan["allocation_preview"]

    require(preview["existing_candidate_mappings"] == 0, "A2 existing")
    require(preview["new_candidate_mappings"] == 5799, "A2 new")
    require(preview["predicted_first_new_id"] == 1, "A2 first ID")
    require(preview["predicted_last_new_id"] == 5799, "A2 last ID")
    require(preview["prediction_is_non_authoritative"] is True, "A2 authority")

    plan_safety = plan["safety"]

    require(plan_safety["transaction_read_only"] is True, "A2 read only")
    require(plan_safety["nextval_called"] is False, "A2 nextval")
    require(plan_safety["sequence_advanced"] is False, "A2 sequence advance")
    require(plan_safety["visit_id_map_mutated"] is False, "A2 map mutation")
    require(plan_safety["cdm_visit_occurrence_write"] is False, "A2 CDM write")
    require(plan_safety["s3_mutation"] is False, "A2 S3 mutation")

    # STEP06A3
    result_sha = sha256_file(reconciliation_result_path)

    require(
        result_sha == contract["fingerprints"]["reconciliation_result_sha256"],
        "A3 result SHA",
    )
    require(recon_state["task"] == "TASK-003", "A3 state task")
    require(recon_state["step"] == "STEP-06A3", "A3 state step")
    require(
        recon_state["status"]
        == "VISIT_ID_BUSINESS_KEY_RECONCILIATION_VERIFIED",
        "A3 state status",
    )
    require(recon_state["run_id"] == run_id, "A3 state run")
    require(recon_state["git_checkpoint"] == expected_git, "A3 state git")
    require(recon_state["allocation_plan_sha256"] == plan_sha, "A3 plan lineage")
    require(
        recon_state["reconciliation_result_sha256"] == result_sha,
        "A3 result lineage",
    )

    require(
        recon_state["candidate_business_key_sha256"]
        == expected_candidate["business_key_sha256"],
        "A3 business key fingerprint",
    )
    require(recon_state["candidate_rows"] == 5799, "A3 rows")
    require(recon_state["candidate_unique_business_keys"] == 5799, "A3 keys")
    require(recon_state["existing_candidate_mappings"] == 0, "A3 existing")
    require(recon_state["new_candidate_mappings"] == 5799, "A3 new")
    require(recon_state["candidate_only_keys"] == 5799, "A3 candidate only")
    require(recon_state["map_only_synthea_keys"] == 0, "A3 map only")

    require(recon_state["s3_read_only"] is True, "A3 S3 read only")
    require(recon_state["database_read_only"] is True, "A3 DB read only")
    require(recon_state["visit_id_allocation_started"] is False, "A3 allocation")
    require(recon_state["visit_id_map_mutated"] is False, "A3 map mutation")
    require(recon_state["sequence_advanced"] is False, "A3 sequence")
    require(recon_state["cdm_visit_occurrence_write"] is False, "A3 CDM")

    require(recon_result["task"] == "TASK-003", "A3 result task")
    require(recon_result["step"] == "STEP-06A3", "A3 result step")
    require(
        recon_result["status"]
        == "VISIT_ID_BUSINESS_KEY_RECONCILIATION_PASS",
        "A3 result status",
    )

    result_candidate = recon_result["candidate"]
    require(result_candidate["rows"] == 5799, "result rows")
    require(result_candidate["unique_business_keys"] == 5799, "result keys")
    require(result_candidate["referenced_persons"] == 113, "result persons")
    require(result_candidate["duplicate_business_key_groups"] == 0, "candidate dupes")
    require(
        result_candidate["business_key_sha256"]
        == expected_candidate["business_key_sha256"],
        "result business key fingerprint",
    )

    db_map = recon_result["database_map"]
    require(db_map["total_rows"] == 0, "result DB map rows")
    require(db_map["synthea_rows"] == 0, "result synthea map rows")
    require(db_map["duplicate_business_key_groups"] == 0, "result map key dupes")
    require(db_map["duplicate_visit_id_groups"] == 0, "result map ID dupes")

    recon = recon_result["reconciliation"]
    require(recon["rows"] == 5799, "reconciliation rows")
    require(recon["existing_mappings"] == 0, "reconciliation existing")
    require(recon["new_mappings"] == 5799, "reconciliation new")
    require(recon["candidate_only_keys"] == 5799, "reconciliation candidate only")
    require(recon["map_only_synthea_keys"] == 0, "reconciliation map only")

    safety = recon_result["safety"]
    require(safety["s3_read_only"] is True, "result S3 read only")
    require(safety["jdbc_read_only"] is True, "result JDBC read only")
    require(safety["nextval_called"] is False, "result nextval")
    require(safety["setval_called"] is False, "result setval")
    require(safety["sequence_advanced"] is False, "result sequence")
    require(safety["visit_id_map_write"] is False, "result map write")
    require(safety["cdm_visit_occurrence_write"] is False, "result CDM write")

    return {
        "task": "TASK-003",
        "step": "STEP-06A4",
        "status": "VISIT_ID_READONLY_PREFLIGHT_FROZEN",
        "run_id": run_id,
        "git_checkpoint": expected_git,
        "candidate_business_key_sha256": expected_candidate["business_key_sha256"],
        "allocation_plan_sha256": plan_sha,
        "reconciliation_result_sha256": result_sha,
        "candidate_rows": 5799,
        "candidate_unique_business_keys": 5799,
        "existing_candidate_mappings": 0,
        "new_candidate_mappings": 5799,
        "predicted_visit_id_range": [1, 5799],
        "predicted_range_authoritative": False,
        "sequence_last_value": 1,
        "sequence_is_called": False,
        "visit_id_allocation_started": False,
        "visit_id_map_mutated": False,
        "sequence_advanced": False,
        "cdm_visit_occurrence_write": False,
        "s3_mutation": False
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--baseline-state", required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--reconciliation-state", required=True)
    parser.add_argument("--reconciliation-result", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = validate(
        args.contract,
        args.baseline_state,
        args.plan,
        args.reconciliation_state,
        args.reconciliation_result,
    )

    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )

    print("VISIT_ID_READONLY_PREFLIGHT_FREEZE=PASS")
    print(
        "CANDIDATE_BUSINESS_KEY_SHA256="
        + result["candidate_business_key_sha256"]
    )
    print(
        "ALLOCATION_PLAN_SHA256="
        + result["allocation_plan_sha256"]
    )
    print(
        "RECONCILIATION_RESULT_SHA256="
        + result["reconciliation_result_sha256"]
    )


if __name__ == "__main__":
    main()
