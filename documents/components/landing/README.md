# Landing and batch identity

The landing layer provides the boundary between **published source batches** and downstream processing.

It uses validated source manifests, batch identity, discovery logic, and claim/ledger records to make the ingestion path auditable. Raw batch publication and a completed database write are distinct events.

**Related material**

- [Landing discovery and claims applications](../../../apps/README.md)
- [Source and writer contracts](../../../contracts/README.md)
- [Airflow orchestration](../airflow/README.md)
- [Data flow overview](../../architecture/DATA-FLOW.md)

[All components](../README.md).
