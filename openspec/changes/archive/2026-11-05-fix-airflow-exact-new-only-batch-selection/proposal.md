# Proposal: Decouple manual Airflow NEW_ONLY Batch selection from Discovery XCom preview

## Why

A genuine fresh Synthea Batch `synthea-new-only-gh-39625216978` reached READY (17 Person / 2,755 Encounter) but its manual Airflow `new_only_omop_consumer` failed at `select_verified_new_only_batch`, before Spark or Writer, with `BLOCKED:NEW_ONLY_DISCOVERY_INCOMPLETE`. Read-only XCom [Run #39626250729](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39626250729) proved `ready_count=26`, `ready_batches_preview length=25`, `preview_truncated=True`. This is not the separately fixed multi-Parquet Writer defect.

The Discovery image intentionally caps XCom preview at 25 items to keep a bounded display-only payload, but the Airflow selection routine erroneously requires the preview to contain every READY Batch. Existing users supply exact `batch_id`, `manifest_uri`, `manifest_sha256`.

## Change

Use the **already S3-credentialed Discovery Pod** to attest the manual requested Batch against its **complete validated S3 inventory** (same manifest contract, digest, source identity and 18-file check). Return one `verified_selected_batch` alongside the existing bounded XCom preview. Make Airflow `select_verified_new_only` require this exact attestation and reject identity drift; it must not require the preview to be exhaustive.

Keep the source scan cap (1,000 manifests), 25-item preview, schedules, read-only claims, Spark and Writer boundaries unchanged until real E2E passes. **After successful Airflow E2E**, in a second independently verified commit, increase only the display-only XCom preview from **25 to 100** for demonstration readability; routing remains independent even beyond 100 READY Batches.

## Non-goals

No changes to Synthea, Spark partitions, OMOP Writer, PostgreSQL SQL/tables, old READY Batches, generation, image deletion, automatic claiming, or unbounded XCom payloads.

## Acceptance

- CI/contract tests prove 26 READY with target outside first 25 is accepted and bad SHA/URI/missing target fails closed; 101 READY with 100-item preview remains logically safe.
- Rebuild/publish Discovery and DAG code on Main; verify new image identity and deployed GitSync.
- Run an actual previously READY new Synthea Batch through `new_only_omop_consumer` and complete Spark, Writer atomic COMMIT, independent PG readback and same-Batch SKIP.
- Only afterward expand preview to 100, rebuild/publish, and verify both bounded rendering and unchanged exact selection; leave `preview_truncated=True` for counts over 100 rather than blocking business.
