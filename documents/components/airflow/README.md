# Airflow orchestration

Airflow is the **workflow coordinator** for landing batches, Spark jobs, reconciliation, and OMOP writing.

The main Person/Visit consumer handles explicitly selected batches; a separate discovery DAG can inspect incoming batches without automatically committing them.

**Related material**

- [DAG source directory](../../../airflow/README.md)
- [Landing component](../landing/README.md)
- [Spark component](../spark/README.md)
- [Data flow overview](../../architecture/DATA-FLOW.md)

[All components](../README.md).
