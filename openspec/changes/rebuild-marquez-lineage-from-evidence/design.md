# Design — Evidence-first Marquez lineage recovery

## P0 recovery-source inventory
Read-only `dw-postgre14` table counts / PV; scan declared K8s snapshot resources, SeaweedFS root and named archive buckets, and prior GitHub Actions artifacts. Avoid printing patient data, credentials, raw URLs or event facets. No existing PostgreSQL restore is authorized without verified dump provenance, format, expected database and SHA.

## P1 bounded live proof (not historical restoration)
Check that live `dw-marquez/marquez-config` has no `dbRetention`. Verify the isolated DAG source and Airflow metadata show no active conflicts. Trigger exactly one uniquely named run of `platform_portal_openlineage_probe` with original installed DAG code (no source edits), wait for two terminal successful tasks, then GET Marquez for the genuine task Job entries and PostgreSQL counts. No PG14 direct writes, no synthetic `/lineage` POST by an agent.

If a precondition fails, stop without mutating. No full NEW_ONLY E2E, Spark job, or Writer is triggered by this P1.

## P2 tiny real Spark fixture lineage (optional and separate from history)
To verify true dataset graph recovery after successful Airflow probe, use the existing checked-in `platform-portal/openlineage/spark/` static renderer and self-contained 3-row fixture. Gate the resource names, source SHA, no live TASK004 processing, isolated SparkApplication + 1 Gi per-run PVC, and Marquez no-retention. Write only to the newly created probe PVC, never to healthcare business S3 or PostgreSQL OMOP. Require live Completed SparkApplication, and independent Marquez dataset/job/event row-count increase before accepting.

## P3 Patient/Encounter recovery (future)
Only use actual saved lineage event bytes, or a separately approved real Spark-only test with immutable input manifest, no Writer/OMOP mutation and explicit new run identity. Never fabricate COMPLETE for known START-only Spark action or claim original historical Run UUID as recovered.

## Evidence
- Original data loss RCA: [Self-Runner investigation](https://github.com/JohnZhang-DataForge/Self-Runner/blob/investigation/marquez-20261104/investigations/marquez-20261104/ROOT_CAUSE.md)
- Original 2026-10-25 Patient/Encounter independent evidence: [PORTAL-P5-FRESH-BATCH-EXECUTION-20261025](../archive/2026-10-25-complete-platform-portal-lineage-integration/evidence/PORTAL-P5-FRESH-BATCH-EXECUTION-20261025.md)


## P3 — real business Spark-only regeneration (2026-11-04, gated; not executed by this design)

Provenance: execute NEW Spark applications only, never synthesize October event bytes or replay historical Run IDs. This stage is distinct from the synthetic three-row P2 fixture. Pin the exact Healthcare main commit, checked-in DAG / S3 resolver / OpenLineage templates, the deployed Airflow GitSync hashes and actual container imageID. Select one immutable, source-verified Synthea READY manifest with exact URI+SHA256; its batch must have no conflicting Claim or Writer ledger row and no active lease. A previously committed batch is explicitly rejected even if its Landing payload is intact. The run name must be globally unique.

The primary execution route is the existing manual `new_only_omop_consumer` DAG, only if its current code and installed code match and the `consumer_readonly=true`, `spark_processing=true` gate is verified. Omit `writer_commit` and test the branch before running. Never run the generator, historical completed writer or full P5 E2E. If no suitable unclaimed READY batch exists, stop and design a separate isolated fixture with genuine canonical business rows; do not bypass Claim/Replay Fence.

### Operational gate

1. Preflight (read only): Marquez `dbRetention` absent; API healthy; existing expected PG14/PV; no conflicting GitHub Actions / K8s SparkApplication or Pod / Airflow business DagRun or Task; current installed DAG and identity guards match pinned source; no overlapping Agent operation. State exactly which namespaces and paths may be affected.
2. Independent PostgreSQL OMOP read-only baseline: `cdm.person`, `cdm.visit_occurrence`, `etl.landing_batch_ledger`, `etl.task004_batch_ledger` and available stable checkpoint/ledger fingerprints. Use `transaction_read_only=on`; reject unknown status or non-matching batch/Manifest SHA.
3. Trigger at most one uniquely named Airflow DagRun with exact immutable manifest and flags above, keep original pause state and restore it even on failure. Enforce no concurrent shared processing and serialize through the existing `local-dp-shared-new-only-e2e-exclusive` workflow group, acknowledging this is not a global cross-session lock.
4. Read back every real SparkApplication and Airflow task, actual imageID, then Marquez Job/Run and child action Jobs, *not merely top-level application Job*. Patient and Encounter each require exactly the expected Landing input and freshly written Processing DatasetVersion. Reconcile requires both exact Processing DatasetVersion IDs as inputs; no output is expected from a read-only reconciliation.
5. Verify genuine Column Lineage facets for Patient where emitted; explicitly list any Encounter/column gaps and START-only RDD children. No fabricated COMPLETE, no rewriting a failed workflow. Verify the public GET-only Marquez graph separately when reachable.
6. Independent post-run PG17 readback must match baseline across protected tables and controls; if diff or unknown transaction state, HOLD and investigate, not rerun. No OMOP Writer, Claim or replay mutations. Preserve immutable Run artifacts, precise new Run IDs, exact SHA, original workflow result, and any actual errors.

Safety: no Retention changes, DB/PVC restart or deletion, overwrite of S3 READY/Processing keys, historic Writer replay, original Run ID reuse, synthetic OpenLineage POST, or automatic retry. Workflow implementation must be explicitly one-shot and fail-closed; no permanent scheduled business workload is authorized.
