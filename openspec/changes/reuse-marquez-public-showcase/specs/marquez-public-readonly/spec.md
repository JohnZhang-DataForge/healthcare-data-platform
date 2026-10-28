# Native Marquez Public Read-only Showcase

## ADDED Requirements

### Requirement: Reuse the existing Marquez Web and metadata store

Public showcase SHALL reuse the existing Marquez 0.51.1 Web UI, its associated internal API and PostgreSQL 14 metadata without duplicating the Marquez service, importing unauthorised Marquito code, or fabricating lineage edges. A new website implementation MUST NOT be a release dependency for the first public MVP.

#### Scenario: Recruiter inspects an existing lineage
- **GIVEN** an existing authorized/accepted local Patient or Encounter OpenLineage Job/Run/Dataset
- **WHEN** a visitor navigates through the public native Marquez UI
- **THEN** the UI SHALL show the authentic Table/Column lineage currently supported by Marquez, and missing RDD/Reconcile lineage SHALL NOT be described as complete

### Requirement: Public requests pass a default-deny read-only gateway

Anonymous access SHALL be routed through a distinct gateway before the native Marquez Web proxy, with a reviewed HTTP method and endpoint allowlist. The Gateway MUST refuse changing methods and any non-allowlisted management or GraphQL interface. Hiding or disabling GUI controls MUST NOT be presented as API authorization.

#### Scenario: Public visitor attempts metadata mutation
- **GIVEN** the user has network access to the public showcase hostname
- **WHEN** the user sends an arbitrary POST, PUT, PATCH or DELETE to an API or UI route
- **THEN** the gateway SHALL reject the request before it reaches Marquez Web/API, without changing existing metadata

#### Scenario: GUI requires a POST to query filtering
- **GIVEN** a native Marquez UI feature uses POST even for search/filter
- **WHEN** the Gateway denies it by default
- **THEN** the feature SHALL remain blocked or receive a *separately reviewed exact-endpoint read-only exception*, never a broad POST bypass

### Requirement: Public dataset and metadata review

Allowed GET endpoints SHALL be reviewed for visible raw SQL, internal network/storage URLs, run parameters, secrets, and other non-public metadata before anonymous exposure. A GET-only method policy alone MUST NOT be treated as sanitization.

#### Scenario: GET response contains private metadata
- **GIVEN** a required dataset response contains private URLs, SQL or credentials
- **WHEN** a public release is considered
- **THEN** release SHALL HOLD until the field/endpoint is restricted, safely adapted, or access is restricted to approved visitors

### Requirement: User-operated Cloudflare Tunnel with reversible cutover

Cloudflare public hostname SHALL map to the gateway origin over an outbound Tunnel, not directly to Marquez Web's NodePort, Marquez API, PG14 or a public router port. Tunnel credentials SHALL remain outside Git. Actual public activation requires separate user authorization, and rollback SHALL leave original LAN data plane untouched.

#### Scenario: Public gateway fails its negative test
- **GIVEN** a public API write attempt succeeds or a private endpoint remains reachable
- **WHEN** the cutover acceptance checks run
- **THEN** public activation MUST NOT proceed; disabling the Tunnel/route SHALL restore private-only access

### Requirement: Offline and live evidence are distinct

Source review and offline gateway tests SHALL not be represented as real external browser acceptance or current cluster availability. The final reviewer SHALL independently verify the released commit SHA, GUI pages and paths, blocked operations, allowed data exposure and rollback.

#### Scenario: Historical LAN evidence but no Tunnel run
- **GIVEN** P6 historical LAN UI screenshots and GET-only validation exist
- **WHEN** only a design or offline test PR is merged
- **THEN** public Deployment/External Browser status SHALL remain NOT_VERIFIED
