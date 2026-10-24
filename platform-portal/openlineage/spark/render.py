"""OFFLINE manifest renderer ONLY. Never talks to Kubernetes or other services.

Output is a ConfigMap + per-run PVC + SparkApplication manifest set, for future manual-gated
controlled execution. No API operations are performed by this script.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml


BASE = Path(__file__).resolve().parent
TOKEN = re.compile(r"[a-z][a-z0-9-]{0,20}[a-z0-9]\Z")
NAMESPACE = "dw-spark"


def render(token: str) -> str:
    if not TOKEN.fullmatch(token):
        raise ValueError("Invalid run token; choose 2-22 lowercase DNS-safe characters")
    app_name = "portal-a4-" + token
    cm_name = app_name + "-source"
    template = (BASE / "sparkapplication.yaml.tpl").read_text(encoding="utf-8")
    application = yaml.safe_load(template.replace("__RUN_TOKEN__", token))
    pvc_name = app_name + "-output"
    pvc = {
        "apiVersion": "v1",
        "kind": "PersistentVolumeClaim",
        "metadata": {
            "name": pvc_name,
            "namespace": NAMESPACE,
            "labels": {
                "app.kubernetes.io/name": "portal-p3-spark-probe",
                "platform-portal-phase": "p3",
            },
        },
        "spec": {
            "accessModes": ["ReadWriteOnce"],
            "storageClassName": "local-path",
            "resources": {"requests": {"storage": "1Gi"}},
        },
    }
    configmap = {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {
            "name": cm_name,
            "namespace": NAMESPACE,
            "labels": {
                "app.kubernetes.io/name": "portal-a4-spark-probe",
                "platform-portal-phase": "a4",
            },
        },
        "data": {
            "probe.py": (BASE / "probe.py").read_text(encoding="utf-8"),
            "input.csv": (BASE / "input.csv").read_text(encoding="utf-8"),
        },
    }
    assert application["metadata"]["name"] == app_name
    assert application["metadata"]["namespace"] == NAMESPACE
    assert application["spec"]["volumes"][0]["configMap"]["name"] == cm_name
    assert application["spec"]["volumes"][1]["persistentVolumeClaim"]["claimName"] == pvc_name
    assert application["spec"]["arguments"][-1] == (
        f"file:///opt/spark/portal-a4-output/{token}/summary.parquet"
    )
    assert application["spec"]["restartPolicy"]["type"] == "Never"
    assert application["spec"]["sparkConf"]["spark.openlineage.transport.type"] == "http"
    return yaml.safe_dump_all(
        [configmap, pvc, application], sort_keys=False, explicit_start=True
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Static Portal A4 manifest renderer")
    parser.add_argument(
        "--run-token", required=True,
        help="Unique DNS-safe token for a future manually authorized test run",
    )
    args = parser.parse_args()
    print(render(args.run_token), end="")


if __name__ == "__main__":
    main()
