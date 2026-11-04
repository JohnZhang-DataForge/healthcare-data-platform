# Proposal — FHIR Approved Silver → Fabric OMOP handoff v1

## Why

G5 FHIR Pipeline has real cloud proof of the accepted G4 Silver Delta readback (100 Patients, 5,918 Encounters, 0 Quarantine), but **no physical OMOP handoff contract** currently binds that source approval to the independent Fabric OMOP Foundation. The separate OMOP Agent already deployed the 39-table/432-column OHDSI 5.4 empty Warehouse base schema, but its Fabric-owned Identity Map and approved Vocabulary are still F1 work. A Git merge or Pipeline Completed is neither a Gold commit nor an authorization to write.

Local PostgreSQL and Local DP are independent runtime systems. Existing G5 Candidate code's injected Person ID map uses `source_system/source_person_id`; the cross-hospital/cross-feed scope and Warehouse-controlled ID allocation must be explicit before integration.

## What changes

- Introduce **one versioned, platform-neutral, machine-readable interface contract** for G4 Approved Silver Patient/Encounter + independent Approval fence, complete request/Manifest/batch/processing provenance, scoped patient/encounter keys and downstream F1 handoff obligations.
- Introduce a **pure, no-network/no-Spark/no-Warehouse-write envelope validator** and negative tests. Structural validation MUST be explicitly weaker than actual Delta physical readback.
- Link the exact existing canonical v1 raw-hash authorities, **without copying or modifying** the Local DP contract sources and without allowing Local Postgres reads.
- Freeze Fabric Workspace/Lakehouse/Warehouse physical IDs, trusted G4 processing path derivation, immutable versioned mapping/profile/identity/vocabulary requirements and Candidate-vs-Gold boundaries.
- Hand the contract to the separate OMOP Foundation workstream; F1 implements ID/Vocabulary and F2/F3 later enable new reviewed Candidate/Gold write and E2E run.

## Scope / impact

Only `shared-data-engine/contracts`, pure model validation/tests, OpenSpec, offline CI and G5 Fabric CODE-map docs. **No Fabric Notebook/Pipeline, Azure Blob, Delta, Warehouse DDL/DML, Self-Runner deployment, Local DP or credential mutations** in this change.

## Rollback

Revert this versioned source/validator/CI change; published Silver and Warehouse schema remain unchanged. v1's semantic meaning is immutable; breaking contract changes require v2 with a separate migration.
