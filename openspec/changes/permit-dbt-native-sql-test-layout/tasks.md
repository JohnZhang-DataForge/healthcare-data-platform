# Tasks — Permit Fabric dbt native SQL tests (guarded)

## P1 — Governance and offline implementation
- [x] 1.1 Confirm current Main, Ruleset-facing trusted Gate, existing tests/legacy baseline and exact dbt project owner; reject broad test exceptions.
- [x] 1.2 Design exact allowlist for `azure-fabric/dbt/hl7-canonical/tests/` with negative cases and a separate governance Change.
- [x] 1.3 Implement narrowly scoped protected checker patch, targeted test cases and read-only candidate PR-head policy check on a branch.
- [ ] 1.4 Observe candidate positive/negative tests, confirm PR diff and OpenSpec CI; register reviewed PR/HEAD.

## P2 — Controlled administration (requires GitHub ruleset administrative rights)
- [ ] 2.1 Approve a documented, time-bounded trusted-policy maintenance window; do NOT merge protected checker with failed Required Check as if it passed.
- [ ] 2.2 Merge pinned reviewed PR using administrator governance, restore all original Required Checks immediately, read back Main and Ruleset.
- [ ] 2.3 Validate real PR-level positive allowlist and negative rejection cases against NEW default-branch trusted checker; only then close `govern-fabric-dbt-project-layout` task P2.1.

## P3 — Independent business source
- [ ] 3.1 Only AFTER P2, allow the actual `azure-fabric/dbt/hl7-canonical/` standard scaffold and SQL candidate; it belongs to a separate business PR. No Legacy HL7 cleanup in this governance Change.

<!-- Ephemeral negative PR-only test fixture. Not for merge into main. -->
