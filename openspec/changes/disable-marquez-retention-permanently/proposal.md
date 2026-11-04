# Disable automatic Marquez metadata retention

## Why
The Marquez 0.51.1 chart advertises `marquez.dbRetention.enabled: false` but its ConfigMap template condition checks the nonempty `dbRetention` map instead of `enabled`. The deployed chart rendered a 7-day cleanup policy (every 15 minutes), and Marquez's built-in job deleted historical OpenLineage Jobs, Runs, Datasets and Events. The app can safely keep all metadata at the current small scale.

## Decision
Keep the existing pinned chart version, dedicated PostgreSQL 14/PVC and all public proxy policies intact. Override `marquez.dbRetention: null` to **omit** `dbRetention:` from Marquez `config.yml` entirely. Do not use `enabled: false` in this chart version.

## Safety and validation
1. `helm template` must show no retention config before any Helm mutation; retain existing DB location, credentials secret, ClusterIP policy, and no bundled PostgreSQL.
2. Helm upgrade with `--reset-values` so old release values cannot re-enable retention; do not run destructive SQL or recreate PVC.
3. Verify live ConfigMap is missing `dbRetention:`; only restart the Marquez API Deployment to reload mounted config.
4. Verify fresh API logs have **no** “Started db retention job”, API returns HTTP 200, existing PostgreSQL count unchanged (no new cleanups).
5. Record before/after evidence in Self-Runner workflow and document RCA.

## Scope excluded
Restoring previously deleted data, upgrading Marquez, new automatic maintenance and unrelated Helm changes.

## Risk
Without retention, PostgreSQL growth becomes unbounded; this is intentional while data volume is small. Later volume review requires an explicit separately approved proposal rather than silently enabling deletion.
