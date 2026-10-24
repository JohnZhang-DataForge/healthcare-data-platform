#!/usr/bin/env python3
"""GET-only Kubernetes inventory for the existing Portal/Marquez runtime.

This is NOT an HTTP health, PG SQL, or OpenLineage readback, nor a deployment.
It never contacts Kubernetes without an explicit expected context.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone


# Fixed inventory targets; no ability to point this tool at arbitrary secrets.
QUERIES = (
    ("namespaces", "namespace", None, ("dw-marquez", "dw-postgre14"), None),
    ("marquez_deployments", "deployment", "dw-marquez",
     ("marquez", "marquez-web"), None),
    ("marquez_services", "service", "dw-marquez",
     ("marquez", "marquez-web", "marquez-web-lan"), None),
    ("api_endpoints", "endpointslice", "dw-marquez", (),
     "kubernetes.io/service-name=marquez"),
    ("web_endpoints", "endpointslice", "dw-marquez", (),
     "kubernetes.io/service-name=marquez-web"),
    ("lan_endpoints", "endpointslice", "dw-marquez", (),
     "kubernetes.io/service-name=marquez-web-lan"),
    ("postgres_pod", "pod", "dw-postgre14", ("dw-postgre14-database-0",), None),
    ("postgres_pvc", "pvc", "dw-postgre14", ("dw-postgre14-data",), None),
    ("postgres_service", "service", "dw-postgre14", ("dw-postgre14",), None),
)


def command_for(query):
    _, kind, namespace, names, selector = query
    command = ["kubectl", "--request-timeout=12s", "get", kind, *names]
    if namespace:
        command.extend(("-n", namespace))
    if selector:
        command.extend(("-l", selector))
    return command + ["-o", "json"]


def run_stdout(command):
    result = subprocess.run(
        command, check=True, capture_output=True, text=True, timeout=18
    )
    return result.stdout


def fetch_inventory(expected_context):
    actual_context = run_stdout(["kubectl", "config", "current-context"]).strip()
    if not actual_context or actual_context != expected_context:
        raise ValueError("KUBE_CONTEXT_MISMATCH_OR_EMPTY")
    items = {}
    for query in QUERIES:
        name = query[0]
        try:
            items[name] = json.loads(run_stdout(command_for(query)))
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError):
            # Never dump environment/cluster stderr, which might contain details.
            raise ValueError("GET_ONLY_QUERY_FAILED:" + name) from None
    return actual_context, items


def named(obj):
    if obj.get("kind") == "List":
        return {item["metadata"]["name"]: item for item in obj.get("items", [])}
    return {obj["metadata"]["name"]: obj}


def ready_endpoint(obj):
    return any(
        endpoint.get("conditions", {}).get("ready") is True
        for item in obj.get("items", [])
        for endpoint in item.get("endpoints", [])
    )


def evaluate(data):
    ns = named(data["namespaces"])
    dp = named(data["marquez_deployments"])
    svc = named(data["marquez_services"])
    pod = named(data["postgres_pod"])
    pvc = named(data["postgres_pvc"])
    pgsvc = named(data["postgres_service"])
    results = {}

    results["namespaces_active"] = all(
        ns.get(name, {}).get("status", {}).get("phase") == "Active"
        for name in ("dw-marquez", "dw-postgre14")
    )
    results["marquez_deployments_ready"] = all(
        int(dp.get(name, {}).get("spec", {}).get("replicas") or 0) >= 1
        and int(dp.get(name, {}).get("status", {}).get("readyReplicas") or 0)
        >= int(dp[name]["spec"]["replicas"])
        for name in ("marquez", "marquez-web")
    )
    results["api_web_clusterip"] = all(
        svc.get(name, {}).get("spec", {}).get("type") == "ClusterIP"
        for name in ("marquez", "marquez-web")
    )
    web = svc.get("marquez-web-lan", {})
    results["web_only_nodeport_30999"] = (
        web.get("spec", {}).get("type") == "NodePort"
        and any(p.get("nodePort") == 30999
                for p in web.get("spec", {}).get("ports", []))
    )
    results["api_endpoint_ready"] = ready_endpoint(data["api_endpoints"])
    results["web_endpoint_ready"] = ready_endpoint(data["web_endpoints"])
    results["lan_endpoint_ready"] = ready_endpoint(data["lan_endpoints"])
    results["postgres_pod_running"] = (
        pod.get("dw-postgre14-database-0", {}).get("status", {}).get("phase")
        == "Running"
    )
    results["postgres_pvc_bound"] = (
        pvc.get("dw-postgre14-data", {}).get("status", {}).get("phase") == "Bound"
    )
    results["postgres_service_clusterip"] = (
        pgsvc.get("dw-postgre14", {}).get("spec", {}).get("type") == "ClusterIP"
    )
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Read only Portal Kubernetes resource metadata; no exec/apply/port-forward"
    )
    parser.add_argument("--expected-context", required=True,
                        help="Exact output of a separately verified kubectl context")
    args = parser.parse_args(argv)
    try:
        context, inventory = fetch_inventory(args.expected_context)
        checks = evaluate(inventory)
    except (ValueError, KeyError, TypeError, subprocess.CalledProcessError,
            subprocess.TimeoutExpired) as exc:
        # No kubectl stdout or stderr is included in this failure report.
        print(json.dumps({"scope": "K8S_GET_ONLY", "result": "UNVERIFIED",
                          "error": str(exc)}, sort_keys=True))
        return 2
    report = {
        "scope": "K8S_GET_ONLY",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "kubernetes_context": context,
        "k8s_resources_ready": all(checks.values()),
        "checks": checks,
        "http_api_checked": False,
        "postgres_sql_checked": False,
        "marquez_job_run_dataset_checked": False,
        "portal_live_health": "UNKNOWN",
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["k8s_resources_ready"] else 1


if __name__ == "__main__":
    sys.exit(main())
