# OIE FHIR to HL7 v2 ADT Conversion (PoC)

## ADDED Requirements

### Requirement: OIE converter is independent of Synthea generation and legacy OMOP

The Johns Creek producer SHALL consume independently verified FHIR R4 from
the parameterized Generator through an external handoff and SHALL map events
using a dedicated OIE Channel. Neither the Generator nor the legacy Local DP
OMOP path shall be changed by this integration.

#### Scenario: OIE unavailable
- **GIVEN** a validated immutable source Request and FHIR Bundle
- **WHEN** OIE is unavailable
- **THEN** local source remains valid and unchanged; no HL7 or Blob success is declared

### Requirement: ADT^A01 is emitted only for proven inpatient encounters

The OIE PoC SHALL emit HL7 v2.5.1 ADT^A01 only for eligible FHIR R4
Encounter.class IMP, valid Patient link, valid admission start and
in-progress/finished status. All control and visit identifiers SHALL be
deterministic and scoped to source hospital/feed/request.

#### Scenario: Verified inpatient encounter
- **GIVEN** a real FHIR Bundle with a qualifying inpatient Encounter
- **WHEN** the versioned OIE Channel processes it
- **THEN** MSH/EVN/PID/PV1 fields parse correctly and the MSH-10 is stable on retry

#### Scenario: Outpatient or not-yet-admitted encounter
- **GIVEN** only AMB/EMER/OBSENC or cancelled/planned Encounters
- **WHEN** processed
- **THEN** no A01 is emitted and counted skips are auditable

#### Scenario: Invalid data
- **GIVEN** a broken Patient reference, missing admission time or duplicate identity
- **WHEN** the event mapping is evaluated
- **THEN** OIE rejects the malformed candidate rather than inventing a visit

### Requirement: OIE runtime is isolated on worker01

OIE PoC workload SHALL run only in `dw-oie` on `worker01`,
using a distinct persistent state volume, nonpublic admin access, and a
version-pinned verified image. The initial PoC SHALL use bundled Derby
instead of deploying an additional external database.

#### Scenario: Deployment pending approval
- **GIVEN** no completed cross-session resource gate or no shared-runtime approval
- **WHEN** a deployment is requested
- **THEN** only static definitions may be reviewed; no live Namespace/PVC/Pod is created
