# OMOP Writer

The writer is responsible for **loading standardized clinical records into PostgreSQL OMOP CDM**, including batch identity checks, transaction boundaries, source-ID mapping, and reconciliation.

The demonstrated scope is **Person and Visit**. Other OMOP domains are not implied to be complete.

**Related material**

- [Python writer implementation](../../../apps/README.md)
- [PostgreSQL SQL](../../../sql/README.md)
- [OMOP writer batch contract](../../../contracts/omop-writer/writer-batch-identity-v1.json)
- [Recorded Person/Visit acceptance](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md)

[All components](../README.md).
