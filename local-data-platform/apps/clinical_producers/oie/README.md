# OIE Clinical ADT^A01 Source Mapping (PoC Code Template)

The source file `adt_a01.js` is an **ES5-style OIE channel JavaScript Code
Template candidate**, built to avoid Node-specific behavior. Invoke its
`fhirToAdtA01(bundle, config)` function from an OIE JavaScript
transformer/destination after the source connector has accepted **one**
independently validated FHIR Bundle. The result returns individually
framed HL7 v2.5.1 messages and skip counts; it does **not** write files.

`config` must carry `hospital_id`, `feed_id`, frozen `request_id`,
and a synthetic `assigning_authority`. The caller owns the configuration
and verifies the source-handoff manifest; there is no hospital-specific
branch in Synthea itself.

The current implementation emits A01 **only** for
`Encounter.class` coding `v3-ActCode/IMP` with
`status=in-progress|finished`, resolvable Patient, and a valid
`period.start`. A finished Encounter indicates a historical admission
at that start time. AMB/EMER/OBSENC, planned or cancelled events skip.
Malformed candidate admissions block conversion. MSH-10 is stable and
source scoped. The Pure-Function result uses `MAPPING_VERIFIED_ONLY`.

**Do not treat this as an OIE importable channel or a deployed converter.**
The exact OIE 4.7.0 Channel XML configuration/connector bindings,
real parsing of OIE output, authenticated HTTP input, persistent destination
spool and K8s worker01 placement are tracked by OpenSpec 2.2–2.5.
No external DB, Kafka, Blob or Fabric work is included in this unit test.
