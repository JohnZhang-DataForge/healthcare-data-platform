# Tasks — Human-first full repository structure consolidation

## P0 — Structure audit and reviewed model
- [x] 0.1 Inspect latest main, PRs and Git tree by every root/system; capture baseline numbers and exact paths.
- [x] 0.2 Identify 223 legacy `taskNNN` paths, nine source README, 35 OpenSpec active changes and stale root ownership/long history problems.
- [x] 0.3 PR #709 merged protected main `10482bcd41ebe9cdbd6a06282bc26144b0f4736e`: all three Required Checks, OpenSpec, links and source-closure PASS; root map and exact full audit present.

## P0b — Freeze new directory debt before new business development

- [x] 0.4 PR #715 merged protected main `0e1c95d46ae577e5c5b3467cc39484c4ba48d644`: bootstrap default-branch-only `pull_request_target` job `require-trusted-component-paths`, offline 12 positive/negative unit tests, owner CODE/docs and source-path freeze. Original three Required Checks passed. New job is **NOT Required** until administrator adopts Ruleset.
- [ ] 0.5 **REAL POSITIVE + NEGATIVE CONFIRMED, final closure HOLD for Ruleset** — PR #716 head `2c7b1a7256498f6cf8ba769f709de4ae3e792a32` trusted job #127647252327 SUCCESS; merged `f1cce2cfe19e579059e39053e87493891b3778b8`. PR #717 Draft head `30ff41243e52b00f10fafc1f1ee2b6da51ed4866` trusted job #127647950076 FAIL with exact `local-data-platform/apps/task005/condition.py:new-task-or-step-source-path`, 12/12 policy tests PASS, and the original three Required checks SUCCESS. Keep #717 Draft/unmerged until administrator promotes the new check and actual non-Draft `mergeable_state=blocked` is verified, then close negative PR unmerged.
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

## P0.4–0.6 independently verified branch protection evidence (2026-11-05 ET)

- [PR #715](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/715) bootstrapped `.github/workflows/component-source-structure-trusted.yml` (`pull_request_target`) with `require-trusted-component-paths` and trusted default-branch script/tests; merged main `0e1c95d46ae577e5c5b3467cc39484c4ba48d644`. Head-branch `source`, default Required `require-trusted-change`, `validate-openspec`, `require-trusted-fabric-deployment-owner`, docs and Spark offline static all SUCCESS. No live cloud actions.
- [Positive real PR #716](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/716) head `2c7b1a7256498f6cf8ba769f709de4ae3e792a32`: new trusted component path job `127647252327` SUCCESS; existing three Required SUCCESS; merged main `f1cce2cfe19e579059e39053e87493891b3778b8`.
- [Negative real PR #717](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/717) head `30ff41243e52b00f10fafc1f1ee2b6da51ed4866`: new trusted component path job `127647950076` FAIL after **12 policy regressions pass**, printed `SOURCE_STRUCTURE_VIOLATION=local-data-platform/apps/task005/condition.py:new-task-or-step-source-path` and `SOURCE_STRUCTURE_TRUSTED=FAIL; cloud_actions=0`. Existing `require-trusted-change`, `validate-openspec`, `require-trusted-fabric-deployment-owner` all SUCCESS. Existing optional `check-added-code-paths` also FAIL as expected; Cloudflare Portal external non-Required failure is unrelated.
- **Admin-only HOLD:** GitHub Ruleset #25365902 currently lists ONLY the original three Required contexts; the new `require-trusted-component-paths` is **not yet Required**. After adding exact job context from GitHub Actions (integration ID `15368`), reread the ruleset and turn the negative PR #717 Ready temporarily for an independent mergeability check; it must return `blocked` because the new Required check is red. Then close #717 without merging. Do not archive this human-first Change or claim four-Required enforcement before this is complete.
- Local DP's **223 existing Task directory blobs** remain untouched by this forward-only rule. Old task-numbered PG objects/image names/DAG runtime identities were not renamed, released or replayed.
