# Tasks: Fix multi-part Spark Parquet Writer reading

> Scope: **minimal source-adapter bugfix only**. Other Local DP infrastructure and architecture are unchanged. Evidence is recorded separately from historical `native` Race Mapping and from migration cleanup.

## 1. Confirm root cause and contract

- [x] 1.1 Record failed Batch `synthea-new-only-gh-39591929462` (78 Person, 15,828 Visit), [failed E2E Run #39591929462](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39591929462), and [read-only S3 Run #39593501193](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39593501193): Person 1 part, Visit 2 parts, error `BLOCKED=parquet_cardinality`, no Writer COMMIT.
- [x] 1.2 Fix the interface definition: a Processing URI points to a logical Parquet dataset prefix, not one physical file. Freeze non-goals in Proposal/Design and add a focused Delta Spec.

## 2. Implement minimum fix and unit/CI validation

- [x] 2.1 Change only the Writer's bound dynamic source reader to combine all sorted nonempty Parquet parts before a single existing `transform()` call.
- [x] 2.2 Add focused one/multi-part and fail-closed regression tests; connect them to existing eight-image PR workflow.
- [ ] 2.3 Verify final PR-head unit and image/contract CI, investigate any failures without relaxing boundaries, then squash-merge to protected Main.

## 3. Real-system acceptance

- [ ] 3.1 Rebuild/publish affected Writer runtime from exact Main SHA; capture actual immutable Digest and Pod imageID.
- [ ] 3.2 Run the original immutable failed Batch (78/15,828; Visit 2 parts) through the repaired reader in strict read-only mode; prove no PG connection/COMMIT.
- [ ] 3.3 Run a new unique Synthea NEW_ONLY Batch full E2E using published Writer; verify S3/manifest, Spark, COMMIT, independent PG counts, and same-Batch SKIP with zero PG mutation.
- [ ] 3.4 Document real runs and decide Change archival after acceptance. Preserve old image packages and unrelated cleanup scope.
