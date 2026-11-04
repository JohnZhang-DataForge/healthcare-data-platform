# Tasks — Fabric FHIR→OMOP handoff v1

## Part 1 — contract-first (this change)

- [x] 1.1 Cross-check G4/G5 real Silver approvals, exact request/Manifest, Warehouse F0 schema readback and both OpenSpecs.
- [x] 1.2 Freeze a v1 versioned Approved Silver envelope with source keys, row/Approval fence, physical target coordinates, canonical contract digest and replay semantics.
- [x] 1.3 Define namespace-scoped F1 identity, official Vocabulary and Warehouse-only Gold ownership without claiming these F1 dependencies are implemented.
- [x] 1.4 Implement no-network structural-only validator, negative/positive tests and offline PR CI; publish links in CODE-map/docs.
- [ ] 1.5 Verify CI on reviewed PR and merge with latest main only after required checks; record observed PR run IDs.

## Part 2 — separately approved after OMOP Foundation F1 (NOT in this change)

- [ ] 2.1 Inspect real F1 `etl` Identity Map and official Concept/Vocabulary release; ratify join adapter and length/type constraints.
- [ ] 2.2 Adapt existing pure Candidate mapper for fully namespaced Warehouse-owned IDs; add negative cross-hospital/duplicate/invalid Concept tests without Local PG dependency.
- [ ] 2.3 Fabric Spark physical Delta Silver → Candidate staging, independent DQ/readback + replay; publish pinned Wheel before first cloud import.

## Part 3 — separately approved after F1/F2 (NOT in this change)

- [ ] 3.1 Warehouse F2 transaction and ledger integration, Person/Visit actual COMMIT, independent TDS readback and FK checks.
- [ ] 3.2 E2E FHIR-approved 100/5918 input, expected OMOP row reconciliation (not assumed 1:1 for Visit), replay verified SKIP and negative Quarantine refusal.
- [ ] 3.3 Record actual GitHub Actions and Fabric Job UUIDs; never infer Gold COMMITTED from Silver or a metadata-only PASS.
