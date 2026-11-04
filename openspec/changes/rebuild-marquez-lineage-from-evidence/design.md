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
