# HL7 Canonical Silver → existing Warehouse Gold

- [x] 1.1 Implement the HL7 source-bound Silver readback and Candidate/Gold handoff using the existing 0.1.17 Shared Engine and Warehouse writer; no new Mapper or SQL writer.
- [x] 1.2 Add synthetic DQ/source/FK/approval/replay/offline tests and a self-hosted GitHub Actions workflow.
- [ ] 1.3 Validate all required PR CI and naming gates, then merge `main`.
- [ ] 1.4 Resolve Fabric Git Environment identity safely without overwriting local Workspace resources, and confirm real Notebook and published Wheel readiness.
- [ ] 1.5 Run HL7 source → real Canonical Silver → shared Candidate → Warehouse Gold with independent SQL readback and idempotent replay; attach actual run evidence.
