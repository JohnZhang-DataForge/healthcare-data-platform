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

### Requirement: Tunnel routing and WebAPI-native authorization must protect clinical APIs

A public ATLAS hostname SHALL use the existing Cloudflare Tunnel and the internal Atlas3 frontend Service, SHALL enforce WebAPI3 Database Authentication and least-privilege RBAC on all sensitive API operations, and SHALL NOT expose PostgreSQL/WebAPI directly through router ingress, NodePort or bypass routes. Cloudflare Zero Trust Access MAY be added later but is not required by the user-selected initial architecture.

#### Scenario: Unauthenticated API access is rejected

- **GIVEN** the Tunnel route is already configured and a browser has no valid WebAPI login
- **WHEN** it requests sensitive Sources, Cohort, Results, or attempts an analysis write
- **THEN** WebAPI rejects it with the appropriate 401/403 and returns no protected clinical or task data

#### Scenario: Valid login with scoped role

- **GIVEN** a newly established non-default WebAPI Database Auth user with an authorized RBAC role
- **WHEN** it logs in and accesses allowed resources
- **THEN** the request reaches WebAPI via the same ATLAS hostname and authorized actions complete without modifying CDM clinical tables

#### Scenario: Existing Lineage Tunnel remains unmodified

- **GIVEN** a user-established `healthcare-marquez-public` Tunnel hosts `lineage` and `atlas` Published application routes
- **WHEN** the ATLAS private origin Service becomes ready
- **THEN** the existing Lineage route and Marquez Gateway remain untouched, and independent Lineage regression readback still passes

#### Scenario: Missing auth or unsafe exposure

- **GIVEN** DB login, WebAPI permission enforcement or the public route fail an independent negative test
- **WHEN** external ATLAS acceptance is requested
- **THEN** public acceptance HALTS, with the UI origin held private or removed until authenticated API tests pass

### Requirement: ATLAS workload placement separates research API from Marquez application nodes

The ATLAS UI and WebAPI SHALL schedule on the user-selected `worker03` node, with verified hostname constraints and runtime capacity gates. Placement SHALL NOT move PG17/PG14 volumes or modify running Marquez Pods. Existing PG14 and the Marquez Public Web may remain on worker03.

#### Scenario: Existing three-worker placement

- **GIVEN** worker03 is Ready with sufficient verified resources, contains PG17 and PG14, and is the user-approved node
- **WHEN** approved ATLAS UI and WebAPI Deployments are admitted
- **THEN** both Atlas components schedule on worker03; public Marquez Web and PG14 co-location is permitted, while Marquez API/Nginx remain unchanged, and real Pod nodeName is independently read back

#### Scenario: Required separation cannot be scheduled

- **GIVEN** worker03 lacks capacity, is tainted/NotReady, or violates reviewed constraints
- **WHEN** Kubernetes evaluates the required placement constraints
- **THEN** the ATLAS rollout remains Pending/HOLD and SHALL NOT relax constraints or schedule to another worker without a reviewed placement change

#### Scenario: Marquez moves after ATLAS starts

- **GIVEN** Kubernetes required anti-affinity with `IgnoredDuringExecution` does not evict existing Pods
- **WHEN** a future Marquez rollout would move an application onto ATLAS's node
- **THEN** the operation MUST be separately checked against the separation policy; permanent guarantees require symmetrical constraints or live placement drift detection, not a claim based only on ATLAS scheduling rules

### Requirement: Distinguish persisted research records from reconstructible cache

WebAPI user/configuration and analytic Results SHALL persist in approved PostgreSQL storage covered by backup. The Atlas3 static UI SHALL NOT require a PVC, and TrexSQL cache MAY use bounded ephemeral storage unless persistence has been separately approved.

#### Scenario: Restart WebAPI with ephemeral cache

- **GIVEN** Cohort Definitions and Results exist in PostgreSQL while TrexSQL cache uses emptyDir
- **WHEN** the WebAPI Pod restarts
- **THEN** user/configuration and analytic results remain available, while cache must be reconstructed

#### Scenario: Unexpected database storage replacement

- **GIVEN** a deployment proposes a fresh PostgreSQL PVC or replacement of the current OMOP PVC without approval
- **WHEN** release preflight runs
- **THEN** the release is rejected before creating or changing storage

### Requirement: Kubernetes manifests follow the centralized Local DP source owner

All ATLAS and WebAPI Kubernetes resources SHALL be authored only under `local-data-platform/kubernetes/manifests/atlas/`. The implementation SHALL NOT create a parallel `local-data-platform/atlas/kubernetes/` manifest tree.

#### Scenario: Implementing ATLAS deployments

- **GIVEN** a change adds ATLAS3 and WebAPI3 Deployments, Services, Namespace, RBAC, resource or placement policies
- **WHEN** their source is checked for review
- **THEN** all Kubernetes manifests are in the centralized Atlas component directory while image build contexts remain under `local-data-platform/images/`

#### Scenario: Duplicate Kubernetes path

- **GIVEN** a change adds deployment YAML under `local-data-platform/atlas/kubernetes/`
- **WHEN** the repository ownership gate runs
- **THEN** the addition is rejected until consolidated in `local-data-platform/kubernetes/manifests/atlas/`

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
