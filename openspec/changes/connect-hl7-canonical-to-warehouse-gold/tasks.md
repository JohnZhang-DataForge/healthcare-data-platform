# HL7 Canonical Silver → existing Warehouse Gold

- [x] 1.1 Implement the HL7 source-bound Silver readback and Candidate/Gold handoff using the existing 0.1.17 Shared Engine and Warehouse writer; no new Mapper or SQL writer.
- [x] 1.2 Add synthetic DQ/source/FK/approval/replay/offline tests and a self-hosted GitHub Actions workflow.
- [ ] 1.3 Validate all required PR CI and naming gates, then merge `main`.
- [ ] 1.4 Resolve Fabric Git Environment identity safely without overwriting local Workspace resources, and confirm real Notebook and published Wheel readiness.
- [ ] 1.5 Run HL7 source → real Canonical Silver → shared Candidate → Warehouse Gold with independent SQL readback and idempotent replay; attach actual run evidence.

- [x] 1.6 Pin the reviewed HL7 ADT source-code → OMOP Standard Concept mapping as immutable, source-namespaced data. Add offline namespace/tamper tests. Real Warehouse Concept SQL validation remains required before Candidate publication.

- [x] 1.7 Independently re-read real HL7 4/8 Silver approval and both full Warehouse SQL identity snapshots with Shared Engine 0.1.17, read-only evidence: Self-Runner run 45035617569. This is not Candidate or Gold publication.

- [x] 1.8 Retire the never-published HL7 profile v1, which incorrectly used FHIR male/female labels; pin v2 to Parser's actual HL7 M/F values and enforce parser-to-profile tests before real Standard Concept SQL validation.
