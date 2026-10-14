"""TASK004 NEW_ONLY reusable, *render-only* atomic Claim + Person/Visit Writer.

The first live commit's proven transaction is reused rather than copied.
No direct COMMIT runner, DB credentials or Airflow operator are added here.
The renderer is explicitly downstream of independent immutable S3/PG reader
preflight, whose executable integration belongs to the next phase.
"""
from __future__ import annotations

from commit_new_only_batch_once import (
    _render_atomic_new_only_sql, BATCH as HISTORIC_COMPLETED_BATCH,
)
from joint_s3_rollback import verified_plan
from precommit_gate import validate_input

_ALLOWED_VERSION = "synthea-new-only-v1"


def generate_dynamic_commit_sql(context: dict, people: list, visits: list,
                                lease_owner: str, handoff: dict) -> str:
    """Bounded dynamic new-batch renderer. Never execute returned SQL here.

    The handoff must originate from the Airflow S3 -> Spark Person/Visit
    verification contract. SQL itself still does fail-closed current-DB
    empty-Claim/empty-writer precheck, role separation, same-TX fencing,
    row-by-row reconciliation and single COMMIT.
    """
    from new_only_omop_writer_handoff import assert_dynamic_handoff

    plan = verified_plan(context)
    assert_dynamic_handoff(plan, handoff)
    if plan["batch_id"] == HISTORIC_COMPLETED_BATCH:
        raise ValueError("BLOCKED:ALREADY_COMMITTED_HISTORIC_BATCH")
    if plan.get("writer_identity_version") != _ALLOWED_VERSION:
        raise ValueError("BLOCKED:DYNAMIC_NEW_ONLY_IDENTITY_VERSION")
    if not (1 <= len(people) <= 100 and 1 <= len(visits) <= 100000):
        raise ValueError("BLOCKED:DYNAMIC_NEW_ONLY_BOUNDS")
    validate_input(plan, people, visits)
    return _render_atomic_new_only_sql(
        plan, people, visits, lease_owner,
        expected_identity=(
            plan["batch_id"], plan["manifest_sha256"], plan["manifest_uri"],
            len(people), len(visits),
        ),
    )
