## Why

The repository has 1,239 tracked files across seven meaningful source/governance roots. Top-level categories are mostly coherent, but human browsing remains hard: 223 legacy `taskNNN/`/`stepNNN/` directory files in Local DP, nine remaining source-area README copies, long time-ordered component README histories, stale source paths in root policy, and 35 Active OpenSpec changes including five with no unchecked tasks.

Existing machine-readable rules reject some new bad paths, but they do **not** guarantee that a human can understand ownership and project scope from a GitHub folder tree. Human-readable information architecture is an explicit goal, not optional cosmetics.

## What Changes

- Establish a permanent human-first directory taxonomy, with target ownership, exceptions, and a verified inventory before further physical moves.
- Improve GitHub root navigation and repair stale cross-system path assertions, without changing source or production configuration.
- Centralize existing source-area human README files in their owning `documents/systems/` component, retaining unique content and exact historical provenance.
- Archive independently verified, fully accepted OpenSpec changes so `changes/` contains actual active work instead of finished history.
- Assess and prepare bounded, role-based Local DP `taskNNN` migration: immutable evidence/consumer inventory, old+new path compatibility, independent runtime/CI protection **before** any physical deletion. Do not break deployed DAGs, scripts, K8s image paths or fixed-SHA workflows.
- Ensure quality checks and CODE maps keep the human-readable taxonomy stable for new work.

## Capabilities

### Modified Capabilities
- `repository-human-navigation-and-source-ownership`: root/system/legacy paths must be intuitively discoverable, and migrations have explicit compatibility and evidence gates.

## Impact

Phase 1 is docs/Git governance only, phase 2 moves human Markdown with link rewrites, phase 3 archives accepted OpenSpec history. **No unverified batch moves** of Local DP executable code. Source identities, Contracts, Native Fabric Items, SQL, live systems and running deployments are frozen until separate verification.
