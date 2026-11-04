# Design — Disable Marquez Automatic Deletion

## Deployment behavior

Marquez 0.51.1's default chart values include a nonempty `dbRetention` map with `enabled: false`. The ConfigMap template nevertheless checks truthiness of the map rather than the flag, so the 7-day retention scheduler starts. The installed release demonstrably deleted all historical Jobs, Runs, Datasets and Lineage Events.

Keep upstream chart, PG14 PVC and namespace unchanged. Set `marquez.dbRetention: null` in the project values. Helm's rendering shall omit the application `dbRetention:` block entirely. A shallow `enabled: false` change is insufficient.

## Safeguards

- Fail deployment before mutation when Helm rendering includes `dbRetention:`, bundled PostgreSQL, public API NodePort or an unexpected DB host.
- Use `helm upgrade --reset-values` with project values so old release values cannot restore retention.
- Verify the live ConfigMap and the freshly restarted API container both lack `dbRetention:`. Only the API Deployment is restarted; PG14 is not.
- Verify the new Marquez process did not start the retention scheduler, API is healthy, PV is the same and database counts have not changed.
- Past data restoration is a separate task; increasing history will require future disk/backup monitoring, never implicit timed deletion.

## Verified execution

[Self-Runner guarded Helm deployment #41846708576](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41846708576) succeeded on 2026-11-04: render, Helm upgrade, live ConfigMap, container config, no retention job, API GET and PG14 PV/count preservation PASS.
