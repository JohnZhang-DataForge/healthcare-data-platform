# Platform Portal — OpenLineage and Marquez

The Portal is the platform's **data lineage and observability subsystem**. It explores how Airflow and Spark jobs report their processing events, with Marquez storing and displaying the metadata.

## Main pieces

- Airflow OpenLineage integration
- Standalone Spark listener/probe
- Marquez API and native Web interface
- Dedicated PostgreSQL 14 metadata database

Airflow event integration and an isolated Spark smoke have recorded validation. Complete Person/Visit dataset lineage remains an open integration goal.

**Related material**

- [Portal source directory](../../../platform-portal/README.md)
- [Detailed design and test findings](TECHNICAL-REFERENCE.md)
- [Architecture overview](../../architecture/SYSTEM-OVERVIEW.md)
- [Current project status](../../status/PROJECT-STATUS.md)

[All components](../README.md).
