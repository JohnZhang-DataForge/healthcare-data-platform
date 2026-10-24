#!/usr/bin/env python3
"""Bounded GET-only Marquez audit for one real NEW_ONLY Spark business run.

No OpenLineage POST, synthetic completion, Kubernetes mutation, or PG write.
This tool never calls a public endpoint and never treats a top-level Spark Job's
lack of DatasetVersions as evidence that child Job I/O is missing.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request

ROOT = "http://marquez.dw-marquez.svc.cluster.local/api/v1"
SPARK_NS = "healthcare-platform-spark-business"
AIRFLOW_NS = "healthcare-platform-airflow"
AIRFLOW_TASK = {
    "person": "spark_patient",
    "encounter": "spark_encounter",
    "reconcile": "spark_reconcile",
}
ROLES = ("person", "encounter", "reconcile")


def get_json(path):
    """Only GET the existing private Marquez API; fail closed on off-host URLs."""
    url = urllib.parse.urljoin(ROOT + "/", path)
    parsed = urllib.parse.urlsplit(url)
    expected = urllib.parse.urlsplit(ROOT)
    if (parsed.scheme, parsed.netloc) != (expected.scheme, expected.netloc):
        raise ValueError("OFF_HOST_MARQUEZ_QUERY")
    if not parsed.path.startswith("/api/v1/"):
        raise ValueError("NON_API_MARQUEZ_QUERY")
    request = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)


def job_path(namespace, name):
    return "namespaces/{}/jobs/{}".format(
        urllib.parse.quote(namespace, safe=""),
        urllib.parse.quote(name, safe=""),
    )


def list_jobs(namespace):
    path = "namespaces/{}/jobs?limit=500".format(namespace)
    all_jobs = []
    for _ in range(5):
        page = get_json(path)
        all_jobs.extend(page.get("jobs") or [])
        if len(all_jobs) > 2500:
            raise ValueError("JOB_INVENTORY_LIMIT")
        next_page = page.get("next")
        if not next_page:
            return all_jobs
        # The next link is untrusted: get_json enforces the service + API prefix.
        path = next_page
    raise ValueError("JOB_PAGINATION_LIMIT")


def get_runs(namespace, name, limit=35):
    url = job_path(namespace, name) + "/runs?limit={}".format(limit)
    return get_json(url).get("runs") or []


def snapshot(apps):
    jobs = list_jobs(SPARK_NS)
    result = {"roles": {}, "airflow": {}}
    for role in ROLES:
        app = apps[role]
        names = sorted({
            job.get("name", "") for job in jobs
            if job.get("name") == app or job.get("name", "").startswith(app + ".")
        })
        if not names or len(names) > 40:
            raise ValueError("MISSING_OR_EXCESSIVE_SPARK_JOBS:" + role)
        entries = []
        for name in names:
            for run in get_runs(SPARK_NS, name, limit=15):
                run_id = str(run["id"])
                details = get_json("jobs/runs/" + urllib.parse.quote(run_id, safe=""))
                entries.append({"job": name, "id": run_id,
                                "state": details.get("state", run.get("state")),
                                "detail": details})
        result["roles"][role] = entries
        airflow_job = "new_only_omop_consumer." + AIRFLOW_TASK[role]
        result["airflow"][role] = [
            {"id": str(run["id"]), "state": run.get("state")}
            for run in get_runs(AIRFLOW_NS, airflow_job, limit=20)
        ]
    return result


def identities(detail, direction):
    values = set()
    for edge in detail.get(direction + "DatasetVersions") or []:
        item = edge.get("datasetVersionId") or {}
        namespace, name, version = (
            item.get("namespace"), item.get("name"), item.get("version")
        )
        if all(isinstance(x, str) and x for x in (namespace, name, version)):
            values.add((namespace, name, version))
    return values


def has_batch(identity, batch):
    return "/batch_id=" + batch + "/" in "/" + identity[1].strip("/") + "/"


def select_writes(entries, batch, entity, source_name):
    """Select the real completed action with BOTH exact batch source and output."""
    for entry in entries:
        if entry["state"] != "COMPLETED":
            continue
        ins = identities(entry["detail"], "input")
        outs = identities(entry["detail"], "output")
        source = any(ns == "s3://health-landing"
                     and name.endswith("/payload/csv/" + source_name)
                     and has_batch(item, batch) for item in ins
                     for ns, name, _ in (item,))
        dests = {x for x in outs if x[0] == "s3://health-processing"
                 and "/entity=" + entity + "/" in "/" + x[1] + "/"
                 and has_batch(x, batch)}
        if source and dests:
            return sorted(dests)[0]
    return None


def parent_matches_airflow(entry, airflow_runs, role):
    facet = (entry["detail"].get("facets") or {}).get("parent") or {}
    parent_job = facet.get("job") or {}
    parent_run = facet.get("run") or {}
    return (parent_job.get("namespace") == AIRFLOW_NS
            and parent_job.get("name") == "new_only_omop_consumer." + AIRFLOW_TASK[role]
            and parent_run.get("runId") in airflow_runs)


def evaluate(data, batch):
    roles = data["roles"]
    patient = select_writes(roles["person"], batch, "patient", "patients.csv")
    encounter = select_writes(roles["encounter"], batch, "encounter", "encounters.csv")
    expected = {x for x in (patient, encounter) if x is not None}
    matching = []
    for entry in roles["reconcile"]:
        if identities(entry["detail"], "input") & expected:
            matching.append(entry)
    observed = set().union(*(identities(e["detail"], "input")
                             for e in matching)) if matching else set()
    complete_input = len(expected) == 2 and expected <= observed
    terminal = complete_input and all(e["state"] == "COMPLETED"
                                      for e in matching)
    parent_verified = all(
        any(parent_matches_airflow(
            e, {r["id"] for r in data["airflow"][role]
                if r.get("state") == "COMPLETED"}, role
        ) for e in roles[role])
        for role in ROLES
    )
    return {
        "batch_id": batch,
        "person_read_write": patient is not None,
        "encounter_read_write": encounter is not None,
        "reconcile_has_exact_two_produced_versions": complete_input,
        "reconcile_input_runs_terminal": bool(terminal),
        "reconcile_input_run_states": sorted(
            [{"job": e["job"], "run_id": e["id"], "state": e["state"]}
             for e in matching], key=lambda x: (x["job"], x["run_id"])),
        "airflow_task_runs_present": all(
            any(r.get("state") == "COMPLETED" for r in data["airflow"][role])
            for role in ROLES
        ),
        "airflow_spark_direct_parent": (
            "VERIFIED" if parent_verified else "UNPROVEN"
        ),
        "business_dataset_gate": (
            "PASS" if patient is not None and encounter is not None
            and complete_input and terminal else "INCOMPLETE"
        ),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-id", required=True)
    for role in ROLES:
        parser.add_argument("--" + role + "-app", required=True)
    args = parser.parse_args(argv)
    apps = {role: getattr(args, role + "_app") for role in ROLES}
    if not re.fullmatch(r"synthea-new-only-[a-zA-Z0-9-]{1,90}", args.batch_id):
        parser.error("expected one exact synthetic NEW_ONLY batch id")
    if any(not re.fullmatch(r"[a-z0-9_]{8,110}", app)
           for app in apps.values()):
        parser.error("expected exact lower-case Spark Marquez application Job names")
    try:
        report = evaluate(snapshot(apps), args.batch_id)
    except (ValueError, KeyError, TypeError, OSError, json.JSONDecodeError):
        print(json.dumps({"business_dataset_gate": "UNVERIFIED",
                          "reason": "MARQUEZ_GET_OR_SCHEMA_FAILED"}))
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["business_dataset_gate"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
