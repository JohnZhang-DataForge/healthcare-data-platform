# Proposal — Unify FHIR / HL7 G5 Technical Admission

## Why

The user has explicitly removed the requirement for **two distinct human Clinical / License reviewers** for this personal synthetic-data platform. The Shared Engine already has one source-neutral technical contract for FHIR_R4 and HL7_V2, while independently developed FHIR and HL7 source adapters, an existing guarded Silver Writer, Candidate/Gold technical branches and F1 governance have different completion states. Planning two separate "remove human double-signoff" implementations would duplicate authority and risk drift. Conversely, an offline code test does not establish protected release, licensed vocabulary rights or actual cloud publication.

This is a **cross-workstream, design-only coordination change**. It records the audited current implementation, explicit ownership, one contract and the ordered dependency gates. It must not silently overwrite the active source-specific G5 / HL7 / F1 OpenSpecs or authorize cloud work.

## What Changes

- Adopt **one** Shared G5 technical evidence + Stage admission policy for FHIR_R4 and HL7_V2, after source-specific ingress and Canonical/approved Silver boundaries. Remove mandatory Clinical/License **human quorum**, not the real F1/F2, Concept, source provenance, legal code-set rights, idempotency or physical readback gates.
- Reuse the already merged Shared Engine 0.1.13 transport v3 / target-concept-v2, Native Candidate technical path, GoldBatch technical path, Native Silver single guarded Writer and HL7 local Delta/dbt bridge; **do not rebuild them**.
- Track remaining critical integration: F1 obsolete human-quorum strings and missing nine-file provenance, protected machine attestation + independently pinned TrustedTechnicalScope, Stage release callbacks and durable nonce/claim, New Batch FHIR/HL7 Native physical acceptance, version-isolated 0.1.13 Fabric runtime, and actual Candidate/Gold acceptance.
- Freeze file ownership to prevent simultaneous G5 Notebook / Shared edits by independent FHIR and HL7 sessions; integrate both by conformance tests against the same contract.
- Keep old reviewer-based signatures/receipts as **legacy compatibility only**. Never populate fake clinical/permission approvals.

## Capabilities

### Proposed future capabilities (NOT yet live)

- One source-neutral, protected G5 technical admission controller for accepted FHIR and HL7 Canonical Silver and independent stage-specific release.
- One Candidate/Gold proof and replay protocol with format-specific ingress, no duplicate Mapper, identity engine, SQL F1/F2 reader, Silver or OMOP Writer.

### Scope of this proposal

This OpenSpec has skip_specs: true because **this PR changes documentation only**, not a runtime or enforceable new API contract. Functional code, CI and live acceptance must be implemented in separate, scoped PRs and evidenced in the existing owning changes.

## Impact and exclusions

Repositories: JohnZhang-DataForge/healthcare-data-platform (design authority, Shared, Native Notebook, Gold and source adapters) and JohnZhang-DataForge/Self-Runner (evidence collector, trusted Controller, stage orchestration and real jobs).

No changes now to existing raw messages, Blob, Azure, Fabric capacity, published 0.1.7 wheel, local PostgreSQL, ATLAS, OIE feeds, cloud credentials, Candidate or Gold tables. No HL7 -> FHIR conversion, new Processing cache/ledger/container, second universal OMOP mapper, new permanent writer or artificial licensing approval.

## Rollback

Remove this design-only coordination change if superseded. No production rollback is necessary because no runtime state, secrets, cloud data or permissions are modified.
