# OpenSpec Adoption Plan — Healthcare Data Platform

Status: PHASE 1 IN PROGRESS (bootstrap branch; NOT merged)
Owner repositories:
- Code and OpenSpec: `JohnZhang-DataForge/healthcare-data-platform`
- Execution and evidence: `JohnZhang-DataForge/Self-Runner`
- `JohnZhang-DataForge/Healthcare-Specs`: reserved for future shared governance; not an active spec source.

## Core boundaries
1. One authoritative set of project specs in this code repository at `openspec/specs/`; no duplicate specs in Healthcare-Specs.
2. Existing `docs/` stays intact. Do not bulk import conflicting legacy documents as authoritative specs.
3. Existing business logic, Airflow DAGs, Spark jobs, infrastructure and deployed services must not change in the bootstrap phase.
4. No CLI installation or workflow runtime mutation should be assumed successful without execution evidence.
5. A task checkbox is not a proof of merged code, live deployment or test success. Associate evidence with an exact SHA.
6. Respect current mainline PR/SHA/Self-Runner validation, user approvals and shared cluster coordination rules.

## Implementation phases

### Phase 1 — Minimal project bootstrap
- [x] Review repository layout and current authoritative documentation entrypoints.
- [x] Create isolated `feature/openspec-bootstrap-20261016` from a recorded main SHA.
- [x] Add `openspec/config.yaml` and empty, version-controlled `specs/`, `changes/` and `changes/archive/`.
- [ ] On a runner with npm access, run supported OpenSpec CLI initialization/integration checks and record exact CLI version/output.
- [ ] Review changes and merge a documentation-only PR after validation.
Acceptance: OpenSpec CLI recognises project; only bootstrap docs/config files changed; current main branch untouched until approved merge.

### Phase 2 — Evidence-backed baseline specs
- [ ] Audit top-level architecture, TASK status and current source code; classify implemented vs proposed vs historical.
- [ ] Establish the first baseline specs for Synthea Generator, Airflow S3 consumer, Person/Visit, and OMOP Writer using verified evidence.
- [ ] Link each baseline spec to source paths, test evidence and exact source SHA; resolve contradictions explicitly.
Acceptance: a new Agent can identify the current verified behavior without treating historical docs as current.

### Phase 3 — Agent-driven change pilot
- [ ] Choose a small approved change; generate proposal, delta specs, design and tasks.
- [ ] Run a limited multi-step experiment, persist evidence, then resume from a fresh Agent session.
- [ ] Validate and archive only after the implementation is accepted.
Acceptance: Agent can correctly resume without conversational memory and distinguish task state from actual evidence.

### Phase 4 — Self-Runner verification integration
- [ ] Reuse an existing runner pattern if suitable; otherwise add a minimal dedicated read-only validation entry.
- [ ] Pin tool version, validate OpenSpec files, report Git SHA and status; never expose arbitrary shell injection.
- [ ] Keep business mutations and auto-merge disabled for these checks.
Acceptance: a repeatable SHA-bound GitHub Actions PASS/FAIL report.

### Phase 5 — Incremental documentation drift governance
- [ ] Map changed source paths to specs and affected legacy docs.
- [ ] Start with advisory reports and reviewable PR suggestions (no automatic authoritative changes).
- [ ] Add stronger gates only after measured false-positive and workflow impact review.
Acceptance: drift detected with citations/paths and traceable reconciliation decisions.

## Working with an AI Agent
Users may describe desired changes in natural language. The Agent proposes updates to OpenSpec artifacts, identifies impacts, maintains tasks, uses the existing PR/SHA and test workflow, and hands off reproducible checkpoints. For architecture-changing or destructive actions, request approval. Do not silently archive or claim live validation from files alone.

## Phase 1 verification recipe (execute later in a suitable runner)
```bash
node --version                         # Node >= 20.19.0
npm install -g @fission-ai/openspec@latest
openspec --version
openspec init --tools none             # CLI only; no local agent required
openspec list
openspec validate --all
git status --short
```
If the CLI reports no changes/specs yet, that is expected before Phase 2.
Record command output, tool version, branch and exact SHA as acceptance evidence.
