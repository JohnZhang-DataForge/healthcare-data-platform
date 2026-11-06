## Directory review baseline — exact main

- Main commit: `bf18e65eb593dd5cc75988bdcc692c100cc3044a` (2026-11-05). Tracked files 1,239; Azure Fabric 210; Local DP 440; Portal 52; Shared Engine 21; Documents 104; OpenSpec 297; .github 112.
- Legacy Local DP task-/step-named directory files: 223, spanning apps/scripts/spark/sql/Kubernetes/tests. Their physical paths are operationally referenced and must not be renamed as a single cosmetic task.
- Nine source-area README.md remain: six Local DP and three Portal. Existing scoped `shared-data-engine/AGENTS.md` must stay beside source.
- Thirty-five active OpenSpec tasks; five with zero unchecked tasks are candidates for **evidence-based** archival, not automatic acceptance.

## Human-first target

```text
AGENTS.md                         # Root agent policy
README.md                         # Portfolio overview + simple code navigation
local-data-platform/              # On-prem Airflow / Spark / OMOP production sources; legacy task paths held until compatibility
azure-fabric/                     # native Fabric Git, business source, deployment assets, Terraform
platform-portal/                  # lineage / Marquez / public Web implementation
shared-data-engine/              # one shared Python wheel and scoped AGENTS
documents/                        # all human-oriented authoritative documentation
  systems/{data-platform,azure-fabric,platform-portal}/  # paired README/CODE by component
  engineering/development/       # directory model and compatibility policies
openspec/{specs,changes,changes/archive}/       # adopted, truly active, completed
.github/{workflows,quality}/       # CI / tests / source guards
```

## Physical move criteria

1. Document exact source blob IDs, current `main`, owners and cross-repo references first.
2. Prefer byte-identical relocation of human README content into docs with functional relative links; keep `AGENTS.md` in actual scope.
3. For Local DP task paths, require a consumer registry across Healthcare workflows, Self-Runner, Airflow DAGs, Python import paths, image build contexts, Helm/K8s/SQL, operational scripts and read-only contracted evidence. First merge dual-read compatibility; then move one bounded function at a time; run relevant offline/real system tests; only then retire old paths.
4. Never substitute a symlink/duplicate code tree for real migration. Legacy paths still required by a live consumer must remain explicitly documented as an exception; do not claim the entire tree is canonical before that phase is complete.
5. Protect existing trusted policy, 185-entry legacy baseline and GitHub Ruleset. New governance policy must use separately authorized trusted route and verified negative blocking.
6. Preserve archival history and link integrity. Fixed-SHA source evidence is referenced as immutable Git history, not rewritten as present-day source.

## Acceptance

Zero incorrect active docs links. All three Required Checks SUCCESS. No unrelated source/runtime blob changes. Current `main` independently checked after each merge. Live Azure/K8s/PG/Marquez writes remain out of scope.
