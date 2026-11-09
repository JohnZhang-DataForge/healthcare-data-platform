## ADDED Requirements

### Requirement: One existing Azure Landing container and one credential MVP

The system SHALL use the already-existing Azure Blob Storage account `johnzhang` and container `landing`; it SHALL NOT create a new `g5-trust-ledger`, another container/account, a dedicated second identity, a new IAM isolation layer, WORM policy or a Fabric Delta control ledger as part of this MVP. A single pre-existing, independently checked credential SHALL perform the permitted Blob data-plane actions.

#### Scenario: Existing identity has no write permission

- **GIVEN** the existing Fabric WorkspaceIdentity AzureBlobs connection is Reader-only, or the candidate single runtime identity cannot conditionally create under `landing`
- **WHEN** the adapter is enabled
- **THEN** execution MUST HOLD and report a sanitized permission gap, never silently assign RBAC or overwrite the existing connection.

### Requirement: Immutable original landing and separate control prefixes

The system SHALL preserve existing `clinical/v1` Publisher paths, original FHIR/HL7 objects, SHA, ETag and manifest-last protocol; it SHALL store mutable stage-scoped Claim state only below `_control/v1/` and verifiable stage-completion JSON receipts only below `processed/v1/`. Control writes SHALL never COPY, DELETE, MOVE, RENAME, or overwrite any original Landing data.

#### Scenario: Batch marked complete

- **GIVEN** an exact existing source Manifest is fully verified and the corresponding Fabric target stage has been independently read back
- **WHEN** the stage is finalized
- **THEN** the system SHALL conditionally create and independently GET-verify the precise stage-version `processed` receipt without moving source data.

#### Scenario: Wrong prefix or malicious path

- **GIVEN** a caller attempts `../`, foreign hospital/feed/request, a write into `clinical/v1`, or a cross-stage receipt
- **WHEN** any storage operation is planned
- **THEN** the adapter MUST reject it before any outbound write.

### Requirement: Race-safe batch lifecycle using Blob ETag and Lease

The system SHALL use Blob conditional create/ETag compare-and-swap and scoped time-bounded Lease/owner fencing when mutation or concurrency requires it. It SHALL preserve source Manifest SHA, exact stage, processing versions and attempt identity; previously completed or conflicting requests SHALL not take another active claim.

#### Scenario: Two workers compete for one batch

- **GIVEN** two runners request the identical claim simultaneously
- **WHEN** Azure conditional create or ETag/Lease acquisition races
- **THEN** at most one attempt SHALL gain the active claim; the other SHALL return BUSY/HOLD or recheck a completed proven receipt, never execute a duplicate writer.

#### Scenario: Lease expires or stale worker resumes

- **GIVEN** a Lease owner is stale, an ACK is unknown, or the current ETag differs
- **WHEN** the worker attempts to finalize `processed`
- **THEN** it SHALL fail closed pending an independent current ownership and target-state reconciliation; it SHALL NOT auto-steal an expired lease or assert business completion.

### Requirement: Shared replay decision and stage-specific physical evidence

The system SHALL reuse the canonical Shared Engine Batch Identity/Replay decisions. The Blob adapter SHALL only persist/translate status, never create a second clinical Mapper or treat a status JSON as Warehouse Gold authorization. Receipt validity SHALL bind the exact Batch/Manifest and processing + mapping version to the independently proven target output.

#### Scenario: Already verified stage while Capacity is paused

- **GIVEN** an immutable stage-specific processed receipt with exact source and publication identity, verified previously against the target, and no scope/version drift
- **WHEN** the same request is rediscovered
- **THEN** the controller MAY return SKIP without resuming Fabric CU; an incomplete, unverified or inconsistent receipt MUST return VERIFY_READONLY/HOLD and require target readback when available.

#### Scenario: Gold inferred from Silver

- **GIVEN** a valid `SILVER_APPROVED` or `CANDIDATE_APPROVED` receipt
- **WHEN** `GOLD_COMMITTED` is requested
- **THEN** the system MUST NOT infer a Gold COMMIT or Writer permission without separately verified Fabric Warehouse transaction evidence and existing approval gates.

### Requirement: Source design must not be mistaken for a live deployment

The OpenSpec documents SHALL identify that the single-container layout is an approved design, not a deployed Azure prefix, runtime Credential authorization, real Blob Claim/Lease, Fabric Candidate/Gold commit or production Native nonce/signature service.

#### Scenario: Offline contract test passes

- **GIVEN** local mock/Azurite CI produces simulated ETag collisions and valid JSON receipts
- **WHEN** reporting the result
- **THEN** the report MUST mark the result SOURCE/CI ONLY and SHALL NOT claim any real Azure conditional PUT/Lease or clinical/License/G5 Native approval.
