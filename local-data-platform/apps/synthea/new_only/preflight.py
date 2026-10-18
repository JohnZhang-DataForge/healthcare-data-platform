#!/usr/bin/env python3
"""Read-only NEW_ONLY Kubernetes/storage and legacy contract audit.

Consumes kubectl GET snapshots only. Does not access S3, create Kubernetes
resources, run Synthea, or connect to PostgreSQL.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path


def items(document):
    return document.get("items", []) if isinstance(document, dict) else []


def audit(snapshot: dict, root: Path) -> dict:
    contract = json.loads((root / "contracts/synthea/v3.3.0/csv-contract.json").read_text())
    entrypoint = (root / "images/synthea/entrypoint.sh").read_text()
    dockerfile = (root / "images/synthea/Dockerfile").read_text()
    plan_path = root / "airflow/dags/task004_cdm_materialization_plan.py"
    spec = importlib.util.spec_from_file_location("readonly_legacy_materialization_plan", plan_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    node = snapshot.get("node", {})
    ready = any(c.get("type") == "Ready" and c.get("status") == "True"
                for c in node.get("status", {}).get("conditions", []))
    namespaces = {x.get("metadata", {}).get("name") for x in items(snapshot.get("namespaces", {}))}
    storage_classes = [
        {"name": x.get("metadata", {}).get("name"),
         "provisioner": x.get("provisioner"),
         "reclaim_policy": x.get("reclaimPolicy"),
         "binding_mode": x.get("volumeBindingMode")}
        for x in items(snapshot.get("storageclasses", {}))
    ]
    selected_sc = next((x for x in storage_classes if x["name"] == "local-path"), None)
    pv_inventory = []
    for pv in items(snapshot.get("pvs", {})):
        spec_pv = pv.get("spec", {})
        claim = spec_pv.get("claimRef", {})
        if claim.get("namespace") in {"dw-synthea", "dw-seaweedfs", "seaweedfs"}:
            pv_inventory.append({
                "name": pv.get("metadata", {}).get("name"),
                "claim_namespace": claim.get("namespace"),
                "claim_name": claim.get("name"),
                "reclaim_policy": spec_pv.get("persistentVolumeReclaimPolicy"),
                "storage_class": spec_pv.get("storageClassName"),
                "local_path": spec_pv.get("local", {}).get("path"),
                "host_path": spec_pv.get("hostPath", {}).get("path"),
                "node_affinity": spec_pv.get("nodeAffinity", {}),
            })
    synthea_pvcs = [{
        "name": x.get("metadata", {}).get("name"),
        "phase": x.get("status", {}).get("phase"),
        "volume": x.get("spec", {}).get("volumeName"),
        "storage_class": x.get("spec", {}).get("storageClassName"),
        "access_modes": x.get("spec", {}).get("accessModes", []),
    } for x in items(snapshot.get("pvcs", {}))
       if x.get("metadata", {}).get("namespace") == "dw-synthea"]
    synthea_pods = [{
        "name": x.get("metadata", {}).get("name"),
        "node": x.get("spec", {}).get("nodeName"),
        "phase": x.get("status", {}).get("phase"),
    } for x in items(snapshot.get("pods", {}))
       if x.get("metadata", {}).get("namespace") == "dw-synthea"]
    cm = snapshot.get("localpath_config", {})
    cm_data = cm.get("data", {}) if isinstance(cm, dict) else {}
    try:
        path_map = json.loads(cm_data.get("config.json", "{}")).get("nodePathMap", [])
    except (ValueError, TypeError):
        path_map = []
    # Readable paths from provisioner configuration are NOT evidence of a
    # dedicated physical device, an actual mount, or free space.
    node_paths = [
        {"node": item.get("node"), "paths": [p.get("path") if isinstance(p, dict) else p
                                             for p in item.get("paths", [])]}
        for item in path_map if item.get("node") in {"DEFAULT_PATH_FOR_NON_LISTED_NODES", "worker01"}
    ]
    ns_present = "dw-synthea" in namespaces

    def handoff(batch: str) -> dict:
        date = "2026-10-13"
        base = f"source=synthea/source_version=v3.3.0/ingest_date={date}/batch_id={batch}"
        return {
            "state": "HANDOFF_VERIFIED_NOT_LOADED", "cdm_write_permitted": False,
            "batch_id": batch, "manifest_sha256": "a" * 64, "source_version": "v3.3.0",
            "manifest_uri": f"s3://health-landing/{base}/manifest.json",
            "person_processing_uri": f"s3a://health-processing/{base}/entity=patient/run_id=probe/work/normalized/data/",
            "visit_processing_uri": f"s3a://health-processing/{base}/entity=encounter/run_id=probe/work/normalized/data/",
            "person_rows": 2, "visit_rows": 3,
        }

    module.plan(handoff("task004-airflow-compat-probe"))
    rejection = ""
    try:
        module.plan(handoff("synthea-new-only-probe"))
    except ValueError as exc:
        rejection = str(exc)
    if rejection != "BLOCKED=batch_id":
        raise RuntimeError("legacy writer batch-id gate unexpectedly changed: " + rejection)

    files = contract.get("files", [])
    expected_count = contract.get("expected_file_count")
    assert expected_count == len(files) == len({x["filename"] for x in files}) == 18
    assert contract["source_version"] == "v3.3.0"
    assert contract["require_nonempty_data_rows"] is True
    assert "POPULATION_SIZE" in entrypoint and "!= \"20\"" in entrypoint and "!= \"50\"" in entrypoint
    assert "SYNTHEA_COMMIT=995cf2fd33e67918d4e33110d9f68ad248002221" in dockerfile
    assert re.search(r"^\s*\"-cs\"\s*$", entrypoint, re.M)
    assert re.search(r"^\s*\"-r\"\s*$", entrypoint, re.M)

    capacity = node.get("status", {}).get("capacity", {})
    report = {
        "audit_mode": "READ_ONLY", "database_mutation": False,
        "kubernetes_mutation": False, "generator_deployed_by_audit": False,
        "worker01": {
            "found": node.get("metadata", {}).get("name") == "worker01",
            "ready": ready, "schedulable": not node.get("spec", {}).get("unschedulable", False),
            "capacity_ephemeral_storage": capacity.get("ephemeral-storage"),
            "kubelet_rootfs_available_bytes": snapshot.get("kubelet_summary", {}).get("node", {}).get("fs", {}).get("availableBytes"),
        },
        "namespace": {"dw_synthea_exists": ns_present, "synthea_pods": synthea_pods},
        "storage": {
            "storage_classes": storage_classes, "local_path_class": selected_sc,
            "local_path_config_worker01_paths": node_paths,
            "dedicated_synthea_pvcs": synthea_pvcs, "relevant_existing_pvs": pv_inventory,
            "worker01_dedicated_physical_mount_verified": False,
            "physical_disk_capacity_verified": False,
            "storage_decision": "BLOCKED_UNTIL_HOST_MOUNT_AND_RETAIN_PV_VERIFIED",
        },
        "synthea": {
            "existing_image_source_pin": "v3.3.0@995cf2fd33e67918d4e33110d9f68ad248002221",
            "legacy_population_values": [20, 50], "new_population_supported_by_old_entrypoint": False,
            "cli_overflow_flag_o_false_runtime_verified": False,
            "synthea_cli_runtime_test": "NOT_RUN",
        },
        "csv_contract": {
            "version": contract["contract_version"], "expected_files": expected_count,
            "nonempty_required_for_every_file": True,
            "low_population_contract_acceptance": "UNVERIFIED_REAL_GENERATION_REQUIRED",
        },
        "writer_batch_id": {
            "legacy_prefix_only": "task004-airflow-", "new_only_rejected_by_legacy_plan": True,
            "rejection": rejection, "versioned_contract_extension_required": True,
            "drift_gate": "MUST_REMAIN_ENABLED",
        },
        "secrets": {"dw_synthea_s3_secret_presence": snapshot.get("synthea_s3_secret", "UNKNOWN")},
        "next_step": "SELECT_AND_VERIFY_PHYSICAL_MOUNT_THEN_NEW_ONLY_IMPLEMENTATION",
        "generator_ready_to_deploy": False,
        "result": "PREFLIGHT_AUDIT_COMPLETED_WITH_BLOCKERS",
    }
    if not report["worker01"]["found"]:
        raise RuntimeError("worker01 not returned by API")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = audit(json.loads(Path(args.snapshot).read_text()), Path(args.root))
    Path(args.output).write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps(output, indent=2, sort_keys=True))
    print("SYNTHEA_NEW_ONLY_READONLY_PREFLIGHT=PASS")
    print("GENERATOR_DEPLOYMENT=NO")
    print("DATABASE_MUTATION=NO")


if __name__ == "__main__":
    main()
