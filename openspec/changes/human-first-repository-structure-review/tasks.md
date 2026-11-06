# Tasks — Human-first full repository structure consolidation

## P0 — Structure audit and reviewed model
- [x] 0.1 Inspect latest main, PRs and Git tree by every root/system; capture baseline numbers and exact paths.
- [x] 0.2 Identify 223 legacy `taskNNN` paths, nine source README, 35 OpenSpec active changes and stale root ownership/long history problems.
- [x] 0.3 PR #709 merged protected main `10482bcd41ebe9cdbd6a06282bc26144b0f4736e`: all three Required Checks, OpenSpec, links and source-closure PASS; root map and exact full audit present.

## P0b — Freeze new directory debt before new business development

- [x] 0.4 PR #715 merged protected main `0e1c95d46ae577e5c5b3467cc39484c4ba48d644`: bootstrap default-branch-only `pull_request_target` job `require-trusted-component-paths`, offline 12 positive/negative unit tests, owner CODE/docs and source-path freeze. Original three Required Checks passed. New job is **NOT Required** until administrator adopts Ruleset.
- [ ] 0.5 After bootstrap merge, run one real valid PR PASS and one intentionally invalid new `task005` source PR FAIL. Record immutable head SHAs, job logs and negative evidence, close the negative PR unmerged.
- [ ] 0.6 Require the exact new status `require-trusted-component-paths` (GitHub Actions integration ID `15368`) in Ruleset #25365902, retaining the existing three Required contexts with no bypass. Independently verify a non-Draft invalid PR reports `mergeable_state=blocked`. Until then, this new check is NOT an enforced Required gate.

## P1 — Repo-wide human navigation and current ownership
- [x] 1.1 Fix stale Warehouse/Deployment references in root AGENTS, Documentation Governance and Developer CODE; preserve all safety restrictions; review PR merge pending.
- [x] 1.2 Add first-class clickable top-level codebase map for human GitHub browsing, exact component owners and explicit legacy distinction; review PR merge pending.
- [x] 1.3 Split the cumulative Document Index, Portal System, Portal Component and Fabric System readmes into concise current navigation while preserving four exact byte-identical former Markdown blobs at sibling dated HISTORY paths; CI acceptance pending.

## P2 — Centralize duplicate source READMEs
- [x] 2.1 Six Local DP source READMEs relocated with unchanged substantive content, immutable original SHA permalink and central Clinical Producers/Synthea owners; final PR #710 review pending.
- [x] 2.2 Three Portal READMEs moved to centralized documentation and component CODE maps updated; one Public Web concise current overview plus full implementation history; final PR #710 review pending.
- [x] 2.3 PR #710 merged main `d460116ec886eece35c598d55146ed4d688bed66` with docs links, OpenSpec, three Required Checks PASS and 874/874 non-Markdown blob SHA equivalence. All nine source READMEs absent. Also migrate the one remaining source-area OIE Channel-PoC Markdown in this PR, pending final CI/readback.

## P3 — Active OpenSpec hygiene
- [x] 3.1 Review five zero-unchecked Change task checklists against their recorded accepted merge/Run evidence, preserving historical failures and known boundaries; archive each unchanged except its path and adopt four scoped Current Specs. PR acceptance pending independent CI/main readback.
- [x] 3.2 PR #712 merged main `335fde4c87307e185836154abeae0c4afaaa56ae`; OpenSpec Strict, links, Notebook offline and three Required Checks PASS. Independent post-merge tree readback shows 31 Active Changes (vs 36 after new review Change + original 35) and five successfully archived Changes. Scope-limited four Current Specs adopted; no business runtime impact.

## P4 — Legacy Local DP functional migration (HOLD pending dependency proof)
- [ ] 4.1 **PARTIAL — exact 223/223 Healthcare Task directory Git tree/blob inventory and 19 functional-owner groupings recorded**, plus concrete Dockerfile/Airflow/PG/8-image workflow consumers and a Self-Runner 545-file/134 Task-name-path inventory. The separate full cross-repo content scan, live read-only PG/S3/K8s/Airflow consumer inventory and immutable SHA checker still require independent evidence; NOT ACCEPTED.
- [ ] 4.2 **PARTIAL — 19 functional destination categories and mandatory boundary gates published**, exact per-file new paths/compatibility and independent Clean Slate Path A/B choice remain under existing `modernize-legacy-task-code` OpenSpec; DO NOT treat planning targets as implemented.
- [ ] 4.3 Merge and test safe old/new compat first; move bounded functional batches with executable CI and required live acceptance where necessary; only then delete an obsolete task directory.
- [ ] 4.4 Independently verify full final Git tree contains no accepted task paths except approved compatibility exceptions. Do not claim done until real path consumer tests pass.

## P5 — Final whole-repo readback
- [ ] 5.1 **PARTIAL:** after PRs #709–#713, independently read merged main `68962c3e34c3daa10f01367cb1bafcf62c7f8cb5`: no source READMEs, 31 Active Changes, no open PR, exact 223 Local Task files unchanged, all scoped Required Checks passed. Complete P5 only after approved Local DP task-path migration and live consumer validation.
- [ ] 5.2 Adopt the architecture layout Current Spec and archive only when all required physical/compatibility tasks have passed; otherwise explicitly retain Active HOLD for Local DP and do not claim full cleanup.

## P3 archive scope and historical proof (2026-11-05)

- Five fully checked, previously accepted Change histories moved to dated Archive: [fabric-native-notebook-git-onboarding](../archive/2026-11-05-fabric-native-notebook-git-onboarding/tasks.md), [fabric-workspace-native-layout-cleanup](../archive/2026-11-05-fabric-workspace-native-layout-cleanup/tasks.md), [fix-airflow-exact-new-only-batch-selection](../archive/2026-11-05-fix-airflow-exact-new-only-batch-selection/tasks.md), [fix-multi-parquet-omop-writer-read](../archive/2026-11-05-fix-multi-parquet-omop-writer-read/tasks.md), [marquez-pg14-local-seven-day-backup](../archive/2026-11-05-marquez-pg14-local-seven-day-backup/tasks.md). Their content/acceptance proof remains immutable by matching each original Git blob SHA at new location; source Python/SQL and live resources are not altered by archive.
- Archive is **scoped**: New Git Native Notebook onboarding source and independent smoke accepted; *formal FHIR/Gold E2E remains distinct*. Airflow exact selection and multi-part Parquet Writer had separately verified successful real E2E/SKIP. Marquez PG14 backup CronJob + one manual dump was accepted; the first unattended scheduled 03:00 Job, restore and offsite recovery remain separate operational verification and are not implied.
- Behaviors from four delta specs are adopted as Current Specs with ADDED converted to Requirements. Fabric Workspace empty placeholder cleanup had no spec delta.

## P4 exact Git-only inventory evidence

Healthcare b3313aff archive receipt has accepted P3; current snapshot uses main `335fde4c87307e185836154abeae0c4afaaa56ae`, 223 task-subtree sources, 19 owners, each file's original Git Blob SHA in `documents/engineering/development/LEGACY-TASK-GIT-INVENTORY-20261105.json`. Self-Runner main `3faa9c243e07f62d96474b1989c2ad0ed831d9e3` has 134 Task-name-path matches among 545 tracked files. This supports only static dependency prioritization; P4.1/P4.2/P4.3/P4.4 and P5 remain OPEN until complete dual-repo/live acceptance.

## P0.5 real positive PR acceptance probe

A bounded documentation/task update (this PR) probes that the newly bootstrapped default-branch-only source-structure job runs, reads current main policy, and **PASSES** when no source violates naming. Actual job SHA/Run acceptance is to be recorded in the follow-up evidence PR, not guessed here. Existing Local DP runtime and OpenSpec P4 Clean Slate HOLDS remain unchanged.

## Real negative test (PR-only, NEVER MERGE)

- A deliberately invalid new path `local-data-platform/apps/task005/condition.py` is introduced **only** in this separate negative PR. Its substantive OpenSpec record and CODE map are included so existing trusted Change, CODE-map and OpenSpec checks can pass, isolating the new source-structure failure. This test PR must remain unmerged and its code never becomes a source artifact.
