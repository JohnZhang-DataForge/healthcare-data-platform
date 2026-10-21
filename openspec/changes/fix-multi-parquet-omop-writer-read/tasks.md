# Tasks: Fix multi-part Spark Parquet Writer reading

> Scope: **minimal source-adapter bugfix only**. Other Local DP infrastructure and architecture are unchanged. Evidence is recorded separately from historical `native` Race Mapping and from migration cleanup.

## 1. Confirm root cause and contract

- [x] 1.1 Record failed Batch `synthea-new-only-gh-39591929462` (78 Person, 15,828 Visit), [failed E2E Run #39591929462](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39591929462), and [read-only S3 Run #39593501193](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39593501193): Person 1 part, Visit 2 parts, error `BLOCKED=parquet_cardinality`, no Writer COMMIT.
- [x] 1.2 Fix the interface definition: a Processing URI points to a logical Parquet dataset prefix, not one physical file. Freeze non-goals in Proposal/Design and add a focused Delta Spec.

## 2. Implement minimum fix and unit/CI validation

- [x] 2.1 Change only the Writer's bound dynamic source reader to combine all sorted nonempty Parquet parts before a single existing `transform()` call.
- [x] 2.2 Add focused one/multi-part and fail-closed regression tests; connect them to existing eight-image PR workflow.
- [x] 2.3 Verify final PR-head unit and image/contract CI, investigate any failures without relaxing boundaries, then squash-merge to protected Main.

## 3. Real-system acceptance

- [x] 3.1 Rebuild/publish affected Writer runtime from exact Main SHA; capture actual immutable Digest and Pod imageID.
- [x] 3.2 Run the original immutable failed Batch (78/15,828; Visit 2 parts) through the repaired reader in strict read-only mode; prove no PG connection/COMMIT.
- [ ] 3.3 Run a new unique Synthea NEW_ONLY Batch full E2E using published Writer; verify S3/manifest, Spark, COMMIT, independent PG counts, and same-Batch SKIP with zero PG mutation.
- [ ] 3.4 Document real runs and decide Change archival after acceptance. Preserve old image packages and unrelated cleanup scope.

## 4. Actual acceptance evidence and outstanding hold (2026-10-21)

> **Completed narrow Writer fix**: [Healthcare PR #363](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/363) passed final PR-head checks and Squash Merged Main `a19c7d90b4425e607b0d139a0604e1ce9f2af8de`. [Eight-image publication #39623841290](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39623841290) **SUCCESS**, including new Writer actual Pod imageID `sha256:565eb1f7598d1625a48f3230108c6031acdeea8368965cfe39395c7888734a10`.

> **Original failed Batch regression PASS**: [Self-Runner #39624499095](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39624499095), immutable Batch `synthea-new-only-gh-39591929462`, Person **1 Parquet / 78 mapped**, Visit **2 Parquets / 15,828 mapped**. Read-only S3 and Mapper only; `DATABASE_CONNECTION=NONE`, `DATABASE_COMMIT=NO`. **This satisfies 3.2, not 3.3**.

> **Task 3.3 HOLD — independent upstream issue**: Fresh [E2E #39625216978](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39625216978) generated and S3-published a new **17 Person / 2,755 Visit** Batch but failed *before Spark/Writer* in `select_verified_new_only_batch` with `BLOCKED:NEW_ONLY_DISCOVERY_INCOMPLETE`. Read-only [Discovery XCom #39626250729](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39626250729) proves **26 READY Batches**, preview length **25**, `preview_truncated=True`, requested new Batch not in preview. No PG COMMIT, so **full E2E, PG Readback and same-Batch SKIP remain unverified**. Do not modify Discovery or cleanup data as part of the narrowly approved Writer fix.

Full immutable evidence and cross-Run references: [2026-10-21 Multi-Parquet Writer evidence](evidence/MULTI-PARQUET-WRITER-READER-REAL-REGRESSION-20261021.md). Change remains Active, **not archived**. Tasks 3.3/3.4 stay unchecked until separately resolving upstream Discovery and rerunning E2E.

> **2026-10-21 three fresh Synthea batches, Landing-only PASS**: User-requested [Self-Runner Run #39630497311](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39630497311) **3/3 successful independent NEW_ONLY batches**, 100 Person each and 15,188 / 15,400 / 13,237 Encounter (**300 Person, 43,825 Encounter in total**); real S3 18/18 ready/payload readback, historical source-ID collision checks and same-request publish reuse PASS. Immutable IDs `synthea-new-only-gh-39630497311-01`, `-02`, `-03` are recorded in [three-Batch evidence](evidence/THREE-FRESH-SYNTHEA-BATCHES-20261021.md). **Scope = Synthea→Landing only; no Spark/Writer/PG COMMIT or SKIP**. Discovery preview limit still blocks full E2E, so Tasks 3.3 and 3.4 remain **unchecked**.
