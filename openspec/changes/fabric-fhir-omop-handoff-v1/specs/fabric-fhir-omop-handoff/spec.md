## ADDED Requirements

### Requirement: Versioned, single-source Approved Silver handoff

The system SHALL expose an immutable, versioned contract that references an existing request-scoped G4 Patient and Encounter Silver Delta pair and one exact Approval fence. It SHALL pin the logical source identity, delivered Manifest SHA, processing version, stable source-batch identity, original canonical v1 raw hashes and physical Fabric target IDs.

#### Scenario: Approved matching physical Silver

- **GIVEN** independently reopened physical Delta Patient, Encounter and single Approval row from the same request and processing path
- **WHEN** their source identity, SHA, row counts, zero Quarantine, source preservation and publication identity match the contract
- **THEN** the handoff MAY be used as eligible read-only data for a subsequent explicitly authorized OMOP Candidate process, and MUST NOT be labeled Gold COMMITTED.

#### Scenario: Failed approval, drift, inconsistent namespace or malformed envelope

- **GIVEN** a missing, duplicated, HOLD/DQ/denied Approval row, a changed Manifest SHA, mismatch between Patient and Encounter source namespace, a different processing hash or any untrusted path
- **WHEN** the handoff is evaluated
- **THEN** it SHALL fail closed before requesting an OMOP Candidate or Warehouse Gold write.

### Requirement: Fully scoped persistent Fabric identity

The system SHALL use composite source Patient identity `(hospital_id, feed_id, raw_source_system, source_record_id)` and source Visit identity `(hospital_id, feed_id, raw_source_system, source_encounter_id)`. Person and Visit OMOP ID allocation SHALL be owned by the independent Fabric Warehouse F1/F2 service, not by FHIR Silver/Local DP.

#### Scenario: Same source ID in two hospitals

- **GIVEN** two different hospitals emit equal source Patient or Encounter IDs
- **WHEN** the OMOP Consumer resolves stable identities
- **THEN** the implementation MUST preserve the hospital/feed namespace, reject an unscoped join and never silently merge those records.

### Requirement: Vocabulary and Candidate/Gold separation

The system SHALL require an independently pinned official Vocabulary release and exact Concept lookup before OMOP mapping, and SHALL treat Candidate stage, Warehouse Gold transaction and physical readback as separate gates.

#### Scenario: No F1 identity or Vocabulary release

- **GIVEN** Approved Silver exists but the Warehouse-managed ID Map, source-scoped adapter or Vocabulary version has not passed real validation
- **WHEN** FHIR and OMOP integration is requested
- **THEN** the system SHALL HOLD the real candidate/writer execution without inventing numeric IDs or clinical Concepts.

### Requirement: Structural validation is not evidence of data presence

The pure interface validator SHALL perform offline schema, namespace, hash, path and Approval-metadata consistency checks without network/Blob/Spark/SQL access. It SHALL never claim to have independently read Delta, committed Warehouse rows or validated the real Concept release.

#### Scenario: Well-formed envelope alone

- **GIVEN** a syntactically and logically valid envelope
- **WHEN** the pure validator runs offline
- **THEN** it SHALL return only `STRUCTURAL_PASS_PHYSICAL_READBACK_REQUIRED` and MUST require a separate physical Silver readback before any later approved runtime action.
