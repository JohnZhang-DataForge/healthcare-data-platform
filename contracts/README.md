# Data contracts — source identity and writer boundaries

[← Repository overview](../README.md) · [Component CODE maps](../documents/components/README.md) · [Spark Contracts CODE](../documents/components/spark/CODE.md)

This directory stores **versioned machine-readable agreements** for source batches and Writer identity. Contracts specify what an upstream producer must publish and what downstream consumers may accept; they are not the data itself.

| Path | Responsibility |
| --- | --- |
| [`synthea/v3.3.0/csv-contract.json`](synthea/v3.3.0/csv-contract.json) | Synthea v3.3.0 **18 CSV file/header** contract |
| [`synthea/producer-batch-identity-v1.json`](synthea/producer-batch-identity-v1.json) | Producer batch identity fields |
| [`synthea/new-only/csv-contract-v2.json`](synthea/new-only/csv-contract-v2.json) | NEW_ONLY CSV producer / batch contract |
| [`synthea/new-only/ready-publication-policy-v1.json`](synthea/new-only/ready-publication-policy-v1.json) | Criteria for immutable READY publication |
| [`omop-writer/writer-batch-identity-v1.json`](omop-writer/writer-batch-identity-v1.json) | NEW_ONLY OMOP Writer versioned batch identity |

## Why identity matters

The accepted run binds **`batch_id` + `manifest_uri` + `manifest_sha256`** to an immutable S3 landing batch and a versioned Writer plan. Validation must fail closed on missing or conflicting identity values.

**Compatibility rule:** do not casually rename version fields, alter prefixes, or update an old contract in place to support a new data type. A contract change requires producer/consumer compatibility, explicit tests and a new version when necessary. The historical `task004` identifiers are still used in running Python modules and database records.

**Scope:** Person and Visit have a verified end-to-end OMOP path. The presence of `conditions.csv` in the 18-file intake contract does **not** mean Condition has already been transformed and committed.

See [TASK004 final acceptance](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md) and [TASK005 Condition STEP00](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-005-CONDITION-DEVELOPMENT-PLAN-v1.0.zh-CN.md).
