# Design — Prevent development-number identifiers from re-entering source

## Verified baseline

2026-11-13 Healthcare main started at `f790c0610c934072c6512520ea220994f0f9daa1`. Self-Runner main rechecked before work. Existing Healthcare `check_new_code_names.py` and protected `check_new_source_structure_trusted.py` detect only `task/step` in added file paths. The latter rejects its own modification in ordinary PRs. Ruleset #25365902 currently requires four checks but NOT the existing advisory `Component Code Naming` job.

## Implementation

1. Use one source-only scanner over Git candidate diff `--unified=0`: reject added forbidden file paths; reject **new declarations** of Python functions/classes/variables and public status/schema/identifier assignments using project phases; reject newly introduced named YAML Workflow/jobs and shell identifiers. Existing code references and untouched lines remain readable, not auto-renamed.
2. Project stages: segment `G0-G9`, `P0-P9`, `F0-F9`, `B0-B9` and `taskNNN/stepNNN`. These are project planning names, not stable runtime concepts. Permit FHIR R4, HL7 v2, package `v3`, OMOP 5.4 and real batch quantities such as P100. Formal exceptions must have reviewed, explicit semantic justification, not blanket ignore by directory.
3. Add negative tests for newly added G5 module names, modified Notebook `_g5_` declaration, F2 field, B4 status, YAML pipeline name; positive tests for standards, old references, unaffected files, legacy runtime compatibility.
4. Attach to Healthcare current advisory naming workflow. **Do not modify** the protected trusted checker or impersonate its required context. For complete enforcement, a future separately approved governance operation must update the trusted default-branch policy under protection and include its status in GitHub Ruleset.
5. Mirror Self-Runner checker and CI; do not rely on Healthcare governance crossing GitHub repository boundaries.

## Safety and rollout

Static Git/file-text validation only, no execution of candidate code, cloud secrets, deployment or writes. The new checker scans source declarations, not arbitrary prose. Since the scanner is new, record limitations: dynamic generated identifiers, all possible languages and multiline protocol construction need further coverage. If a required status is not registered in Ruleset, report it as pending, not complete.

## Rollback

Revert advisory scanner, test and workflow via reviewed PR if it yields false positives; keep existing required branch protections intact. Never disable a required check or loosen previously approved legacy protections to get a green build.
