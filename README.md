# Healthcare Data Platform

> **CURRENT Agent START HERE:** [docs/README.md](docs/README.md) → [TASK-STATUS](docs/tasks/TASK-STATUS.md) → [TASK004 Person/Visit OMOP 入库与批次幂等实施计划](docs/tasks/TASK-004-OMOP-CDM-INTEGRATION-AND-IDEMPOTENCY-PLAN-v1.0.zh-CN.md)。TASK004 已验收的 Processing MVP 保留冻结，但 **TASK004 overall = IN PROGRESS**，唯一 NEXT = STEP04A read-only preflight；TASK005 Condition ON HOLD。以下早期 TASK001/phase3c 描述属于历史工程背景。


Hybrid healthcare data engineering lab based on:

- Kubernetes
- SeaweedFS / S3 API
- Spark Operator / PySpark
- Airflow
- PostgreSQL
- OMOP CDM 5.4.3

## Current development baseline

The currently verified legacy implementation is preserved under:

`/data/spark/phase3c`

That implementation includes the previously validated:

`Synthea patients.csv -> Raw -> OMOP person -> PostgreSQL cdm.person`

pipeline.

The V2 development implementation lives in this repository.

## Current development scope

TASK-001:

Synthea v3.3.0 whole-batch intake.

One Synthea delivery contains 18 CSV files and represents one logical
`batch_id`.

TASK-001 will:

1. validate all 18 source files;
2. freeze and validate the Synthea source contract;
3. calculate row counts, headers, file sizes and SHA256;
4. build one batch manifest;
5. upload source files to the V2 Landing prefix;
6. independently read files back from S3 and verify SHA256;
7. publish `INTAKE_VERIFIED` only after all 18 objects pass;
8. verify idempotent rerun and conflict handling.

TASK-001 does NOT modify OMOP CDM or the existing Person pipeline.

## Local development paths

Permanent project:

`/data/spark/healthcare-data-platform`

Legacy verified implementation:

`/data/spark/phase3c`

Temporary development scripts:

`/data/spark/temp_shell`

Runtime reports and logs:

`/data/spark/healthcare-data-platform/runtime`
