# 2026-10-21 — Scheduled Landing Batch Discovery Claim preview mismatch

> OpenSpec `relocate-local-data-platform` Task **4.9.11**. This is incident evidence plus code/acceptance plan, not proof of post-fix Live success.

## Symptom and confirmed evidence

On 2026-10-21 the user observed the 15-minute scheduled Airflow 3 `landing_batch_discovery` DAG red: `scan_ready_manifests` SUCCESS, `evaluate_batch_claims` FAILED and following Python/Spark tasks `upstream_failed`. The separate manual-gated `new_only_omop_consumer` had completed real NEW_ONLY Person/Visit Writer and idempotency E2E; that is **not** a test of the scheduled Discovery/Claim path.

Read-only Self-Runner [PR #215](https://github.com/JohnZhang-DataForge/Self-Runner/pull/215) / [Run #39699192149](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39699192149) succeeded: Airflow Scheduler+Kubernetes historical failure Pod inspection (no DagRun trigger/pause, no DB or S3 changes) showed multiple `landing-batch-claim-guard` Pods terminated Failed with actual stack traces:

- `batch_ledger.ClaimError: BLOCKED:INCOMPLETE_INVENTORY`
- `batch_ledger.ClaimError: BLOCKED:DISCOVERY_SAFETY_GATE`

Cause confirmed from versioned implementation: `local-data-platform/apps/landing_discovery/run_airflow_scan.py` emits at most `MAX_XCOM_PREVIEW = 100` ready batches; `local-data-platform/apps/landing_claim/claim_discovered_inventory.py` had `MAX_ITEMS = 25` and rejected any truncated preview or `ready_count != len(ready_batches_preview)`. Scheduled DAG always uses `CLAIM_ENABLE=NO`, `CLAIM_ALLOWLIST=""`; therefore 26+ READY manifests triggered a fatal input exception **before** the intended read-only report. The prev 25-row limit was a stale consumer protocol, not S3 corruption or failed OMOP commit.

The Airflow UI shows a red scheduled chain because task `evaluate_batch_claims` fails. That alone does not demonstrate a PG mutation, missing S3 objects, or writer failure; avoid wiping ready manifests, resetting batches, claiming data, or running synthetic Writer to solve the UI.

## Minimal fix with explicit Claim safety

1. Align claim `MAX_ITEMS = 100` with scanner's XCom preview cap. Strictly validate type/ready count/truncation consistency and deduplicate manifest/batch identity.
2. When `CLAIM_ENABLE=NO` **only**, allow a bounded 100-row `ready_batches_preview` with `preview_truncated=True` and `ready_count > 100`. Evaluate only those preview rows as OBSERVED_ONLY/legacy/completed, return explicit `inventory_ready_count`, `preview_truncated`, `evaluation_scope=PREVIEW_ONLY`. This report does **not** claim to have evaluated unshown rows.
3. When `CLAIM_ENABLE=YES`, reject all truncated previews (even with explicit allowlist); preserve full inventory requirement, immutable Manifest identity, SHA256 re-read, atomic ledger transaction, lease fencing and failed-retry guard. Nothing enables real claims, adds ETL triggers, or changes DAG schedule here.
4. Add 26/35/100-row full-preview tests and 107-row truncated read-only test plus negative mismatch, forged full-preview, data-mutation flag, malformed count, disabled/active claim cases.
5. Merge only after trusted OpenSpec/Docs/Claim offline contract and Claim clean Docker Build PASS. Main `local-dp-image-rebuild.yml` auto-builds 8 images on `local-data-platform/apps/**` push, publishes immutable SHA and latest; capture actual new Claim Digest. Trigger no write on PR, and verify actual Airflow scheduled (or controlled read-only manual) DagRun `scan_ready_manifests/evaluate_batch_claims` both SUCCESS, processing disabled/no Claim and independent PG readback. Check no other failure replaces this one.

## Acceptance levels

- Diagnosis: **confirmed** by real failed Pod logs.
- Code and tests: **pending final PR CI**.
- New Claim image GHCR and live Airflow: **pending after merge**.
- Impact: read-only observation semantics only; no new S3/PG/OMOP data write or schema/credential change.
