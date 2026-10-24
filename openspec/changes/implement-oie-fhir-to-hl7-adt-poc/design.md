# Design — minimum Eclipse OIE ADT PoC

## Verified upstream and OIE choice

- Generator's immutable source state is `SOURCE_GENERATED_VALIDATED`.
- P4.1 external verifier emits `SOURCE_HANDOFF_VERIFIED` after rechecking
  request, source files and manifest; this is **not a Blob publication receipt**.
- OIE 4.7.0: upstream announcement 2026-10-21, MPL 2.0. Official 4.7.0
  release announcement explicitly states **it does not publish a Docker image**.
  Official Docker Hub `latest` is not acceptable as a 4.7.0 pin. Verify
  SHA256 of official release tarball and construct own pinned, provenance
  labeled image; record registry Digest and `oie --version`/startup proof.
  Sources: https://openintegrationengine.org/news/oie-4-7-0/ ,
  https://www.openintegrationengine.org/downloads/ ,
  https://github.com/OpenIntegrationEngine/engine-docker .
- OIE requires Java 17+, comes with embedded Derby for the PoC. OIE 4.7.0
  initial admin password **must not** assume admin/admin; configure a Secret
  before first start, do not log credentials. No optional Web Administrator
  required for PoC.

## K8s topology

```text
dw-synthea / worker01                         dw-oie / worker01
Generator (existing immutable FHIR PVC)          one OIE Pod
      |                                             |
source_handoff readonly verification              ClusterIP HTTP Listener
      |--------- scoped HTTP input (FHIR JSON) ---->| 
                                                    OIE ADT Channel
                                                      |
                                               isolated HL7 output spool
                                                 (OIE-specific PVC)
```

- Create `dw-oie` namespace and **distinct** `oie-state` PVC (Retain where
  supported; actual StorageClass/node affinity gated by read-only preflight).
- Single replica of OIE, pinned digest, `nodeSelector:
  kubernetes.io/hostname: worker01`; no tolerations which allow other nodes.
  For any OIE PoC Job or alternate workload, inherit this placement.
- ClusterIP only: don't expose Administrator port as public NodePort.
  OIE channel scripts execute in the OIE JVM, so restrict permissions,
  outbound network and ServiceAccount Token; use an external Secret for
  initial admin password and configuration. Runtime image's UID/write
  paths must be tested; do not invent a securityContext that makes it crash.
- Embedded Derby is solely OIE internal configuration/message store, not an
  independently managed application DB. Persist and back up OIE `appdata`
  and Derby state before wider deployment. Only one writer at a time.
- Kubernetes PVCs are namespaced: OIE MUST NOT assume it can mount the
  generator's `dw-synthea` PVC. Use a bounded explicitly authenticated
  in-cluster HTTP handoff or controlled read-only transfer. One source request
  per payload, no external endpoint in this PoC.

## Clinical event mapping — v1 strict A01 admission subset

FHIR input: one validated R4 Bundle with Patient/Encounter associations.
Only `Encounter.class.system =
http://terminology.hl7.org/CodeSystem/v3-ActCode` and `code=IMP`
is a potential admission. Additionally require valid Encounter ID, subject
reference to a Patient, `period.start`, and Encounter status
`in-progress` or `finished`. A finished Encounter represents a
**historical** admission event at period.start, not an assertion that the
person is currently in hospital. Other classes (AMB/EMER/OBSENC),
planned/cancelled encounters are **SKIP with counts**, never A01.
Malformed candidate admission or broken reference **REJECT** the batch.

HL7 v2.5.1 fields for A01:
- MSH-3/4 = configured simulated application/facility;
- MSH-7 = event timestamp (UTC normalized); MSH-9 = ADT^A01^ADT_A01;
- MSH-10 = deterministic stable control ID from profile/feed, frozen
  request and Encounter ID (retry => identical ID);
- MSH-12 = 2.5.1; EVN-1=A01, EVN-2=event time;
- PID-3 = Patient.id under simulated assigning authority;
  PID-5 = escaped family^given if available;
- PV1-2=I; PV1-19 = stable Encounter ID under assigning authority;
  PV1-44 = event admission timestamp when mapped.

No cross-hospital patient identity matching, fake patient encounter creation,
or admission events synthesized from an ambulatory visit.

## PoC verification gates

1. Strict offline mapping cases: valid historical/in-progress IMP; AMB/EMER
   skip; planned/cancelled skip; missing Patient/subject/start reject;
   two hospitals produce distinct IDs; exact retry deterministic; HL7
   reserved-character escaping; duplicate IDs reject.
2. Use actual output FHIR from the Generator, not only a handcrafted fixture,
   and run **inside the real OIE Channel**. Read output from OIE destination
   spool/receipt; independently parse HL7 v2.5.1 MSH/EVN/PID/PV1 fields,
   assert counts and stable IDs. A script tested outside OIE is STATIC/UNIT
   evidence, not OIE Runtime conversion.
3. Preflight exact `dw-oie` namespace/node/StorageClass/PVC/active
   Workflow resources; require explicit coordinated approval before any
   namespace, PVC, secret, pod or OIE state mutation.
4. Retain persistent OIE state on failure; only clean this run's independently
   identified ephemeral resources. Blob/HL7 delivery status remains pending.
