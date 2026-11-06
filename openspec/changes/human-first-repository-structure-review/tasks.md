# Tasks — Human-first full repository structure consolidation

## P0 — Structure audit and reviewed model
- [x] 0.1 Inspect latest main, PRs and Git tree by every root/system; capture baseline numbers and exact paths.
- [x] 0.2 Identify 223 legacy `taskNNN` paths, nine source README, 35 OpenSpec active changes and stale root ownership/long history problems.
- [ ] 0.3 Merge human-readable target taxonomy, dependency/hazard boundaries and root navigation after Required Checks.

## P1 — Repo-wide human navigation and current ownership
- [ ] 1.1 Fix stale Warehouse/Deployment references in root AGENTS and active engineering docs; preserve all safety restrictions.
- [ ] 1.2 Add first-class clickable top-level codebase map for human GitHub browsing, exact component owners and explicit legacy distinction.
- [ ] 1.3 Shorten duplicated current-vs-history summaries without discarding accepted evidence; keep release states accurate.

## P2 — Centralize duplicate source READMEs
- [ ] 2.1 Migrate six Local DP source-area READMEs into central system/owner docs, preserve unique code/setup/security/runbook content and correct links.
- [ ] 2.2 Migrate three Portal source-area READMEs similarly and update authoritative CODE maps.
- [ ] 2.3 Prove no source/runtime blobs changed, docs links PASS, archived historical cross-links remain resolvable, no deleted source README can be reintroduced.

## P3 — Active OpenSpec hygiene
- [ ] 3.1 Reconcile five zero-unchecked Changes with actual accepted evidence and unresolved HOLD; archive each only when safe, preserving delta specs and history.
- [ ] 3.2 Run link/trusted Required validation and independently count active/archive changes after merge.

## P4 — Legacy Local DP functional migration (HOLD pending dependency proof)
- [ ] 4.1 Inventory every executable old `taskNNN/` path, owned logical function and all first-party/cross-repo consumers, especially Self-Runner, Airflow, image build contexts, manifests, SQL/DB and historical SHA pins.
- [ ] 4.2 Publish exactly one semantic target per source module and versioned compatibility/rollback matrix. Enforce incremental no-duplicate ownership.
- [ ] 4.3 Merge and test safe old/new compat first; move bounded functional batches with executable CI and required live acceptance where necessary; only then delete an obsolete task directory.
- [ ] 4.4 Independently verify full final Git tree contains no accepted task paths except approved compatibility exceptions. Do not claim done until real path consumer tests pass.

## P5 — Final whole-repo readback
- [ ] 5.1 Read merged main and check all root systems, Markdown links, CODE maps, required checks, OpenSpec status and frozen source blobs.
- [ ] 5.2 Adopt the architecture layout Current Spec and archive only when all required physical/compatibility tasks have passed; otherwise explicitly retain Active HOLD for Local DP and do not claim full cleanup.
