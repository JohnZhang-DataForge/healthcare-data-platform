# P4.1 — FHIR Source Handoff (local, read-only)

## Authority and layout

This handoff is a **new downstream consumer**, not a change to `synthea_new_generator`.
The existing immutable producer layout remains:

```text
<state-root>/requests/<request-id>/
  request.json
  payload/fhir/*.json
  generation-manifest.json
```

The only supported success marker for local generation is `SOURCE_GENERATED_VALIDATED`.
The handoff validator checks the existing normalized frozen request, request fingerprint,
profile geography, manifest identity/status, actual FHIR payload files, file SHA256,
Patient/Encounter references and metrics before emitting a JSON response on stdout.
It fails closed on missing/modified assets, symlinked inputs or profile mismatch.

## Consumer command and contract

Run with Python module search root at `local-data-platform/`:

```sh
python -m apps.clinical_producers.source_handoff \
  --state-root /state \
  --profile config/synthea-new-generator/johns-creek-hl7.json \
  --request-id <actual-frozen-request-id>
```

Output follows `contracts/synthea/new-generator/source-handoff-v1.schema.json`.
The `request_relative_path` is relative to `state-root`; each `files[].path`
is relative to `<state-root>/<request_relative_path>/payload/`.
Files are read-only FHIR R4 bundles. Each recipient MUST independently check
`source_manifest_sha256`, per-file SHA256 and expected hospital/feed identity
before accepting a payload. The generated JSON handoff is not stored, signed,
or an authorization token; its status `SOURCE_HANDOFF_VERIFIED` merely means
the local source bytes were revalidated at that moment.

The profile routes Atlanta `FHIR_R4 -> DIRECT` or Johns Creek
`FHIR_R4 -> HL7_V2 via OIE`. No clinical ADT events are generated here.
OIE Channel mapping/parse readback, delivery receipt, idempotent immutable Azure
Blob upload, and eventual Fabric ingestion use separate OpenSpec Changes and gates.

## Runtime boundary

This CLI requires no cloud credentials, network, OIE, Fabric, Airflow, Spark,
legacy NEW_ONLY PVC or OMOP access. No READY/COMMIT/upload marker is written.
The previously accepted Kubernetes run remains an independent historic source
generation acceptance only; P4.1 offline tests cannot prove a live OIE or
Blob downstream consumer. The consumer must have explicit read-only access
to source PVC bytes via a separate authorized job when deployed.
