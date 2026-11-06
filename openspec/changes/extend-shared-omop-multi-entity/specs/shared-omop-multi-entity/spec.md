## ADDED Requirements

### Requirement: Explicit, versioned multi-entity registry

The shared engine SHALL maintain an explicit versioned registry of supported clinical entities, required Canonical contract references and hashes, target OMOP tables, mapper bindings, identity strategy, declared dependencies, validation requirements and publication groups. It SHALL reject unregistered entities, duplicate identifiers, conflicting targets, invalid mapping definitions and dependency cycles; it MUST NOT auto-discover executable modules or create target tables as a side effect.

#### Scenario: Existing two entities remain compatible

- **GIVEN** approved Canonical Patient v1 and Encounter v1 and a registered Person/Visit mapping
- **WHEN** the caller uses the new registry interface
- **THEN** the existing Person/Visit Candidate values, source identity, version pins and fail-closed validation MUST remain equivalent to the legacy API before caller migration.

#### Scenario: Invalid extension

- **GIVEN** an unregistered entity, circular parent reference or two incompatible definitions claiming the same target identity scope
- **WHEN** the registry validates the plan
- **THEN** it SHALL fail closed without invoking a mapper or publishing data.

### Requirement: Deterministic source-to-target entity fan-out

The shared mapper SHALL allow an approved Canonical source entity to produce one or more defined OMOP target tables and multiple target rows only under explicit clinically reviewed deterministic rules. Every output MUST preserve source provenance and a stable derived-row business identity independent of input row order or replay attempt. No lexical or field-name coincidence SHALL authorize clinical routing.

#### Scenario: One source record generates two target records

- **GIVEN** a future registered Canonical entity whose reviewed semantics require two distinct target roles
- **WHEN** the mapper processes an unchanged approved source record in any input ordering
- **THEN** target table, derived role/key and output content MUST remain identical across replay and MUST NOT collide with Person, Visit or another target identity scope.

#### Scenario: Missing fan-out discriminator

- **GIVEN** two outputs would have the same target table and derivation identity
- **WHEN** the mapper builds candidates
- **THEN** it MUST HOLD instead of using row numbers, random UUIDs or hash-modulo surrogate IDs.

### Requirement: Reviewed, domain-safe concept resolution

Concept resolution SHALL use a pinned source namespace, target table/column, mapping version, vocabulary release and verified profile SHA. It SHALL verify the applicable standard Concept, Domain, validity, code meaning and required release/license evidence before Gold authorization. Unknown, invalid, expired, wrong-domain or unreviewed mappings MUST HOLD; no inferred zero/identity mapping or silent truncation is permitted.

#### Scenario: Wrong vocabulary Domain

- **GIVEN** a source Race LOINC concept exists but its target Domain is Measurement instead of approved Person Race
- **WHEN** the Person mapper requests a Race Concept
- **THEN** the request MUST HOLD pending a clinically reviewed mapping rather than publishing the lexical match.

#### Scenario: Reusing one mapper for another hospital

- **GIVEN** the same Canonical field is delivered under a different hospital/source-system namespace without an approved mapping profile
- **WHEN** a batch requests Concept resolution
- **THEN** the engine MUST reject that mapping profile regardless of field-name similarity.

### Requirement: Stable target-scoped identity planning

Identity planning SHALL use a validated Map/Allocator/Gold/Ledger snapshot and target- and hospital-scoped stable source identities. It MAY propose provisional positive INT IDs, but preview SHALL NOT persist or reserve them. The writer MUST revalidate the whole snapshot behind a verified single-writer fence before atomic Gold COMMIT.

#### Scenario: First batch before a persistent map

- **GIVEN** no Person or Visit source identities have previously been allocated and a verified snapshot is empty
- **WHEN** the mapper builds a candidate from a valid identity preview
- **THEN** candidate IDs MUST be explicitly provisional and traceable to that snapshot, and MUST NOT be represented as a committed Map or a valid parent for another publication group.

#### Scenario: Warehouse changed before commit

- **GIVEN** a candidate was generated with an approved provisional allocation plan
- **WHEN** the writer discovers Map, Gold or Allocator drift during transaction revalidation
- **THEN** it MUST HOLD or regenerate the plan without silently committing the stale proposed IDs.

#### Scenario: Cross-hospital collision and overflow

- **GIVEN** two hospitals share an external business key, or a proposed OMOP INT exceeds 2147483647
- **WHEN** the identity planner validates its assignments
- **THEN** hospitals MUST remain isolated, and any range/collation/allocator collision MUST HOLD without Gold mutation.

### Requirement: Dependency graph and FK verification

Each target entity SHALL declare required and optional parent relationships in an acyclic dependency graph. A child target may reference a parent only after the parent is independently verified as committed or is included in the same approved atomic transaction group. Namespace correctness, source referential integrity and required-FK presence MUST be checked in software even when the database FK/UNIQUE constraints are NOT ENFORCED.

#### Scenario: Missing committed parent

- **GIVEN** a Condition candidate references a Person that is neither durably committed nor part of the same verified atomic transaction group
- **WHEN** the dependency planner validates publication
- **THEN** the Condition group MUST HOLD without a committed child row.

#### Scenario: Parent and child in one transaction

- **GIVEN** Person and Visit provisional IDs are planned under one consistent snapshot and the publisher verifies all FK references within a fenced transaction
- **WHEN** the transaction commits Map, Person, Visit, Allocator and Ledger together
- **THEN** the two entity targets MAY use the verified provisional parent-child IDs atomically, subject to independent committed readback.

### Requirement: Candidate evidence and replay-fenced publication groups

The execution owner SHALL persist version-scoped immutable Candidates with per-target counts, keys, hashes and provenance; approval MUST follow independent physical readback. Gold publication groups SHALL atomically commit Map, Allocator, target rows and Ledger, followed by independent receipt verification. All source, processing, mapping, vocabulary and definition fingerprints MUST fence replay.

#### Scenario: Partial candidate write

- **GIVEN** one target table in a group wrote candidates successfully but another table failed or cannot be independently read back
- **WHEN** the publisher evaluates Candidate Approval
- **THEN** it MUST NOT approve that publication group or emit GOLD_COMMITTED.

#### Scenario: Exact replay versus conflicting replay

- **GIVEN** a durable verified Gold receipt for a source/processing/publication fingerprint
- **WHEN** the exact same fingerprint is requested again
- **THEN** independently verified unchanged targets MUST SKIP without new IDs; a changed fingerprint or inconsistent counts MUST HOLD.

#### Scenario: Unknown SQL acknowledgement

- **GIVEN** a Gold transaction's commit response is missing or ambiguous
- **WHEN** the caller considers retrying
- **THEN** it MUST first independently query committed Ledger, Map and all target rows and MUST NOT blindly reinsert.

### Requirement: Multi-group visibility barrier is not cross-transaction atomicity

The platform publisher SHALL explicitly declare the set of publication groups required by a released data-product version, and SHALL expose that version to consumers only when all required groups have independently verified committed receipts. It MUST distinguish individually committed groups from a fully published product and MUST NOT claim transactional atomicity across separate Warehouse transactions.

#### Scenario: Base group committed and dependent group fails

- **GIVEN** Person/Visit has committed but a required Condition group fails
- **WHEN** the data-product version is evaluated for public consumption
- **THEN** the version MUST remain unpublished and record the partial state for safe recovery, without falsely rolling back the already committed base group.

### Requirement: Shared logic remains platform-neutral and backward compatible

The shared engine SHALL own pure deterministic transformations and planning only. Fabric and Local platform implementations SHALL independently own physical Spark/Delta/SQL/PG operations and transactional publication, while existing Canonical v1 bytes, legacy Local writer behavior, historical Fabric partitions and supported Person/Visit APIs remain unchanged until separately versioned, tested and approved migration.

#### Scenario: Documentation-only architecture change

- **GIVEN** this new multi-entity Delta Spec is accepted without a corresponding implementation
- **WHEN** current system status is reported
- **THEN** the system MUST continue to identify physical Candidate/Gold COMMIT and multi-entity runtime as NOT_DONE; static design acceptance SHALL NOT be treated as a cloud release.
