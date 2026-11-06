# Design — Canonical-first documentation reconciliation

## Authority order (must be visible to humans and agents)

1. Clinical/Medallion semantics: `documents/architecture/design/FABRIC-MEDALLION-CANONICAL-ADR-20261030.md`.
2. Runtime and one-wheel ownership: `documents/architecture/design/FABRIC-NATIVE-NOTEBOOK-PIPELINE-ENVIRONMENT-ADR-20261031.md` and `documents/engineering/development/SHARED-DATA-ENGINE-STRUCTURE-AND-OWNERSHIP.md`.
3. Current overview/data flow/architecture decision index: short navigation and evidence boundaries; no replacement or contradictory business contracts.
4. Current code/Contract/OpenSpec tasks and independently read-back artifacts determine implementation status.

## Data routes

- **Multi-source transform route (current Fabric FHIR MVP):** independently versioned source/entity adapter (CSV/FHIR/HL7) → shared Canonical Patient/Encounter v1 → Silver approved physical Delta → the **same** pure OMOP mapper, DQ, Concept validation, identity planning and reconciliation; source-specific, reviewed mapping profile is input data → Candidate → platform-native Gold Writer → independently verified COMMIT/SKIP.
- Local CSV→Canonical→Postgres is proven via legacy Local runtime; **do not claim** its full production runtime is already imported from `healthcare_data_engine`.
- Fabric FHIR→Canonical Silver is physically proven for synthetic G4 100 Patient/5918 Encounter; its actual Gold COMMIT is not yet proven. Fabric adapters and post-Canonical Candidate are implemented in the Shared Wheel 0.1.3, but the physical Candidate and Gold paths still have HOLDS.
- **Separate cloud analytical product (not current FHIR prerequisite):** Local PG17 CDM → read-only snapshot exporter (not yet implemented) → Blob → future Fabric analytical replica. No requirement to re-normalize already-conformed OMOP snapshot via Canonical.
- Clinical mapping profiles may differ for CSV, FHIR R4 and HL7 v2; their existence does not authorize a guessed concept_id, wrong Domain, unlicensed source, or implicit unknown-to-0 fallback.
- Identity preview is not Warehouse reservation. Commit only under a fenced, independently verified Warehouse transaction; PostgreSQL and Fabric physical writers must not share an unportable implementation.

## Document ownership and bounded edits

Revise `SYSTEM-OVERVIEW.md`, `DATA-FLOW.md`, `decisions/README.md`, root `documents/README.md`, and Local/Fabric/Shared README navigation; update root `AGENTS.md` only as needed to expose canonical-first read order. No source CODE maps or approved ADRs are moved/rewritten. Historical snapshot links stay immutable.

## Acceptance

Review current main/open PR first; verify every new relative link points to an existing source document; ensure no outdated "not deployed" assertion survives in current overview; confirm consistent terms for Silver approved, Candidate, Gold COMMITTED and PG snapshot; review PR diff and applicable OpenSpec/Markdown link/required GitHub checks before merge. Docs-only status must not imply real cloud tests.
