# Tasks — Semantic source naming migration

- [x] 0.1 Inspect both latest Main SHAs, current open PRs and existing naming governance.
- [x] 0.2 Establish Tier A/B/C ownership, freeze published contract identifiers and list initial 12 private Notebook helper mappings.
- [ ] 1.1 Inventory all Tier A Notebook references and negative source-introspection tests.
- [ ] 1.2 Rename Tier A helpers/call sites in a separate isolated PR; no business logic, mode/status/schema/path changes.
- [ ] 1.3 Exact-HEAD offline Notebook CI and other required checks PASS; merge to Main only when safe.
- [ ] 2.1 Inventory Shared Engine and Self-Runner Tier B public entrypoints and all cross-repo callers.
- [ ] 2.2 Add semantic call sites + compatible old entrypoints, verify both repos and no live writes.
- [ ] 3.1 Prepare separate Tier C protocol/version matrix including old signed envelope and Replay.
- [ ] 3.2 Migrate Tier C only with explicit versioned transport and authorized physical E2E validation.
- [ ] 4.1 Audit residual stage-number names with explicit legacy classification and enforce naming guard.
