# Tasks — Fabric FHIR→OMOP handoff v1

## Part 1 — contract-first (this change)

- [x] 1.1 Cross-check G4/G5 real Silver approvals, exact request/Manifest, Warehouse F0 schema readback and both OpenSpecs.
- [x] 1.2 Freeze a v1 versioned Approved Silver envelope with source keys, row/Approval fence, physical target coordinates, canonical contract digest and replay semantics.
- [x] 1.3 Define namespace-scoped F1 identity, official Vocabulary and Warehouse-only Gold ownership without claiming these F1 dependencies are implemented.
- [x] 1.4 Implement no-network structural-only validator, negative/positive tests and offline PR CI; publish links in CODE-map/docs.
- [x] 1.5 Verify CI on reviewed PR and merge with latest main only after required checks; record observed PR run IDs.

## Part 2 — separately approved after OMOP Foundation F1 (NOT in this change)

- [ ] 2.1 Inspect real F1 `etl` Identity Map and official Concept/Vocabulary release; ratify join adapter and length/type constraints.
- [ ] 2.2 Adapt existing pure Candidate mapper for fully namespaced Warehouse-owned IDs; add negative cross-hospital/duplicate/invalid Concept tests without Local PG dependency.
- [ ] 2.3 Fabric Spark physical Delta Silver → Candidate staging, independent DQ/readback + replay; publish pinned Wheel before first cloud import.

## Part 3 — separately approved after F1/F2 (NOT in this change)

- [ ] 3.1 Warehouse F2 transaction and ledger integration, Person/Visit actual COMMIT, independent TDS readback and FK checks.
- [ ] 3.2 E2E FHIR-approved 100/5918 input, expected OMOP row reconciliation (not assumed 1:1 for Visit), replay verified SKIP and negative Quarantine refusal.
- [ ] 3.3 Record actual GitHub Actions and Fabric Job UUIDs; never infer Gold COMMITTED from Silver or a metadata-only PASS.

## Actual Stage-1 acceptance — 2026-11-03 ET

- [Healthcare PR #637](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/637) **merged** main SHA `d43985368fb9433dc5c1c3379ad6d678decde18f`, candidate head `06c4335167077f13972b1c16256ede3d8802a314`. All required contract/code/docs/OpenSpec gates passed on that head.
- [Stage-1 Python 3.11 and 3.13 No-Cloud Contract CI #41747597343](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41747597343) SUCCESS: source raw SHA and field contract, BatchContext identity, path derivation, DENIED/Quarantine negative, cross-hospital source isolation, replay classifier and no Gold authorization.
- [Shared Engine Wheel offline CI #41747597483](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41747597483) SUCCESS both Python 3.11/PySpark 3.5.7 and Python 3.13/PySpark 4.1.1. Wheel build/install compatibility is **not Fabric publish**.
- [OpenSpec Change Gate #41747597613](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41747597613), [OpenSpec Static #41747597426](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41747597426), [Component Code Naming #41747597479](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41747597479), [Documentation Relative Links #41747597349](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41747597349) and [Trusted OpenSpec #41747594529](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41747594529) SUCCESS.
- This **closes only Part 1**. Structural handoff tests are not real Fabric Delta readback or Warehouse Gold COMMIT. Independent OMOP F1 stable Identity Map and official Vocabulary remain incomplete; downstream Steps 2/3 stay unchecked and must have separate cloud acceptance.
