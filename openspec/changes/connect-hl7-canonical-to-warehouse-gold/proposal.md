# Connect HL7 Canonical Silver to the existing Warehouse Gold writer

## Why

HL7 Parser, Delta, dbt and Canonical Candidate have an independently tested local
handoff, and the Fabric Notebook already contains an HL7 Silver publisher.
The existing FHIR route has demonstrated physical Candidate/Gold readback and
idempotent Warehouse replay on Shared Engine 0.1.17. HL7 must reuse that same
Candidate/Gold integration without creating a separate Mapper, ID allocator,
clinical signoff or SQL writer.

## Scope

- Add an HL7 source-bound handoff from authenticated Canonical Silver physical
  readback to the existing Candidate/Gold transaction.
- Verify source provenance, pinned canonical contract, patient/encounter FK,
  approval-last DQ=0 and two complete independent Silver observations.
- Reuse existing physical Candidate and SQL readback/COMMIT/replay implementation.
- Add synthetic offline regression and execute it on existing ARC runners.

## Explicit non-goals

This source-only change does not alter the Workspace Git connection, publish an
Environment, execute a Notebook, authorize Fabric/OIDC writes, claim real
Silver/Gold success, or reintroduce clinical/license signatures.
