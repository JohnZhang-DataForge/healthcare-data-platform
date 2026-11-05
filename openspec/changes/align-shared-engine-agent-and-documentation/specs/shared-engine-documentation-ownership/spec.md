## ADDED Requirements

### Requirement: Scoped Agent instructions remain beside Shared Engine code
The repository SHALL retain `shared-data-engine/AGENTS.md` as stable, directory-scoped agent constraints and routing. It MUST NOT duplicate package version, development progress or runtime acceptance.

#### Scenario: Version changes
- **WHEN** package source version changes
- **THEN** AGENTS instructions SHALL remain valid without a duplicate version edit; authoritative source and actual release evidence determine version status.

### Requirement: Human documentation is centrally owned
Shared Engine component responsibilities, source CODE map, offline build and test operations SHALL live in `documents/systems/data-platform/shared-engine/`. A duplicate explanatory README MUST NOT be recreated under source root once the legacy one is migrated.

#### Scenario: Legacy README removed
- **WHEN** `shared-data-engine/README.md` is retired
- **THEN** its valuable procedures and safety boundaries MUST remain in central BUILD-AND-TEST/README/CODE and active links MUST resolve.

### Requirement: Source and Fabric runtime claims remain separate
The documentation SHALL distinguish 0.1.3 source version, offline CI acceptance, Fabric Environment Published 0.1.3, isolated Spark Import, and still-unaccepted formal business Notebook FHIR/OMOP E2E and Gold COMMIT.

#### Scenario: Isolated 0.1.3 import succeeds
- **WHEN** independent Fabric Publish and temporary Notebook Import PASS are verified
- **THEN** those facts MAY be reported with exact Run evidence, while formal `nb_fhir_ingest`/Gold acceptance MUST NOT be implied.
