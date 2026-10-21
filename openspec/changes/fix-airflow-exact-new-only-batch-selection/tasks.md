# Tasks: Remove Airflow NEW_ONLY preview-dependent Batch selection

## 1. Evidence and contract

- [x] 1.1 Reproduce failure from read-only Airflow XCom and logs: [Run #39626250729](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39626250729), 26 READY, preview 25, truncated; target missing.
- [x] 1.2 Freeze minimal fix, guardrails and ordered 25→100 display-only follow-up in Proposal/Design/Spec.

## 2. Fix Airflow selection first (preview stays 25)

- [x] 2.1 Make existing S3 Discovery KPO receive exact requested Batch identity and attest it against full validated S3 inventory; keep its bounded display preview.
- [x] 2.2 Have manual Airflow selector consume attested Batch identity rather than preview membership, preserving all downstream guards.
- [x] 2.3 Add regression for 26 Ready, 101 Ready, missing/tampered target, and legacy preview-only call.
- [ ] 2.4 PR CI clean build/contract tests; merge Main and publish Discovery runtime and refreshed DAGs.
- [ ] 2.5 Verify actual deployed GitSync, target selection, Spark, Writer COMMIT, independent PG counts and same-Batch SKIP on existing READY Batch; record immutable runs and actual imageID.

## 3. Then expand preview for demonstration (separate commit / PR)

- [ ] 3.1 Raise only display XCom `MAX_XCOM_PREVIEW` 25→100 and update boundary tests.
- [ ] 3.2 Validate 100-item display, truncation at 101, exact selection remains independent and legacy scheduled scanner contract.
- [ ] 3.3 CI, merge and republish affected runtime; record evidence. No blanket S3/PG cleanup or business logic change.
