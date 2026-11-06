# Fabric Git Native Notebook Onboarding

## ADDED Requirements

### Requirement: Deploy new native Notebook definitions from reviewed Git only

Healthcare SHALL treat `main` as the single source for root-level `nb_*.Notebook` Native Items. A main Push modifying an Item's `.platform` or `notebook-content.py` MUST dispatch its immutable SHA to the trusted private Self-Runner; a PR event MUST NOT run the cloud deployment.

#### Scenario: A new native Notebook is merged to main
- **GIVEN** a reviewed, valid `nb_validation.Notebook/.platform` and `notebook-content.py` are introduced on main
- **WHEN** Healthcare Git Dispatch runs
- **THEN** the private updater SHALL receive the exact main SHA and independently validate the Fabric change before considering an update

### Requirement: Permit only exact Git-added Notebook identity

The Fabric updater MUST accept `remoteChange=Added` only for a Git Native Notebook whose source exists, logicalId is unique, PySpark metadata is valid, Environment refers to `env_healthcare`, and whose displayName does not already exist in the target Workspace. New Pipeline, Environment, deletion, local change, conflict, folder and unknown file changes MUST fail closed.

#### Scenario: Safe Git-added Notebook
- **GIVEN** Fabric Git Status contains an `Added` Notebook from the verified Git inventory and no local or conflicting change
- **WHEN** the updater performs preflight
- **THEN** it MAY issue exactly one non-retried `UpdateFromGit` with current remote/workspace head

#### Scenario: Existing item name or mixed unapproved change
- **GIVEN** the intended name is already present in Workspace or the update batch includes another unknown Item
- **WHEN** Git Status is inspected
- **THEN** the updater MUST stop before cloud writes; it MUST NOT override or delete that Item

### Requirement: Preserve existing business guards and independently verify results

The known `nb_fhir_ingest`, `pl_fhir_ingest` and `env_healthcare` identifiers, HALT and readback safety guards MUST remain protected. Newly created or later remote-only `Modified` Notebooks SHALL be validated against actual independent Fabric definitions and physical Item identities, including PySpark code and Environment binding; dispatch acceptance or UpdateFromGit HTTP 202 alone SHALL NOT count as deployment PASS. The updater SHALL NOT execute Notebook/Pipeline or publish the Environment.

#### Scenario: Live code is missing or has different environment
- **GIVEN** UpdateFromGit returned success but a Notebook definition loses code or resolves a different Environment
- **WHEN** post-update GetDefinition comparison executes
- **THEN** deployment SHALL NOT be declared PASS and any unknown live outcome MUST be preserved for read-only investigation

#### Scenario: Source-only offline tests succeed without cloud execution
- **GIVEN** GitHub Actions validates static Source/Status/readback mocks only
- **WHEN** PR CI completes
- **THEN** the Change SHALL be reported as implemented/CI-verified, not as live new Notebook creation E2E
