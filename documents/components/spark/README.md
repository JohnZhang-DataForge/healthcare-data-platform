# Spark transformations

PySpark provides the platform's **distributed data preparation layer**. It reads source batches, produces canonical Patient/Encounter records, applies Person/Visit OMOP mappings, and performs quality and reconciliation checks.

The transformations prepare data for the PostgreSQL writer; they do not replace the writer's transactional responsibility.

**Related material**

- [Spark application source](../../../spark/README.md)
- [OMOP writer](../omop/README.md)
- [Batch and data flow](../../architecture/DATA-FLOW.md)

[All components](../README.md).
