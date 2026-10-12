# TASK-004 Batch Reconciliation Pilot

Status: **SOURCE READY / RUNTIME NOT YET VERIFIED**.

This additive TASK004 step reconciles already verified Patient and Encounter Processing outputs for the same Synthea batch.

Checks:
- Patient row count and unique source_record_id;
- Encounter row count and unique source_encounter_id;
- source_system/source_version/source_batch_id/source_ingest_date agreement;
- Encounter source_person_id foreign-key coverage against Patient source_record_id;
- zero orphan Encounter references.

The step is intentionally read-only with respect to business data: it reads the two immutable Processing Parquet datasets and emits validation markers only. It does not write PostgreSQL or a new Processing dataset. Successful temporary SparkApplication and ConfigMap resources are deleted; failed resources are retained for diagnosis.

Runtime verification will be performed from Self-Runner against the exact PR HEAD before merge.
