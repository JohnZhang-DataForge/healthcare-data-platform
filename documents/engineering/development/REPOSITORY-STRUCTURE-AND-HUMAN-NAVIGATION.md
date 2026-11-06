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

**Duplicated docs:** nine remaining source-area README files are legacy exceptions (six Local DP, three Platform Portal), several with essential OIE, Blob, public security and exporter instructions. Preserve the unique knowledge centrally, fix links, then remove source duplicates under proper PR/CI.

**Stale/current ambiguity:** 35 Active OpenSpec Changes, with five zero-unchecked candidates requiring evidence-level review; avoid auto-archiving an unresolved business HOLD. Some system READMEs are excessively dated and duplicate archived Run chronologies. The root AGENTS has an obsolete Warehouse source statement inconsistent with adopted [Fabric deployment owner spec](../../../openspec/specs/fabric-deployment-component-ownership/spec.md).

## 4. Migration order and rollback

1. Fix root navigation and authoritative ownership statements; no executable movement.
2. Relocate only reviewed explanatory READMEs (preserve exact useful content and crosslinks); keep scoped AGENTS beside their source.
3. Archive individually accepted OpenSpec Change directories with accurate evidence and updated dependent links.
4. Stage existing task-named Local DP code in **bounded functional** changes, after cross-repo consumer graph and compatibility. No bulk rename into a `legacy/` folder and no symlink-based duplicated implementations.
5. Compare exact Git blobs before/after, run all Required Checks and relevant offline tests, collect deployment/runtime checks where needed; use independent main readback. Record separate HOLD if actual producer/consumer migration not accepted.

**This audit does not certify that task-numbered operational paths have been migrated, or that Runtime/Gold/Lineage E2E is complete.** Each checkpoint must be accepted separately.
