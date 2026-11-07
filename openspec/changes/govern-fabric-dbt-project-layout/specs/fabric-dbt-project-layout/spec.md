## ADDED Requirements

### Requirement: Fabric dbt projects SHALL use a governed parent and a single owner
After an approved migration, Fabric-oriented dbt Core project source SHALL belong to `azure-fabric/dbt/<project>/`. The first planned project SHALL be `hl7-canonical` with `name: hl7_canonical`. Additional projects MUST be justified in a separate Active OpenSpec; Native Workspace items, Self-Runner experiments and `shared-data-engine/` MUST NOT become duplicate permanent dbt project owners.

#### Scenario: A future Agent adds FHIR with dbt
- **WHEN** an Agent proposes FHIR dbt SQL
- **THEN** it SHALL examine current PySpark and shared business code, obtain a separate project owner decision, and only then propose `fhir-canonical/`.

#### Scenario: Another hospital requires HL7 SQL
- **WHEN** a new hospital or clinical entity uses HL7 SQL
- **THEN** the Agent SHALL extend the existing approved HL7 project instead of automatically creating a per-hospital or per-table project.

### Requirement: Standard dbt projects SHALL preserve their full directory scaffold
Each new approved dbt project SHALL contain `dbt_project.yml`, `models/staging/`, `models/intermediate/`, `models/canonical/`, `macros/`, `tests/`, `seeds/`, `snapshots/`, `analyses/` and `profiles/`. Empty directories SHALL use `.gitkeep`; unnecessary packages and dummy SQL MUST NOT be added.

#### Scenario: Macros and snapshots are not yet implemented
- **WHEN** the new project does not need a macro or snapshot
- **THEN** its standard empty directories SHALL remain visible in Git via placeholders.

#### Scenario: dbt native SQL tests conflict with protected layout policy
- **WHEN** adding `azure-fabric/dbt/<project>/tests/`, even just `tests/.gitkeep`
- **THEN** a separately approved, narrowly scoped change to the trusted repository layout checker MUST pass positive/negative CI and applicable Ruleset checks before the source is introduced; other source-area tests remain prohibited.

### Requirement: dbt Canonical candidates SHALL not duplicate shared business ownership
dbt SQL SHALL produce source-specific Contract-aligned Canonical Candidates and MUST NOT create a second authoritative Canonical approval, identity, OMOP concept mapper or Gold publisher without an explicit approved ownership transfer.

#### Scenario: An Agent proposes shared Canonical business logic in dbt
- **WHEN** a project such as `canonical-transform/` is proposed
- **THEN** the Agent SHALL first obtain a Shared Engine responsibilities decision and an Active OpenSpec Change, avoiding overlapping implementations.

### Requirement: Planned paths SHALL not be treated as implemented
The existing HL7 dbt implementation under `local-data-platform/spark/apps/hl7/` SHALL remain the authoritative running source until a separate tested physical migration updates CODE owners, consumers and verification evidence.

#### Scenario: An Agent reads the new Fabric dbt documentation
- **WHEN** `azure-fabric/dbt/hl7-canonical/` is described but the physical migration is still open
- **THEN** the Agent SHALL use the existing real CODE Map and MUST NOT report the Fabric path as already deployed or tested.

#### Scenario: An Agent moves dbt code
- **WHEN** a later PR moves HL7 SQL to the Fabric dbt tree
- **THEN** it SHALL update all workflow consumers and CODE maps, independently revalidate the local Delta/dbt Contract, and not leave two maintained production dbt sources.
