# Johns Creek OIE 4.7.0 clinical Channel — deployed and verified

Use the upstream OIE 4.7.0 repository's **actual** Channel Reader + Channel
Writer no-op fixture as an XStream-compatible base:
`upstream-raw-reader.xml` copied from
`OpenIntegrationEngine/engine@f9ba73e28de151b041b97e7383e0ab9d2c4f1799`
path `ci/tests/101-raw-no-op/channels/01-raw-no-op/channel.xml`.
Its XML says `version=4.5.2` because that is the actual bundled v4.7.0
compatibility test fixture. Do not arbitrarily replace version strings.

`build_channel.py` modifies ONLY the fixture Channel ID, name and
preprocessingScript, inserting canonical `adt_a01.js` and a strict single
event wrapper. No Code Template global library required in this minimum PoC.

```sh
cd local-data-platform
python3 -m apps.clinical_producers.oie.build_channel --output /tmp/johns-creek-channel.xml
python3 -m unittest discover -s tests/clinical_producers -p test_oie_channel_build.py -v
```

### Ingest / readback contract

The REST API on the existing OIE internal Administrator HTTPS 8443 offers
`POST /api/channels/{id}/messages` with `Content-Type: text/plain`;
it returns a message ID. The PoC source connector is **Channel Reader**,
not an exposed HTTP listener. Sender submits **one mini FHIR Bundle per
Encounter** (actual Patient+Encounter unmodified resources) wrapped with
`request_id`; our `fhir_events.py` only splits a previously verified
source and does **not** decide whether any Encounter is an admission.
OIE `preprocessingScript` invokes canonical `fhirToAdtA01` and produces
HL7 v2.5.1 for IMP in-progress/finished admissions, a
`OIE_ADT_NON_INPATIENT_SKIPPED` marker for other encounters, or an
OIE error for malformed admission. The sender must check OIE message
records and verify the returned bytes independently, never treat an HTTP
2xx response alone as a delivered HL7/Blob message.

**Clinical conversion accepted live on 2026-10-24** (see proof below). 
The current Channel retains the upstream Channel Writer `none` destination;
its **downstream delivery is NOT ACCEPTED** (although source-side 31 FHIR conversions and message readback passed on the live engine).
A different destination connector may be needed before publication.
Import/deploy messages can modify persistent OIE Derby; do not run
on `dw-oie` until a coordinated, guarded Self-Runner workflow checks
existing channel IDs and current shared tasks. No channel overwrites,
database reset, PVC deletion or local-path restart permitted.

When the real OIE Channel is accepted, a separately designed controlled
transport will deliver completed HL7 messages to Azure Blob Landing.
This PoC does not enable direct public ports or Blob writes.

### Worker01 persisted OIE clinical acceptance (2026-10-24)

- [Channel create/deploy #40127786353](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40127786353): canonical Johns Creek Channel ID `69ace705-a675-45f6-b126-a3b22a65212a` created once in existing `dw-oie` Derby PVC, independent GET readback, STARTED on worker01 OIE 4.7.0. No PVC reset.
- [Real 31 FHIR event + replay acceptance #40128211780](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40128211780): frozen generated Johns Creek source, 1 IMP A01 and 30 AMB skipped, same IMP retry identical HL7 bytes; independently parsed source records, verified 32 persistent OIE message records. Exact source artifact SHA256 `af41fd1c84001c9a11f721a0c0004bd12164997b5e243c7071257e38fca3c67d`.
- Do not rerun the accepted batch: the `--existing-channel` preflight requires no prior Channel messages and now appropriately HOLDs. Later Producer integrations require a new immutable source request, immutable delivery metadata and separate idempotent publisher contract. Azure Blob publication has **not** occurred.
