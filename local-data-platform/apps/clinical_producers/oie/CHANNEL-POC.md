# Versioned Johns Creek OIE 4.7.0 Channel — not yet deployed

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

**Current implementation only builds the XML and tests offline.**
The static XML still has upstream Channel Writer `none` destination,
whose runtime behavior and errors MUST be independently verified on OIE.
A different destination connector may be needed before publication.
Import/deploy messages can modify persistent OIE Derby; do not run
on `dw-oie` until a coordinated, guarded Self-Runner workflow checks
existing channel IDs and current shared tasks. No channel overwrites,
database reset, PVC deletion or local-path restart permitted.

When the real OIE Channel is accepted, a separately designed controlled
transport will deliver completed HL7 messages to Azure Blob Landing.
This PoC does not enable direct public ports or Blob writes.
