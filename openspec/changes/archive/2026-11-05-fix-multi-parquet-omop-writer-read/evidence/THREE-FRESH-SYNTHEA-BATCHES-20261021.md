# Three independent Synthea NEW_ONLY batches: real Landing validation (2026-10-21)

> Scope: generator, S3 Landing publication, historical source-ID collision validation, independent S3 readback and immutable replay only. **This is NOT a Spark/Writer/OMOP database E2E.** The independent Discovery 25-entry preview limit remains unresolved, and Writer Change Task 3.3 remains open.

## Execution

- Temporary Self-Runner [PR #197](https://github.com/JohnZhang-DataForge/Self-Runner/pull/197) and actual [GitHub Actions Run #39630497311](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39630497311): **workflow success; 3/3 matrix jobs success**. Temporary PR closed without merge; runtime evidence preserved in job logs.
- Generator source exact pinned Healthcare Main source/image tag: `git-a19c7d90b4425e607b0d139a0604e1ce9f2af8de`, published by eight-image [Run #39623841290](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39623841290). Three distinct frozen `gh-39630497311-0{1,2,3}` request IDs, generated sequentially on Worker01 with independently random frozen seeds and a test target population of 100 each.
- No database business mutation. The workflow's PostgreSQL source-map audit was read-only. No Spark, Airflow Consumer, OMOP Writer or Commit task was executed.

| Matrix | Batch ID | Person rows | Encounter rows | Generation | S3 18/18 + Manifest | Source IDs | Same-request Replay |
| --- | --- | ---: | ---: | --- | --- | --- | --- |
| 01 | `synthea-new-only-gh-39630497311-01` | 100 | 15,188 | PASS | PASS | S3/PG collision-free | `REUSE_EXISTING` PASS |
| 02 | `synthea-new-only-gh-39630497311-02` | 100 | 15,400 | PASS | PASS | S3/PG collision-free | `REUSE_EXISTING` PASS |
| 03 | `synthea-new-only-gh-39630497311-03` | 100 | 13,237 | PASS | PASS | S3/PG collision-free | `REUSE_EXISTING` PASS |
| **Total** | **3 independent immutable READY Batches** | **300** | **43,825** | **3/3** | **3/3** | **3/3** | **3/3** |

Each persisted READY manifest URI follows:

`s3://health-landing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-21/batch_id=<batch-id>/manifest.json`

For each Batch, the workflow also verified `NEW_ONLY_GENERATION=PASS`, `CSV_INVENTORY=18/18`, prepublish `LANDING_GLOBAL_SOURCE_IDS=PASS`, `FRESH_PG_SOURCE_ID_ZERO_COLLISION=PASS`, `PUBLISH_MODE=PUBLISHED_NEW`, `S3_PAYLOAD_READBACK_SHA256=18/18`, `NEW_ONLY_INDEPENDENT_S3_READBACK=18/18`, `PUBLISH_MODE=REUSE_EXISTING` on repeat, and `FRESH_BATCH_S3_READY=PASS`.

## Limits / next action

1. These are genuine, distinct, newly generated immutable Synthea Batches and may be used later as test inputs for real Spark/Writer E2E without regenerating them.
2. The actual Writer multi-Parquet fix was already proven independently on the original failed **two-part** Visit Batch by [Run #39624499095](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39624499095) (78 Person, 15,828 Visit, no PostgreSQL connection/COMMIT).
3. Earlier [Run #39626250729](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39626250729) confirmed the separate upstream Discovery selection issue: `ready_count=26`, `ready_batches_preview length=25`, `preview_truncated=True`, and new Batch absent from preview. Three more READY Batches do not fix this. **Do not mark Writer full E2E, PG COMMIT, PG Readback or same-Batch SKIP as PASS.**
4. To complete Task 3.3, address Discovery preview selection in a distinct, approved scope; then route these already READY Batch IDs through Spark processing and the fixed Writer, with atomic COMMIT, independent PostgreSQL readback and subsequent SKIP.
