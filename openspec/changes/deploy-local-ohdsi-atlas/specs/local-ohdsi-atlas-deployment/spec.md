## ADDED Requirements

### Requirement: Compatible ATLAS and WebAPI major versions

The Local ATLAS deployment SHALL use an explicitly verified, version-pinned compatible ATLAS3 3.0.x and WebAPI 3.0.x pair and SHALL NOT silently mix ATLAS3 with WebAPI 2.x, floating `latest` images, or development-only `3.0-dev` tags in an accepted deployment.

#### Scenario: Compatible production candidate

- **GIVEN** independently verified release artifacts and immutable image digests
- **WHEN** an implementation PR proposes a runtime release
- **THEN** its manifest records both version/digest pairs, runtime architecture and tested API compatibility

#### Scenario: Incompatible or unpinned artifact

- **GIVEN** Atlas3 points to WebAPI 2.x or uses an unpinned mutable/development image
- **WHEN** the deployment preflight runs
- **THEN** publication is rejected before a Kubernetes rollout

### Requirement: Local OMOP source readiness must be measured independently

The deployment SHALL read the existing Local PostgreSQL OMOP inventory before data changes, SHALL distinguish Fabric Vocabulary from Local Vocabulary and SHALL refuse to represent absent `observation_period` or required vocabulary data as present.

#### Scenario: Existing Local CDM is incomplete

- **GIVEN** Local PostgreSQL contains Person/Visit but no complete verified Vocabulary or Observation Period
- **WHEN** the readiness report is generated
- **THEN** it identifies the specific missing tables/rows, allows bounded UI/API validation and marks dependent research analyses BLOCKED

#### Scenario: Fabric vocabulary exists but Local vocabulary is empty

- **GIVEN** the Fabric Warehouse has accepted Vocabulary files and the local source has no complete matching evidence
- **WHEN** ATLAS data source readiness is evaluated
- **THEN** the Fabric counts SHALL NOT substitute for local physical SQL readback

### Requirement: Separate application write privileges from OMOP CDM data

The WebAPI service SHALL use dedicated application/Results/Temp storage and database roles that cannot modify the existing clinical `cdm` tables; any schema migrations SHALL be authorized, scoped, backed up and independently read back.

#### Scenario: Cohort results are stored

- **GIVEN** a correctly authorized synthetic cohort execution
- **WHEN** the Results schema is written
- **THEN** the application stores results only in approved storage and produces no unauthorized `cdm.*` mutation

#### Scenario: Unsafe migration targets CDM

- **GIVEN** a migration attempts to ALTER or DELETE existing `cdm` clinical records
- **WHEN** the preflight applies its allowlist
- **THEN** the change is rejected without executing the operation

### Requirement: Cloudflare and gateway access must protect UI and WebAPI together

A public ATLAS hostname SHALL require Cloudflare Access authorization on all UI and API routes, SHALL forward solely through the existing outbound Tunnel and approved gateway, and SHALL NOT expose WebAPI or PostgreSQL on a public NodePort or router ingress. Internal WebAPI authentication and Access authentication SHALL NOT be conflated.

#### Scenario: Unauthorized API request

- **GIVEN** a browser without an allowed Cloudflare Access session
- **WHEN** it requests `/WebAPI/source/sources` or posts a cohort operation
- **THEN** access is denied before origin WebAPI and no patient data or job execution is returned

#### Scenario: Allowed identity

- **GIVEN** an allowlisted identity with a valid Access session
- **WHEN** it opens the ATLAS UI and invokes its API
- **THEN** matching-host API requests reach internal WebAPI only through the accepted gateway and the configured WebAPI identity layer is independently enforced where enabled

#### Scenario: Misconfigured Access or route

- **GIVEN** Access is disabled, API is publicly reachable directly or the Tunnel route bypasses the gateway
- **WHEN** an external release is proposed
- **THEN** the release SHALL HALT and remain private

### Requirement: ATLAS workload placement separates research API from Marquez application nodes

The ATLAS UI and WebAPI SHALL require the verified `workload=storage` node role and hostname-scoped anti-affinity to Marquez application Pods. A rollout SHALL HALT without a suitable node and SHALL verify actual Pod placement. Existing PG14/PG17 volumes SHALL remain unchanged.

#### Scenario: Existing three-worker placement

- **GIVEN** live evidence that worker01 has label `workload=storage`, Marquez application Pods are on worker02/worker03, and worker01 meets resource limits
- **WHEN** approved ATLAS UI and WebAPI Deployments are admitted
- **THEN** both Atlas components are scheduled to worker01 with no co-location with Marquez application Pods, and runtime Pod nodeName is independently read back

#### Scenario: Required separation cannot be scheduled

- **GIVEN** worker01 lacks capacity, is tainted/NotReady, or hosts a matching Marquez application Pod
- **WHEN** Kubernetes evaluates the required placement constraints
- **THEN** the ATLAS rollout remains Pending/HOLD and SHALL NOT relax constraints or schedule to another worker without a reviewed placement change

#### Scenario: Marquez moves after ATLAS starts

- **GIVEN** Kubernetes required anti-affinity with `IgnoredDuringExecution` does not evict existing Pods
- **WHEN** a future Marquez rollout would move an application onto ATLAS's node
- **THEN** the operation MUST be separately checked against the separation policy; permanent guarantees require symmetrical constraints or live placement drift detection, not a claim based only on ATLAS scheduling rules

### Requirement: Preserve existing Marquez and business workloads

The implementation SHALL avoid changing Marquez, PG14, OMOP Writer, existing Source Batch/Identity records, Cloudflare lineage host routes, or Fabric capacity state.

#### Scenario: Add ATLAS to an existing Tunnel

- **GIVEN** a verified live lineage hostname and its upstream
- **WHEN** a new ATLAS hostname route is added
- **THEN** the lineage route and its method/path restrictions remain unchanged and are independently regression-tested

#### Scenario: PostgreSQL or Kubernetes resource contention

- **GIVEN** resource ownership, capacity or concurrent jobs cannot be confirmed
- **WHEN** ATLAS setup would cause shared runtime changes
- **THEN** the rollout HALTs for read-only inspection and explicit authorization

### Requirement: Research acceptance must use synthetic physical readback

A completed ATLAS research MVP SHALL prove a real synthetic Concept Set/Cohort workflow and independent persisted Results readback, or SHALL explicitly report analytics blocked when CDM prerequisites have not been met.

#### Scenario: UI is healthy but observation period is missing

- **GIVEN** ATLAS UI and WebAPI return 200 but OMOP observation period is absent
- **WHEN** acceptance is reported
- **THEN** only UI/API/data-source connectivity is accepted, not cohort or patient-level analytics

#### Scenario: Synthetic cohort is generated

- **GIVEN** verified Vocabulary, clinical data and observation period plus authorized Results storage
- **WHEN** an approved synthetic cohort is generated
- **THEN** its output is independently queried, reconciled to synthetic source identities and documented with immutable version/run evidence
