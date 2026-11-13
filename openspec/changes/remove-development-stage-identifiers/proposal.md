# Proposal — Replace development-stage names with business names

## Why

The source uses temporary project progress markers (G3/G4/G5, P2/P3, F1/F2, B2/B4 and taskNNN) in source declarations, cross-repository script paths, published protocol/schema identifiers and historical evidence. Existing semantic naming gate prevents many new occurrences but does not refactor existing code. Blanket replacement would invalidate signed bytes, cross-repo imports, frozen run receipts and Fabric Notebook/Wheel compatibility.

## What Changes

- Inventory and classify each changed symbol/path as internal-only, cross-module/runtime-facing, or persisted/signed contract.
- Replace private Python helper names with capability-first names using exact reference inventories, tests and a source-only PR.
- Transition public module/entrypoint names with compatibility adapters and verified consumers before any old name retirement.
- Version external status/schema/protocol changes separately, preserving legacy byte-for-byte verification and fail-closed behavior.

## Scope / exclusions

This proposal introduces no new business behavior or external wire contract, so `skip_specs: true`. This Change is an implementation/refactor task ledger. Existing functional OMOP, FHIR, HL7, Silver/Gold specs remain authoritative; no Fabric/Blob/K8s/database run is authorized by a naming refactor.

## Critical invariants

FHIR and HL7 remain separate source adapters converging on one Canonical + Shared Engine. Do not reintroduce required Clinical/License dual-human signatures. The HALT/source-only modes, Stage Controller authority, Replay/nonces, Candidate/Gold Writer authorization and readback must be preserved.
