# Spark processing

The project's **PySpark transformation layer**. It reads validated clinical source batches, produces canonical records, applies OMOP mappings, and prepares data for downstream reconciliation and database writing.

## Contents

| Folder | Purpose |
| --- | --- |
| [`apps/person/`](apps/person/) | Patient/Person transformations |
| [`apps/visit/`](apps/visit/) | Encounter/Visit transformations |
| [`apps/task004/`](apps/task004/) | Historical processing and reconciliation modules |
| [`common/`](common/) | Shared batch and validation utilities |
| [`contracts/`](contracts/) | Canonical and OMOP-related data structures |
| [`manifests/`](manifests/) | SparkApplication job templates |

**Person and Visit** have recorded end-to-end ingestion acceptance; other OMOP domains require separate work.

See the [Spark component](../documents/components/spark/README.md), [Airflow orchestration](../airflow/README.md), and [database writing](../apps/README.md).
