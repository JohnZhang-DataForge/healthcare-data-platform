# Airflow — batch orchestration

[← Repository overview](../README.md) · [Current acceptance](../docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md)

`dags/` is the Git-synchronized source of Airflow DAGs and the Python helpers they import. It coordinates Kubernetes workloads; heavy Spark transformations run in Spark driver/executor Pods, not inside Airflow workers.

## Active and reference entry points

| Source file | Role |
| --- | --- |
| [`dags/new_only_omop_consumer.py`](dags/new_only_omop_consumer.py) | **Accepted Person/Visit batch DAG**: discover S3 READY, select exact manifest, read claim, launch Spark, reconcile, hand off and gate atomic Writer |
| [`dags/new_only_omop_routing.py`](dags/new_only_omop_routing.py) | Pure validation and routing: `COMPLETED → already_completed_no_replay`; new batch requires explicit processing selection |
| [`dags/new_only_omop_writer_handoff.py`](dags/new_only_omop_writer_handoff.py) | Validated immutable Spark→Writer handoff |
| [`dags/landing_batch_discovery.py`](dags/landing_batch_discovery.py) | Landing discovery DAG components |
| [`dags/landing_spark_processing.py`](dags/landing_spark_processing.py) | Reusable Kubernetes/Spark processing tasks |
| [`dags/task004_cdm_*.py`](dags/) | Historical-name but still relevant CDM plan, source reader, row adapters, PG renderer, preflight and safety components |
| [`dags/task004_processing_pipeline.py`](dags/task004_processing_pipeline.py) | Earlier Processing-first orchestration, retained for backward evidence |
| [`dags/platform_portal_openlineage_probe.py`](dags/platform_portal_openlineage_probe.py) | OpenLineage observability experiment; not a substitute for confirmed dataset lineage |

## Operational boundaries

- DAG: `new_only_omop_consumer`, **manual** (`schedule=None`), `max_active_runs=1`, default paused, 14 tasks.
- Input must identify the same immutable `batch_id`, `manifest_uri` and `manifest_sha256`.
- Explicit `spark_processing` and `writer_commit` flags plus the separate Kubernetes Writer Secret gate are required for a **new** batch commit.
- An already `COMPLETED` batch is routed to SKIP even if those flags were supplied.
- The Writer image is pinned by digest. Avoid clearing/retrying a failed Writer until PostgreSQL Claim/Stage/Checkpoint state has been independently inspected.

This folder contains **source**, not a command to safely re-run an accepted batch. See [runtime acceptance](../docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md) and [current Agent instructions](../docs/README.md) before cluster work.
