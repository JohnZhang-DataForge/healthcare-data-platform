# Healthcare Data Platform

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
