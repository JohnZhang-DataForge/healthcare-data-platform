# Tasks — Disable Marquez Automatic Retention

## 1. Investigation and decision
- [x] 1.1 Verify the Marquez 0.51.1 Helm template bug, live `dbRetention` configuration, scheduled job logs and SQL delete counters.
- [x] 1.2 Record permanent no-retention behavior and rollback/verification design in OpenSpec.

## 2. Configuration and deployment
- [x] 2.1 Set `marquez.dbRetention: null` in the pinned Helm overrides, with comments explaining why `enabled: false` is unsafe.
- [x] 2.2 Add Helm rendering and live ConfigMap fail-closed gates and API-only restart/verification in the existing deploy script.
- [x] 2.3 Verify actual Helm upgrade: no retention in rendered ConfigMap or API process; API healthy; original PostgreSQL PV and metadata counts unchanged. Evidence: [Run #41846708576](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41846708576).
- [ ] 2.4 Merge verified fix to protected Healthcare main through CI.

## 3. Out of scope
- [ ] 3.1 Recover already-deleted historical Marquez data (future separate change).
