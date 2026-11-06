# Tasks — Canonical-first shared architecture documentation correction

## 1. Verify current authority and evidence
- [x] 1.1 Compare latest main/open PR with approved 2026-10-30 Medallion ADR, 2026-10-31 Fabric-native ADR, shared ownership, Local DP code and existing Fabric G4/G5/F0–F2 proof.
- [x] 1.2 Identify stale current entry points and separate active FHIR transformation from proposed PostgreSQL snapshot product.

## 2. Repair human and agent navigation
- [x] 2.1 Reconcile current overall architecture overview, data flow, decision index and appropriate navigation links with two distinct cloud paths.
- [x] 2.2 Clarify source-specific adapters, same Canonical contract, one platform-neutral post-Canonical engine, per-platform physical writer; explicitly distinguish target sharing from current Local integration.
- [x] 2.3 Preserve historical evidence, accurately mark G4 Silver, F0/F1 schemas and vocab, G5 Candidate/Gold OPEN; no live mutations.

## 3. Verify and deliver
- [x] 3.1 Inspect complete changeset for link targets, stale claims, duplicate authorities and prohibited runtime/source changes.
- [ ] 3.2 Run applicable PR OpenSpec, document-link and trusted change checks; merge only if branch protections permit and update task evidence.

## Git-only verification (docs PR; no runtime operations)

- Base main pinned at `e384777a093a402449eac8dadadd46772bdcf92e`, no open PR at branching. The first branch diff has exactly 13 files: 9 existing Markdown entry points + 4 OpenSpec metadata/proposal/design/tasks; 0 source, SQL, test, workflow, runtime or Terraform files. New relative architecture links were inspected against existing CODE/ADR/Tasks paths; final automated markdown-link/strict OpenSpec checks must still run on the PR.
- Approved [2026-10-30 Medallion ADR](../../../documents/architecture/design/FABRIC-MEDALLION-CANONICAL-ADR-20261030.md) and [2026-10-31 Native ADR](../../../documents/architecture/design/FABRIC-NATIVE-NOTEBOOK-PIPELINE-ENVIRONMENT-ADR-20261031.md) are unchanged, as are immutable Local history and true G4/F0/F1/G5 evidence; updated current overview accurately distinguishes FHIR Bronze/Silver from future PG snapshot and keeps Candidate/Gold HOLDS.
