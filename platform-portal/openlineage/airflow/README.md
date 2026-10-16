# Airflow OpenLineage integration

Scripts in this folder support the connection between **Apache Airflow and Marquez**.

## Files

- [`configure-scheduler.sh`](configure-scheduler.sh) — prepares the Airflow scheduler's OpenLineage integration settings
- [`verify-real-events.sh`](verify-real-events.sh) — checks for real Airflow events and their appearance in Marquez

The related opt-in probe DAG is kept with the main [Airflow DAGs](../../../airflow/README.md). The scripts relate to a deployed service and are not merely local examples.

See the [Portal overview](../../README.md), [Portal component documentation](../../../documents/components/platform-portal/README.md), and [historical A3 evidence](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/A3-AIRFLOW-OPENLINEAGE-REAL-LIVE-CLOSEOUT-2026-10-13.zh-CN.md).
