"""Opt-in Spark Processing-only replay from verified S3 discovery.

Generator-independent: consume exactly one immutable published Landing batch.
This file does not define an additional DAG. It provides pure selection gates
and Spark control Pod factories for the existing scheduled Landing DAG.
The 15-minute scheduled scan never starts Spark without an explicit manual
DagRun and exact manifest identity; no PostgreSQL CDM write is possible.
"""
from __future__ import annotations

import json
import re
from datetime import timedelta

from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from airflow.providers.cncf.kubernetes.secret import Secret

from task004_cdm_preflight_contract import validate_handoff

# Frozen and previously validated Spark orchestration runtime. Rename the
# image in a separate release; never rebuild the existing historical image.
PROCESSING_IMAGE = (
    "ghcr.io/johnzhang-dataforge/healthcare-data-platform-task004-runtime"
    "@sha256:8d55a150e7fcd8ea9a1ed8e8c2c64d09bf4d19687822c0ec84857fdf429c05a7"
)
# New image is an additive layer over the frozen historic image with the
# deployed v2-only manifest resolver and the exact pinned CSV contract.
NEW_ONLY_PROCESSING_IMAGE = (
    "ghcr.io/johnzhang-dataforge/healthcare-landing-processing-v2"
    "@sha256:9af63252823bae0187b2517a013c147e2df8dfbe9a7c783ac31cd5dd7dbbb937"
)
# KubernetesPodOperator.image is templated by Airflow; historic replays keep
# their exact original digest. Only a manually authorized source probe selects
# the new digest, never a scheduled scan or automatic Claim.
PROCESSING_IMAGE_SELECT = (
    "{{ '"
    + NEW_ONLY_PROCESSING_IMAGE
    + "' if ti.xcom_pull(task_ids='authorize_processing_replay').get("
    + "'new_only_processing_probe') is sameas true else '"
    + PROCESSING_IMAGE
    + "' }}"
)

S3_KEYS = [
    Secret("env", "AWS_ACCESS_KEY_ID", "dw-spark-s3-secret", "AWS_ACCESS_KEY_ID"),
    Secret("env", "AWS_SECRET_ACCESS_KEY", "dw-spark-s3-secret", "AWS_SECRET_ACCESS_KEY"),
]

IDENTITY = re.compile(r"^[A-Za-z0-9._-]{1,256}$")
SHA = re.compile(r"^[0-9a-f]{64}$")


def select_verified_processing_replay(
    discovery_json: str, claim_json: str, conf: dict | None, run_type: str
) -> dict | None:
    """Fail-closed manual-only selection; historical batch is never claimed.

    Existing historical READY batches must still show SKIP_LEGACY_BATCH.
    Independent NEW_ONLY batches may undergo an EXPLICIT dual-flagged manual
    processing-only probe only if PostgreSQL reports OBSERVED_ONLY. No Claim
    is taken and no business database SQL is executed.
    """
    if str(run_type).lower() != "manual":
        return None
    # Airflow's default Jinja renderer passes `| tojson` as a JSON string,
    # not as a Python dict. Decode it before checking manual opt-in.
    if isinstance(conf, str):
        try:
            conf = json.loads(conf)
        except (ValueError, TypeError) as exc:
            raise ValueError("BLOCKED:INVALID_MANUAL_DAGRUN_CONF") from exc
    if not isinstance(conf, dict) or conf.get("processing_only") is not True:
        return None

    try:
        d = json.loads(discovery_json)
        q = json.loads(claim_json)
    except (ValueError, TypeError) as exc:
        raise ValueError("BLOCKED:PROCESSING_UPSTREAM_JSON") from exc
    if (d.get("status") != "READ_ONLY_DISCOVERED"
        or d.get("processing_authorized") is not False
        or d.get("database_mutation") is not False
        or d.get("preview_truncated") is not False
        or d.get("ready_count") != len(d.get("ready_batches_preview", []))
        or q.get("status") != "EVALUATED"
        or q.get("claim_enabled") is not False
        or q.get("claim_count") != 0
        or q.get("input_count") != d["ready_count"]
        or q.get("spark_trigger") is not False
        or q.get("omop_business_mutation") is not False):
        raise ValueError("BLOCKED:PROCESSING_NOT_READ_ONLY")

    batch = conf.get("batch_id")
    uri = conf.get("manifest_uri")
    sha = conf.get("manifest_sha256")
    if not (isinstance(batch, str) and IDENTITY.fullmatch(batch)
            and isinstance(sha, str) and SHA.fullmatch(sha)
            and isinstance(uri, str) and uri.startswith("s3://health-landing/")):
        raise ValueError("BLOCKED:PROCESSING_IDENTITY")

    matches = [row for row in d["ready_batches_preview"]
               if row.get("batch_id") == batch
               and row.get("manifest_uri") == uri
               and row.get("manifest_sha256") == sha
               and row.get("status") == "INTAKE_VERIFIED"
               and row.get("source") == "synthea"
               and row.get("source_version") == "v3.3.0"
               and row.get("file_count") == 18]
    if len(matches) != 1:
        raise ValueError("BLOCKED:PROCESSING_MANIFEST_NOT_IN_VERIFIED_DISCOVERY")
    decisions = q.get("decisions")
    if not isinstance(decisions, list):
        raise ValueError("BLOCKED:PROCESSING_CLAIM_DECISIONS")
    matching_decisions = [r for r in decisions if r.get("batch_id") == batch]
    if len(matching_decisions) != 1:
        raise ValueError("BLOCKED:PROCESSING_CLAIM_DECISION_NOT_UNIQUE")
    new_only_probe = conf.get("new_only_processing_probe") is True
    if new_only_probe:
        # This is a specific manual processing PROBE, not a Claim substitute.
        # OBSERVED_ONLY, not SKIP_LEGACY_BATCH, proves no historic ledger
        # overlap. Reject any stray or non-boolean opt-in field.
        if not (re.fullmatch(r"synthea-new-only-[A-Za-z0-9][A-Za-z0-9._-]{1,127}",batch)
                and uri.startswith(
                    "s3://health-landing/source=synthea/source_version=v3.3.0/ingest_date="
                )
                and "/batch_id="+batch+"/manifest.json" in uri
                and uri.endswith("/manifest.json")
                and matching_decisions[0].get("decision")=="OBSERVED_ONLY"):
            raise ValueError("BLOCKED:NEW_ONLY_PROBE_NOT_SAFE")
    elif ("new_only_processing_probe" in conf
          or matching_decisions[0].get("decision") != "SKIP_LEGACY_BATCH"):
        raise ValueError("BLOCKED:ONLY_HISTORICAL_PROCESSED_BATCH_REPLAY_ALLOWED")

    selection = {
        "batch_id": batch,
        "manifest_uri": uri,
        "manifest_sha256": sha,
        "source_version": "v3.3.0",
        "status": "INTAKE_VERIFIED",
        "verified_file_count": 18,
        "processing_only": True,
        "omop_business_mutation": False,
        "producer_trigger": False,
    }
    # Preserve the exact original XCom shape for historical replays.
    # Never silently convert an old batch into a NEW_ONLY probe.
    if new_only_probe:
        selection["new_only_processing_probe"] = True
    return selection


def processing_gate(selection_json: str) -> bool:
    """Short-circuit all Spark KPOs for normal scheduled runs."""
    try:
        obj = json.loads(selection_json)
    except (ValueError, TypeError) as exc:
        raise ValueError("BLOCKED:INVALID_PROCESSING_GATE") from exc
    if obj is None:
        return False
    if (not isinstance(obj, dict) or obj.get("processing_only") is not True
            or obj.get("omop_business_mutation") is not False):
        raise ValueError("BLOCKED:PROCESSING_MODE")
    return True


def validate_processing_output(batch_json: str, person_json: str,
                               visit_json: str) -> dict:
    b, p, v = map(json.loads, (batch_json, person_json, visit_json))
    if b.get("processing_only") is not True:
        raise ValueError("BLOCKED:PROCESSING_MODE")
    if any(x.get("canonical_rows", 0) < 1 for x in (p, v)):
        raise ValueError("BLOCKED:EMPTY_SPARK_PROCESSING")
    if not all(x.get("processing_readback") == "PASS" for x in (p, v)):
        raise ValueError("BLOCKED:SPARK_PROCESSING_READBACK")
    # Independently verify same-batch immutable Landing context.
    result = validate_handoff(
        b,
        {"processing_data_uri": p["processing_data_uri"],
         "canonical_rows": p["canonical_rows"],
         "run_id": p["run_id"]},
        {"processing_data_uri": v["processing_data_uri"],
         "canonical_rows": v["canonical_rows"],
         "run_id": v["run_id"]},
    )
    return {"status": "PROCESSING_ONLY_PASS",
            "batch_id": b["batch_id"],
            "person_rows": p["canonical_rows"],
            "visit_rows": v["canonical_rows"],
            "omop_business_mutation": False,
            "handoff": result}


STATE_PUBLISH_COMMAND = r"""
set -Eeuo pipefail
LOG="$(mktemp)"
trap 'rm -f "$LOG"' EXIT
task004-runtime "$PROCESSING_ENTITY" 2>&1 | tee "$LOG"
STATE_FILE="$(awk -F= '$1=="STATE_FILE"{print substr($0,index($0,"=")+1)}' "$LOG" | tail -1)"
test -n "$STATE_FILE" && test -s "$STATE_FILE"
python3 - "$STATE_FILE" "$EXPECTED_ENTITY" <<'PY'
import json,sys
from pathlib import Path
state=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert state["status"]=="PASS",state
assert state["entity"]==sys.argv[2],state
assert state["processing_readback"]=="PASS",state
rows=int(state["canonical_rows"])
assert rows>0
result={
    "processing_data_uri": state["processing_data_uri"],
    "canonical_rows": rows,
    "run_id": state["run_id"],
    "processing_readback": "PASS"
}
Path("/airflow/xcom/return.json").write_text(
    json.dumps(result,sort_keys=True),encoding="utf-8"
)
print("LANDING_SPARK_PROCESSING_ONLY=PASS",flush=True)
PY
"""

RECONCILE_COMMAND = r"""
set -Eeuo pipefail
task004-runtime reconcile
echo "LANDING_SPARK_RECONCILIATION=PASS"
echo "OMOP_BUSINESS_MUTATION=NO"
"""


def make_processing_pod(task_id: str, *, process: str,
                        env_vars: dict[str, str], with_xcom: bool,
                        image_override: str | None = None):
    pod=KubernetesPodOperator(
        task_id=task_id,
        name=task_id.replace("_", "-"),
        namespace="dw-spark",
        service_account_name="task004-control-runtime",
        image=PROCESSING_IMAGE_SELECT,
        image_pull_policy="IfNotPresent",
        in_cluster=True,
        cmds=["/bin/bash", "-lc"],
        arguments=[RECONCILE_COMMAND if process == "reconcile" else STATE_PUBLISH_COMMAND],
        env_vars={
            **env_vars,
            **({} if process == "reconcile" else {
                "PROCESSING_ENTITY": process,
                "EXPECTED_ENTITY": "patient" if process == "person" else "encounter",
            }),
        },
        secrets=S3_KEYS,
        do_xcom_push=with_xcom,
        node_selector={"kubernetes.io/hostname": "worker02"},
        security_context={"fsGroup": 10001},
        container_security_context={
            "runAsNonRoot": True, "runAsUser": 10001, "runAsGroup": 10001,
            "allowPrivilegeEscalation": False, "capabilities": {"drop": ["ALL"]},
        },
        on_finish_action="delete_succeeded_pod",
        on_kill_action="keep_pod",
        startup_timeout_seconds=180,
        execution_timeout=timedelta(minutes=9),
    )
    if image_override is not None:
        if image_override != NEW_ONLY_PROCESSING_IMAGE:
            raise ValueError("BLOCKED:UNTRUSTED_SPARK_IMAGE_OVERRIDE")
        # Preserve the legacy factory's source/image selection contract;
        # apply the pinned v2 image ONLY for new consumer explicit opt-in.
        pod.image=image_override
    return pod
