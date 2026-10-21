# Proposal: Fix multi-part Spark Parquet reading in the NEW_ONLY OMOP Writer

## Why

The post-cleanup NEW_ONLY E2E generated an immutable Synthea Batch `synthea-new-only-gh-39591929462` (78 Person, 15,828 Encounter). S3 publish, Spark processing, reconciliation and writer handoff passed, but the Writer failed before COMMIT with `BLOCKED=parquet_cardinality` ([Run #39591929462](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39591929462)).

A separate read-only S3 inventory ([Run #39593501193](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39593501193)) confirms **one Person Parquet part and two Visit Parquet parts in one immutable Processing dataset prefix**. Spark's normal partitioned write is compatible with the Processing contract; only `task004_cdm_dynamic_source.read` incorrectly enforces exactly one part.

## What changes

- Make the existing S3 source adapter read every Parquet part in the validated immutable Processing prefix, in deterministic key order.
- Validate the **combined dataset once** through the unchanged Mapper/plan contract (exact total row count, source Batch, unique IDs).
- Retain manifest digest, immutable plan, existing Writer fence, precommit audit, single SQL transaction and same-Batch SKIP.
- Add in-memory S3/decoder tests for one-part compatibility, multi-part rows, count loss, duplicates across parts, unexpected identities and corrupt objects. Run them in existing image CI.

## Non-goals

No changes to Spark output partitions, Synthea generation, Airflow DAG flow, OMOP mapping, PostgreSQL schema/SQL, Writer transaction strategy, image retention, historical cleanup, or Fabric.

## Acceptance

PR CI passes; a real failed immutable Batch is re-read without any PG write; after merge the rebuilt Writer image completes a **new** Batch E2E (with independent PG readback and same-Batch SKIP). Old failure remains documented.
