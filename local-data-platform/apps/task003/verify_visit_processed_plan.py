"""Verify an immutable STEP05G1 plan against exact STEP05F2 evidence."""
import argparse
import hashlib
import json
from pathlib import Path

from plan_visit_processed import build_plan


def verify_plan_bytes(plan_bytes, f2_bytes, policy, run_id):
    f2 = json.loads(f2_bytes)
    expected = build_plan(
        f2, policy, run_id, hashlib.sha256(f2_bytes).hexdigest()
    )
    expected_bytes = (
        json.dumps(expected, indent=2, sort_keys=True, ensure_ascii=False)
        + '\n'
    ).encode('utf-8')
    if plan_bytes != expected_bytes:
        raise ValueError(
            'CONFLICT: plan differs from pinned STEP05F2 evidence'
        )
    return expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--f2-state', type=Path, required=True)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()

    policy = json.loads((
        args.root
        / 'spark/contracts/processed/visit-candidate-publication-v1.json'
    ).read_bytes())

    plan_bytes = args.plan.read_bytes()
    result = verify_plan_bytes(
        plan_bytes, args.f2_state.read_bytes(), policy, args.run_id
    )

    print('PLAN_EVIDENCE_RECONCILIATION=PASS')
    print('EXPECTED_ROWS=' + str(result['expected_rows']))
    print('EXPECTED_PERSONS=' + str(result['expected_persons']))
    print('PLAN_STATUS=' + result['status'])
    print('PROCESSED_RUN_ID=' + result['run_id'])
    print('PLAN_SHA256=' + hashlib.sha256(plan_bytes).hexdigest())
    print('CANDIDATE_PERSISTED=NO')
    print('CANDIDATE_PUBLISHED=NO')
    print('VISIT_ID_ALLOCATED=NO')


if __name__ == '__main__':
    main()
