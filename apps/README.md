# Python applications — ingestion, claims and OMOP writers

[← Repository overview](../README.md) · [Spark code](../spark/README.md) · [Contracts](../contracts/README.md)

This directory contains Python business/application logic outside the Airflow DAG declarations and Spark application layer. It covers **source validation, intake publication, S3 discovery, Claim/fencing and PostgreSQL OMOP materialization**.

## Modules by capability

| Path | What it contains |
| --- | --- |
| [`synthea/`](synthea/) | Synthea NEW_ONLY producer/publish helpers and source-version gates |
| [`landing_discovery/`](landing_discovery/) | Find immutable READY manifests and expose read-only discovery results |
| [`landing_claim/`](landing_claim/) | Ledger queries, claim/lease fencing and rollback probes |
| [`omop_writer/`](omop_writer/) | **Accepted NEW_ONLY Person + Visit atomic Writer** and SQL generation / reconciliation / precommit checks |
| [`task001/`](task001/) | Historical milestone code for 18-file intake validation and manifest construction |
| [`task003/`](task003/) | Visit pipeline, candidate DQ, approved publication and mapping/preflight components |
| [`task004/`](task004/) | Generator/Landing/CDM runtime support and earlier Person/Visit source/loader components |
| [`resolve_verified_intake_file.py`](resolve_verified_intake_file.py) | Source resolver for a verified intake manifest |

## Runtime relationships

```text
Synthea source → apps/synthea + task001
Immutable S3 READY → landing_discovery + landing_claim
Airflow → PySpark Person / Visit (spark/)
Spark handoff → apps/omop_writer → PostgreSQL OMOP
```

The key production-style entry in this lab is [`omop_writer/new_only_airflow_writer.py`](omop_writer/new_only_airflow_writer.py), executed via a digest-pinned container in Airflow KPO; **do not run it locally as a generic one-shot importer**.

## Compatibility and scope

`task001`, `task003`, and `task004` are traceable historical implementation labels. Some of their Python modules are still imported at runtime; do not globally rename or delete them without updating Docker COPY, imports, contract checks and tests. Approved Person/Visit load does **not** imply that Condition, Drug or Procedure ingestion is implemented.

Relevant tests: [`tests/omop_writer/`](../tests/omop_writer/), [`tests/landing_claim/`](../tests/landing_claim/), [`tests/synthea_new_only/`](../tests/synthea_new_only/). See [final accepted data evidence](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md).
