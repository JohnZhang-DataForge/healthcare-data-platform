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

The single-image Workflow SHALL default to `validate` without GHCR mutation. On Main, explicit `publish` SHALL publish a named candidate without changing latest; explicit `publish-latest` SHALL publish ONLY the selected image as latest after smoke, with an immutable Run tag and verified rollback snapshot. The optional `promote-tested` workflow SHALL still support later tested candidate releases.

#### Scenario: A DAG-only change is merged

- **GIVEN** an Airflow DAG or another source file changes on Main
- **WHEN** the commit is pushed without a manual image build request
- **THEN** neither the single-image nor the retained full eight-image Workflow SHALL build or publish any images because of that push

#### Scenario: A feature-branch publish is requested

- **GIVEN** a manual Workflow selection on a non-Main ref
- **WHEN** `publish`, `publish-latest`, or `promote-tested` is selected
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

### Requirement: Optional candidate promotion MUST preserve the tested digest

For the optional staged-release workflow, manual `promote-tested` SHALL require a valid release candidate tag (default `portal-v1.0`), exact `sha256` Digest, and a nonempty independent test evidence reference. The runner SHALL verify that the candidate tag resolves to the expected Digest immediately before publishing and SHALL NOT invoke a new Docker build for promotion.

#### Scenario: A candidate is published but not accepted

- **GIVEN** `portal-v1.0` is published with a recorded Digest but has no accepted business test
- **WHEN** only `validate`, `publish`, or `verify-candidate` is performed
- **THEN** the previously deployed `:latest` tag SHALL remain untouched

#### Scenario: An already tested candidate is promoted

- **GIVEN** a test evidence reference for the exact candidate Digest and no concurrent GitHub release
- **WHEN** `promote-tested` is deliberately dispatched and rechecks candidate Tag/Digest
- **THEN** the runner SHALL tag exactly that Digest as `:latest`, without building again, and report the actual pushed Digest

#### Scenario: Candidate tag drifted after testing

- **GIVEN** the tag `portal-v1.0` resolves to a different Digest than the tested value
- **WHEN** `promote-tested` is requested
- **THEN** GHCR `:latest` SHALL NOT be updated, and the workflow SHALL report a digest-drift failure

### Requirement: Image versioning SHALL NOT masquerade as Airflow DAG isolation

A business image candidate tag SHALL NOT be treated as evidence that GitSync-managed Airflow DAG source was separately tested. Portal P2's `new_only_omop_consumer.py` SHALL require separate isolation and real Provider/Marquez verification before a Portal E2E claim.

#### Scenario: OpenLineage is added only to the GitSync DAG source

- **GIVEN** the eight existing Dockerfiles do not package that DAG's OpenLineage opt-in
- **WHEN** any image receives a `portal-v1.0` tag
- **THEN** that tag by itself SHALL NOT qualify as P2 DAG/Provider or business lineage acceptance

### Requirement: Local development single-image latest SHALL be explicitly requested and reversible

Local development MAY use `publish-latest` after selected-image Clean Build and no-network Smoke. It MUST publish a unique SHA/Run tag, verify and preserve the previous latest Digest under an immutable rollback tag, then update only the selected package's `:latest` and verify Registry readback. PR/Main pushes MUST NOT auto-publish. No workflow in this change SHALL alter a running Pod, shared Airflow scheduler, or business database.

#### Scenario: Local portal-related image code needs an updated runtime

- **GIVEN** the user authorizes `publish-latest` for one of the eight images on Main, with no conflicting release
- **WHEN** the selected Docker build and smoke succeed and the previous latest is safely backed up
- **THEN** only the selected package's `:latest` SHALL be updated, leaving the seven siblings unchanged
- **AND** the new Digest, prior Digest and rollback tag SHALL be recorded for controlled rollback

#### Scenario: The previous latest cannot be read or backed up

- **GIVEN** the Registry lookup of previous latest or rollback backup fails
- **WHEN** `publish-latest` is requested
- **THEN** the workflow SHALL fail before replacing the existing `:latest`

#### Scenario: Portal P2 source is DAG-only

- **GIVEN** `new_only_omop_consumer.py` is delivered through GitSync instead of the eight image Dockerfiles
- **WHEN** Airflow/OpenLineage integration is updated
- **THEN** no image rebuild is necessary solely due to this DAG source change
- **AND** Provider/Transport and real Marquez Job/Run verification remain independent gates
