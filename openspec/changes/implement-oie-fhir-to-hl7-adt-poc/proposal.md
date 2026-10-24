# Proposal — Johns Creek FHIR-to-HL7 ADT PoC with Eclipse OIE

## Why

`synthea_new_generator` has independent, accepted FHIR R4 output. Johns Creek needs a
separate OIE-based **actual clinical event transformation**, not a format rename
or a generator-internal branch. The Atlanta FHIR and existing Local DP/OMOP
paths must remain unaffected.

## Scope

- A small versioned FHIR Bundle → ADT^A01 proof, including documented skip/reject
  behavior for encounters without admission evidence and independent HL7 v2.5.1
  parse/readback.
- Eclipse Open Integration Engine 4.7.0 single instance, Docker image produced
  from an official versioned release artifact (not an assumed Docker Hub latest).
- `dw-oie` dedicated namespace; **all OIE Pods scheduled to worker01**,
  separate persistent state volume, no extra external database in PoC.
- Versioned handoff from separate Johns Creek `synthea_new_generator` source.
- Offline and real OIE runtime evidence before declaring conversion accepted.

## Exclusions / operational safety

No Azure Blob publication yet, no Fabric, Kafka, shared cohort crosswalk,
external production hospital data, Local DP NEW_ONLY edits, OMOP DB writes,
existing PVC changes, or deployment without coordinated shared K8s authorization.
Blob Publisher and per-hospital delivery follow separate implementation Changes.

## Success definition

Actual pinned OIE release and channel run on real FHIR Bundle, appropriate
A01 events verified after parsing output, stable MSH-10 across retries,
unsupported/invalid encounters never mislabeled as admissions, and exact
runtime image, worker01 placement, namespace, readback and Run IDs recorded.
