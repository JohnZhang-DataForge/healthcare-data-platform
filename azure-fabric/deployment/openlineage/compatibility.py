"""Offline candidate Spark OpenLineage listener config. NEVER starts Spark."""
from __future__ import annotations
from dataclasses import dataclass
from urllib.parse import urlsplit

@dataclass(frozen=True)
class ListenerPlan:
    backend: str
    spark: str
    scala: str
    java: str
    artifact: str
    properties: dict[str, str]
    status: str

def plan_listener(backend: str, collector_url: str, *, artifact_version: str = "1.54.0") -> ListenerPlan:
    """Construct a candidate config, not proof of Spark/Fabric compatibility."""
    if backend not in ("local", "fabric"):
        raise ValueError("backend must be local or fabric")
    url = urlsplit(collector_url)
    if url.scheme != "https" or not url.netloc or url.username or url.password or url.query or url.fragment:
        raise ValueError("collector_url must be HTTPS without credentials/query/fragment")
    if not artifact_version or not all(c.isdigit() or c == "." for c in artifact_version):
        raise ValueError("pin a numeric artifact version")
    scala = "2.12" if backend == "local" else "2.13"
    artifact = f"io.openlineage:openlineage-spark_{scala}:{artifact_version}"
    props = {
        "spark.jars.packages": artifact,
        "spark.extraListeners": "io.openlineage.spark.agent.OpenLineageSparkListener",
        "spark.openlineage.transport.type": "http",
        "spark.openlineage.transport.url": collector_url.rstrip("/"),
        "spark.openlineage.namespace": f"healthcare-{backend}",
    }
    return ListenerPlan(backend, "3.5.7" if backend == "local" else "4.1",
                        scala, "not-inventoried" if backend == "local" else "21",
                        artifact, props, "CANDIDATE_NOT_RUNTIME_VERIFIED")
