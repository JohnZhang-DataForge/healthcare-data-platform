# Development-only Marquez PostgreSQL 14 seven-day local backup

## Why
On 2026-11-04, the Marquez 0.51.1 retention configuration unexpectedly deleted historical lineage metadata. The retention job is now disabled. The owner wants a minimal development-environment backup: no external object store or separate PVC, nightly 03:00 US Eastern, delete backup files older than seven days.

## Decision
Install one namespace-scoped Kubernetes CronJob `dw-postgre14/marquez-pg14-local-backup`. Use PostgreSQL 14 `pg_dump --format=custom` through the existing `dw-postgre14` database service. Mount the existing `dw-postgre14-data` PVC on the same node as the live PG14 Pod and save in `/backup/marquez-backups` (PVC root `marquez-backups/`), **outside** PostgreSQL `pgdata/`. Run at `0 3 * * *` with `timeZone: America/New_York`. After a verified successful backup, delete only `marquez-*.dump` files older than 10,080 minutes.

## Scope and accepted limitation
This is a **development convenience backup**, not disaster recovery: loss/corruption of the local PVC/node can destroy the live database **and** all backups. No cloud storage, replication, offsite storage, snapshot controller, existing PVC/PV/StatefulSet migration, Marquez metadata retention change, or OMOP PG17 access.

## Safety and acceptance
1. Live read-only preflight must verify correct PG14 Pod, RWO PVC, node, free space, Secret, no existing backup CronJob and no overlapping jobs.
2. Static validation must prove SQL dump, restricted backup directory and pruning scope, Kubernetes schedule/timezone, no Service/PG data mutation, and no privileged credentials in Git.
3. Apply only the new CronJob after required CI and exact source pin. No changes to StatefulSet, existing service, PVC, PGDATA, Helm or other namespaces.
4. Trigger exactly one manual Job from the CronJob for first-live acceptance. Confirm successful `pg_dump`, readable `pg_restore --list`, backup file size >0, 0600 permissions and on-volume location. Do not execute `pg_restore` against production.
5. Record exact Run, SHA, deployment and readback. If any gate fails, HOLD; do not delete or retry unknown database writes. Old unrelated files must never be deleted.
