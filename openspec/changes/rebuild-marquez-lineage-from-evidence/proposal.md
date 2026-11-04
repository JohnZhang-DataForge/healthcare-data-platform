# Rebuild Marquez lineage from verified sources after retention loss

## Incident
Marquez 0.51.1's unintended seven-day database retention deleted historical Job, Run, Dataset and Lineage Event metadata. The Helm retention policy has already been disabled and verified live by [Self-Runner #41846708576](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41846708576).

## Goal
Recover historical OpenLineage RunEvents only from exact immutable originals (backup / committed event archive), if discovered. When byte-exact originals are unavailable, distinguish original historical recovery from **new genuinely executed** lineage data. Never invent historical RunEvents or re-label new executions as restored historical runs.

## Scope / safety
- Inventory existing PostgreSQL backups, SeaweedFS archive prefixes, GitHub Actions artifacts and retained logs before writing.
- Use only opt-in Airflow's `platform_portal_openlineage_probe` for a bounded live Marquez ingest/reliability check. It has two Python tasks and does not access S3, OMOP, Spark or Writer.
- Preserve historical batch manifests, SHA256, durable PG17 COMMIT and run evidence. Do not re-run a completed NEW_ONLY batch or delete/reinitialize PG14.
- Rebuilding Patient/Encounter lineage requires a separate evidence-driven, idempotent execution gate and must not fabricate graph edges.
- Permanent no-retention remains a precondition; no automatic cleanup shall be reintroduced.
