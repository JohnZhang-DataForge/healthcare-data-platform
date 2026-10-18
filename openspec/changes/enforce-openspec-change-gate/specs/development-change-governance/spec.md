## ADDED Requirements

### Requirement: Material changes require an OpenSpec association
The repository SHALL reject material pull requests that do not identify a valid active OpenSpec Change and an existing task, and SHALL require a task record update in the same pull request.

#### Scenario: Material source code change without an associated Change
- **GIVEN** a pull request changes a business or automation source path
- **WHEN** the OpenSpec Change Gate evaluates the pull request
- **THEN** the check fails if the associated active Change and task are absent

#### Scenario: Change exists but tasks are not synchronized
- **GIVEN** a material pull request identifies an existing active Change
- **WHEN** the pull request does not modify the associated tasks.md
- **THEN** the check fails

#### Scenario: Valid active Change and task
- **GIVEN** a material pull request identifies a valid active Change and existing task
- **WHEN** the pull request updates that Change's tasks.md
- **THEN** the static association check succeeds

### Requirement: Documentation-only exemptions are strictly scoped
The repository SHALL allow a declared docs-only exemption only for explicitly approved non-governance Markdown paths and SHALL reject mixed code or architectural changes using that exemption.

#### Scenario: Safe documentation-only exemption
- **GIVEN** a pull request declares OpenSpec-Exemption: docs-only
- **WHEN** all changed paths are within the restricted documentation allowlist
- **THEN** the exemption may pass without a Change

#### Scenario: Mixed code and documentation exemption
- **GIVEN** a pull request declares OpenSpec-Exemption: docs-only
- **WHEN** a source, workflow, architectural, governance, or protected document changes
- **THEN** the check fails

### Requirement: Archived Changes must be completed
The repository SHALL reject archival of a Change with incomplete tasks and SHALL preserve traceability to the previous active Change.

#### Scenario: Premature archive
- **GIVEN** a pull request moves an active Change into the archive
- **WHEN** tasks remain incomplete or the prior active Change cannot be found at PR base
- **THEN** the archive association check fails
