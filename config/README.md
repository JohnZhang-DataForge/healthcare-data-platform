# Configuration examples

[← Repository overview](../README.md) · [Kubernetes runtime manifests](../kubernetes/README.md)

This directory currently contains the example [`local.env.example`](local.env.example), illustrating historical runner-local paths and the Synthea/SeaweedFS settings for the development lab.

## How to read the example

- `PROJECT_ROOT` and `RUNTIME_ROOT` describe local development directories on a particular lab host; they are not portable defaults.
- `LEGACY_PHASE3C`, `SYNTHEA_SOURCE_DIR` and related paths point to the **protected historical baseline**.
- `SOURCE_SYSTEM`, `SOURCE_VERSION`, `BATCH_ID` and the S3 bucket settings are examples, **not the identity of the most recent committed batch**.
- Actual runtime S3 and PostgreSQL credentials are supplied through namespace-specific Kubernetes Secrets, **not** through committed environment files.

Do **not** paste secrets into `local.env.example`, push an active `.env`, or assume the example values automatically reflect the latest Airflow or Cluster configuration. See [development baseline](../docs/BASELINE.md), [operation rules](../docs/development/PLATFORM-DEVELOPMENT-OPERATIONS-v1.0.zh-CN.md), and [latest TASK status](../docs/tasks/TASK-STATUS.md).
