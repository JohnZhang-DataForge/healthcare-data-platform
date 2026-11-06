# Design: Multi-part Processing dataset source adapter

## Observed failure

- [Failed real NEW_ONLY E2E #39591929462](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39591929462): Person 78; Visit 15,828; Writer `BLOCKED=parquet_cardinality`, before database commit.
- [Read-only S3 inventory #39593501193](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39593501193): Person prefix has 1 Parquet object, Visit prefix 2, both under the same Batch and Processing run. No PostgreSQL connection or COMMIT in the inventory probe.
- The Spark Visit source uses `canonical.write.mode("errorifexists").parquet(output_data_uri)` without `coalesce(1)`; multiple `part-*.parquet` are a normal Spark dataset representation.

## Decision

Modify only `local-data-platform/airflow/dags/task004_cdm_dynamic_source.py`:
1. Keep the existing plan-bound immutable S3 prefix and manifest SHA validation.
2. Require at least one Parquet part and disallow duplicate listed keys. Sort keys for deterministic read order.
3. Read/decode each nonempty Parquet object in that prefix; concatenate logical canonical row lists.
4. Call existing `transform(all_rows, context, entity)` **once**. Its exact overall count, Batch identity, source date, unique IDs, mapping and sorted result remain authoritative.
5. Keep `joint_s3_rollback.s3_rows` global Person/Visit referential checks, PG preflight, Writer transaction/fencing, same-Batch skip untouched.

## Costs and boundaries

This change preserves the existing single-process in-memory Writer and is not a streaming redesign. Parquet-part count may grow independently of business record count; enforcing one physical file is incorrect. PyArrow reads part files independently; memory remains bounded by the existing batch-size contract and available Writer resources, not by an added infrastructure component. S3 `_SUCCESS` is ignored as before.

## Verification

Add source adapter tests with mocked S3 pagination and injected decoder: one/two parts; out-of-order listing; missing part; duplicate IDs across parts; mixed Batch; missing, repeated, empty, malformed Parquet; modified manifest. Wire into the existing eight-image PR smoke workflow. After merge, pin actual Writer digest for a real immutable failed-batch **read-only** regression, then new Synthea data → Airflow → Spark → Writer COMMIT → independent PG readback → same-Batch SKIP.

Do not retry a batch after an ambiguous commit outcome without durable-state inspection.
