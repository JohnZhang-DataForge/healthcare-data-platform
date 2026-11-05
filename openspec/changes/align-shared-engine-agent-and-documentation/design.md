## Context and decision

Keep directory-scoped AGENTS beside code for coding-agent discovery; keep human-facing README, CODE and BUILD-AND-TEST centrally. The source README is a frozen historical file, so delete only after preserving unique procedures and fixing links.

## Canonical owners

- `shared-data-engine/AGENTS.md`: stable Agent constraints only.
- `documents/systems/data-platform/shared-engine/README.md`: role, boundaries, reality-based capability and evidence.
- `documents/systems/data-platform/shared-engine/CODE.md`: unique links to live source/test/contract/workflow.
- `documents/systems/data-platform/shared-engine/BUILD-AND-TEST.md`: offline setup, reproducible wheel and Handoff procedures.

## Version evidence

Source version `0.1.3` comes from pyproject and offline Run #41827968535; Fabric Published 0.1.3 from Self-Runner #41834029745; isolated Spark 4.1 import from #41835694167. None of these establish business `nb_fhir_ingest`/OMOP Gold COMMIT.

## Compatibility and testing

Keep legacy `shared-data-engine/tests/`, `src/`, `contracts/`, pyproject, native Wheel, CI workflows and frozen baseline untouched. The Git root-tree SHA changes for docs alone; fixed-tree historical Wheel staging workflows must not be mistaken for current new release evidence. Check real docs links, CODE map and applicable OpenSpec/Required rules. No runtime or cloud operations.
