# Local DP Selective Image Rebuild

## ADDED Requirements

### Requirement: A single-image manual request SHALL target only one allowlisted package

The maintained single-image Workflow SHALL accept a fixed allowlist of the eight currently supported Local DP image identities and SHALL build only the chosen Dockerfile/context, without automatically rebuilding parents, siblings or children. Arbitrary image names, Dockerfile paths and Shell commands MUST be rejected.

#### Scenario: An operator selects the Landing processing runtime

- **GIVEN** a manual dispatch with `image=landing-processing-runtime`
- **WHEN** source validation and image build run
- **THEN** only `healthcare-data-platform-local-dp-landing-processing-v2` is built, using the explicitly resolved task004 runtime parent Digest
- **AND** the other seven images are neither rebuilt nor published

### Requirement: Publication SHALL be separately and explicitly authorized by operation

The Workflow MUST default to `operation=validate` (build and isolated smoke, no GHCR mutation). `publish` SHALL push only a unique SHA/Run/Attempt tag for the selected package, and `promote-latest` SHALL additionally retag only that same package as `:latest`. Publication MUST require a dispatch on the Main branch.

#### Scenario: A DAG-only change is merged

- **GIVEN** an Airflow DAG or another source file changes on Main
- **WHEN** the commit is pushed without a manual image build request
- **THEN** neither the single-image nor the retained full eight-image Workflow SHALL build or publish any images because of that push

#### Scenario: A feature-branch publish is requested

- **GIVEN** a manual Workflow selection on a non-Main ref
- **WHEN** `publish` or `promote-latest` is selected
- **THEN** validation SHALL fail before GHCR publishing

### Requirement: Child image parent SHALL be recorded and immutable for the build

For the three child images, the Workflow SHALL either accept a validated parent `sha256` digest or resolve the existing parent `:latest` tag to an immutable RepoDigest before building. The corresponding Base Image SHALL use the immutable ref, not a floating tag during build. This Workflow SHALL NOT implicitly publish/rebuild a parent or grant permission to change business runtime resources.

#### Scenario: A child image is selected without an explicit parent digest

- **GIVEN** the parent GHCR `:latest` tag is accessible
- **WHEN** a child image build begins
- **THEN** its parent RepoDigest is resolved and recorded before the Docker build
- **AND** failures to resolve a valid digest prevent publishing

### Requirement: Existing full eight-image release SHALL remain manual-only

The existing full image rebuild workflow SHALL no longer respond to normal PR or Main push changes. It MAY retain a separately initiated manual full rebuild/publish option but MUST NOT silently promote all eight images as part of an Airflow/OpenLineage merge.

#### Scenario: Portal P2 adds Airflow instrumentation

- **GIVEN** the Portal Airflow PR merges source-only OpenLineage opt-in
- **WHEN** Main is updated
- **THEN** the full eight-image workflow SHALL remain idle unless separately manually dispatched
