## ADDED Requirements

### Requirement: GitHub directory hierarchy must communicate functional ownership to humans
Every new maintainable component SHALL have a unique functional owner and descriptive, stable directory. New source dirs MUST NOT be named after an implementation task/step, sprint, test run, arbitrary environment or personal handoff. GitHub root navigation SHALL identify exactly where source, machine deploy assets, human docs, tests, adopted specs, active changes and archived work live.

#### Scenario: Maintainer opens the code repository
- **WHEN** a reader opens the root README without reading OpenSpec files
- **THEN** they can follow a concise system directory map to one authoritative module README/CODE, including an explicit indicator of retained operational legacy paths.

### Requirement: Operational legacy moves must preserve proven runtime entrypoints
Already accepted Local DP task-named module locations SHALL only be relocated following exact dependency and SHA/contract inventory, merged consumer compatibility and independently accepted deployment/runtime results as applicable. This specification MUST NOT authorize risky massive renames solely for cosmetic goals.

#### Scenario: Agent proposes moving task003 scripts
- **WHEN** a source path is referenced by an Airflow DAG, image, cross-repo script or immutable workflow
- **THEN** preserve the existing contract until the consumer is compatibly migrated, tested and read back; do not silently duplicate or delete production source.

### Requirement: Current documentation and historical evidence are separated
Human README/CODE shall show current role/navigation concisely; dated chronology belongs in historical evidence/archived OpenSpec with immutable links. Source area SHALL only retain scoped AGENTS/approved machine-readable assets and agreed legacy exceptions.

#### Scenario: Source README duplicates centralized CODE
- **WHEN** a source-area README has unique setup/safety notes
- **THEN** those notes are preserved under the appropriate `documents/systems/` owner before source README is removed and all active links pass checks.

### Requirement: Completed changes exit the active OpenSpec directory only with real acceptance
Changes with zero open checkboxes are candidates, not proof, of completed work. Only accepted changes with recorded main/Run/consumer evidence SHALL move to `changes/archive/`; remaining HOLD must remain visible and unarchived.

#### Scenario: A task checklist is fully checked but a runtime hold remains
- **WHEN** the historical task narrative records an unresolved launch/runtime gate
- **THEN** the Change SHALL not be marked wholly accepted or moved solely based on checkbox counts.

### Requirement: New source directories use a trusted component naming boundary
A trusted, default-branch-only CI policy SHALL reject newly added Task/Step-numbered source, quality and Workflow paths across all four platform source roots. The PR checkout MUST remain passive Git data, and existing historical source paths SHALL remain operable. Enforcement is not accepted until the check is Required and an invalid, non-Draft PR is blocked.

#### Scenario: Agent adds a new Condition module
- **WHEN** the candidate adds `local-data-platform/apps/task005/condition.py` or `shared-data-engine/src/healthcare_data_engine/step04.py`
- **THEN** the trusted checker MUST fail before merge, regardless of PR-modified code or naming tests; valid `apps/omop_writer/condition.py` may pass ordinary component CODE-map/OpenSpec checks.

### Requirement: New production sources do not acquire untracked legacy Task dependencies
New business source files SHALL NOT directly import task-numbered Python modules or hardcode task-numbered legacy source file paths. Existing code and fixed runtime identities (for example `etl.task004_batch_ledger`, GHCR image names, K8s service accounts and approved Batch identities) SHALL remain untouched until the independent Clean Slate migration is accepted.

#### Scenario: New domain code tries to import an old Task module
- **WHEN** newly added `spark/apps/condition/loader.py` imports `apps.task004` or hardcodes `apps/task003/`
- **THEN** the trusted checker MUST reject the new direct dependency; the owner must design a semantic interface and record exact replacement/compatibility plan under Active OpenSpec rather than silently expanding old Task reachability.
