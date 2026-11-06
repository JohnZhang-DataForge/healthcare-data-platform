# Operational HL7 v2.5.1 ADT Producer

## ADDED Requirements

### Requirement: Source-scoped admission and discharge event lifecycle
The OIE HL7 Producer SHALL generate HL7 v2.5.1 ADT^A01 admissions only from source-verified inpatient Encounter.start; SHALL generate ADT^A03 discharge only if the Encounter is finished with a valid sourced Encounter.end; SHALL preserve source-scoped Patient/Visit identifiers and deterministic per-event MSH-10.

#### Scenario: Completed inpatient Encounter has two distinct events
- **GIVEN** one approved synthetic source Patient and finished inpatient Encounter with sourced start and end
- **WHEN** the versioned OIE producer evaluates the source event
- **THEN** it emits independently addressable ADT^A01 and ADT^A03 with distinct deterministic MSH-10 and consistent PID-3/PV1-19, and A03 includes sourced PV1-45.

#### Scenario: In-progress admission is not fabricated as discharge
- **GIVEN** a valid in-progress inpatient Encounter with a start but no end
- **WHEN** the versioned OIE producer evaluates the source
- **THEN** only A01 is eligible and no discharge time or A03 is invented.

### Requirement: Clinical facts required by current Canonical contract are source-provenanced
The versioned HL7 Producer MUST source PID-7/8/10/22 from validated patient facts and approved mapping profile, and MUST fail closed on absent, unknown, invalid or contradictory required facts instead of fabricating gender, race, ethnicity or dates.

#### Scenario: Demographic fact missing
- **GIVEN** an otherwise valid inpatient Encounter whose Patient lacks a required verified birthDate or mapped demographic extension
- **WHEN** the producer tries to build a Canonical-v1-compatible ADT event
- **THEN** it HOLDs or rejects the event with a typed reason and does not publish an approved HL7 message or a fake value.

### Requirement: Raw HL7 payload and delivery evidence are immutable and independently verified
The HL7 Publisher MUST publish raw HL7 bytes, source identity, per-event SHA256/length and a manifest-last readiness boundary; MUST independently read back published objects before any delivery success statement; same request/version replay MUST SKIP without duplicate objects, and conflicting same request IDs MUST HOLD.

#### Scenario: Same batch replay after verified delivery
- **GIVEN** an already published batch with verified source/processing SHA and immutable object metadata
- **WHEN** the same batch is submitted again
- **THEN** it does not overwrite objects, records SKIP and preserves the existing publication evidence.

#### Scenario: Source batch conflicts with immutable bytes
- **GIVEN** the same source request identity and a different source object checksum
- **WHEN** a publisher receives this conflicting request
- **THEN** it quarantines or holds the request without overwriting the approved payload.

### Requirement: Legacy OIE deployment and shared silver remain protected
The operational HL7 implementation MUST NOT alter existing accepted OIE Channel/Derby/PVC/history or claim live OIE/Blob/Fabric results before independently evidenced, authorized operations; downstream Parser/dbt Adapter MUST produce a Contract-gated Candidate rather than writing directly to Approved Silver.

#### Scenario: Offline development is not runtime acceptance
- **GIVEN** CI unit tests and Channel XML generation succeed on synthetic data
- **WHEN** the developer publishes the implementation PR
- **THEN** status is SOURCE or STATIC_PASS only until OIE physical runtime, Blob GET/readback and single Silver Publisher are separately accepted.
