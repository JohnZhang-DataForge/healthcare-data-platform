# Python applications

Application-level Python code for **clinical source generation, S3 landing management, batch claims, and OMOP database writing** lives here.

## Main areas

| Folder | Purpose |
| --- | --- |
| [`synthea/`](synthea/) | Independent Synthea generation and publication helpers |
| [`landing_discovery/`](landing_discovery/) | Discover published, validated landing batches |
| [`landing_claim/`](landing_claim/) | Batch state, claim, and fencing logic |
| [`omop_writer/`](omop_writer/) | Validated Person/Visit loading and reconciliation |
| [`task001/`](task001/), [`task003/`](task003/), [`task004/`](task004/) | Earlier implementation modules retained for compatibility and traceability |

This layer is distinct from the Airflow DAG definitions in [`airflow/`](../airflow/README.md) and distributed transformations in [`spark/`](../spark/README.md).

For domain responsibilities, see the [component catalog](../documents/components/README.md).
