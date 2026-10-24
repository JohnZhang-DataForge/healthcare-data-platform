# Engineering — Development, operations and governance

> **Status: ACTIVE (Engineering).** This directory owns stable engineering policies, code navigation, safe operations, project-level status and fixed historical evidence. **It is not the current work-item/implementation-plan tracker**; material changes are managed under `openspec/changes/`.

- [Development Workflow](development/DEVELOPMENT-WORKFLOW.md) — source-first implementation, PR, testing and evidence processes; [Agent Rules](development/AGENT-RULES.md), [OpenSpec Lifecycle](development/OPENSPEC-DEVELOPMENT-LIFECYCLE.md), naming, session coordination and documentation governance are standing rules.
- [Developer CODE](development/CODE.md) — repository-wide quality scripts and environment example navigation.
- [Operations](operations/README.md) — safety, recovery and shared-runtime guardrails.
- [Project Status](status/PROJECT-STATUS.md) — **only** cross-project CURRENT / NEXT summary, linking to active Changes instead of duplicating their Tasks.
- [Historical documentation migration](migration/MIGRATION-STATUS.md) and [G0–G7 bootstrap evidence](migration/OPENSPEC-IMPLEMENTATION-PLAN.md) — source provenance and dated audit only; **neither is the ongoing task ledger**.
- [Legacy code inventory (historical)](development/LEGACY-CODE-REFACTOR-PLAN.md) — preserved pre-relocation snapshot; future R2–R5 development is tracked, without authorization to implement, by the [Legacy modernization Change](../../openspec/changes/modernize-legacy-task-code/tasks.md).
- [Active Local DP relocation](../../openspec/changes/relocate-local-data-platform/tasks.md) — new-root Import/Docker/Airflow/Spark/E2E tasks pending.
- [Active OpenSpec enforcement closeout](../../openspec/changes/enforce-openspec-change-gate/tasks.md) — required CI proven; separate Current Spec/Archive closeout pending.

**Authority split:** `AGENTS.md` routes AI work; `documents/` records lasting system knowledge and policy; `openspec/changes/` owns each material change's Proposal, Design, Tasks and acceptance; `openspec/specs/` owns only verified adopted behavior; actual source/Contracts/PR/CI/Run own execution evidence. Historical PR/SHA/Run facts are not rewritten. This documentation cleanup does not deploy or execute runtime systems.
