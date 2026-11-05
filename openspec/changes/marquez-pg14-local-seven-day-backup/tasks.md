# Tasks — Marquez PG14 development local backup

- [x] 1.1 Scope agreed: 03:00 US Eastern, existing dw-postgre14-data PVC, 7-day retention, dev-only accepted same-PVC failure domain.
- [ ] 1.2 Verify live Pod/PVC/Secret/space/existing scheduled backup (GET only) with exact Runner run evidence.
- [ ] 2.1 Add new namespace-scoped CronJob manifest and component-first static safety regression tests.
- [ ] 2.2 Update component documentation and OpenSpec; verify trusted CI and merge source PR.
- [ ] 3.1 Deploy exact merged manifest only after current-resource preflight; verify no existing PG14 object was changed.
- [ ] 3.2 Trigger exactly one manual backup Job and read back on-volume file, dump metadata and CronJob schedule.
- [ ] 3.3 Record final deployment SHA, GitHub Run, safety limits, and ongoing Job status; merge evidence PR.
