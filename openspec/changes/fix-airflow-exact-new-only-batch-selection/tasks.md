# Tasks: Remove Airflow NEW_ONLY preview-dependent Batch selection

## 1. Evidence and contract

- [x] 1.1 Reproduce failure from read-only Airflow XCom and logs: [Run #39626250729](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39626250729), 26 READY, preview 25, truncated; target missing.
- [x] 1.2 Freeze minimal fix, guardrails and ordered 25→100 display-only follow-up in Proposal/Design/Spec.

## 2. Fix Airflow selection first (preview stays 25)

- [x] 2.1 Make existing S3 Discovery KPO receive exact requested Batch identity and attest it against full validated S3 inventory; keep its bounded display preview.
- [x] 2.2 Have manual Airflow selector consume attested Batch identity rather than preview membership, preserving all downstream guards.
- [x] 2.3 Add regression for 26 Ready, 101 Ready, missing/tampered target, and legacy preview-only call.
- [x] 2.4 PR CI clean build/contract tests; merge Main and publish Discovery runtime and refreshed DAGs.
- [x] 2.5 Verify actual deployed GitSync, target selection, Spark, Writer COMMIT, independent PG counts and same-Batch SKIP on existing READY Batch; record immutable runs and actual imageID.

## 3. Then expand preview for demonstration (separate commit / PR)

- [x] 3.1 Raise only display XCom `MAX_XCOM_PREVIEW` 25→100 and update boundary tests.
- [x] 3.2 Validate 100-item display, truncation at 101, exact selection remains independent and legacy scheduled scanner contract.
- [x] 3.3 CI, merge and republish affected runtime; record evidence. No blanket S3/PG cleanup or business logic change.

## 4. Actual first-phase acceptance and bounded display update (2026-10-21)

- **Exact selection at 25-row preview, real E2E PASS**: [Writer/Discovery Main #67776c1](https://github.com/JohnZhang-DataForge/healthcare-data-platform/commit/67776c1dfdc2fc7a23919c36fcdc0437f021bdfb), [8-image publisher #39636935979](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39636935979), [Self-Runner full E2E #39637787637](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39637787637). Existing READY Batch `synthea-new-only-gh-39630497311-01`, 100 Person / 15,188 Visit; Airflow exact-selection, Spark, Writer COMMIT, independent PG readback **394→494 Person / 52,308→67,496 Visit**, and repeat SKIP with zero DB changes all **PASS**. Preview deliberately remained 25. Evidence: [real E2E acceptance](evidence/EXACT-BATCH-E2E-BEFORE-PREVIEW-100-20261021.md).
- **Display preview 100 implementation**: `MAX_XCOM_PREVIEW` changed 25→100; no changes to Airflow exact selection, S3 validation, PostgreSQL, Spark or Writer. Tests cover fully visible 26, bounded 100/101 and exact target beyond preview. **Task 3.3 remains unchecked until second PR CI, Main merge and GHCR publication are confirmed.**

- **Final display release PASS**: [PR #371](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/371), merged Main `7ff5d0a990e15c0ff9e2ca58b1d6b12fb9727ae6`, [eight-image publisher #39639881397](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39639881397) SUCCESS. Read-only [Self-Runner Run #39640585101](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39640585101) returned `READY_COUNT=29`, `XCOM_PREVIEW_COUNT=29`, `preview_truncated=False`, exact Batch `-02` verified, Spark/Writer skipped, no database mutation, DAG and pause restoration PASS. 101→100 bounded truncation covered by CI. [Final real-environment evidence](evidence/PREVIEW-100-FINAL-REAL-AIRFLOW-20261021.md). **All this Change's numbered Tasks are completed.**
