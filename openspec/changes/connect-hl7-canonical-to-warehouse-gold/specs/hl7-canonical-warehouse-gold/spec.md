## ADDED Requirements

### Requirement: HL7 Canonical Silver SHALL reuse the existing shared Candidate and Warehouse Gold implementation

The HL7-to-Gold handoff SHALL accept only authenticated, independently reopened
Canonical Silver Patient/Encounter and Approval state matching the immutable
HL7 hospital, feed, source, manifest, processing version, canonical contract,
zero-quarantine acceptance and parent-encounter reference integrity. It SHALL
delegate Candidate/Gold to the existing source-neutral Shared Engine and
Warehouse Writer without a second OMOP Mapper or SQL writer.

#### Scenario: Verified HL7 Canonical Silver advances to the existing Gold writer

- **WHEN** the trusted runner obtains two matching complete Silver physical readbacks, valid HL7 source/Batch/contract keys, and the single DQ-zero Silver Approval
- **THEN** the existing Candidate/Gold writer is invoked with its independent Candidate and Warehouse SQL readers, technical evidence and single-writer release fence

#### Scenario: Changed source or persisted Silver state is rejected without Gold DML

- **WHEN** either Silver observation, contract field, provenance identity, approval, patient/encounter key or foreign key differs
- **THEN** the handoff SHALL fail closed before invoking Candidate/Gold and SHALL NOT grant a write

#### Scenario: Gold acknowledgement and replay remain independently verified

- **WHEN** the existing writer cannot independently establish a successful SQL commit or the replay fingerprint
- **THEN** the handoff SHALL preserve the existing read-only reconciliation behavior rather than retry an unknown write
