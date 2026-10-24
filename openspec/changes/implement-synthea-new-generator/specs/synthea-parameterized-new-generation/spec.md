# Synthea Parameterized New Generation

## ADDED Requirements

### Requirement: Independent synthea_new_generator preserves existing OMOP producer

The platform SHALL provide a separately packaged `synthea_new_generator` implementing `NEW_ONLY` without importing runtime state or mutating paths/contracts of the existing `apps/synthea/new_only/`. It MUST NOT require Airflow, Spark, OMOP PostgreSQL, SeaweedFS or Azure to generate a local source asset.

#### Scenario: New generator starts while legacy deployment exists
- **GIVEN** an existing `synthea-new-only` image, PVC and accepted OMOP NEW_ONLY path
- **WHEN** the new generator is built and a new local job starts
- **THEN** it uses its own image entrypoint, request namespace and output path, and no legacy source, Batch ID, PVC, existing contract or database object is modified

#### Scenario: Downstream service is unavailable
- **GIVEN** OIE, Azure Blob or Fabric is unavailable
- **WHEN** a valid local generation request runs
- **THEN** local generation and validation MAY complete independently without invoking or requiring the downstream services

### Requirement: Strict parameterized request supports CSV and FHIR R4

The generator SHALL accept a versioned request with `request_id`, `generation_mode`, `population`, `state`, optional `city`, seed parameters, reference date and `output_formats`. Formats SHALL be independently selectable from `CSV` and `FHIR_R4`. Unsupported, unsafe, incompatible or invalid parameter values MUST fail before publication of a successful local asset.

#### Scenario: FHIR-only Atlanta request
- **GIVEN** a valid `NEW_ONLY` request with `state=Georgia`, `city=Atlanta` and `output_formats=[FHIR_R4]`
- **WHEN** Synthea runs
- **THEN** it invokes the pinned Synthea with FHIR R4 enabled and produces validated FHIR source assets without requiring CSV publication

#### Scenario: CSV-only or combined request
- **GIVEN** a valid request selects `CSV` alone or `CSV` and `FHIR_R4`
- **WHEN** generator arguments are constructed
- **THEN** only selected native exporters are enabled and no hardcoded hospital branch changes the exporter selection

#### Scenario: Invalid city or unsupported mode
- **GIVEN** an unknown or unsupported `state/city` or `generation_mode=UPDATE_ONLY` / `MIX_DATA`
- **WHEN** the request is validated or Synthea reports an unsupported geographical selection
- **THEN** the request fails explicitly without silently falling back to another region or reporting a successful generation

### Requirement: Request identity and generated source assets are immutable

For each `request_id`, the generator SHALL freeze normalized parameters, Synthea version/commit and a request fingerprint before generation. Successful local artifacts SHALL have a versioned manifest with safe relative file paths, hashes, actual counts and source provenance. A retry MUST NOT silently replace different bytes or regenerate a completed request.

#### Scenario: Exact retry of a successful request
- **GIVEN** a completed request with a valid frozen request and local generation manifest
- **WHEN** the same request is executed again
- **THEN** existing files are independently revalidated against the manifest and no new Synthea run or mutable overwrite occurs

#### Scenario: Same request ID with changed parameters
- **GIVEN** a frozen request ID with a specific state, population, seed and format set
- **WHEN** a caller reuses the ID with any conflicting normalized parameter or generator version
- **THEN** the generator rejects the request without replacing the previous asset

#### Scenario: Partial or conflicting output
- **GIVEN** a failed generation or corrupt/partial JSON or mismatching SHA-256
- **WHEN** the local completion gate is evaluated
- **THEN** no `SOURCE_GENERATED_VALIDATED` completion is emitted and the error is retained for diagnosis

### Requirement: Native FHIR output is verifiable and not implicitly an HL7 event

FHIR R4 output SHALL preserve parseable Synthea Bundle data with verifiable patient identities, associated Encounter resources and references when present. The generator MUST NOT treat any Encounter as an admission event or claim that local FHIR files are already HL7, Blob READY or Fabric processed.

#### Scenario: FHIR resource validation
- **GIVEN** generated FHIR JSON files from a pinned Synthea run
- **WHEN** the validator inspects the files
- **THEN** valid Bundle/Patient records and relevant Encounter references are verified and the actual file/resource counts and hashes are persisted in the generation manifest

#### Scenario: Empty or non-admission Encounter
- **GIVEN** a FHIR Bundle without an inpatient admission
- **WHEN** local FHIR generation completes
- **THEN** the generator MAY complete successfully without inventing an `ADT^A01` or invoking OIE

### Requirement: The same generator can serve independent hospital profiles

The platform SHALL allow separate external hospital/feed profiles to produce independent generation requests without hardcoding hospital IDs, feed formats, cloud destinations or OIE Channel logic into `synthea_new_generator`.

#### Scenario: Atlanta and Johns Creek produce independent FHIR sources
- **GIVEN** two external profiles with `hospital_id` / `feed_id`, distinct request IDs and independent seeds, both selecting `FHIR_R4`
- **WHEN** both valid jobs run
- **THEN** each produces a separately frozen local FHIR asset and manifest; no shared Cohort or cross-hospital Patient Crosswalk is required for MVP

#### Scenario: Johns Creek downstream OIE consumes FHIR
- **GIVEN** a valid Johns Creek FHIR R4 source asset and its immutable generation manifest
- **WHEN** a separate OIE conversion pipeline is run
- **THEN** the generator remains unchanged; the separate consumer owns FHIR-to-HL7 event semantics, message mapping, storage and delivery status

#### Scenario: New hospital configuration is added
- **GIVEN** a valid third hospital/feed profile selecting a supported output format and geographic location
- **WHEN** that profile is converted into a generator request
- **THEN** no generator source-code modification is necessary to support the new hospital


### Requirement: External FHIR consumer verifies frozen local source before handoff

A downstream producer SHALL verify the independent generator's immutable request,
completed generation manifest and actual FHIR R4 payload bytes against a versioned,
hospital-profile-scoped handoff contract before further transport or transformation.
The generator itself MUST remain unaware of the recipient and MUST NOT emit Blob
READY, HL7 delivery or Fabric processing status.

#### Scenario: Valid independent Johns Creek source
- **GIVEN** a completed local FHIR R4 request with matching frozen manifest, source hashes and Johns Creek feed profile
- **WHEN** a read-only downstream handoff is requested
- **THEN** the caller receives FHIR inventory, immutable manifest checksum and route metadata with `SOURCE_HANDOFF_VERIFIED`, but no HL7 or Blob publication is claimed

#### Scenario: Source drift or hospital mismatch
- **GIVEN** a missing or corrupted file, changed hash, mismatched city/profile or unsafe symbolic-link asset
- **WHEN** the downstream handoff is requested
- **THEN** it fails without writing to source state or enabling downstream publication
