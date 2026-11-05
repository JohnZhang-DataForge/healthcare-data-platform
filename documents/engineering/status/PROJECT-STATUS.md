# Healthcare Project Status — OpenSpec-first Navigation

> **NAVIGATION ONLY — no manually maintained CURRENT/NEXT here.** Each Active OpenSpec Change's `tasks.md` is the sole source of its outstanding task state. Runtime/acceptance truth comes from actual source, PR, Workflow Run and independent readback, not from this index.

## Find the current work

- [All Active Changes](../../../openspec/changes/) — active per-change Proposal / Design / Tasks. Ignore `archive/` when looking for pending tasks.
- [Adopted Current Specs](../../../openspec/specs/) — verified behavioral contracts; **not** a list of future tasks.
- [Archive of completed Changes](../../../openspec/changes/archive/) — detailed past decisions and evidence; completed history is never reclassified as current work.
- [System/component navigation](../../README.md) — choose the owning README / CODE; for Warehouse see [Warehouse README](../../systems/azure-fabric/warehouse/README.md), [CODE](../../systems/azure-fabric/warehouse/CODE.md), and the actual [OMOP Foundation tasks](../../../openspec/changes/fabric-omop-foundation/tasks.md) while active.

## Dynamic Active Change index (read-only)

From a checkout of the intended commit (normally latest main), run:

```bash
python3 .github/quality/scripts/active_openspec_index.py --format markdown
python3 .github/quality/scripts/active_openspec_index.py --format json
```

This standard-library-only index discovers the **actual current** `openspec/changes/*/tasks.md` files and displays their checked/unchecked tasks. It excludes archived changes, shows UNKNOWN for incomplete task metadata and **does not write a new status file**. Results reflect the Git checkout's SHA and may lag unmerged PRs.

## Historical context (not current status)

The full pre-conversion text was preserved in [PROJECT-STATUS-HISTORY-20261105.md](PROJECT-STATUS-HISTORY-20261105.md) without removing any of its Run IDs, failure evidence or historical statements. This compatibility path remains stable for older links. Do not promote a dated snapshot to a live deployment or task completion claim.

Before shared-runtime work read [Safe Operations](../operations/SAFE-OPERATIONS.md) and [Session Coordination](../development/SESSION-COORDINATION.md). A list of unchecked tasks does **not** authorize running them.
