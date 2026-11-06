# Repository structure and human navigation — verified baseline

**Baseline:** Healthcare `main` `bf18e65eb593dd5cc75988bdcc692c100cc3044a` · 2026-11-05. **Purpose:** a human should understand the repo from GitHub folders without loading an AI agent or reading all OpenSpec files.

## 1. GitHub root: what each directory means

| Folder | Files audited | Human-facing responsibility | First canonical entry |
| --- | ---: | --- | --- |
| `local-data-platform/` | 440 | Local Synthea/producer → Airflow/Spark → OMOP transaction engines; some historical task-named operational code | [Local components](../../systems/data-platform/README.md) |
| `azure-fabric/` | 210 | Fabric Native Items, Warehouse Writer, governed deploy assets, OpenLineage, IaC | [Fabric overview](../../systems/azure-fabric/README.md) |
| `platform-portal/` | 52 | Marquez/PG14, OpenLineage transport, public-safe viewer and exporter | [Portal components](../../systems/platform-portal/README.md) |
| `shared-data-engine/` | 21 | Platform-neutral Python Wheel and scoped Agent instructions | [Shared Engine](../../systems/data-platform/shared-engine/README.md) |
| `documents/` | 104 | Human architecture, component READMEs/CODE, build and operations knowledge | [Documentation](../../README.md) |
| `openspec/` | 297 | Current specs, active Changes and archived evidence (not executable code) | [OpenSpec lifecycle](CODE-ORGANIZATION-AND-NAMING.md) |
| `.github/` | 112 | CI workflows, centralized tests, fixtures and static quality guards | [Developer CODE map](CODE.md) |

Root `README.md` is the portfolio overview, root `AGENTS.md` sets mandatory Agent behavior, and `shared-data-engine/AGENTS.md` is an explicitly scoped exception. Avoid adding another root `src/`, `docs/`, `tests/` or top-level `scripts/`: source belongs to the proper functional system.

## 2. The human-first rule: one question, one path

| What you want | Go to | Avoid |
| --- | --- | --- |
| Understand a system | `documents/systems/<system>/README.md` | Reading historical task logs as current architecture |
| Locate/modify a source | `documents/systems/<system>/<component>/CODE.md` → actual source directory | Inferring ownership from an old filename |
| Add a feature | Relevant system owner + `openspec/changes/<change>/` | New task-number folders or separate CURRENT/NEXT docs |
| Find accepted architectural constraints | `openspec/specs/` | Treating drafts/archived tasks as active |
| Test new code | `.github/quality/tests/<system>/<component>/` | Creating another source-local tests tree |
| Add deployment assets | `azure-fabric/deployment/<registered-component>/` / actual platform-specific ownership | Mixing application business modules with deployment manifests |
| Find historical outcomes | `openspec/changes/archive/`, Git PR / immutable Runs | Copying a large dated timeline into the current README |

## 3. Findings by priority

**Critical human-browsing debt — Local DP:** 223 files under legacy task/step directories. These include Python, shell scripts, SQL, K8s templates and tests. The owner of runtime endpoints must be determined before moving. Use [legacy refactor plan](LEGACY-CODE-REFACTOR-PLAN.md) and [active Local DP relocation Change](../../../openspec/changes/relocate-local-data-platform/tasks.md) for known history; this new review does not silently supersede its business contracts.

**Historical audit (before PR #710):** nine source-area README files were legacy exceptions (six Local DP, three Platform Portal), several with essential OIE, Blob, public security and exporter instructions. Preserve the unique knowledge centrally, fix links, then remove source duplicates under proper PR/CI.

**Historical audit (before PRs #711–#712):** 35 Active OpenSpec Changes, with five zero-unchecked candidates requiring evidence-level review; avoid auto-archiving an unresolved business HOLD. Some system READMEs are excessively dated and duplicate archived Run chronologies. The root AGENTS has an obsolete Warehouse source statement inconsistent with adopted [Fabric deployment owner spec](../../../openspec/specs/fabric-deployment-component-ownership/spec.md).

## 4. Migration order and rollback

1. Fix root navigation and authoritative ownership statements; no executable movement.
2. Relocate only reviewed explanatory READMEs (preserve exact useful content and crosslinks); keep scoped AGENTS beside their source.
3. Archive individually accepted OpenSpec Change directories with accurate evidence and updated dependent links.
4. Stage existing task-named Local DP code in **bounded functional** changes, after cross-repo consumer graph and compatibility. No bulk rename into a `legacy/` folder and no symlink-based duplicated implementations.
5. Compare exact Git blobs before/after, run all Required Checks and relevant offline tests, collect deployment/runtime checks where needed; use independent main readback. Record separate HOLD if actual producer/consumer migration not accepted.

**This audit does not certify that task-numbered operational paths have been migrated, or that Runtime/Gold/Lineage E2E is complete.** Each checkpoint must be accepted separately.

## Live Task-number migration status — source path inventory complete, runtime mapping HOLD

The [223-file exact Git Blob inventory](LEGACY-TASK-GIT-INVENTORY-20261105.json) and [19-subtree semantic migration map](LEGACY-TASK-COMPONENT-MIGRATION-MAP.md) document each current Task-number path and proposed function owner. These are **STATIC / NOT MIGRATED**: real consumers include Local Docker/Airflow/PG identifiers and active Self-Runner workflows. The existing approved [Clean Slate local refactor](../../../openspec/changes/modernize-legacy-task-code/tasks.md) still governs isolated replacement and actual live testing before any cutover or old resource deletion.

## P2/P3 source document readback — current main

[PR #709](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/709) established root navigation and repaired stale ownership. [PR #710](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/710) removed all nine duplicate source READMEs, migrating their full content to human-facing component docs; 874 source/non-Markdown blobs were identical pre/post. [PR #711](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/711) separated four system overview READMEs from byte-identical archived history at their new sibling paths. [PR #712](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/712) archived five completed OpenSpec Changes and adopted four Current Specs. The remaining historical OIE Channel-PoC Markdown also moved to [Clinical Producers](../../systems/data-platform/clinical-producers/OIE-CHANNEL-POC.md) in this bounded document PR. All source-area human Markdown is now retired except the intentionally scoped Shared Engine `AGENTS.md`.

## Development resumption gate — immutable legacy, no new debt

New business development may continue along stable component/function paths. The original [Component Code Naming CI](../../../.github/workflows/code-component-naming-check.yml) gives head-branch feedback but is **not itself** one of the protected Required checks. A separate [default-branch-only trusted path workflow](../../../.github/workflows/component-source-structure-trusted.yml) + [source-path policy](../../../.github/quality/scripts/check_new_source_structure_trusted.py) rejects newly created Task/Step-named files under all owned source, quality and CI roots and new business Python imports/hardcoded source paths into old Task directories. **Do not claim it is enforced until Ruleset #25365902 independently requires job `require-trusted-component-paths` and a real negative PR is merge-blocked.**

This is forward-only: the 223 existing Local DP Task paths and their Docker/Airflow/PG/Self-Runner consumers are frozen until a separately authorized Clean Slate E2E and retirement decision. A new domain (e.g. Condition) starts in its existing functional component's source area with one CODE owner and an Active OpenSpec task, without creating a second monolithic task directory. Archive and Local DP physical cleanup remain an independent future migration.

## Real new-source gate verification and final administrator adoption

- The new [Trusted Component Path workflow](../../../.github/workflows/component-source-structure-trusted.yml) executes policy/tests from the default branch and inspects candidate Git bytes without executing PR-controlled code. It extends the existing optional [Component Code Naming workflow](../../../.github/workflows/code-component-naming-check.yml) to Shared Engine/Portal and detects new business-source direct imports/hardcoded file paths into old Task folders. It does not rewrite existing Task004 SQL, DAGs, images or 223 legacy files.
- **PR #716 positive PASS / merged:** [review](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/716), exact head `2c7b1a7256498f6cf8ba769f709de4ae3e792a32`, trusted job `127647252327` SUCCESS.
- **PR #717 negative FAIL / Draft unmerged:** [review](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/717), head `30ff41243e52b00f10fafc1f1ee2b6da51ed4866`; trusted job `127647950076` returned the exact `apps/task005/condition.py:new-task-or-step-source-path` violation. Other original Required checks succeeded.
- **Not yet fully protected:** administrator must require context `require-trusted-component-paths` in existing GitHub Ruleset #25365902 (GitHub Actions integration ID `15368`) and verify non-Draft PR #717 becomes merge-blocked. That Ruleset mutation is not available through the connected GitHub integration; no false enforcement assertion is permitted.
