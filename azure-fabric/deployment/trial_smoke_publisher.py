"""Scoped Fabric Git-native Trial publisher. No Terraform resource management.

This module intentionally performs no cloud calls in 'validate' mode.
'publish' MUST be called only by the reviewed Self-Runner workflow after it
obtains two actual Terraform outputs from independently scoped read-only states.
"""
import argparse
import json
import os
import re
import urllib.request
from pathlib import Path
from uuid import UUID

WORKSPACE_NAME = "johnzhang-test"
NOTEBOOK_NAME = "nb_trial_smoke"
PIPELINE_NAME = "pl_trial_smoke"
ITEM_TYPES = ("Notebook", "DataPipeline")
CONFIRMATION = "publish-johnzhang-test-smoke-no-delete"
ZERO_GUID = "00000000-0000-0000-0000-000000000000"
API = "https://api.fabric.microsoft.com/v1"


def _guid(value):
    if not isinstance(value, str):
        raise ValueError("Expected a UUID string in Terraform outputs")
    return str(UUID(value))


def _platform(path, expected_type, expected_name):
    payload = json.loads(path.read_text())
    if payload.get("metadata", {}).get("type") != expected_type:
        raise ValueError("Fabric Item type mismatch")
    if payload["metadata"]["displayName"] != expected_name:
        raise ValueError("Fabric Item displayName mismatch")
    if path.parent.name != f"{expected_name}.{expected_type}":
        raise ValueError("Fabric Item source directory mismatch")
    logical = _guid(payload["config"]["logicalId"])
    if logical == ZERO_GUID:
        raise ValueError("Default empty logicalId is not permitted")
    return logical


def validate_source(source):
    source = Path(source).resolve()
    nb = source / "notebooks" / f"{NOTEBOOK_NAME}.Notebook"
    pl = source / "pipelines" / f"{PIPELINE_NAME}.DataPipeline"
    expected = {nb / ".platform", nb / "notebook-content.py",
                pl / ".platform", pl / "pipeline-content.json", source / "README.md"}
    actual = {p for p in source.rglob("*") if p.is_file()}
    if actual != expected:
        raise ValueError("Unexpected or missing Fabric Git-native source item")
    nb_id = _platform(nb / ".platform", "Notebook", NOTEBOOK_NAME)
    pl_id = _platform(pl / ".platform", "DataPipeline", PIPELINE_NAME)
    if nb_id == pl_id:
        raise ValueError("Duplicate logicalId across Notebook and Pipeline")
    pipeline = json.loads((pl / "pipeline-content.json").read_text())
    acts = pipeline["properties"]["activities"]
    if len(acts) != 1 or acts[0]["type"] != "TridentNotebook":
        raise ValueError("Pipeline must have exactly one Notebook activity")
    refs = acts[0]["typeProperties"]
    if refs.get("notebookId") != nb_id or refs.get("workspaceId") != ZERO_GUID:
        raise ValueError("Pipeline must reference same-workspace Notebook logicalId")
    if acts[0]["policy"].get("retry") != 0:
        raise ValueError("Smoke retry must remain disabled")
    notebook = (nb / "notebook-content.py").read_text()
    if "FABRIC_NOTEBOOK_SMOKE=PASS" not in notebook or "MODE=NO_DATA_WRITE" not in notebook:
        raise ValueError("No-write Notebook contract missing")
    if any(s in notebook for s in ("spark.sql(", ".save(", ".write.", "abfss://",
                                   "DROP TABLE", "CREATE TABLE", "notebookutils.fs.")):
        raise ValueError("Smoke Notebook contains disallowed data-write constructs")
    return {"notebook_logical_id": nb_id, "pipeline_logical_id": pl_id}


def _read_output(path, name):
    payload = json.loads(Path(path).read_text())
    if not isinstance(payload, dict) or name not in payload:
        raise ValueError("Missing required Terraform output: " + name)
    value = payload[name]
    if not isinstance(value, dict) or value.get("sensitive") is True:
        raise ValueError("Invalid or sensitive Terraform output: " + name)
    return value["value"]


def validate_outputs(workspace_path, onelake_path):
    name = _read_output(workspace_path, "fabric_workspace_name")
    if name != WORKSPACE_NAME:
        raise ValueError("Wrong Terraform workspace selected")
    workspace_id = _guid(_read_output(workspace_path, "fabric_workspace_id"))
    upstream_id = _guid(_read_output(onelake_path, "fabric_workspace_id"))
    lakehouse_id = _guid(_read_output(onelake_path, "lakehouse_id"))
    if workspace_id != upstream_id:
        raise ValueError("OneLake State does not belong to selected Workspace")
    if len({workspace_id, lakehouse_id}) != 2:
        raise ValueError("Workspace and Lakehouse IDs cannot be identical")
    return workspace_id, lakehouse_id


def readback_items(credential, workspace_id):
    """Independently list existing Fabric items; never mutate via this API."""
    token = credential.get_token("https://api.fabric.microsoft.com/.default").token
    found = {}
    continuation = ""
    for _ in range(20):
        url = f"{API}/workspaces/{workspace_id}/items"
        if continuation:
            import urllib.parse
            url += "?continuationToken=" + urllib.parse.quote(continuation, safe="")
        req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.load(resp)
        if not isinstance(payload, dict) or not isinstance(payload.get("value"), list):
            raise ValueError("Unexpected Fabric items list response")
        for item in payload["value"]:
            if item.get("type") in ITEM_TYPES and item.get("displayName") in (NOTEBOOK_NAME, PIPELINE_NAME):
                key = (item["type"], item["displayName"])
                if key in found:
                    raise ValueError("Ambiguous duplicate Fabric item")
                found[key] = _guid(item["id"])
        continuation = payload.get("continuationToken") or ""
        if not continuation:
            break
    else:
        raise ValueError("Fabric item listing exceeds bounded pagination")
    return found


def publish(source, workspace_id, confirmation):
    if confirmation != CONFIRMATION or os.getenv("FABRIC_TRIAL_PUBLISH_ALLOWED") != "true":
        raise PermissionError("Reviewed publish authorization is required")
    # Import credential/deployment SDK only after all source/state safety checks.
    from azure.identity import AzureCliCredential
    from fabric_cicd import FabricWorkspace, publish_all_items
    credential = AzureCliCredential()
    before = readback_items(credential, workspace_id)
    # Never mutate an unknown existing same-name Item; initial deployment is new-only.
    # Repeat/updates need an independently reviewed existing-item identity contract.
    if before:
        raise ValueError("Matching Fabric Item already exists; verify ownership before update")
    workspace = FabricWorkspace(
        workspace_id=workspace_id,
        repository_directory=str(source),
        item_type_in_scope=list(ITEM_TYPES),
        token_credential=credential,
    )
    publish_all_items(workspace)
    # Intentionally DO NOT call unpublish_all_orphan_items().
    after = readback_items(credential, workspace_id)
    for key in (("Notebook", NOTEBOOK_NAME), ("DataPipeline", PIPELINE_NAME)):
        if key not in after:
            raise RuntimeError("Published item missing in independent Fabric API readback: " + str(key))
    return after


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--mode", choices=("validate", "publish"), default="validate")
    parser.add_argument("--workspace-outputs", type=Path)
    parser.add_argument("--onelake-outputs", type=Path)
    parser.add_argument("--confirmation", default="")
    args = parser.parse_args()
    print("#### FABRIC_TRIAL_GIT_ITEM_PUBLISH_OUTPUT_BEGIN ####", flush=True)
    ids = validate_source(args.source_root)
    print("SOURCE_CONTRACT=PASS NOTEBOOK_LOGICAL_ID=" + ids["notebook_logical_id"], flush=True)
    print("PIPELINE_LOGICAL_ID=" + ids["pipeline_logical_id"], flush=True)
    if args.mode == "validate":
        if args.workspace_outputs or args.onelake_outputs or args.confirmation:
            raise ValueError("Offline validation does not accept Cloud output or confirmation parameters")
        print("MODE=VALIDATE REMOTE_STATE_READ=NO FABRIC_ITEMS_WRITTEN=NO", flush=True)
        print("#### FABRIC_TRIAL_GIT_ITEM_PUBLISH_OUTPUT_END ####", flush=True)
        return
    if not args.workspace_outputs or not args.onelake_outputs:
        raise ValueError("Both real Terraform output files are required for publish")
    workspace_id, lakehouse_id = validate_outputs(args.workspace_outputs, args.onelake_outputs)
    if args.confirmation != CONFIRMATION or os.getenv("FABRIC_TRIAL_PUBLISH_ALLOWED") != "true":
        raise PermissionError("Missing exact publish gate")
    print("TARGET_WORKSPACE_ID=" + workspace_id + " EXISTING_LAKEHOUSE_ID=" + lakehouse_id, flush=True)
    result = publish(args.source_root, workspace_id, args.confirmation)
    for (item_type, name), guid in sorted(result.items()):
        print("LIVE_READBACK=" + item_type + "/" + name + ":" + guid, flush=True)
    print("FABRIC_GIT_ITEM_PUBLISH=PASS DELETION_EXECUTED=NO", flush=True)
    print("#### FABRIC_TRIAL_GIT_ITEM_PUBLISH_OUTPUT_END ####", flush=True)


if __name__ == "__main__":
    main()
