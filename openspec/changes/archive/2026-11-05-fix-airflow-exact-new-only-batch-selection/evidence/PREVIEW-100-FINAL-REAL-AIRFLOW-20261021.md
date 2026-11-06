# Airflow exact Batch + 100-item preview — final real-environment acceptance (2026-10-21)

## Ordered implementation

1. [PR #369](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/369), merged `67776c1dfdc2fc7a23919c36fcdc0437f021bdfb`: Discovery Pod checks exact `batch_id`/`manifest_uri`/`manifest_sha256` against **full validated S3 inventory**, returns attested `verified_selected_batch`; Airflow routing does not depend on whether the requested Batch appears in preview. Global S3 scan and immutable identity/Claim/Writer boundaries untouched.
2. [Eight-image publish #39636935979](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39636935979): successful real GHCR rebuild from exact merged source.
3. [Full original 25-preview E2E #39637787637](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39637787637): success using previously READY Batch `synthea-new-only-gh-39630497311-01`, Person 100 and Encounter 15,188. Real Airflow selection, Spark Person/Encounter, reconcile, Writer, atomic PG COMMIT, independent PG 394→494 Person and 52,308→67,496 Visit, and same Batch repeat SKIP with zero PG mutation all **PASS**. Actual Writer imageID validated. 25-preview failure demonstrably resolved **without increasing preview**. [More detailed evidence](EXACT-BATCH-E2E-BEFORE-PREVIEW-100-20261021.md).
4. **Only after real E2E PASS**, display-only [PR #371](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/371) changed `MAX_XCOM_PREVIEW` 25→100 and bounded preview tests, merged `7ff5d0a990e15c0ff9e2ca58b1d6b12fb9727ae6`. [Eight-image Main publication #39639881397](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39639881397) **SUCCESS** with immutable SHA and latest tags.

## Real Airflow XCom readback after preview 100

Temporary Self-Runner [PR #202](https://github.com/JohnZhang-DataForge/Self-Runner/pull/202), [Run #39640585101](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39640585101): **SUCCESS**. Manual read-only DAG selected the next existing READY Batch `synthea-new-only-gh-39630497311-02` (100 Person, 15,400 Encounter), with exact immutable Manifest SHA and no Spark or Writer authorization.

- `DAGRUN=local-dp-preview100-39640585101 STATE=success`
- `DISCOVERED_READY_COUNT=29`
- `XCOM_PREVIEW_COUNT=29` (**all** currently READY Batches visible; no 25-row truncation)
- `XCOM_PREVIEW_TRUNCATED=False`
- `EXACT_BATCH_02_VERIFIED=PASS`
- `SPARK_AND_WRITER_SKIPPED=YES`
- `DISCOVERY_PREVIEW_100_REAL_AIRFLOW=PASS`
- `DATABASE_BUSINESS_MUTATION=NO`
- `DAG_PAUSE_RESTORED=PASS`

New CI/contract tests also verify `ready_count=101` yields exactly 100 preview rows with `preview_truncated=True`, while exact requested Batch beyond preview remains verifiable and normal scheduled preview-only Discovery remains supported. This prevents presentation failure when total READY is 26–100 and prevents Airflow selection failures even beyond 100 READY Batches (until the separately existing 1,000-manifest full-scan safety limit is reached).

## Scope and follow-up

- **PASS**: Airflow exact Batch selection independent of display size, real full E2E and same-Batch SKIP, 100-item display release, and actual 29-row XCom production verification.
- No changes to Synthea, Spark partitioning, Writer Mapper/transaction, PostgreSQL schema, global Discovery scan cap, old READY source objects, or historic database records. Temporary Self-Runner PRs #200, #201, #202 closed unmerged; action run logs preserved.
- `synthea-new-only-gh-39630497311-02` remains uncommitted to OMOP after its read-only display test; `-03` also remains available. No additional Writer commit is implied by this test.
- Optional future work, not required for this change: show newest 100 in descending order when READY inventory exceeds 100; separately design a scalable exact GetObject selection when inventory approaches the existing 1,000-manifest scan cap. Do not change these for the present demo fix.
